import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";

const root = "node_modules/.pnpm";
const licenses = readdirSync(root, { recursive: true, withFileTypes: true })
  .filter(
    (entry) =>
      entry.isFile() && /^(licen[cs]e|copying|notice)(\.|$)/i.test(entry.name),
  )
  .map((entry) => path.join(entry.parentPath, entry.name))
  .sort();
if (licenses.length === 0) throw new Error("Dependency licenses are missing");
for (const file of licenses) {
  process.stdout.write(`\n--- ${file} ---\n${readFileSync(file, "utf8")}\n`);
}
