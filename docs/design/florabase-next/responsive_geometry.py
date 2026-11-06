"""Florabase Next: real-browser responsive geometry regression (M8 QA P1/P2).

Measures actual layout in Chromium under both scrollbar models, because jsdom has no
layout and Playwright's headless default (--hide-scrollbars) hides classic scrollbars:

- classic: desktop Chromium with real 15px classic scrollbars (the layout viewport,
  documentElement.clientWidth, is narrower than window.innerWidth);
- overlay: mobile emulation with overlay scrollbars (clientWidth == innerWidth).

The mode is asserted on a tall page, so a pass can never come from the wrong condition.

Checks per page and viewport:
- no page-wide horizontal overflow (documentElement.scrollWidth <= clientWidth);
- every visible control lies inside the layout viewport or inside an intentional
  horizontal scroller (reachability);
- the document's scroll-padding equals the geometry actually covered by the pinned
  phone header and bottom bar (measured after scrolling, not assumed);
- keyboard focus walking forward and back never leaves a focused control under them;
- Schedule Month: the selected day's heading takes focus and is visible below the
  header and above the bottom bar, the document (not an inner element) scrolls, and
  Escape returns focus to the visible originating day.

Runs inside the pinned Playwright image, against UAT Preview, with the synthetic fixture
owner only:

    docker run --rm --network host --ipc host \
      -v "$PWD/docs/design/florabase-next:/work:ro" -v "$OUT:/out" \
      -e GEOMETRY_ORIGIN=http://localhost:15174 \
      -e GEOMETRY_LOGIN=preview -e GEOMETRY_PASSWORD=preview \
      mcr.microsoft.com/playwright/python:v1.48.0-noble python /work/responsive_geometry.py

Exits 1 when any check fails; writes geometry.json (and screenshots on Schedule) to /out.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys
from typing import Any

from playwright.sync_api import Page, sync_playwright

ORIGIN = os.environ.get("GEOMETRY_ORIGIN", "http://localhost:15174").rstrip("/")
LOGIN = os.environ["GEOMETRY_LOGIN"]
PASSWORD = os.environ["GEOMETRY_PASSWORD"]
OUT = pathlib.Path(os.environ.get("GEOMETRY_OUT", "/out"))
LABEL = os.environ.get("GEOMETRY_LABEL", "geometry")
APPEARANCE = os.environ.get("GEOMETRY_APPEARANCE", "light")
PANEL_KEY = "florabase.workbench.panel-collapsed.v1"

# (name, width, height, device scale factor). Zoom rows are 1280x800 at 200% and 400%.
PHONE = [
    ("390", 390, 844, 1),
    ("320", 320, 640, 1),
    ("zoom200", 640, 400, 2),
    ("zoom400", 320, 200, 4),
]
DESKTOP = [("desktop-1440", 1440, 844, 1), ("tablet-1024", 1024, 844, 1)]

ROUTES = [
    ("schedule-month", "/schedule?view=calendar&month=2026-11"),
    ("settings-theme", "/settings"),
    ("import-export", "/import-export"),
    ("labels", "/labels"),
    ("history", "/history"),
    ("plants", "/plants"),
    ("plant-detail", "/plants/{plant}"),
    ("identity-detail", "/identities/{identity}"),
]

MEASURE = """() => {
  const html = document.documentElement;
  const header = document.querySelector('.wb-sidebar');
  const bar = document.querySelector('.wb-bottombar');
  const rect = (e) => { if (!e) return null; const r = e.getBoundingClientRect();
    return {top: r.top, bottom: r.bottom, left: r.left, right: r.right, width: r.width, height: r.height}; };
  const pinnedTop = (() => {
    if (!header) return 0;
    const s = getComputedStyle(header);
    if (s.position !== 'sticky' && s.position !== 'fixed') return 0;
    const r = header.getBoundingClientRect();
    // Pinned across the top: starts at the top edge, spans the layout viewport, short.
    return r.top <= 0.5 && r.left <= 0.5 && r.right >= html.clientWidth - 0.5 && r.height < html.clientHeight / 2 ? r.bottom : 0;
  })();
  const pinnedBottom = (() => {
    if (!bar) return 0;
    const s = getComputedStyle(bar);
    if (s.position !== 'fixed' || s.display === 'none') return 0;
    const r = bar.getBoundingClientRect();
    return r.height > 0 ? Math.max(0, html.clientHeight - r.top) : 0;
  })();
  const scroller = (e) => { for (let p = e.parentElement; p; p = p.parentElement) {
      const o = getComputedStyle(p).overflowX; if ((o === 'auto' || o === 'scroll') && p !== html && p !== document.body) return p; }
    return null; };
  const unreachable = [];
  for (const e of document.querySelectorAll('a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])')) {
    const r = e.getBoundingClientRect();
    if (r.width === 0 || r.height === 0 || getComputedStyle(e).visibility === 'hidden') continue;
    if (e.closest('dialog:not([open]), [hidden], [inert]')) continue;
    if (r.right <= html.clientWidth + 0.5 && r.left >= -0.5) continue;
    const s = scroller(e);
    if (s) { const sr = s.getBoundingClientRect(); if (sr.right <= html.clientWidth + 0.5 && sr.left >= -0.5) continue; }
    unreachable.push(`${e.tagName.toLowerCase()} "${(e.getAttribute('aria-label') || e.textContent || '').trim().slice(0, 40)}" ${Math.round(r.left)}..${Math.round(r.right)}`);
  }
  const vScrolled = [...document.querySelectorAll('body *')].filter((e) => e.scrollTop > 0 && getComputedStyle(e).overflowY !== 'visible').map((e) => e.tagName.toLowerCase() + '.' + String(e.className).split(' ')[0]);
  const cs = getComputedStyle(html);
  return {
    innerWidth, clientWidth: html.clientWidth, scrollWidth: html.scrollWidth,
    innerHeight, clientHeight: html.clientHeight, scrollHeight: html.scrollHeight,
    scrollbar: innerWidth - html.clientWidth,
    scrollY, pinnedTop, pinnedBottom,
    paddingTop: parseFloat(cs.scrollPaddingTop) || 0, paddingBottom: parseFloat(cs.scrollPaddingBottom) || 0,
    header: rect(header), bar: rect(bar), unreachable, vScrolled,
  };
}"""

# The focused element's visible box: its border box clipped by every scrolling or clipping
# ancestor (a bounded directory list, for example). A part hidden by its own scroller is
# not what a pinned bar covers; any visible part under a pinned bar still fails.
ACTIVE = """() => {
  const a = document.activeElement;
  if (!a || a === document.body) return null;
  const r = a.getBoundingClientRect();
  let top = r.top, bottom = r.bottom;
  for (let p = a.parentElement; p && p !== document.body; p = p.parentElement) {
    const o = getComputedStyle(p).overflowY;
    if (o === 'visible') continue;
    const pr = p.getBoundingClientRect();
    top = Math.max(top, pr.top + p.clientTop);
    bottom = Math.min(bottom, pr.top + p.clientTop + p.clientHeight);
  }
  const inShell = Boolean(a.closest('.wb-sidebar, .wb-bottombar, dialog'));
  return {name: (a.getAttribute('aria-label') || a.textContent || a.tagName).trim().slice(0, 50), top, bottom, height: Math.max(0, bottom - top), clipped: top > r.top + 0.5 || bottom < r.bottom - 0.5, inShell};
}"""


def login(context: Any) -> None:
    response = context.request.post(
        f"{ORIGIN}/api/v1/auth/login",
        data={"login_name": LOGIN, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    if not response.ok:
        raise SystemExit(f"login failed: {response.status}")


def ids(context: Any) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, path in (("plant", "/api/v1/plants"), ("identity", "/api/v1/botanical-identities")):
        payload = context.request.get(f"{ORIGIN}{path}?limit=1").json()
        items = payload.get("items", payload) if isinstance(payload, dict) else payload
        if items:
            out[key] = str(items[0]["id"])
    return out


def settle(page: Page, ms: int = 700) -> None:
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(ms)


def obscured(page: Page) -> dict[str, Any]:
    """Measures pinned geometry after scrolling, so a sticky header shows as pinned."""
    # Halfway down (at most 240px): at the very end of a short page a sticky header can be
    # pushed up by the end of its containing block, which would under-measure it.
    page.evaluate(
        "window.scrollTo(0, Math.min(240, (document.documentElement.scrollHeight - document.documentElement.clientHeight) / 2))"
    )
    page.wait_for_timeout(150)
    after = page.evaluate(MEASURE)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(100)
    return after


def walk_focus(page: Page, top: float, bottom_edge: float, steps: int = 25) -> list[str]:
    """Tabs forward then back; reports focused page controls left under pinned bars."""
    issues: list[str] = []
    page.evaluate("document.activeElement?.blur(); window.scrollTo(0, 0)")
    for key in ["Tab"] * steps + ["Shift+Tab"] * steps:
        page.keyboard.press(key)
        page.wait_for_timeout(60)
        a = page.evaluate(ACTIVE)
        if not a or a["inShell"] or a["height"] == 0 or a["height"] > bottom_edge - top:
            continue
        # 1.5px tolerance for sub-pixel layout; anything more is a real obstruction.
        if a["top"] < top - 1.5 or a["bottom"] > bottom_edge + 1.5:
            issues.append(f'{key} "{a["name"]}" {a["top"]:.1f}..{a["bottom"]:.1f} (visible {top:.1f}..{bottom_edge:.1f})')
    return issues


def schedule_focus(page: Page, shot: str) -> dict[str, Any]:
    day = page.get_by_role("button", name=re.compile(r"^Wednesday,? 4 November 2026"))
    day.wait_for()
    page.evaluate("window.scrollTo(0, 0)")
    day.focus()
    page.keyboard.press("Enter")
    page.wait_for_timeout(900)
    m = page.evaluate(MEASURE)
    heading = page.evaluate(ACTIVE)
    page.screenshot(path=str(OUT / f"{shot}-open.png"))
    top = m["pinnedTop"]
    bottom_edge = m["clientHeight"] - m["pinnedBottom"]
    result: dict[str, Any] = {"open": m, "focused": heading}
    failures = []
    if not heading or not re.match(r"^Wednesday,? 4 November 2026$", heading["name"]):
        failures.append(f"heading not focused: {heading}")
    elif heading["top"] < top - 1.5 or heading["bottom"] > bottom_edge + 1.5:
        failures.append(f"heading {round(heading['top'])}..{round(heading['bottom'])} outside visible {round(top)}..{round(bottom_edge)}")
    if m["scrollY"] <= 0 and m["scrollHeight"] > m["clientHeight"]:
        failures.append("document did not scroll to the panel")
    if m["vScrolled"]:
        failures.append(f"inner elements scrolled instead of the document: {m['vScrolled']}")
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    back = page.evaluate(ACTIVE)
    m2 = page.evaluate(MEASURE)
    page.screenshot(path=str(OUT / f"{shot}-escape.png"))
    result["escape"] = back
    if not back or not back["name"].startswith("Wednesday"):
        failures.append(f"Escape did not restore the day: {back}")
    elif back["top"] < m2["pinnedTop"] - 1.5 or back["bottom"] > m2["clientHeight"] - m2["pinnedBottom"] + 1.5:
        failures.append(f"restored day hidden: {round(back['top'])}..{round(back['bottom'])}")
    result["failures"] = failures
    return result


def run_case(pw: Any, mode: str, vp: tuple[str, int, int, int], collapsed: bool | None) -> list[dict[str, Any]]:
    name, width, height, scale = vp
    classic = mode == "classic"
    browser = pw.chromium.launch(
        headless=True,
        ignore_default_args=["--hide-scrollbars"] if classic else None,
    )
    context = browser.new_context(
        viewport={"width": width, "height": height},
        device_scale_factor=scale,
        is_mobile=not classic,
        has_touch=not classic,
    )
    pref = json.dumps({"version": 1, "palette": "field-ledger", "appearance": APPEARANCE})
    script = f"localStorage.setItem('florabase.appearance.v1', {json.dumps(pref)});"
    if collapsed is not None:
        script += f"localStorage.setItem('{PANEL_KEY}', '{str(collapsed).lower()}');"
    context.add_init_script(script)
    login(context)
    resolved = ids(context)
    page = context.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    rows = []
    case = f"{mode}/{name}" + ("" if collapsed is None else f"/{'collapsed' if collapsed else 'expanded'}")
    for key, route in ROUTES:
        url = route.format(**resolved)
        page.goto(f"{ORIGIN}/#{url}")
        settle(page)
        m = page.evaluate(MEASURE)
        pinned = obscured(page)
        failures = []
        if m["scrollWidth"] > m["clientWidth"]:
            failures.append(f"page overflow {m['scrollWidth'] - m['clientWidth']}px")
        if m["unreachable"]:
            failures.append(f"controls outside the viewport: {m['unreachable'][:4]}")
        header_height = (pinned["header"] or {}).get("height", 0)
        bar_height = (pinned["bar"] or {}).get("height", 0)
        for side, want, have, ceiling in (
            ("top", pinned["pinnedTop"], pinned["paddingTop"], header_height if pinned["pinnedTop"] else 0),
            ("bottom", pinned["pinnedBottom"], pinned["paddingBottom"], bar_height if pinned["pinnedBottom"] else 0),
        ):
            # The padding must cover what is pinned, and never exceed the pinned bar itself.
            if have < want - 1 or have > ceiling + 1:
                failures.append(f"scroll-padding-{side} {have}px but pinned {side} covers {want:.1f}px")
        if name in ("390", "320", "desktop-1440"):
            issues = walk_focus(page, pinned["pinnedTop"], pinned["clientHeight"] - pinned["pinnedBottom"])
            if issues:
                failures.append(f"focused controls under pinned bars: {issues[:3]}")
        row: dict[str, Any] = {"case": case, "page": key, "geometry": m, "pinned": pinned, "failures": failures}
        if key == "schedule-month" and not name.startswith("desktop") and not name.startswith("tablet"):
            page.goto(f"{ORIGIN}/#{url}")
            settle(page)
            sched = schedule_focus(page, f"{LABEL}-{mode}-{name}-schedule")
            row["schedule"] = sched
            failures.extend(sched["failures"])
        if key == "schedule-month":
            # Mode guard: Schedule Month is taller than every viewport here.
            if classic and m["scrollbar"] <= 0:
                failures.append("classic scrollbars not active (scrollbar width 0)")
            if not classic and m["scrollbar"] != 0:
                failures.append(f"overlay scrollbars not active (scrollbar width {m['scrollbar']})")
        rows.append(row)
    if errors:
        rows.append({"case": case, "page": "*", "failures": [f"console errors: {errors[:3]}"]})
    browser.close()
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    with sync_playwright() as pw:
        for mode in ("classic", "overlay"):
            for vp in PHONE:
                rows += run_case(pw, mode, vp, None)
        for vp in DESKTOP:
            for collapsed in (False, True):
                rows += run_case(pw, "classic", vp, collapsed)
    (OUT / f"{LABEL}.json").write_text(json.dumps(rows, indent=1) + "\n")
    failed = [r for r in rows if r["failures"]]
    for r in rows:
        g = r.get("geometry") or {}
        p = r.get("pinned") or {}
        print(
            f"{'FAIL' if r['failures'] else 'ok  '} {r['case']:28} {r['page']:16} "
            f"inner={g.get('innerWidth')} client={g.get('clientWidth')} scroll={g.get('scrollWidth')} "
            f"pinned={round(p.get('pinnedTop', 0))}/{round(p.get('pinnedBottom', 0))} "
            f"padding={p.get('paddingTop')}/{p.get('paddingBottom')}"
            + (f"  -> {'; '.join(r['failures'])}" if r["failures"] else "")
        )
    print(f"{len(rows) - len(failed)}/{len(rows)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
