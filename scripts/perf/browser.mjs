// PERF-001 Chromium workload. Install Playwright outside the repository; see the report.
import { createRequire } from "node:module";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { performance } from "node:perf_hooks";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PERF_PLAYWRIGHT ?? "playwright");
const [manifestFile, outputFile] = process.argv.slice(2);
if (!manifestFile || !outputFile || existsSync(outputFile))
  throw Error("Provide manifest and NEW evidence output paths");
const m = JSON.parse(readFileSync(manifestFile, "utf8")).manifest;
const origin = "http://localhost:18080";
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 844 },
});
const login = await context.request.post(`${origin}/api/v1/auth/login`, {
  headers: { Origin: origin },
  data: {
    login_name: "perf-owner",
    password: "disposable-perf-owner-password",
  },
});
if (!login.ok()) throw Error(`Login ${login.status()}`);
// Controlled only in this measurement browser; production application is unchanged.
const png = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==",
  "base64",
);
const external = [];
await context.route("**/*", async (route) => {
  const url = new URL(route.request().url());
  if (url.origin !== origin) {
    external.push(url.hostname);
    return route.fulfill({ contentType: "image/png", body: png });
  }
  if (url.pathname.endsWith("/occurrence-map/summary"))
    return route.fulfill({
      json: {
        source: "GBIF occurrence records",
        provider: "gbif",
        external_taxon_id: "6SHN2",
        taxon_scientific_name: "Aloe vera",
        taxon_provider_url: "https://www.gbif.org/species/6SHN2",
        checklist_key: "7ddf754f-d193-4cc9-b351-99906754a03b",
        checklist_name: "Catalogue of Life eXtended Release",
        total_matching_records: 1000,
        eligible_mapped_records: 800,
        retrieved_at: "2026-09-01T00:00:00Z",
        quality_policy: {
          occurrence_status: "PRESENT",
          has_coordinate: true,
          has_geospatial_issue: false,
        },
        binning: "hexagonal",
        attribution: "GBIF and publishers",
        provider_url: "https://www.gbif.org",
        licensing_url: "https://www.gbif.org/terms",
      },
    });
  if (url.pathname.includes("/occurrence-map/tiles/"))
    return route.fulfill({ contentType: "image/png", body: png });
  return route.continue();
});
const page = await context.newPage();
const cdp = await context.newCDPSession(page);
await cdp.send("Performance.enable");
const requests = [];
const pending = new Set();
let lastActivity = performance.now();
const errors = [];
page.on("request", (req) => {
  pending.add(req);
  lastActivity = performance.now();
  requests.push({ path: new URL(req.url()).pathname, method: req.method() });
});
for (const event of ["requestfinished", "requestfailed"])
  page.on(event, (req) => {
    pending.delete(req);
    lastActivity = performance.now();
  });
