#!/usr/bin/env python3
"""Deterministic generator for Florabase PWA icons and favicons.

Produces:
- frontend/public/icons/icon-192.png (standard 192x192)
- frontend/public/icons/icon-512.png (standard 512x512)
- frontend/public/icons/icon-maskable-192.png (Android adaptive maskable 192x192)
- frontend/public/icons/icon-maskable-512.png (Android adaptive maskable 512x512)
- frontend/public/icons/apple-touch-icon.png (iOS 180x180)
- frontend/public/icons/icon.svg (Vector SVG)
- frontend/public/icons/icon-maskable.svg (Maskable vector SVG)
- frontend/public/favicon.ico (Multi-res 16, 32, 48)
- frontend/public/favicon.svg (Vector favicon)
"""

from pathlib import Path

from PIL import Image, ImageDraw

Point = tuple[float, float]


def cubic_bezier(p0: Point, p1: Point, p2: Point, p3: Point, n: int = 60) -> list[Point]:
    points: list[Point] = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        x = (
            u * u * u * p0[0]
            + 3 * u * u * t * p1[0]
            + 3 * u * t * t * p2[0]
            + t * t * t * p3[0]
        )
        y = (
            u * u * u * p0[1]
            + 3 * u * u * t * p1[1]
            + 3 * u * t * t * p2[1]
            + t * t * t * p3[1]
        )
        points.append((x, y))
    return points


def render_icon(size: int, maskable: bool = False, apple: bool = False) -> Image.Image:
    # 4x super-sampling for anti-aliasing
    scale = 4
    canvas_size = size * scale

    # Color palette
    bg_color = (21, 58, 44, 255)  # #153a2c (Deep Botanical Forest Green)
    main_leaf = (244, 248, 245, 255)  # #f4f8f5 (Botanical Crisp Off-White)
    sec_leaf = (141, 197, 163, 255)  # #8dc5a3 (Sage Green)
    vein_color = (21, 58, 44, 255)  # #153a2c (Inner leaf vein contrast)

    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if maskable or apple:
        # Full bleed background
        draw.rectangle([0, 0, canvas_size, canvas_size], fill=bg_color)
    else:
        # Standard icon: squircle with rounded corners (rx ~ 22%)
        rx = int(canvas_size * 0.22)
        draw.rounded_rectangle([0, 0, canvas_size - 1, canvas_size - 1], radius=rx, fill=bg_color)

    # Safe zone scaling:
    # Maskable safe zone is inner 80% circle (radius 0.40 * canvas_size).
    # Keep artwork tightly within 0.33 * canvas_size radius.
    cx = canvas_size / 2.0
    cy = canvas_size / 2.0
    art_radius = canvas_size * (0.33 if maskable else 0.35)

    def pt(x: float, y: float) -> Point:
        return (cx + x * art_radius, cy + y * art_radius)

    # 1. Secondary leaf (pointing northwest / left)
    sec_base = pt(-0.12, 0.32)
    sec_tip = pt(-0.68, -0.15)
    sec_top = cubic_bezier(sec_base, pt(-0.25, 0.05), pt(-0.48, -0.22), sec_tip)
    sec_bot = cubic_bezier(sec_tip, pt(-0.58, 0.08), pt(-0.35, 0.36), sec_base)
    draw.polygon(sec_top + sec_bot, fill=sec_leaf)

    # 2. Main leaf (pointing northeast / right)
    main_base = pt(-0.08, 0.42)
    main_tip = pt(0.68, -0.62)
    main_left = cubic_bezier(main_base, pt(-0.16, -0.02), pt(0.12, -0.55), main_tip)
    main_right = cubic_bezier(main_tip, pt(0.72, -0.12), pt(0.48, 0.38), main_base)
    draw.polygon(main_left + main_right, fill=main_leaf)

    # 3. Stem and vein
    stem_width = max(int(scale * size * 0.038), 2)
    vein_points = cubic_bezier(
        pt(-0.12, 0.48), pt(0.02, 0.12), pt(0.28, -0.22), pt(0.64, -0.58), n=60
    )
    draw.line(vein_points, fill=vein_color, width=stem_width)

    stem_points = cubic_bezier(
        pt(-0.36, 0.78), pt(-0.25, 0.64), pt(-0.18, 0.52), pt(-0.08, 0.42), n=30
    )
    draw.line(stem_points, fill=sec_leaf, width=stem_width + max(int(scale * size * 0.015), 1))

    # Downsample with Lanczos filter for smooth antialiasing
    return img.resize((size, size), Image.Resampling.LANCZOS)


def generate_svg(maskable: bool = False) -> str:
    rx = 0 if maskable else 112
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" '
        'width="100%" height="100%">\n'
        f'  <rect width="512" height="512" rx="{rx}" fill="#153a2c"/>\n'
        "  <!-- Secondary Leaf -->\n"
        '  <path d="M 235 313 C 213 265 174 219 139 231 C 122 271 161 320 235 313 Z" '
        'fill="#8dc5a3"/>\n'
        "  <!-- Main Leaf -->\n"
        '  <path d="M 242 330 C 228 253 277 160 375 148 C 382 235 340 323 242 330 Z" '
        'fill="#f4f8f5"/>\n'
        "  <!-- Main Vein -->\n"
        '  <path d="M 235 340 C 260 279 305 220 368 155" stroke="#153a2c" '
        'stroke-width="15" stroke-linecap="round" fill="none"/>\n'
        "  <!-- Base Stem -->\n"
        '  <path d="M 193 392 C 212 368 224 347 242 330" stroke="#8dc5a3" '
        'stroke-width="21" stroke-linecap="round" fill="none"/>\n'
        "</svg>\n"
    )


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    public_dir = root / "frontend" / "public"
    icons_dir = public_dir / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    print("Generating PWA icons...")

    # 1. Standard PNG icons
    render_icon(192, maskable=False).save(icons_dir / "icon-192.png", "PNG", optimize=True)
    render_icon(512, maskable=False).save(icons_dir / "icon-512.png", "PNG", optimize=True)

    # 2. Maskable PNG icons (Android adaptive)
    render_icon(192, maskable=True).save(icons_dir / "icon-maskable-192.png", "PNG", optimize=True)
    render_icon(512, maskable=True).save(icons_dir / "icon-maskable-512.png", "PNG", optimize=True)

    # 3. Apple Touch Icon (180x180)
    render_icon(180, apple=True).save(icons_dir / "apple-touch-icon.png", "PNG", optimize=True)

    # 4. Multi-res Favicon (16, 32, 48)
    fav_icon = render_icon(48, maskable=False)
    fav_icon.save(public_dir / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])

    # 5. SVGs
    (icons_dir / "icon.svg").write_text(generate_svg(maskable=False), encoding="utf-8")
    (icons_dir / "icon-maskable.svg").write_text(generate_svg(maskable=True), encoding="utf-8")
    (public_dir / "favicon.svg").write_text(generate_svg(maskable=False), encoding="utf-8")

    print("All PWA icons generated successfully.")


if __name__ == "__main__":
    main()
