// Exercise a stale/missing workspace chunk against the production nginx fallback.
import { createRequire } from "node:module";
import { existsSync, writeFileSync } from "node:fs";
import assert from "node:assert/strict";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PERF_PLAYWRIGHT ?? "playwright");
const [output] = process.argv.slice(2);
if (!output || existsSync(output))
  throw Error("Provide a NEW evidence output path");

const origin = "http://localhost:18080";
const stalePath = "/assets/PERF-review-stale-chunk.js";
const browser = await chromium.launch({ headless: true });
try {
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
  assert.equal(login.status(), 200);

  let staleRequest = false;
  await context.route("**/assets/SeedLotScreen-*.js", async (route) => {
    staleRequest = true;
    const missingAsset = new URL(route.request().url());
    missingAsset.pathname = stalePath;
    await route.continue({ url: missingAsset.toString() });
  });

  const page = await context.newPage();
  const errors = [];
  const documents = [];
  let fallback = null;
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (request.isNavigationRequest()) documents.push(request.url());
  });
  page.on("response", (response) => {
    if (new URL(response.url()).pathname === stalePath) {
      fallback = {
        status: response.status(),
        contentType: response.headers()["content-type"],
      };
    }
  });

  await page.goto(origin);
  await page.getByRole("button", { name: "Seeds", exact: true }).click();
  await page
    .getByRole("alert")
    .filter({ hasText: "Florabase could not load this workspace." })
    .waitFor();
  await page.waitForTimeout(250);
  assert.equal(staleRequest, true, "The Seeds JavaScript chunk was requested");
  assert.equal(fallback?.status, 200);
  assert.ok(fallback?.contentType.toLowerCase().startsWith("text/html"));
  assert.equal(documents.length, 1, "Recovery must not reload automatically");
  assert.equal(
    errors.length,
    0,
    "The handled chunk error must not escape the boundary",
  );
  await page.getByRole("button", { name: "Sign out", exact: true }).waitFor();
  writeFileSync(
    output,
    JSON.stringify(
      {
        stale_asset_path: stalePath,
        nginx_fallback: fallback,
        shell_retained: true,
        automatic_reload: false,
        page_errors: errors,
      },
      null,
      2,
    ) + "\n",
  );
  await context.close();
} finally {
  await browser.close();
}
