// PERF-001 Chromium workload for Golden COMPREHENSIVE. Install Playwright outside the repository.
import { createRequire } from "node:module";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { performance } from "node:perf_hooks";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PERF_PLAYWRIGHT ?? "playwright");
const [manifestFile, outputFile] = process.argv.slice(2);
if (!manifestFile || !outputFile || existsSync(outputFile)) {
  throw Error("Provide manifest and NEW evidence output paths");
}

const rawEnv = JSON.parse(readFileSync(manifestFile, "utf8"));
const m = rawEnv?.manifest;
if (!m?.valid || m?.profile !== "comprehensive" || !m?.targets) {
  throw Error(
    "Invalid or unvalidated COMPREHENSIVE manifest; run measure.py start first",
  );
}
const t = m.targets;
const origin = "http://localhost:18080";
const sampleDir = process.env.PERF_SAMPLE_DIR || "";
if (sampleDir) mkdirSync(sampleDir, { recursive: true });

const launchOptions = { headless: true };
if (process.env.PERF_CHROMIUM_EXECUTABLE) {
  launchOptions.executablePath = process.env.PERF_CHROMIUM_EXECUTABLE;
}
const browser = await chromium.launch(launchOptions);
try {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 844 },
  });
  const login = await context.request.post(`${origin}/api/v1/auth/login`, {
    headers: { Origin: origin },
    data: {
      login_name: "golden-owner",
      password: "disposable-golden-owner-password",
    },
  });
  if (!login.ok()) throw Error(`Login failed with status ${login.status()}`);

  // Controlled only in this measurement browser; production application is unchanged.
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==",
    "base64",
  );
  const external = [];
  await context.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.origin !== origin) {
      external.push(url.hostname);
      return route.fulfill({ contentType: "image/png", body: png });
    }
    if (url.pathname.endsWith("/occurrence-map/cache")) {
      if (request.method() === "GET") {
        return route.fulfill({
          json: {
            summary: null,
            generation: null,
            stale: false,
            provider_error: null,
            persisted: true,
          },
        });
      }
      if (request.method() === "POST") {
        return route.fulfill({
          json: {
            summary: {
              source: "GBIF occurrence records",
              provider: "gbif",
              external_taxon_id: "48GBK",
              taxon_scientific_name: "Ocimum basilicum",
              taxon_provider_url: "https://www.gbif.org/species/48GBK",
              checklist_key: "7ddf754f-d193-4cc9-b351-99906754a03b",
              checklist_name: "Catalogue of Life eXtended Release",
              total_matching_records: 1000,
              eligible_mapped_records: 800,
              retrieved_at: "2026-09-15T12:00:00Z",
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
            generation: "0198f000-0000-7000-8000-000000000001",
            stale: false,
            provider_error: null,
            persisted: true,
          },
        });
      }
    }
    if (url.pathname.includes("/occurrence-map/tiles/")) {
      return route.fulfill({ contentType: "image/png", body: png });
    }
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
  for (const event of ["requestfinished", "requestfailed"]) {
    page.on(event, (req) => {
      pending.delete(req);
      lastActivity = performance.now();
    });
  }
  async function settle(label = "route") {
    const deadline = performance.now() + 30000;
    while (pending.size || performance.now() - lastActivity < 500) {
      if (performance.now() > deadline) {
        throw Error(
          `Browser requests did not settle for ${label} (${pending.size} pending)`,
        );
      }
      await page.waitForTimeout(50);
    }
  }
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("response", (response) => {
    if (response.status() >= 400) {
      errors.push(`${response.status()} ${response.url()}`);
    }
  });
  await page.addInitScript(() => {
    const intervals = new Set();
    const timeouts = new Set();
    const setI = window.setInterval.bind(window);
    const clearI = window.clearInterval.bind(window);
    const setT = window.setTimeout.bind(window);
    const clearT = window.clearTimeout.bind(window);
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

  async function waitTodayReady() {
    await page
      .getByRole("heading", { name: "Today", exact: true })
      .waitFor({ timeout: 15000 });
    await page
      .getByRole("heading", { name: "Collection snapshot", exact: true })
      .waitFor({ timeout: 15000 });
  }

  const begin = performance.now();
  await page.goto(`${origin}/#/dashboard`, {
    waitUntil: "networkidle",
    timeout: 30000,
  });
  await waitTodayReady();
  await settle("initial-today");
  const initial = {
    ms: Math.round(performance.now() - begin),
    requests: [...requests],
    resources: await page.evaluate(() =>
      performance.getEntriesByType("resource").map((e) => ({
        path: new URL(e.name).pathname,
        bytes: e.encodedBodySize,
        transfer: e.transferSize,
        ms: Math.round(e.duration),
      })),
    ),
  };

  async function openWorkbenchLink(workspacePrefix, linkName) {
    const tab = page.getByRole("tab", {
      name: new RegExp(`^${workspacePrefix}`),
    });
    const selected = await tab.getAttribute("aria-selected");
    if (selected !== "true") await tab.click();
    await page
      .getByRole("navigation", { name: "Primary navigation" })
      .getByRole("link", { name: linkName, exact: true })
      .click();
  }

  const routes = [
    ["today", "/dashboard"],
    [
      "identities",
      "/identities",
      { workbench: ["Explore", "Botanical identities"] },
    ],
    ["identity", `/identities/${t.rich_identity}`],
    ["identity_reference", `/identities/${t.rich_identity}?tab=reference`],
    ["identity_maps", `/identities/${t.identity}?tab=maps`],
    ["seeds", "/seeds", { workbench: ["Collection", "Seeds"] }],
    ["seed", `/seeds/${t.seed}`],
    ["photos", `/seeds/${t.seed}`, { tab: "Photos" }],
    ["lineage", `/seeds/${t.lineage_seed}`, { tab: "Lineage" }],
    ["sowings", "/sowings"],
    ["sowing", `/sowings/${t.sowing}`],
    ["germination", `/sowings/${t.sowing}`, { tab: "Germination" }],
    ["cuttings", "/cuttings", { workbench: ["Collection", "Cuttings"] }],
    ["cutting_lot", `/cuttings/lots/${t.cutting_lot}`],
    ["plants", "/plants"],
    ["plant", `/plants/${t.plant}`],
    ["group", `/plant-groups/${t.group}`],
    ["harvests", "/harvests"],
    ["harvest", `/harvests/${t.harvest}`],
    ["stored_material", "/harvests?tab=stored-material"],
    ["suppliers", "/suppliers"],
    ["supplier", `/suppliers/${t.supplier}`],
    ["orders", "/orders", { workbench: ["Sourcing", "Orders"] }],
    ["order", `/orders/${t.order}`],
    ["locations", "/locations"],
    ["location", `/locations/${t.location}`],
    ["geography", "/geography"],
    ["site", `/geography/${t.site}`],
    ["place", `/geography?place=${t.place}`],
    ["native_ranges", "/native-ranges"],
    ["taxonomy", "/taxonomy"],
    ["media", "/media"],
    ["events", "/events"],
    ["history", "/history", { workbench: ["Activity", "History"] }],
    ["schedule", "/schedule"],
    ["provenance", "/map"],
    ["occurrence", `/species-distribution?identity=${t.identity}`],
    ["labels", `/labels?kind=seed_lot&record=${t.seed}`],
    ["dashboard", "/dashboard"],
  ];

  async function visit(name, route, options = {}) {
    const offset = requests.length;
    const externalOffset = external.length;
    const routeBegin = performance.now();
    lastActivity = performance.now();
    if (options.workbench) {
      await openWorkbenchLink(options.workbench[0], options.workbench[1]);
    } else {
      await page.evaluate((hash) => {
        window.location.hash = hash;
      }, route);
    }
    await settle(name);
    if (options.tab) {
      await page
        .getByRole("tab", { name: new RegExp(`^${options.tab}$`, "i") })
        .click();
      await settle(`${name}-${options.tab}`);
    }
    if (name === "today" || name === "dashboard") {
      await waitTodayReady();
    }
    if (name === "provenance") {
      await page.locator(".leaflet-container").waitFor({ timeout: 15000 });
    }
    if (name === "occurrence") {
      await page
        .getByRole("button", { name: "Load GBIF occurrence map", exact: true })
        .click();
      await page
        .getByRole("region", {
          name: "Interactive GBIF occurrence-record density map",
        })
        .waitFor({ timeout: 15000 });
      await settle(`${name}-loaded`);
    }
    return {
      name,
      ms: Math.round(performance.now() - routeBegin),
      requests: requests.slice(offset),
      external: external.length - externalOffset,
      maps: await page.locator(".leaflet-container").count(),
    };
  }

  const workload = [];
  for (const [name, route, options] of routes) {
    workload.push(await visit(name, route, options));
  }

  async function checkpoint() {
    await cdp.send("HeapProfiler.collectGarbage");
    const metrics = await cdp.send("Performance.getMetrics");
    return {
      ...Object.fromEntries(
        metrics.metrics
          .filter((item) =>
            [
              "JSHeapUsedSize",
              "Nodes",
              "JSEventListeners",
              "Documents",
            ].includes(item.name),
          )
          .map((item) => [item.name, item.value]),
      ),
      timers: await page.evaluate(() => window.perfTimers()),
      maps: await page.locator(".leaflet-container").count(),
    };
  }

  const cycles = [await checkpoint()];
  console.log("Representative browser routes complete");
  const cycleNames = new Set([
    "seeds",
    "seed",
    "photos",
    "lineage",
    "cuttings",
    "harvests",
    "provenance",
    "occurrence",
    "dashboard",
  ]);
  const cycleRoutes = routes.filter(([name]) => cycleNames.has(name));
  const cycleRequests = [];
  for (let cycle = 0; cycle < 6; cycle++) {
    const offset = requests.length;
    for (const [name, route, options] of cycleRoutes) {
      const cycleOptions = options?.workbench ? { tab: options.tab } : options;
      await visit(name, route, cycleOptions);
    }
    cycles.push(await checkpoint());
    cycleRequests.push(requests.length - offset);
    console.log(`Navigation cycle ${cycle + 1} complete`);
  }

  console.log("Observing authenticated idle session for 120 seconds");
  const idleOffset = requests.length;
  const idle = [];
  const idleBegin = performance.now();
  for (let i = 0; i <= 12; i++) {
    if (i) {
      await page.waitForTimeout(
        Math.max(0, idleBegin + i * 10000 - performance.now()),
      );
    }
    const out = sampleDir
      ? path.join(sampleDir, `sample-${i}.json`)
      : `${outputFile}.sample-${i}.json`;
    execFileSync(
      "python3",
      ["scripts/perf/measure.py", "sample", "--out", out],
      {
        stdio: "pipe",
      },
    );
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
  console.log(outputFile);
} finally {
  await browser.close();
}
