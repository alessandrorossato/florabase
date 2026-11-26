#!/usr/bin/env python3
"""Deterministic Android launcher icon, adaptive icon, and splash generator.

Derives all Android branding assets from the repository's canonical PWA icons:
  - frontend/public/icons/florabase-maskable-512.png (cream #f8f5e7 background)
  - frontend/public/icons/florabase-512.png (transparent RGBA emblem)

Design tokens (approved in MOBILE-003):
  - Adaptive icon background: #f8f5e7 (matching florabase-maskable-512.png)
  - Theme & splash background: #153a2c (matching frontend/public/manifest.webmanifest)

Outputs are byte-for-byte deterministic across repeated runs (empty PngInfo, fixed
compression settings, no timestamps or random metadata).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw
from PIL.PngImagePlugin import PngInfo

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RES_DIR = ROOT / "mobile" / "android" / "app" / "src" / "main" / "res"

ICON_BG_HEX = "#F8F5E7"
ICON_BG_RGB = (0xF8, 0xF5, 0xE7)
THEME_HEX = "#153A2C"
THEME_DARK_HEX = "#0E291F"
THEME_ACCENT_HEX = "#5E8C45"
THEME_RGB = (0x15, 0x3A, 0x2C)

LEGACY_ICON_SIZES: dict[str, int] = {
    "mdpi": 48,
    "hdpi": 72,
    "xhdpi": 96,
    "xxhdpi": 144,
    "xxxhdpi": 192,
}

ADAPTIVE_FG_SIZES: dict[str, int] = {
    "mdpi": 108,
    "hdpi": 162,
    "xhdpi": 216,
    "xxhdpi": 324,
    "xxxhdpi": 432,
}

SPLASH_SIZES: dict[str, tuple[int, int]] = {
    "drawable": (480, 320),
    "drawable-port-mdpi": (320, 480),
    "drawable-port-hdpi": (480, 800),
    "drawable-port-xhdpi": (720, 1280),
    "drawable-port-xxhdpi": (960, 1600),
    "drawable-port-xxxhdpi": (1280, 1920),
    "drawable-land-mdpi": (480, 320),
    "drawable-land-hdpi": (800, 480),
    "drawable-land-xhdpi": (1280, 720),
    "drawable-land-xxhdpi": (1600, 960),
    "drawable-land-xxxhdpi": (1920, 1280),
}

RESAMPLE = Image.Resampling.LANCZOS


def _save_deterministic_png(image: Image.Image, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    # Empty PngInfo + fixed compress_level + optimize=False guarantees byte-for-byte
    # reproducible output across repeated runs.
    image.save(
        target,
        format="PNG",
        pnginfo=PngInfo(),
        optimize=False,
        compress_level=9,
    )


def _circle_mask(size: int) -> Image.Image:
    # Supersample 4x for clean antialiased circular edges.
    hi = size * 4
    mask = Image.new("L", (hi, hi), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, hi - 1, hi - 1), fill=255)
    return mask.resize((size, size), RESAMPLE)


def _rounded_square_mask(size: int, radius_ratio: float = 0.22) -> Image.Image:
    hi = size * 4
    radius = round(hi * radius_ratio)
    mask = Image.new("L", (hi, hi), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, hi - 1, hi - 1), radius=radius, fill=255)
    return mask.resize((size, size), RESAMPLE)


def _render_adaptive_foreground(transparent_emblem: Image.Image, size: int) -> Image.Image:
    # Android adaptive icon safe zone is the inner 66/108 (~61.1%) diameter.
    # Sizing the transparent emblem to ~58% keeps generous breathing room inside
    # circle, squircle, and rounded-square launcher masks without clipping.
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    emblem_px = max(1, round(size * 0.58))
    resized = transparent_emblem.resize((emblem_px, emblem_px), RESAMPLE)
    offset = (size - emblem_px) // 2
    canvas.alpha_composite(resized, (offset, offset))
    return canvas


def _render_legacy_launcher(
    maskable_icon: Image.Image, size: int, *, round_mask: bool
) -> Image.Image:
    base = maskable_icon.convert("RGBA").resize((size, size), RESAMPLE)
    mask = _circle_mask(size) if round_mask else _rounded_square_mask(size)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(base, (0, 0), mask)
    return out


def _render_splash(maskable_icon: Image.Image, width: int, height: int) -> Image.Image:
    canvas = Image.new("RGBA", (width, height), (*THEME_RGB, 255))
    badge_size = max(72, round(min(width, height) * 0.34))
    badge = _render_legacy_launcher(maskable_icon, badge_size, round_mask=True)
    x = (width - badge_size) // 2
    y = (height - badge_size) // 2
    canvas.alpha_composite(badge, (x, y))
    return canvas.convert("RGB")


def _write_text_lf(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content.encode("utf-8"))


def generate_assets(root: Path = ROOT, res_dir: Path = DEFAULT_RES_DIR) -> list[Path]:
    icons_dir = root / "frontend" / "public" / "icons"
    maskable_src = icons_dir / "florabase-maskable-512.png"
    emblem_src = icons_dir / "florabase-512.png"
    if not maskable_src.is_file():
        raise FileNotFoundError(f"Missing source maskable icon: {maskable_src}")
    if not emblem_src.is_file():
        raise FileNotFoundError(f"Missing source emblem icon: {emblem_src}")

    maskable_icon = Image.open(maskable_src).convert("RGBA")
    transparent_emblem = Image.open(emblem_src).convert("RGBA")

    written: list[Path] = []

    for density, size in LEGACY_ICON_SIZES.items():
        mipmap_dir = res_dir / f"mipmap-{density}"
        launcher = mipmap_dir / "ic_launcher.png"
        round_launcher = mipmap_dir / "ic_launcher_round.png"
        _save_deterministic_png(
            _render_legacy_launcher(maskable_icon, size, round_mask=False), launcher
        )
        _save_deterministic_png(
            _render_legacy_launcher(maskable_icon, size, round_mask=True), round_launcher
        )
        written.extend([launcher, round_launcher])

    for density, size in ADAPTIVE_FG_SIZES.items():
        mipmap_dir = res_dir / f"mipmap-{density}"
        fg = mipmap_dir / "ic_launcher_foreground.png"
        _save_deterministic_png(_render_adaptive_foreground(transparent_emblem, size), fg)
        written.append(fg)

    for folder, (width, height) in SPLASH_SIZES.items():
        splash = res_dir / folder / "splash.png"
        _save_deterministic_png(_render_splash(maskable_icon, width, height), splash)
        written.append(splash)

    ic_bg_xml = res_dir / "values" / "ic_launcher_background.xml"
    _write_text_lf(
        ic_bg_xml,
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<resources>\n"
        f'    <color name="ic_launcher_background">{ICON_BG_HEX}</color>\n'
        "</resources>\n",
    )
    written.append(ic_bg_xml)

    colors_xml = res_dir / "values" / "colors.xml"
    _write_text_lf(
        colors_xml,
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<resources>\n"
        f'    <color name="colorPrimary">{THEME_HEX}</color>\n'
        f'    <color name="colorPrimaryDark">{THEME_DARK_HEX}</color>\n'
        f'    <color name="colorAccent">{THEME_ACCENT_HEX}</color>\n'
        f'    <color name="splash_background">{THEME_HEX}</color>\n'
        "</resources>\n",
    )
    written.append(colors_xml)

    # Remove unused default Capacitor template grid/foreground drawables if present.
    for obsolete in (
        res_dir / "drawable" / "ic_launcher_background.xml",
        res_dir / "drawable-v24" / "ic_launcher_foreground.xml",
    ):
        if obsolete.exists():
            obsolete.unlink()

    return written


def verify_deterministic_and_committed(root: Path, committed_res_dir: Path) -> None:
    """Verify two runs produce identical bytes and match the committed Android res/ assets."""
    with (
        tempfile.TemporaryDirectory(prefix="florabase-assets-a-") as tmp_a,
        tempfile.TemporaryDirectory(prefix="florabase-assets-b-") as tmp_b,
    ):
        dir_a = Path(tmp_a)
        dir_b = Path(tmp_b)
        files_a = sorted(p.relative_to(dir_a) for p in generate_assets(root=root, res_dir=dir_a))
        files_b = sorted(p.relative_to(dir_b) for p in generate_assets(root=root, res_dir=dir_b))
        if files_a != files_b:
            raise AssertionError("Asset generator produced different file sets across two runs")
        for rel in files_a:
            bytes_a = (dir_a / rel).read_bytes()
            bytes_b = (dir_b / rel).read_bytes()
            if bytes_a != bytes_b:
                raise AssertionError(f"Non-deterministic asset output for {rel}")
            committed = committed_res_dir / rel
            if not committed.is_file():
                raise AssertionError(f"Missing committed mobile asset: {committed}")
            if committed.read_bytes() != bytes_a:
                raise AssertionError(
                    f"Committed mobile asset {rel} drifts from generator; run make mobile-assets"
                )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root.")
    parser.add_argument(
        "--res-dir",
        type=Path,
        default=DEFAULT_RES_DIR,
        help="Target Android res/ directory.",
    )
    parser.add_argument(
        "--verify-committed",
        action="store_true",
        help="Verify two fresh runs are byte-identical and match the committed res/ assets.",
    )
    args = parser.parse_args(argv)
    if args.verify_committed:
        try:
            verify_deterministic_and_committed(root=args.root, committed_res_dir=args.res_dir)
        except AssertionError as exc:
            print(f"mobile-assets check failed: {exc}", file=sys.stderr)
            return 1
        print("MOBILE_ASSETS_DETERMINISTIC_OK")
        return 0
    generated = generate_assets(root=args.root, res_dir=args.res_dir)
    print(f"Generated {len(generated)} Android branding assets under {args.res_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
