// Frontend-only synthetic review. Requires a Vite server for this worktree at REVIEW_URL.
// No live backend/database is contacted; every /api request is fulfilled here.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixture.json'), 'utf8'));
const base = process.env.REVIEW_URL || 'http://127.0.0.1:15176';
const assert = (condition, message) => { if (!condition) throw new Error(message); };
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const report = { synthetic: true, measurements: [], checks: [], providerRequests: [], consoleErrors: [] };
  const context = await browser.newContext({ viewport: { width: 1440, height: 844 }, reducedMotion: 'reduce' });
  const page = await context.newPage();
  page.on('pageerror', error => report.consoleErrors.push(error.message));
  let data = fixture;
  let failApi = false;
  const saved = [{ id: '01900000-0000-7000-8000-000000000300', name: 'Synthetic seed origins', surface: 'provenance_map', state_version: 1, compatibility: 'supported', state: { plants: false }, created_at: '2026-10-22T00:00:00Z', updated_at: '2026-10-22T00:00:00Z' }];
  await context.route('**/api/**', route => {
    const url = new URL(route.request().url());
    const body = url.pathname.endsWith('/auth/session') ? { user_id: '01900000-0000-7000-8000-000000000001', login_name: 'synthetic', display_name: 'Synthetic review fixture', owner: true, canonical_origin: base }
      : url.pathname.endsWith('/auth/csrf') ? { csrf_token: 'synthetic-fixture-only' }
      : url.pathname.endsWith('/provenance-sites/map') ? data
      : url.pathname.endsWith('/saved-views') ? saved : [];
    return route.fulfill({ status: failApi && url.pathname.endsWith('/provenance-sites/map') ? 503 : 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
  // Observe the actual renderer's outgoing URLs, then inject an unavailable provider.
  await context.route('https://*.tile.openstreetmap.org/**', route => {
    report.providerRequests.push({ url: route.request().url(), referer: route.request().headers().referer || null });
    return route.abort('failed');
  });
  const label = async () => page.evaluate(() => {
    if (document.getElementById('synthetic-evidence')) return;
    const tag = document.createElement('div'); tag.id = 'synthetic-evidence'; tag.textContent = 'SYNTHETIC FRONTEND FIXTURE · no collection data';
    Object.assign(tag.style, { position: 'fixed', bottom: '0', left: '0', zIndex: '9999', padding: '3px 8px', background: '#1e2621', color: '#fff', font: '12px sans-serif', pointerEvents: 'none' }); document.body.append(tag);
  });
  const capture = async (name) => { await label(); await page.screenshot({ path: path.join(__dirname, name + '.png') }); };
  const open = async () => { await page.goto(base + '/#/map'); await page.getByRole('heading', { name: 'Collection origins', exact: true }).waitFor(); await page.locator('.origins-overview').waitFor(); };
  await open();
  await page.getByText(/Online basemap tiles are unavailable/).waitFor();
  await capture('desktop-provider-failure');
  await page.getByRole('checkbox', { name: 'Online basemap' }).uncheck();
  await page.locator('.leaflet-overlay-pane path').first().waitFor();
  for (const width of [1440, 1024, 390]) {
    await page.setViewportSize({ width, height: 844 });
    await page.getByRole('heading', { name: 'Collection origins', exact: true }).waitFor();
    if (width <= 1024) await page.getByRole('button', { name: 'Map & evidence' }).click();
    await page.getByRole('button', { name: 'Fit visible sites' }).click();
    await page.evaluate(() => document.fonts.ready);
    const measurement = await page.evaluate(() => {
      const box = selector => { const e = document.querySelector(selector); const r = e.getBoundingClientRect(); return { x: r.x, y: r.y, width: r.width, height: r.height, bottom: r.bottom }; };
      return { viewport: [innerWidth, innerHeight], scrollWidth: document.documentElement.scrollWidth, scrollHeight: document.documentElement.scrollHeight, map: box('.provenance-map'), canvas: box('.origins-canvas'), inspector: box('.maps-workspace__browser'), kpis: box('.origins-overview') };
    });
    assert(measurement.scrollWidth <= width, 'horizontal overflow at ' + width);
    report.measurements.push(measurement);
    await capture(width === 1440 ? 'desktop-overview' : width === 1024 ? 'tablet-map' : 'mobile-map');
    if (width <= 1024) await page.getByRole('button', { name: 'Inspector', exact: true }).click();
    await page.locator('.origins-sites button').filter({ hasText: 'Monte Pellegrino' }).click();
    await page.getByRole('heading', { name: fixture.sites[0].name, exact: true }).waitFor();
    await page.locator('.origins-identities summary').first().click();
    await capture(width === 1440 ? 'desktop-inspector' : width === 1024 ? 'tablet-inspector' : 'mobile-inspector');
    await page.getByRole('button', { name: '← All visible sites' }).click();
  }
  report.checks.push('1440/1024/390 no horizontal overflow; exact selected details and identity grouping');
  // Responsive mounted pane and map DOM identity preservation.
  await page.getByRole('button', { name: 'Map & evidence' }).click();
  await page.locator('.provenance-map').evaluate(e => { e.dataset.reviewIdentity = 'retained'; });
  await page.getByRole('button', { name: 'Inspector', exact: true }).click();
  await page.getByRole('button', { name: 'Map & evidence' }).click();
  assert(await page.locator('.provenance-map').getAttribute('data-review-identity') === 'retained', 'map remounted');
  assert(await page.locator('.provenance-map').evaluate(e => e.clientWidth > 0), 'hidden map not revealed');
  report.checks.push('mobile map DOM retained across pane switch');
  await page.setViewportSize({ width: 1440, height: 844 });
  // Real browser keyboard marker Enter and Space selection, Escape clearing.
  const marker = page.locator('.leaflet-marker-icon').first(); await marker.focus(); await page.keyboard.press('Enter');

  await page.getByRole('heading', { name: fixture.sites[0].name, exact: true }).waitFor();
  await page.keyboard.press('Escape');
  await page.getByRole('heading', { name: 'Recorded origin sites' }).waitFor();
  await marker.focus(); await page.keyboard.press('Space');
  await page.getByRole('heading', { name: fixture.sites[0].name, exact: true }).waitFor();
  report.checks.push('real Leaflet Enter/Space selection and Escape clearing');
  // Actual Back/Forward and Saved View restoration.
  await page.getByRole('searchbox', { name: 'Botanical identity', exact: true }).fill('Clitoria');
  await page.getByRole('button', { name: /^Filters/ }).click();
  await page.getByRole('checkbox', { name: 'Plants and PlantGroups' }).uncheck();
  await page.getByRole('button', { name: 'Done', exact: true }).click();
  await page.goBack(); assert(!page.url().includes('plants=false'), 'Back failed');
  await page.goForward(); assert(page.url().includes('plants=false'), 'Forward failed');
  await page.getByRole('button', { name: 'Saved views', exact: true }).click();
  await page.getByRole('button', { name: 'Open Synthetic seed origins' }).click();
  assert(page.url().endsWith('#/map?plants=false'), 'legacy Saved View route changed');
  assert(await page.getByRole('searchbox', { name: 'Botanical identity', exact: true }).inputValue() === '', 'saved query not restored');
  report.checks.push('actual browser Back/Forward and legacy Saved View restoration');
  // Reopen same Saved View clears selected site.
  await page.locator('.leaflet-marker-icon').first().focus(); await page.keyboard.press('Enter');
  await page.getByRole('button', { name: 'Saved views', exact: true }).click();
  await page.getByRole('button', { name: 'Open Synthetic seed origins' }).click();
  assert(await page.getByRole('heading', { name: 'Recorded origin sites' }).isVisible(), 'same view retained stale selection');
  report.checks.push('identical Saved View reopening clears inspection');
  // Record empty/failure states without writing any data.
  for (const [name, value] of [['no-sites', { total_provenance_sites: 0, coordinate_less_sites: 0, sites: [] }], ['no-coordinates', { total_provenance_sites: 2, coordinate_less_sites: 2, sites: [] }]]) { data = value; await page.reload(); await page.locator('.origins-overview').waitFor(); await capture(name); }
  data = fixture; failApi = true; await page.reload(); await page.getByRole('alert').waitFor(); await capture('api-failure'); failApi = false; await page.getByRole('button', { name: 'Retry', exact: true }).click(); await page.locator('.origins-overview').waitFor();
  report.checks.push('no-site/no-coordinate/API failure and Retry states');
  assert(report.providerRequests.length > 0, 'provider request audit empty');
  assert(report.providerRequests.every(({ url, referer }) => /^https:\/\/[abc]\.tile\.openstreetmap\.org\/\d+\/\d+\/\d+\.png$/.test(url) && referer === null), 'provider request leaked data/referrer');
  report.checks.push('outgoing provider requests contain only tile z/x/y; no referrer');
  assert(report.consoleErrors.length === 0, 'runtime errors: ' + report.consoleErrors.join('; '));
  const zoomBefore = await page.evaluate(() => ({ width: innerWidth, ratio: devicePixelRatio }));
  await page.keyboard.press('Control++');
  report.zoomAttempt = { before: zoomBefore, after: await page.evaluate(() => ({ width: innerWidth, ratio: devicePixelRatio })), method: 'headless keyboard Control++' };
  await page.keyboard.press('Control+0');
  fs.writeFileSync(path.join(__dirname, 'measurements.json'), JSON.stringify(report, null, 2) + '\n');
  await browser.close(); console.log(JSON.stringify({ checks: report.checks, measurements: report.measurements, requests: report.providerRequests.length }, null, 2));
})().catch(error => { console.error(error); process.exit(1); });
