import { expect, test } from "vitest";
import { qrGeometry } from "./qrCode";
import { labelKinds, recordUrl, sourceHref } from "./labelData";
const id = "01900000-0000-7000-8000-000000000211";
const harvestId = "01900000-0000-7000-8000-000000000212";
test.each(labelKinds)(
  "%s QR uses the saved canonical URL and exact source with quiet zone",
  (kind) => {
    const url = recordUrl(kind, id, "https://flora.example/", harvestId);
    expect(url).toBe(
      `https://flora.example/${sourceHref({ kind, id, harvestId })}`,
    );
    const qr = qrGeometry(url, true);
    const modules = [...qr.path.matchAll(/M(\d+),(\d+)/g)].map((match) => [
      Number(match[1]),
      Number(match[2]),
    ]);
    expect(modules.length).toBeGreaterThan(100);
    expect(
      modules.every(
        ([x, y]) => x >= 4 && y >= 4 && x < qr.size - 4 && y < qr.size - 4,
      ),
    ).toBe(true);
    expect(qr.icon).not.toBeNull();
    if (qr.icon) {
      const count = qr.size - 8;
      expect(qr.icon.size ** 2 / count ** 2).toBeLessThan(0.025);
      expect(qr.icon.x).toBeGreaterThan(12);
      expect(qr.icon.y).toBeGreaterThan(12);
      expect(qr.icon.x + qr.icon.size).toBeLessThan(count - 4);
    }
    expect(qrGeometry(url).icon).toBeNull();
  },
);

// Independent fixed alignment centres for the QR versions reached by these byte payloads.
test.each([
  [60, [6, 22, 38]],
  [70, [6, 24, 42]],
  [90, [6, 26, 46]],
  [110, [6, 28, 50]],
  [130, [6, 30, 54]],
  [150, [6, 32, 58]],
] as const)(
  "glyph leaves every alignment pattern intact at payload length %s",
  (length, positions) => {
    const qr = qrGeometry("x".repeat(length), true);
    const icon = qr.icon;
    if (!icon) throw new Error("Expected a safe inset data area");
    expect(qr.size - 8 - 7).toBe(positions[2]);
    const left = icon.x - 4,
      top = icon.y - 4;
    for (const x of positions)
      for (const y of positions) {
        expect(
          left < x + 3 &&
            left + icon.size > x - 2 &&
            top < y + 3 &&
            top + icon.size > y - 2,
        ).toBe(false);
      }
  },
);
