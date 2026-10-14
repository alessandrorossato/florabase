import qrcode from "qrcode-generator";

export interface QrGeometry {
  size: number;
  path: string;
  icon: { x: number; y: number; size: number } | null;
}
// Alignment centres from ISO QR version geometry. Never mask a functional pattern.
function alignmentPositions(version: number, count: number): number[] {
  if (version === 1) return [];
  const number = Math.floor(version / 7) + 2;
  // Reference geometry: https://github.com/nayuki/QR-Code-generator (alignment pattern positions).
  const step =
    Math.floor((version * 8 + number * 3 + 5) / (number * 4 - 4)) * 2;
  const result = [6];
  for (let i = number - 2; i >= 0; i--) result.push(count - 7 - i * step);
  return result;
}
export function qrGeometry(payload: string, inset = false): QrGeometry {
  const qr = qrcode(0, "H");
  qr.addData(payload, "Byte");
  qr.make();
  const count = qr.getModuleCount();
  const modules: string[] = [];
  for (let y = 0; y < count; y++)
    for (let x = 0; x < count; x++) {
      if (qr.isDark(y, x))
        modules.push(`M${String(x + 4)},${String(y + 4)}h1v1h-1z`);
    }
  let icon: QrGeometry["icon"] = null;
  if (inset) {
    const side = count >= 45 ? 7 : 5;
    const positions = alignmentPositions((count - 17) / 4, count);
    const centre = Math.floor((count - side) / 2);
    // Prefer the centre, then a nearby data-only area. Timing/finder/version areas are outside this search.
    for (const offsetY of [0, -8, 8])
      for (const offsetX of [0, -8, 8]) {
        const x = centre + offsetX,
          y = centre + offsetY;
        const coversAlignment = positions.some((py) =>
          positions.some(
            (px) =>
              x < px + 3 &&
              x + side > px - 2 &&
              y < py + 3 &&
              y + side > py - 2,
          ),
        );
        if (
          !icon &&
          x > 8 &&
          y > 8 &&
          x + side < count - 8 &&
          y + side < count - 8 &&
          !coversAlignment
        )
          icon = { x: x + 4, y: y + 4, size: side };
      }
  }
  return { size: count + 8, path: modules.join(""), icon };
}
