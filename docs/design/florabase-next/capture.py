"""Florabase Next: paired screenshot capture for a running Florabase instance.

Runs inside the pinned official Playwright image so nothing is installed on the host
or in the repository:

    docker run --rm --network host --ipc host \
      -v "$PWD/docs/design/florabase-next:/work:ro" -v "$OUT:/out" \
      -e CAPTURE_ORIGIN=http://localhost:15174 -e CAPTURE_LABEL=main-d94f275 \
      -e CAPTURE_LOGIN=preview -e CAPTURE_PASSWORD=preview \
      mcr.microsoft.com/playwright/python:v1.48.0-noble python /work/capture.py

Credentials are only ever the synthetic UAT/Review fixture owner. Requests to any
other origin (map tiles, external evidence) are answered locally with an empty
response and listed in the manifest, so captures are deterministic and offline.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import time
from typing import Any

from playwright.sync_api import Page, Route, sync_playwright

ORIGIN = os.environ.get("CAPTURE_ORIGIN", "http://localhost:15174").rstrip("/")
LABEL = os.environ["CAPTURE_LABEL"]
LOGIN = os.environ["CAPTURE_LOGIN"]
PASSWORD = os.environ["CAPTURE_PASSWORD"]
OUT = pathlib.Path(os.environ.get("CAPTURE_OUT", "/out")) / LABEL
SETTLE_MS = int(os.environ.get("CAPTURE_SETTLE_MS", "900"))
# Optional filters for representative milestone captures (comma lists); default is everything.
ONLY_ROUTES = {k for k in os.environ.get("CAPTURE_ROUTES", "").split(",") if k}
ONLY_VIEWPORTS = {k for k in os.environ.get("CAPTURE_VIEWPORTS", "").split(",") if k}
FULL_PAGE = os.environ.get("CAPTURE_FULL_PAGE", "1") == "1"
# Optional browser-local theme preference, written before any page script runs.
PALETTE = os.environ.get("CAPTURE_PALETTE")
APPEARANCE = os.environ.get("CAPTURE_APPEARANCE", "light")

# Measures rendered controls against the agreed targets (D3): 40px pointer, 44px touch.
PROBE = """(target) => {
  const sel = 'button, .button-link, input:not([type=checkbox]):not([type=radio]):not([type=hidden]), select, textarea, [role=tab]';
  const seen = [...document.querySelectorAll(sel)].filter((el) => {
    const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && !el.closest('.leaflet-container');
  });
  const heights = seen.map((el) => Math.round(el.getBoundingClientRect().height * 10) / 10);
  const small = seen.filter((el) => el.getBoundingClientRect().height < target - 0.5)
    .map((el) => (el.tagName.toLowerCase() + '.' + [...el.classList].slice(0, 2).join('.')).slice(0, 60));
  const root = getComputedStyle(document.documentElement);
  return {
    palette: document.documentElement.dataset.palette || null,
    appearance: document.documentElement.dataset.appearance || null,
    body_font: getComputedStyle(document.body).fontFamily.split(',')[0],
    control_height_token: root.getPropertyValue('--control-height').trim(),
    controls: seen.length, min_height: heights.length ? Math.min(...heights) : null,
    below_target: small.length, below_target_kinds: [...new Set(small)].slice(0, 8),
  };
}"""

VIEWPORTS = {
    "desktop": {"viewport": {"width": 1440, "height": 844}},
    "tablet": {"viewport": {"width": 1024, "height": 844}, "has_touch": True},
    "mobile": {"viewport": {"width": 390, "height": 844}, "has_touch": True, "is_mobile": True},
}

# (key, area, hash route). "{x}" placeholders resolve to the first record of a list endpoint.
ROUTES: list[tuple[str, str, str]] = [
    ("dashboard", "Dashboard", "/dashboard"),
    ("dashboard-search", "Navigation", "/dashboard?q=basil"),
    ("seeds", "Seeds", "/seeds"),
    ("seed-lot-detail", "Details", "/seeds/{seed_lot}"),
    ("seed-lot-create", "Forms", "/seeds?action=create"),
    ("sowings", "Sowings", "/sowings"),
    ("sowing-detail", "Details", "/sowings/{sowing}"),
    ("plants", "Plants", "/plants"),
    ("plant-groups", "Plants", "/plants?type=group"),
    ("plant-detail", "Details", "/plants/{plant}"),
    ("plant-lineage", "Details", "/plants/{plant}?tab=lineage"),
    ("plant-group-detail", "Details", "/plant-groups/{plant_group}"),
    ("plant-create", "Forms", "/plants?action=create"),
    ("harvests", "Collection", "/harvests"),
    ("harvest-detail", "Details", "/harvests/{harvest}"),
    ("stored-material", "Collection", "/harvests?tab=stored-material"),
    ("locations", "Collection", "/locations"),
    ("location-detail", "Details", "/locations/{location}"),
    ("journal", "Activity", "/events"),
    ("history", "Activity", "/history"),
    ("schedule", "Activity", "/schedule"),
    ("schedule-calendar", "Activity", "/schedule?view=calendar"),
    ("identities", "Explore", "/identities"),
    ("identity-detail", "Details", "/identities/{identity}"),
    ("taxonomy", "Explore", "/taxonomy"),
    ("media", "Explore", "/media"),
    ("geography", "Explore", "/geography"),
    ("collection-origins", "Explore", "/map"),
    ("species-distribution", "Explore", "/species-distribution"),
    ("native-ranges", "Explore", "/native-ranges"),
    ("suppliers", "Sourcing", "/suppliers"),
    ("supplier-detail", "Details", "/suppliers/{supplier}"),
    ("orders", "Sourcing", "/orders"),
    ("order-detail", "Details", "/orders/{order}"),
    ("settings", "Settings", "/settings"),
    ("labels", "Settings", "/labels"),
    ("import-export", "Settings", "/import-export"),
]

LISTS = {
    "seed_lot": "/api/v1/seed-lots",
    "sowing": "/api/v1/sowings",
    "plant": "/api/v1/plants",
    "plant_group": "/api/v1/plant-groups",
    "harvest": "/api/v1/harvests",
    "location": "/api/v1/locations",
    "identity": "/api/v1/botanical-identities",
    "supplier": "/api/v1/suppliers",
    "order": "/api/v1/orders",
}


def first_id(payload: Any) -> str | None:
    items = payload
    if isinstance(payload, dict):
        for key in ("items", "results", "records", "data"):
            if isinstance(payload.get(key), list):
                items = payload[key]
                break
    if isinstance(items, list) and items and isinstance(items[0], dict):
        value = items[0].get("id")
        return str(value) if value else None
    return None


def settle(page: Page) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    page.wait_for_timeout(SETTLE_MS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    blocked: set[str] = set()
    entries: list[dict[str, Any]] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ids: dict[str, str | None] = {}
        for vp_name, vp in VIEWPORTS.items():
            if ONLY_VIEWPORTS and vp_name not in ONLY_VIEWPORTS:
                continue
            context = browser.new_context(device_scale_factor=1, reduced_motion="reduce", **vp)
            if PALETTE:
                pref = json.dumps({"version": 1, "palette": PALETTE, "appearance": APPEARANCE})
                context.add_init_script(
                    f"localStorage.setItem('florabase.appearance.v1', {json.dumps(pref)});"
                )

            def route_external(route: Route) -> None:
                url = route.request.url
                if url.startswith(ORIGIN):
                    route.continue_()
                else:
                    blocked.add(url.split("/")[2])
                    route.fulfill(status=204, body="")

            context.route("**/*", route_external)
            login = context.request.post(
                f"{ORIGIN}/api/v1/auth/login",
                headers={"Origin": ORIGIN},
                data={"login_name": LOGIN, "password": PASSWORD},
            )
            if not login.ok:
                raise SystemExit(f"login failed: {login.status}")
            if not ids:
                for key, path in LISTS.items():
                    response = context.request.get(f"{ORIGIN}{path}")
                    ids[key] = first_id(response.json()) if response.ok else None
            page = context.new_page()
            errors: list[str] = []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            for key, area, route in ROUTES:
                if ONLY_ROUTES and key not in ONLY_ROUTES:
                    continue
                target = route
                missing = [k for k in ids if "{" + k + "}" in target and not ids[k]]
                if missing:
                    entries.append({"key": key, "viewport": vp_name, "skipped": f"no {missing[0]}"})
                    continue
                for k, v in ids.items():
                    target = target.replace("{" + k + "}", v or "")
                errors.clear()
                started = time.monotonic()
                page.goto(f"{ORIGIN}/#{target}")
                settle(page)
                elapsed = round((time.monotonic() - started) * 1000)
                probe = page.evaluate(PROBE, 40 if vp_name == "desktop" else 44)
                shots = [("", False)]
                if vp_name == "desktop" and FULL_PAGE:
                    shots.append(("-full", True))
                for suffix, full in shots:
                    file = OUT / f"{key}-{vp_name}{suffix}.png"
                    page.screenshot(path=str(file), full_page=full)
                    data = file.read_bytes()
                    entries.append({
                        "key": key + suffix, "area": area, "route": "#" + route,
                        "viewport": vp_name, "file": file.name,
                        "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                        "title": page.title(), "settled_ms": elapsed,
                        "console_errors": sorted(set(errors)),
                        "probe": probe,
                    })
            if vp_name == "desktop" and (not ONLY_ROUTES or "focus-keyboard" in ONLY_ROUTES):
                page.goto(f"{ORIGIN}/#/seeds")
                settle(page)
                page.locator("main").first.focus() if page.locator("main[tabindex]").count() else None
                for _ in range(int(os.environ.get("CAPTURE_TABS", "6"))):
                    page.keyboard.press("Tab")
                page.wait_for_timeout(300)
                focused = page.evaluate(
                    "() => { const e = document.activeElement; return e ? (e.tagName.toLowerCase() + ' ' + (e.getAttribute('aria-label') || e.textContent || '').trim().slice(0, 40)) : null; }"
                )
                file = OUT / "focus-keyboard-desktop.png"
                page.screenshot(path=str(file))
                data = file.read_bytes()
                entries.append({"key": "focus-keyboard", "area": "Accessibility", "route": "#/seeds + Tab",
                                "viewport": vp_name, "file": file.name, "focused": focused,
                                "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
            if vp_name == "mobile" and (not ONLY_ROUTES or "navigation-more" in ONLY_ROUTES):
                page.goto(f"{ORIGIN}/#/dashboard")
                settle(page)
                more = page.get_by_role("navigation", name="Mobile primary navigation").get_by_role("button", name="More")
                if more.count():
                    more.first.click()
                    page.wait_for_timeout(SETTLE_MS)
                    file = OUT / "navigation-more-mobile.png"
                    page.screenshot(path=str(file))
                    data = file.read_bytes()
                    entries.append({"key": "navigation-more", "area": "Navigation", "route": "#/dashboard + More",
                                    "viewport": vp_name, "file": file.name,
                                    "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
            context.close()
        browser.close()
    manifest = {
        "label": LABEL, "origin": ORIGIN,
        "theme_preference": {"palette": PALETTE, "appearance": APPEARANCE} if PALETTE else None, "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "viewports": {k: v["viewport"] for k, v in VIEWPORTS.items()},
        "blocked_external_hosts": sorted(blocked), "resolved_ids": ids, "entries": entries,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{len([e for e in entries if 'file' in e])} images -> {OUT}")


if __name__ == "__main__":
    main()