async function settle() {
  const deadline = performance.now() + 30000;
  while (pending.size || performance.now() - lastActivity < 500) {
    if (performance.now() > deadline)
      throw Error("Browser requests did not settle");
    await page.waitForTimeout(50);
  }
}
page.on("pageerror", (error) => errors.push(error.message));
page.on("response", (response) => {
  if (response.status() >= 400)
    errors.push(`${response.status()} ${response.url()}`);
});
await page.addInitScript(() => {
  const intervals = new Set();
  const timeouts = new Set();
  const setI = window.setInterval.bind(window),
    clearI = window.clearInterval.bind(window);
  const setT = window.setTimeout.bind(window),
    clearT = window.clearTimeout.bind(window);
  window.setInterval = (fn, ms, ...args) => {
    const id = setI(fn, ms, ...args);
    intervals.add(id);
    return id;
  };
  window.clearInterval = (id) => {
    intervals.delete(id);
    clearI(id);
  };
  window.setTimeout = (fn, ms, ...args) => {
    const id = setT(() => {
      timeouts.delete(id);
      typeof fn === "function" ? fn(...args) : window.eval(fn);
    }, ms);
    timeouts.add(id);
    return id;
  };
  window.clearTimeout = (id) => {
    timeouts.delete(id);
    clearT(id);
  };
  window.perfTimers = () => ({
    intervals: intervals.size,
    timeouts: timeouts.size,
  });
});
const begin = performance.now();
await page.goto(`${origin}/#/dashboard`, { waitUntil: "networkidle" });
await page.getByRole("heading", { name: "Dashboard", exact: true }).waitFor();
const initial = {
  ms: Math.round(performance.now() - begin),
  requests: [...requests],
  resources: await page.evaluate(() =>
    performance
      .getEntriesByType("resource")
      .map((e) => ({
        path: new URL(e.name).pathname,
        bytes: e.encodedBodySize,
        transfer: e.transferSize,
        ms: Math.round(e.duration),
      })),
  ),
};
const routes = [
  ["dashboard", "/dashboard"],
  ["identities", "/identities"],
  ["identity", `/identities/${m.identity}`],
  ["reference", `/identities/${m.identity}?tab=reference`],
  ["seeds", "/seeds"],
  ["seed", `/seeds/${m.seed}`],
  ["photos", `/seeds/${m.seed}?tab=photos`],
  ["lineage", `/seeds/${m.seed}?tab=lineage`],
  ["sowings", "/sowings"],
  ["sowing", `/sowings/${m.sowing}`],
  ["germination", `/sowings/${m.sowing}?tab=germination`],
  ["plants", "/plants"],
  ["plant", `/plants/${m.plant}`],
  ["group", `/plant-groups/${m.group}`],
  ["suppliers", "/suppliers"],
  ["supplier", `/suppliers/${m.supplier}`],
  ["locations", "/locations"],
  ["location", `/locations/${m.location}`],
  ["geography", "/geography"],
  ["site", `/geography/${m.site}`],
  ["place", `/geography?place=${m.place}`],
  ["events", "/events"],
  ["provenance", "/map"],
  ["occurrence", `/identities/${m.identity}?tab=reference`],
  ["labels", `/labels?kind=seed_lot&record=${m.seed}`],
  ["dashboard", "/dashboard"],
];
async function visit(name, route) {
  const offset = requests.length,
    externalOffset = external.length,
    begin = performance.now();
  lastActivity = performance.now();
  await page.evaluate((hash) => {
    window.location.hash = hash;
  }, route);
  await settle();
  if (["photos", "lineage", "germination"].includes(name)) {
    await page.getByRole("tab", { name: new RegExp(`^${name}$`, "i") }).click();
    await settle();
  }
  if (name === "provenance") await page.locator(".leaflet-container").waitFor();
  if (name === "occurrence") {
    await page.getByRole("tab", { name: "Occurrences", exact: true }).click();
    await page
      .getByRole("button", { name: "Load GBIF occurrence map", exact: true })
      .click();
    await page
      .getByRole("region", {
        name: "Interactive GBIF occurrence-record density map",
      })
      .waitFor();
    await settle();
  }
  return {
    name,
    ms: Math.round(performance.now() - begin),
    requests: requests.slice(offset),
    external: external.length - externalOffset,
    maps: await page.locator(".leaflet-container").count(),
  };
}
const workload = [];
for (const [name, route] of routes) workload.push(await visit(name, route));
async function checkpoint() {
  await cdp.send("HeapProfiler.collectGarbage");
  const metrics = await cdp.send("Performance.getMetrics");
  return {
    ...Object.fromEntries(
      metrics.metrics
        .filter((m) =>
          ["JSHeapUsedSize", "Nodes", "JSEventListeners", "Documents"].includes(
            m.name,
          ),
        )
        .map((m) => [m.name, m.value]),
    ),
    timers: await page.evaluate(() => window.perfTimers()),
    maps: await page.locator(".leaflet-container").count(),
  };
}
const cycles = [await checkpoint()];
console.log("Representative browser routes complete");
const cycleRequests = [];
for (let cycle = 0; cycle < 6; cycle++) {
  const offset = requests.length;
  for (const [name, route] of routes.filter(([name]) =>
    [
      "seeds",
      "seed",
      "photos",
      "lineage",
      "provenance",
      "occurrence",
      "dashboard",
    ].includes(name),
  ))
    await visit(name, route);
  cycles.push(await checkpoint());
  cycleRequests.push(requests.length - offset);
  console.log(`Navigation cycle ${cycle + 1} complete`);
}
console.log("Observing authenticated idle session for 120 seconds");
const idleOffset = requests.length,
  idle = [],
  idleBegin = performance.now();
for (let i = 0; i <= 12; i++) {
  if (i)
    await page.waitForTimeout(
      Math.max(0, idleBegin + i * 10000 - performance.now()),
    );
  const out = `${outputFile}.sample-${i}.json`;
  execFileSync("python3", ["scripts/perf/measure.py", "sample", "--out", out], {
    stdio: "pipe",
  });
  idle.push(JSON.parse(readFileSync(out, "utf8")));
}
const result = {
  chromium: browser.version(),
  initial,
  workload,
  cycles,
  cycleRequests,
  idleSeconds: Math.round((performance.now() - idleBegin) / 1000),
  idleRequests: requests.slice(idleOffset),
  idle,
  final: await checkpoint(),
  errors,
  resources: await page.evaluate(() =>
    performance
      .getEntriesByType("resource")
      .filter((e) => e.name.includes("/assets/"))
      .map((e) => ({
        path: new URL(e.name).pathname,
        bytes: e.encodedBodySize,
        transfer: e.transferSize,
      })),
  ),
};
writeFileSync(outputFile, JSON.stringify(result, null, 2) + "\n");
await browser.close();
console.log(outputFile);
