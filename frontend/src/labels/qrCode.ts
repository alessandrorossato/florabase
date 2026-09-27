import qrcode from "qrcode-generator";

// Read only the encoder's module matrix. React constructs the SVG; no HTML injection.
export function qrGeometry(payload: string): { size: number; path: string } {
  const qr = qrcode(0, "M");
  qr.addData(payload, "Byte");
  qr.make();
  const count = qr.getModuleCount();
  const modules: string[] = [];
  for (let y = 0; y < count; y++) {
    for (let x = 0; x < count; x++) {
      if (qr.isDark(y, x))
        modules.push(`M${String(x + 4)},${String(y + 4)}h1v1h-1z`);
    }
  }
  return { size: count + 8, path: modules.join("") };
}
