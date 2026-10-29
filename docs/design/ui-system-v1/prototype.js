const data = await fetch("./data.json").then((r) => r.json());
const q = new URLSearchParams(location.search);
const page = q.get("page") || "dashboard";
const variant = q.get("variant") === "b" ? "b" : "a";
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const href = (p, v = "a") => `prototype.html?page=${p}&variant=${v}`;
const icon = (name) =>
  `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${{ search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>', filter: '<path d="M3 4h18l-7 8v7l-4 2v-9Z"/>', add: '<path d="M12 4v16M4 12h16"/>', edit: '<path d="m4 16-1 5 5-1L20 8l-4-4ZM13.5 6.5l4 4"/>', close: '<path d="m6 6 12 12M18 6 6 18"/>', menu: '<path d="M3 6h18M3 12h18M3 18h18"/>', more: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>', back: '<path d="m10 5-7 7 7 7M3 12h18"/>', saved: '<path d="M6 3h12v18l-6-4-6 4Z M9 7h6M9 10h6"/>', leaf: '<path d="M19 3C6 2 2 10 7 17c8 5 14-4 12-14ZM4 21 15 8"/>' }[name] || '<circle cx="12" cy="12" r="7"/>'}</svg>`;
const button = (text, attrs = "", kind = "") =>
  `<button type="button" class="${kind}" ${attrs}>${text}</button>`;
const link = (text, p, kind = "") =>
  `<a class="button ${kind}" href="${href(p)}">${text}</a>`;
const badge = (text, kind = "") =>
  `<span class="badge ${kind}">${esc(text)}</span>`;
const rows = (kind) => data.records.filter((r) => r.kind === kind);
const record = (key) => data.records.find((r) => r.key === key);
const name = (r) =>
  `<i class="scientific">${esc(r.scientificName || r.label)}</i>${r.cultivar ? " <span>‘" + esc(r.cultivar) + "’</span>" : ""}`;
const photoFor = (r) =>
  data.photos.find(
    (p) => p.species === r.scientificName || p.species === r.label,
  );
const visual = (r, cls = "") => {
  const p = photoFor(r);
  return p
    ? `<img class="${cls}" src="/photos/${p.file}" alt="${esc(p.species)} — licensed reference illustration">`
    : `<span class="placeholder ${cls}" aria-label="No assigned image">${icon("leaf")}</span>`;
};
const referenceNote =
  "Photographs are licensed v5 species illustrations, not proof of these fictional specimens or saved cover/primary assignments.";
const field = (label, control, help = "", required = false) => {
  const name = control.match(
    /<(?:input|select|textarea)[^>]*name="([^"]+)"/,
  )?.[1];
  if (!name) throw new Error("Design field requires a named control");
  const id = `field-${name}`;
  const labelled = control.replace(
    /<(input|select|textarea)/,
    `<$1 id="${id}"${help ? ` aria-describedby="${id}-help"` : ""}`,
  );
  return `<div class="field"><label class="label" for="${id}">${label}${required ? ' <span class="required" aria-hidden="true">*</span>' : ""}</label>${labelled}${help ? `<p id="${id}-help">${help}</p>` : ""}</div>`;
};
const input = (name, value = "", attrs = "") =>
  `<input name="${name}" value="${esc(value)}" ${attrs}>`;
const select = (name, options) =>
  `<select name="${name}">${options.map((o) => `<option>${esc(o)}</option>`).join("")}</select>`;
const search = (placeholder) =>
  `<div class="search">${icon("search")}<label><span class="sr">Search this design example</span><input type="search" id="example-search" placeholder="${placeholder}"></label></div>`;
const pages = [
  ["dashboard", "Dashboard"],
  ["seeds", "Seeds / SeedLots"],
  ["plants", "Plants / PlantGroups"],
  ["identities", "Botanical Identities"],
  ["identity", "Identity hub"],
  ["journal", "Journal"],
  ["history", "History"],
  ["schedule", "Schedule List"],
  ["calendar", "Schedule Calendar"],
  ["locations", "Locations hierarchy"],
  ["location", "Location detail"],
  ["suppliers", "Suppliers"],
  ["orders", "Orders"],
  ["order", "Order detail"],
  ["form", "Create / Edit form"],
  ["record", "Collection record detail"],
  ["supplier", "Supplier detail"],
  ["specialized", "Maps / Tree boundary"],
  ["media", "Media dependency"],
  ["components", "Component design specimens"],
];
const alternatives = new Set([
  "dashboard",
  "seeds",
  "plants",
  "identities",
  "form",
]);
const selectedPages = Object.fromEntries(pages);
if (!selectedPages[page]) throw new Error("Unknown design specimen");
const studio = `<div class="studio"><a href="index.html">UI System v1 · Gate A</a><label>Page <select id="page-choice">${pages.map(([id, title]) => `<option value="${id}" ${page === id ? "selected" : ""}>${title}</option>`).join("")}</select></label>${alternatives.has(page) ? `<a href="${href(page, variant === "a" ? "b" : "a")}">Compare approach ${variant === "a" ? "B" : "A"}</a>` : ""}<label>Palette <select id="palette"><option>botanical</option><option>herbarium</option><option>mineral</option></select></label><label>Appearance <select id="appearance"><option>light</option><option>dark</option></select></label><span class="studio-note">Static product design · local fixture only · no saved changes</span></div>`;
document.querySelector("#studio").innerHTML = studio;
const groups = [
  ["Overview", [["dashboard", "Dashboard"]]],
  [
    "Collection",
    [
      ["seeds", "Seeds"],
      ["sowings", "Sowings"],
      ["plants", "Plants"],
      ["harvests", "Harvests"],
      ["locations", "Locations"],
    ],
  ],
  [
    "Activity",
    [
      ["journal", "Journal"],
      ["history", "History"],
      ["schedule", "Schedule"],
    ],
  ],
  [
    "Explore",
    [
      ["identities", "Botanical identities"],
      ["taxonomy", "Taxonomy"],
      ["media", "Media"],
      ["geography", "Geography"],
    ],
  ],
  [
    "Sourcing",
    [
      ["suppliers", "Suppliers"],
      ["orders", "Orders"],
    ],
  ],
];
const appPage = (id) =>
  ({
    sowings: "specialized",
    harvests: "specialized",
    taxonomy: "specialized",
    geography: "specialized",
  })[id] || id;
const activePage =
  {
    identity: "identities",
    location: "locations",
    calendar: "schedule",
    order: "orders",
    form: "seeds",
    record: q.get("from") || "seeds",
    supplier: "suppliers",
  }[page] || page;
const brand = `<a class="brand" href="${href("dashboard")}">${icon("leaf")}<span>Florabase</span></a>`;
const nav = groups
  .map(
    ([label, items]) =>
      `<div class="nav-group"><div class="nav-label">${label}</div>${items.map(([id, title]) => `<a class="nav-item" ${activePage === id ? 'aria-current="page"' : ""} href="${href(appPage(id))}">${icon(id === "dashboard" ? "layers" : id === "media" ? "layers" : "leaf")}${title}</a>`).join("")}</div>`,
  )
  .join("");
const utilities = `<small>Synthetic UI Review</small><a class="nav-item" href="${href("components")}">Settings</a>${button("Appearance", "data-appearance-toggle", "quiet")}${button("Sign out", 'data-prototype-action="Authentication remains owned by the app; this design preview has no session."', "quiet")}`;
function header(
  area,
  title,
  description,
  {
    create = "",
    createPage = "form",
    filters = true,
    saved = true,
    placeholder = "Search records…",
    tools = true,
  } = {},
) {
  return `<nav class="crumb" aria-label="Breadcrumb"><span>${area}</span><span>/</span><span aria-current="page">${title}</span></nav><header class="page-head"><div><h2>${title}</h2><p class="description">${description}</p></div>${tools ? `<div class="head-tools">${search(placeholder)}${filters ? button(icon("filter") + "Filters", ["seeds", "plants", "components"].includes(page) ? 'data-open="filters"' : 'data-prototype-action="Keep this page’s existing domain filters and current query; the live drawer specimen is demonstrated on Seeds."') : ""}${saved ? button(icon("saved") + "Saved views", 'data-open="saved"') : ""}${create ? (page === "seeds" ? link(icon("add") + create, createPage, "primary") : button(icon("add") + create, 'data-prototype-action="This action retains its current domain-specific form; compare form hierarchy using the SeedLot create/edit specimens."', "primary")) : ""}</div>` : ""}</header>`;
}
function metrics() {
  return `<div class="metrics" aria-label="Current collection snapshot">${[
    ["Plants", "17", "Active individual records", "plants"],
    ["Plant groups", "7", "Groups, not plant totals", "plants"],
    ["Seed lots", "40", "Active · quantities may be unknown", "seeds"],
    ["Sowings", "12", "Active propagation records", "specialized"],
  ]
    .map(
      ([label, value, context, p]) =>
        `<a class="metric" href="${href(p)}"><span>${label}</span><b>${value}</b><small>${context}</small></a>`,
    )
    .join("")}</div>`;
}
const tasks = rows("schedule").slice(0, 5);
function workQueue(limit = 5) {
  return `<div class="work-queue">${tasks
    .slice(0, limit)
    .map(
      (t) =>
        `<div class="item" data-searchable><div class="date"><time>${t.date}</time><p>${badge("Overdue", "attention")}</p></div><div><h3>${esc(t.title)}</h3><p>${esc(record(t.target)?.label || "Collection")}</p><p>Planned work · ${esc(t.activityKind === "inspect" ? "Inspect" : "General follow-up")}</p></div><div class="actions">${button("Open", `data-open="activity" data-activity="${t.key}"`)}</div></div>`,
    )
    .join("")}</div>`;
}
function fact(label, value) {
  return `<div class="fact"><dt>${label}</dt><dd>${value}</dd></div>`;
}
function photoCard(r, extra = "") {
  return `<article class="photo-card" data-searchable>${visual(r)}<div class="body"><h3>${name(r)}</h3><p>${esc(r.commonName || r.label)}</p>${extra}<small class="illustration">Reference illustration / placeholder</small><div class="actions" style="margin-top:12px">${link("Identity hub example", "identity", "quiet")}</div></div></article>`;
}
function dashboard() {
  let content;
  if (variant === "a")
    content = `${metrics()}<div class="columns"><section><div class="section-head"><h3>Attention & upcoming</h3>${link("Open Schedule", "schedule", "quiet")}</div><div class="chips">${badge("9 overdue", "attention")}${badge("7 due today")}${badge("5 in next 7 days")}</div>${workQueue()}</section><div><section><div class="section-head"><h3>Recent recorded activity</h3>${link("Open History", "history", "quiet")}</div>${recent()}</section><section class="section rule"><h3>Collection context</h3><p style="margin-top:12px"><b>33</b> botanical identities in current material, including stored harvests.</p><div class="actions section">${link("Browse identities", "identities")}${link("Open Geography", "specialized", "quiet")}</div></section></div></div>`;
  else
    content = `<div class="columns"><section><div class="section-head"><h3>Your botanical collection</h3>${link("Browse identities", "identities", "quiet")}</div><div class="botanical-grid" style="grid-template-columns:repeat(2,minmax(0,1fr))">${rows(
      "identity",
    )
      .filter(photoFor)
      .slice(0, 4)
      .map((r) => photoCard(r))
      .join(
        "",
      )}</div><p class="excerpt">${referenceNote}</p></section><section><div class="section-head"><h3>Next work</h3>${link("Schedule", "schedule", "quiet")}</div>${workQueue(3)}<div class="section rule"><h3>Current holdings</h3><dl class="facts">${fact("Individual Plants", "17 active records")}${fact("Plant groups", "7 active groups")}${fact("Seed lots", "40 active lots")}${fact("Sowings", "12 active records")}</dl></div></section></div>`;
  return (
    header(
      "Overview",
      "Dashboard",
      "Current holdings, planned work and recent recorded facts.",
      { tools: false },
    ) + content
  );
}
function recent() {
  return `<div class="timeline"><div class="event"><time>Recorded 26 Oct 2026 · UTC</time><div><span class="badge">History</span><h3>Harvest recorded</h3><p>Preview — Mixed group collection</p><a href="${href("history")}">Open recorded fact</a></div></div><div class="event"><time>26 Oct 2026</time><div><span class="badge">Journal</span><h3>Repotting</h3><p>Preview — Basil mother plant</p><a href="${href("journal")}">Read observation</a></div></div></div>`;
}
const seedKeys = [
  "seed:03",
  "seed:01",
  "seed:00",
  "seed:06",
  "seed:12",
  "seed:23",
  "seed:14",
  "seed:29",
];
const seedExamples = seedKeys.map(record).filter(Boolean);
const plantExamples = rows(q.get("type") === "group" ? "group" : "plant")
  .filter((r) => r.state === "active")
  .slice(0, 8);
let visibleDirectory = [];
function results(total, examples) {
  return `<div class="results"><span><b>${total}</b> active records · <span id="example-count">${examples}</span> fixture examples shown</span>${button("Select records", "data-bulk-toggle")}</div><div id="bulk-bar" class="chips" hidden><span id="bulk-count">0 selected</span>${button("Select visible", "data-select-visible")}${button("Actions", 'data-open="bulk"')}${button("Exit selection", "data-bulk-toggle")}</div>`;
}
function recordTable(records, type) {
  const tableHead =
    type === "seed"
      ? ["Identity / lot", "Remaining", "Storage", "Acquired", ""]
      : [
          "Identity / record",
          records[0]?.kind === "group" ? "Group size (plants)" : "Type",
          "Location",
          "Lifecycle",
          "",
        ];
  return `<div class="surface"><table class="record-table"><colgroup><col style="width:35%"><col style="width:17%"><col style="width:20%"><col style="width:14%"><col style="width:14%"></colgroup><thead><tr>${tableHead.map((x) => `<th scope="col">${x}</th>`).join("")}</tr></thead><tbody>${records.map((r) => `<tr data-searchable data-record="${esc(r.key)}"><td><label class="bulk-choice" hidden><input type="checkbox" aria-label="Select ${esc(r.label)}"></label><span class="identity">${name(r)}</span><small>${esc(r.label)}</small></td><td data-label="${tableHead[1]}">${type === "seed" ? esc(r.quantity) : esc(r.kind === "group" ? r.quantity : "Plant")}</td><td data-label="${tableHead[2]}">${esc(r.location)}</td><td data-label="${tableHead[3]}">${type === "seed" ? esc(r.date) : badge("Active", "active")}</td><td><button class="row-action" data-inspect="${esc(r.key)}" aria-label="Preview ${esc(r.label)}">Preview</button></td></tr>`).join("")}</tbody></table></div>`;
}
function richRows(records, type) {
  return `<div class="surface rows">${records.map((r) => `<article class="record-row" data-searchable data-record="${esc(r.key)}">${visual(r)}<div><h3 class="record-name">${name(r)}</h3><p>${esc(r.label)}</p></div><div><strong>${type === "seed" ? esc(r.quantity) : badge("Active", "active")}</strong><p>${esc(r.location)}</p></div>${button("Preview", `data-inspect="${esc(r.key)}"`)}</article>`).join("")}</div><p class="excerpt">${referenceNote}</p>`;
}
function directory(type) {
  const seed = type === "seed";
  visibleDirectory = seed ? seedExamples : plantExamples;
  const title = seed ? "Seeds" : "Plants";
  let content;
  if (seed)
    content =
      variant === "a"
        ? recordTable(visibleDirectory, "seed")
        : richRows(visibleDirectory, "seed");
  else
    content =
      variant === "a"
        ? recordTable(visibleDirectory, "plant")
        : `<div class="botanical-grid">${visibleDirectory.map((r) => `<article class="photo-card" data-searchable data-record="${r.key}">${visual(r)}<div class="body"><h3>${name(r)}</h3><p>${esc(r.label)}</p>${badge("Active", "active")}${r.kind === "group" ? `<p>Group size: ${esc(r.quantity)} plants</p>` : ""}<small class="illustration">Reference illustration / placeholder</small><div class="actions section">${button("Preview", `data-inspect="${r.key}"`)}</div></div></article>`).join("")}</div><p class="excerpt">${referenceNote}</p>`;
  return (
    header(
      "Collection",
      title,
      seed
        ? "Physical lots, remaining stock and recorded acquisition."
        : "Individual plants and managed groups, with their current context.",
      {
        create: seed ? "New seed lot" : "New plant or group",
        placeholder: seed
          ? "Search lots, identity or location…"
          : "Search plants, identity or location…",
      },
    ) +
    `<div class="toolbar"><div class="segmented">${seed ? '<span class="badge active">Active</span><span class="badge">History</span>' : button("Plants", `data-type="plant" aria-pressed="${q.get("type") !== "group"}"`) + button("Plant groups", `data-type="group" aria-pressed="${q.get("type") === "group"}"`)}</div><div class="chips" style="margin:0">${badge("Lifecycle: Active")}</div></div>${results(seed ? 40 : q.get("type") === "group" ? 7 : 17, visibleDirectory.length)}<div class="directory-frame" id="directory-frame"><div>${content}<p class="excerpt">Design excerpt from existing v5 fixture; not a new server pagination contract.</p></div><aside class="inspector" id="inspector" hidden aria-label="Selected record inspector"></aside></div>`
  );
}
function identities() {
  const list = [
    ...rows("identity").filter(photoFor),
    ...rows("identity").filter((r) => !photoFor(r)),
  ].slice(0, 10);
  return (
    header(
      "Explore",
      "Botanical identities",
      "Reference identity and its real collection footprint.",
      {
        create: "New botanical identity",
        filters: false,
        placeholder: "Search names and cultivars…",
      },
    ) +
    `<div class="results"><span>37 identities · ${list.length} fixture examples</span><span>${variant === "a" ? "Visual reference index" : "Analytical index"}</span></div>${variant === "a" ? `<div class="botanical-grid">${list.map((r) => photoCard(r, `<p>${esc(r.coverage)}</p>`)).join("")}</div><p class="excerpt">Illustrations are design fixtures. Existing cover assignment remains explicit, not inferred from linked-record media.</p>` : `<div class="surface"><table class="record-table"><thead><tr><th>Botanical identity</th><th>Common name</th><th>Active collection coverage</th><th></th></tr></thead><tbody>${list.map((r) => `<tr data-searchable><td><span class="identity">${name(r)}</span></td><td>${esc(r.commonName || "Not recorded")}</td><td>${esc(r.coverage)}</td><td>${link("Open hub", "identity", "quiet")}</td></tr>`).join("")}</tbody></table></div><p class="excerpt">Active SeedLot/Plant counts from the real captured directory; full footprint remains on the hub.</p>`}`
  );
}
function identity() {
  return (
    header(
      "Explore / Botanical identities",
      "Acer palmatum",
      "Review v5 — Japanese maple",
      { tools: false },
    ) +
    `<div class="toolbar"><p>Collection-local botanical identity</p><div class="actions">${button("Add to collection", 'data-open="add"', "primary")}${link(icon("edit") + "Edit identity", "form")}</div></div><div class="tabs" role="tablist" aria-label="Identity sections">${["Overview", "Reference", "Taxonomy", "Maps", "Media", "History"].map((t, i) => button(t, `role="tab" aria-selected="${i === 0}" aria-controls="identity-${i}" id="identity-tab-${i}" tabindex="${i === 0 ? 0 : -1}" data-tab="identity-${i}"`)).join("")}</div><section class="tab-panel" role="tabpanel" aria-labelledby="identity-tab-0" id="identity-0"><h3>Collection footprint</h3><div class="footprint">${[
      ["Seed lots", 1, "seeds"],
      ["Sowings", 1, "specialized"],
      ["Plants", 1, "plants"],
      ["Plant groups", 1, "plants"],
      ["Harvests", 0, "specialized"],
    ]
      .map(
        ([label, n, p]) =>
          `<a href="${href(p)}"><b>${n}</b>${label}<small>${n ? "1 active" : "No recorded Harvests"}</small></a>`,
      )
      .join(
        "",
      )}</div><p class="excerpt">Record counts include history. Groups are separate; Harvests do not indicate stored remainder.</p><div class="columns section rule"><section><h3>Botanical summary</h3><p class="section reading">Synthetic reference text from the v5 Japanese maple fixture. Local names and reference assertions do not establish specimen lineage.</p><dl class="facts section">${fact("GBIF reference", "No confirmed reference")}${fact("Native ranges", "2 structured assertions · synthetic review data")}${fact("Taxonomy", "Optional WFO source not configured")}</dl></section><section><h3>Recorded context</h3><div class="timeline"><div class="event"><time>13 Oct 2026</time><div><span class="badge">Journal</span><h3>Repotting</h3><p>Review v5 — direct plant 04</p></div></div></div><div class="section">${link("Open reference", "identity", "quiet")}</div></section></div></section>${["Reference", "Taxonomy", "Maps", "Media", "History"].map((t, i) => `<section class="tab-panel" role="tabpanel" id="identity-${i + 1}" aria-labelledby="identity-tab-${i + 1}" hidden><h3>${t}</h3>${{ Reference: '<p class="reading section">The existing textual reference profile remains here, with source/uncertainty clearly separated from owned-material facts.</p>', Taxonomy: '<p class="note section">WFO is not configured. Local identity and saved confirmation evidence remain accessible; no placed hierarchy is fabricated.</p>', Maps: '<div class="columns section"><section><h3>Structured native range</h3><p class="section">2 assertions · synthetic reference data</p></section><section><h3>Recorded origins</h3><p class="section">Existing collection-origin evidence remains separate from reference ranges and observed occurrence density.</p></section></div>', Media: '<div class="state section"><h3>No identity cover recorded</h3><p>Linked-record images remain a separate, bounded gallery; they are not automatically covers.</p></div>', History: '<div class="timeline section"><div class="event"><time>13 Oct 2026</time><div><span class="badge">Journal</span><h3>Repotting</h3><p>Review v5 — direct plant 04</p></div></div></div>' }[t]}</section>`).join("")}`
  );
}
function activity(history = false) {
  return (
    header(
      "Activity",
      history ? "History" : "Journal",
      history
        ? "Read-only operational facts with their recorded evidence."
        : "Operator-recorded work, observations and notes.",
      {
        create: history ? "" : "Record",
        createPage: "form",
        placeholder: history ? "Search History…" : "Search Journal…",
      },
    ) +
    `<div class="results"><span>${history ? "Authoritative recorded facts" : "7 recorded entries"}</span><span>Dates retain their recorded precision</span></div><div class="timeline">${(history
      ? [
          [
            "Recorded 26 Oct 2026 · UTC",
            "History",
            "Harvest recorded",
            "Preview — Mixed group collection",
            "4 material lines; collected quantities are separate from current stored remainder.",
          ],
          [
            "Completion recorded 26 Oct 2026 · UTC",
            "History",
            "Scheduled work marked completed",
            "Preview — Completed repot with explicit Event",
            "Completion recorded; a separate Journal occurrence is linked in Schedule.",
          ],
          [
            "26 Oct 2026",
            "Journal",
            "Repotting",
            "Preview — Basil mother plant",
            "Operator-recorded occurrence.",
          ],
          [
            "Recorded 26 Oct 2026 · UTC",
            "History",
            "Scheduled work marked completed",
            "Preview — Completed inspection without Event",
            "Completion recorded without a Journal occurrence.",
          ],
        ]
      : [
          [
            "26 Oct 2026",
            "Journal",
            "Repotting",
            "Preview — Basil mother plant",
            "Synthetic Feature Review data; no real collection or provenance claims.",
          ],
          [
            "13 Oct 2026",
            "Journal",
            "Repotting",
            "Review v5 — direct plant 04",
            "Synthetic operator-recorded observation.",
          ],
          [
            "12 Oct 2026",
            "Journal",
            "Fruiting",
            "Review v5 — direct plant 03",
            "This is a recorded occurrence, not a persistent Plant lifecycle status.",
          ],
          [
            "11 Oct 2026",
            "Journal",
            "Flowering",
            "Review v5 — direct plant 02",
            "Recorded flowering; no claim that all current plants are flowering.",
          ],
          [
            "Recorded 26 Oct 2026 · UTC",
            "Journal",
            "Observation",
            "Preview — Nursery aloe",
            "Occurrence date unknown; recorded timestamp remains a different fact.",
          ],
        ]
    )
      .map(
        ([date, source, title, target, note]) =>
          `<article class="event" data-searchable><time>${date}</time><div class="event-body">${badge(source)}<h3>${title}</h3><a href="${href("plants")}">${target}</a><details><summary>Recorded note</summary><p>${note}</p></details></div></article>`,
      )
      .join("")}</div>`
  );
}
function schedule(calendar = false) {
  return (
    header(
      "Activity",
      "Schedule",
      "Future intended work for your collection.",
      {
        create: "Schedule activity",
        createPage: "form",
        saved: false,
        placeholder: "Search planned work…",
      },
    ) +
    `<div class="toolbar"><div class="segmented"><a class="button" href="${href("schedule")}" ${!calendar ? 'aria-current="page"' : ""}>List</a><a class="button" href="${href("calendar")}" ${calendar ? 'aria-current="page"' : ""}>Calendar</a></div>${badge("Status: Planned / Active")}</div>${calendar ? calendarBody() : `<div class="results"><span>24 planned activities · fixture excerpt below</span><span>Overdue remains planned</span></div><section><h3>Overdue</h3>${workQueue()}</section><section class="section rule"><h3>Due today</h3><div class="work-queue"><div class="item"><time>2026-10-26</time><div><h3>Preview — Water basil mother plant</h3><p>Plant · Preview — Basil mother plant</p></div>${button("Open", activityAttrs("2026-10-26"))}</div></div></section>`}`
  );
}
function activityAttrs(date) {
  const activity = rows("schedule").find((record) => record.date === date);
  return activity
    ? `data-open="activity" data-activity="${activity.key}"`
    : 'data-prototype-action="This excerpt preserves the existing day/task selection workflow; only the v5 inspection previews are interactive here."';
}
function calendarBody() {
  const byDay = {
    18: "Inspection 1",
    19: "Inspection 2",
    20: "Inspection 3",
    21: "Inspection 4",
    22: "Inspection 5",
    23: "Inspection 6",
    24: "Inspection 7",
    25: "Inspection 8",
    26: "7 planned activities",
    29: "Check seed packet storage",
    31: "2 planned activities",
  };
  let cells = ["", "", ""];
  for (let i = 1; i <= 31; i++) cells.push(i);
  while (cells.length % 7) cells.push("");
  return `<div class="toolbar"><h3>October 2026</h3><div class="actions">${button("Previous month", 'data-prototype-action="Calendar period controls retain the existing month URL contract."')}${button("Today", 'data-prototype-action="Snapshot date:26 October2026."')}${button("Next month", 'data-prototype-action="Calendar period controls retain the existing month URL contract."')}</div></div><p class="excerpt" style="margin-bottom:14px">20 planned activities in October · excerpt shows existing fixed review anchors, without invented duration bars.</p><div class="calendar-wide surface"><table class="calendar-table"><thead><tr>${["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => `<th scope="col">${d}</th>`).join("")}</tr></thead><tbody>${Array.from(
    { length: cells.length / 7 },
    (_, w) =>
      "<tr>" +
      cells
        .slice(w * 7, w * 7 + 7)
        .map(
          (d) =>
            `<td class="${d === 26 ? "today" : ""}">${d ? `<time datetime="2026-10-${String(d).padStart(2, "0")}">${d}</time>${byDay[d] ? button(byDay[d], activityAttrs(`2026-10-${String(d).padStart(2, "0")}`), "calendar-event") : ""}` : ""}</td>`,
        )
        .join("") +
      "</tr>",
  ).join(
    "",
  )}</tbody></table></div><div class="agenda"><h3>October agenda</h3>${workQueue()}<div class="work-queue"><div class="item"><time>26 Oct</time><div><h3>7 planned activities</h3><p>Select a day to inspect its real activities.</p></div>${button("Open day", activityAttrs("2026-10-26"))}</div></div></div>`;
}
function locationDetail(full = false) {
  return `<div class="toolbar">${full ? "<h3>Recorded context</h3>" : "<h3>Review v5 collection</h3>"}${full ? "" : link("Open full detail", "location", "quiet")}</div><p class="muted small">Physical hierarchy · Active</p><dl class="facts section">${fact("Parent", "Root location")}${fact("Usage scopes", "Plants, Sowings, Seed lots, Stored material")}${fact("Children", "1 child location")}</dl><h3 class="section">Recorded usage</h3><table class="usage section"><thead><tr><th>Record type</th><th>Directly here</th><th>Including sublocations</th></tr></thead><tbody>${[
    ["Plants", 12],
    ["Plant groups", 6],
    ["Sowings", 12],
    ["Seed lots", 20],
    ["Stored material", 3],
  ]
    .map(
      ([label, n]) =>
        `<tr><th scope="row">${label}</th><td>0</td><td>${n}</td></tr>`,
    )
    .join(
      "",
    )}</tbody></table><p class="excerpt">Counts are records, never individuals within groups, seed quantities or material mass.</p><div class="actions section">${button("Edit location", 'data-prototype-action="Location fields and explicit scopes remain owned by its existing edit form."')}${button("Create child", 'data-prototype-action="Existing explicit child-location creation; scopes do not inherit."')}</div>`;
}
function locations(detail = false) {
  return (
    header(
      "Collection / Locations",
      detail ? "Review v5 collection" : "Locations",
      detail
        ? "Physical position, explicit scopes and inclusive usage."
        : "Find and manage where collection material is kept.",
      {
        create: detail ? "" : "New location",
        tools: !detail,
        placeholder: "Search physical locations…",
      },
    ) +
    (detail
      ? locationDetail(true)
      : `<div class="results"><span>17 active locations · hierarchy excerpt</span>${badge("State: Active")}</div><div class="tree-layout"><div class="surface location-tree"><details><summary>Preview collection</summary><a href="${href("location")}">Preview nursery</a></details><details open><summary>Review v5 collection</summary><p class="path">12 Plants ·6 groups ·12 Sowings ·20 SeedLots ·3 stored records incl.</p>${rows(
          "location",
        )
          .filter((r) => r.parent)
          .slice(0, 5)
          .map(
            (r, i) =>
              `<details ${i < 2 ? "open" : ""}><summary>${esc(r.label)}</summary><a href="${href("location")}">Open location detail</a><p class="path">Physical parent/child relationship; scopes explicit.</p></details>`,
          )
          .join(
            "",
          )}</details></div><aside class="inspector" aria-label="Selected location">${locationDetail()}</aside></div>`)
  );
}
function suppliers() {
  return (
    header(
      "Sourcing",
      "Suppliers",
      "Direct acquisition sources, contacts and linked material.",
      {
        create: "New supplier",
        filters: false,
        placeholder: "Search suppliers…",
      },
    ) +
    `<div class="results"><span>10 Suppliers · selected fixture examples</span><span>No invented Order status or purchase totals</span></div><div class="surface rows">${rows(
      "supplier",
    )
      .slice(0, 7)
      .map(
        (r) =>
          `<article class="record-row" data-searchable><span class="placeholder">${icon("leaf")}</span><div><h3>${esc(r.label)}</h3><p>Existing Supplier record · biological origin remains separate</p></div>${badge("Active", "active")}<a class="button quiet" href="${href("supplier")}&record=${encodeURIComponent(r.key)}">Open detail</a></article>`,
      )
      .join("")}</div>`
  );
}
function orders(detail = false) {
  if (detail)
    return (
      header(
        "Sourcing / Orders",
        "Review v5 PO-010",
        "Purchase transaction · Supplier unknown",
        { tools: false },
      ) +
      `<div class="toolbar"><p>0 physical seed lots linked</p><div class="actions">${link("Add seed lot", "form", "primary")}${button("Link existing seed lot", 'data-prototype-action="Existing ORDER-001 reconciliation remains authoritative."')}${button("Edit Order", 'data-prototype-action="Order editing retains its separate transaction contract."')}</div></div><dl class="facts reading section">${fact("Order date", "2026-08-10")}${fact("Total price", "EUR 34.50")}${fact("Supplier", "Unknown supplier")}${fact("Physical packets", "0 linked SeedLots")}</dl><p class="excerpt">The total transaction price is not allocated per lot. Order date does not fill a SeedLot acquisition date.</p><section class="section rule"><h3>Linked physical seed lots</h3><p class="section">No seed lots are linked to this Order yet.</p></section><details class="section"><summary>Danger zone</summary><p class="section">An Order can be removed only when no SeedLots are linked.</p>${button("Delete Order", 'data-open="confirm"', "danger")}</details>`
    );
  return (
    header(
      "Sourcing",
      "Orders",
      "Purchase transactions and their separate physical packets.",
      { create: "New Order", placeholder: "Search Orders…" },
    ) +
    `<div class="results"><span>12 Orders · v5 examples shown</span><span>Prices preserve unknown values</span></div><div class="surface"><table class="record-table"><colgroup><col style="width:28%"><col style="width:30%"><col style="width:16%"><col style="width:14%"><col style="width:12%"></colgroup><thead><tr><th>Order</th><th>Supplier</th><th>Date</th><th>Total</th><th></th></tr></thead><tbody>${rows(
      "order",
    )
      .slice(0, 8)
      .map(
        (r) =>
          `<tr data-searchable><td><strong>${esc(r.label)}</strong></td><td data-label="Supplier">${esc(r.supplier)}</td><td data-label="Order date">${esc(r.date)}</td><td data-label="Total price">${esc(r.price)}</td><td>${link("Open", "order", "quiet")}</td></tr>`,
      )
      .join("")}</tbody></table></div>`
  );
}
function form() {
  const editing = q.get("mode") === "edit";
  const essentials = `<section class="form-section" id="essentials"><h3>Identity & physical record</h3><div class="form-grid">${field("Botanical identity", input("identity", editing ? "Acer palmatum" : "", 'required placeholder="Search existing identities…"'), "A shared name does not establish lineage.", true)}${field("Lot label", input("label", "Review v5 — packet 04 — Acer palmatum"))}${field("Lifecycle", select("lifecycle", ["Active", "Exhausted", "Discarded", "Lost"]), "Use Exhausted for an exact known zero.")}${field("Storage location", select("location", ["Not recorded", "Review v5 temperate section"]), "Physical storage, separate from provenance.")}</div></section>`;
  const quantity = `<section class="form-section" id="inventory"><h3>Inventory</h3><div class="form-grid">${field("Quantity knowledge", select("knowledge", editing ? ["Exact", "Unknown", "Approximate"] : ["Unknown", "Exact", "Approximate"]), "Unknown never means zero.")}${field("Unit", select("unit", ["Seeds", "Weight"]))}<div id="quantity-value" ${editing ? "" : "hidden"}>${field("Remaining quantity", input("quantity", editing ? "103" : "", 'type="number" min="0" step="any"'), "Zero and unknown remain different.")}</div></div></section>`;
  const acquisition = `<section class="form-section" id="acquisition"><h3>Acquisition & origin</h3><div class="form-grid">${field("Acquisition source", select("source", ["Purchased", "Gift / exchange", "Collection-produced", "Other"]))}${field("Supplier", input("supplier", editing ? record("seed:03").supplier : "", 'placeholder="Optional Supplier"'))}${field("Acquisition date", `<div class="precision">${select("precision", editing ? ["Complete date", "Unknown", "Year", "Year and month"] : ["Unknown", "Year", "Year and month", "Complete date"])}${input("date", editing ? record("seed:03").date : "", `placeholder="No date recorded" aria-label="Date value" ${editing ? "" : "disabled"}`)}</div>`, "Missing month/day stay missing.")}${field("Precise provenance site", input("provenance", editing ? record("seed:03").provenance : "", 'placeholder="Optional recorded site"'), "Never infer provenance from Supplier or storage.")}${editing ? field("Linked Order", input("order", record("seed:03").order, "readonly"), "Existing transaction relationship; not an acquisition-date or provenance source.") : ""}</div></section>`;
  const notes = `<section class="form-section" id="notes"><h3>Notes & seed details</h3>${field("Notes", '<textarea name="notes" placeholder="Record useful context…"></textarea>')}<p class="muted small">Existing Harvest/viability precision and domain validation remain with the owning form.</p></section>`;
  return (
    header(
      "Collection / Seeds",
      editing ? "Edit seed lot" : "Add seed lot",
      "Keep the physical lot distinct from its identity, source and stock.",
      { tools: false },
    ) +
    `<div class="toolbar"><p class="small muted">${editing ? "Existing record draft · no persisted changes" : "New record draft"}</p><a class="button quiet" href="${href("form", variant)}&mode=${editing ? "create" : "edit"}">${editing ? "Review create state" : "Review edit state"}</a></div><div class="form-workspace"><form id="example-form" novalidate><div id="form-error" class="form-error" role="alert"></div><div class="form-layout"><nav class="form-nav" aria-label="Form sections">${[
      ["essentials", "Identity & record"],
      ["inventory", "Inventory"],
      ["acquisition", "Acquisition & origin"],
      ["notes", "Notes & details"],
    ]
      .map(
        ([id, label], i) =>
          `<a href="#${id}" class="${i === 0 ? "current" : ""}" ${variant === "a" ? `data-form-panel="${id}"` : ""}>${label}</a>`,
      )
      .join(
        "",
      )}</nav><div>${variant === "a" ? `<div data-panel="essentials">${essentials}</div><div data-panel="inventory" hidden>${quantity}</div><div data-panel="acquisition" hidden>${acquisition}</div><div data-panel="notes" hidden>${notes}</div>` : essentials + quantity + acquisition + notes}<div class="form-footer">${link("Cancel", "seeds")}<button type="submit" class="primary">${editing ? "Save changes" : "Add seed lot"}</button></div></div></div></form><p class="excerpt">Approach ${variant.toUpperCase()}: ${variant === "a" ? "section navigator with one active panel" : "one continuous semantic form with anchor navigation"}. Contextual Edit retains mounted drafts; Identity keeps independent save boundaries.</p></div>`
  );
}
function boundary(media = false) {
  return (
    header(
      "Explore",
      media ? "Media · integration boundary" : "Specialized workspaces",
      media
        ? "The photographic redesign remains owned by MEDIA-VISUAL-001."
        : "Keep the accepted Map, Tree and Calendar interaction models.",
      { tools: false },
    ) +
    `<div class="note">${media ? "Media has a separate approved implementation candidate, including local F01/F09 corrections. This Gate A package does not replace its gallery or preview." : "Only shared header, action, selection and state framing converge. Scientific evidence and graph/camera ownership remain in their domains."}</div><div class="columns"><section><h3>${media ? "Real baseline, not a new Media mockup" : "Native ranges · retained local scientific workspace"}</h3><img class="baseline-image section" src="/baseline/${media ? "052" : "054"}.jpg" alt="Actual audited ${media ? "Media" : "Native ranges"} baseline"><p class="excerpt">Main ee34874, genuine audit screenshot. No new provider data or source-backed graph is invented.</p></section><section><h3>Preserved contracts</h3><dl class="facts section">${fact("Media", "Record primary, linked media and Identity cover are separate. External load remains explicit.")}${fact("Maps", "Structured native range ≠ observed occurrence density ≠ recorded material origin.")}${fact("Tree", "Accepted hierarchy/camera/fullscreen architecture; WFO source unavailable in audit baseline.")}${fact("Calendar", "Date-only intended work, existing monthly period and mobile agenda. No invented Week view.")}</dl></section></div>`
  );
}
function components() {
  return (
    header(
      "UI System v1",
      "Component design specimens",
      "Gate A contracts illustrated in HTML; production React reuse is Gate B.",
      { tools: false },
    ) +
    `<div class="specimen-grid"><section class="specimen"><h3>Actions & overflow</h3><div class="actions">${button("Primary", 'data-prototype-action="Prototype action only."', "primary")}${button("Secondary", 'data-open="activity"')}${button("Delete", 'data-open="confirm"', "danger")}${button(icon("more") + "More", 'popovertarget="example-menu"')}</div><div popover id="example-menu" class="menu-popover">${link("Open detail", "order", "quiet")}${link("Edit", "form", "quiet")}</div><p>Visible essential labels, 44px house controls; destructive confirmation focuses Cancel.</p></section><section class="specimen"><h3>Filters & Saved Views</h3><div class="actions">${button(icon("filter") + "Filters", 'data-open="filters"')}${button("Saved views", 'data-open="saved"')}</div><p>Existing live filters and dimension counts remain page-owned.</p></section><section class="specimen"><h3>Fields & ReferencePicker contract</h3>${field("Botanical identity", input("reference-example", "Acer palmatum", 'list="reference-options"'), "Existing collection-local reference, not new lineage.")}<datalist id="reference-options"><option>Acer palmatum</option><option>Aloe vera</option></datalist>${field("Precision", select("field-precision", ["Unknown", "Year", "Year and month", "Complete date"]))}<p class="small muted">This native visual specimen does not replace the existing React combobox implementation.</p></section><section class="specimen"><h3>Status & KPI</h3><div class="actions">${badge("Active", "active")}${badge("Overdue", "attention")}${badge("Quantity unknown")}${badge("History")}</div><h3>17 active individual Plant records</h3><p>Groups remain separate; no percentage growth or trend is fabricated.</p></section><section class="specimen"><h3>Empty, loading & error</h3><div class="actions">${button("Empty", 'data-state="empty"')}${button("Loading", 'data-state="loading"')}${button("Error", 'data-state="error"')}</div><div id="example-state" class="state"><h3>No matching records</h3><p>Review the current search and filters.</p></div></section><section class="specimen"><h3>Inspector, row, card & table</h3><p>One content area by default. Open a selected inspector deliberately, close it without losing the row.</p><div class="actions section">${link("Table example", "seeds")}${link("Cards example", "identities")}${link("Detail example", "identity")}</div></section><section class="specimen"><h3>Tokens & six variants</h3><div class="token-grid">${[
      ["Surface", "surface"],
      ["Primary", "primary"],
      ["Muted", "surface-subtle"],
      ["Danger", "danger-subtle"],
    ]
      .map(
        ([title, role]) =>
          `<div class="swatch" style="background:var(--${role});${role === "primary" ? "color:var(--on-primary)" : ""}">${title}</div>`,
      )
      .join(
        "",
      )}</div><p class="excerpt">Use the preview's palette/appearance selectors; typography and geometry remain shared.</p></section><section class="specimen"><h3>Specialized archetypes</h3><div class="actions">${link("Activity", "journal")}${link("Calendar", "calendar")}${link("Spatial boundary", "specialized")}</div><p>No universal component owns API reads, mutations, filters, validation or scientific evidence.</p></section></div>`
  );
}
function collectionRecord() {
  const r = record(q.get("record")) || record("seed:03");
  const from = q.get("from") || "seeds";
  return (
    header(
      "Collection / " + (r.kind === "seed" ? "Seeds" : "Plants"),
      r.label,
      "Recorded identity, location and material remain separate.",
      { tools: false },
    ) +
    `<div class="toolbar">${link(icon("back") + "Back to results", from)}<a class="button primary" href="${href("form", "b")}&mode=edit">Edit seed lot example</a></div><div class="columns section"><section><h3>${name(r)}</h3><dl class="facts section">${fact("Lifecycle", esc(r.state))}${fact("Quantity", esc(r.quantity))}${fact("Physical location", esc(r.location))}${fact("Acquired", esc(r.date))}${fact("Supplier", esc(r.supplier))}</dl></section><section><h3>Related context</h3><p class="section">Identity naming, lineage, acquisition source and physical location retain their existing independent contracts.</p><div class="actions section">${link("Identity hub example", "identity")}${button("Delete", 'data-open="confirm"', "danger")}</div></section></div>`
  );
}
function supplierDetail() {
  const r = record(q.get("record")) || rows("supplier")[0];
  return (
    header(
      "Sourcing / Suppliers",
      r.label,
      "Acquisition source context. Provenance remains recorded separately.",
      { tools: false },
    ) +
    `<div class="toolbar">${link(icon("back") + "Back to Suppliers", "suppliers")}${button("Edit Supplier", 'data-prototype-action="Existing Supplier fields, references and validation remain authoritative."')}</div><dl class="facts reading section">${fact("Name", esc(r.label))}${fact("Lifecycle", badge("Active", "active"))}${fact("Contact details", "Open existing supplied contact fields when recorded; no synthetic contact is invented.")}</dl><section class="section rule"><h3>Linked acquisition context</h3><p class="section">Keep direct SeedLot sources, Plant sources and Orders as distinct groups. Empty groups stay compact.</p>${link("Browse Orders", "orders")}</section>`
  );
}
const renderers = {
  record: collectionRecord,
  supplier: supplierDetail,
  dashboard,
  seeds: () => directory("seed"),
  plants: () => directory("plant"),
  identities,
  identity,
  journal: () => activity(false),
  history: () => activity(true),
  schedule: () => schedule(false),
  calendar: () => schedule(true),
  locations: () => locations(false),
  location: () => locations(true),
  suppliers,
  orders: () => orders(false),
  order: () => orders(true),
  form,
  specialized: () => boundary(false),
  media: () => boundary(true),
  components,
};
const main = renderers[page]();
const dialogs = `<dialog id="filters" class="filter-drawer" aria-labelledby="filter-title"><div class="dialog-head"><h3 id="filter-title">Filters</h3>${button(icon("close") + "Close", "data-close")}</div><div class="filter-fields">${field("Lifecycle", select("filter-lifecycle", ["Active", "History", "All"]))}${field("Botanical identity", input("filter-identity", "", 'placeholder="Find existing identity…"'))}<p class="small muted">Design specimen for inventory fields. Values are local and are not persisted. Search stays unchanged.</p></div><div class="actions">${button("Reset filters", "data-reset-filters")}${button("Done", "data-close")}</div></dialog><dialog id="saved" aria-labelledby="saved-title"><div class="dialog-head"><h3 id="saved-title">Saved views</h3>${button("Close", "data-close")}</div><p>No Saved Views yet. Existing page state is the save target.</p><div class="actions">${button("Save view", 'data-prototype-action="No SavedView is persisted by the design preview."')}</div></dialog><dialog id="confirm" aria-labelledby="confirm-title"><h3 id="confirm-title">Delete this record permanently?</h3><p class="section">Deletion still follows the owning domain's reference and eligibility guards. This preview cannot delete data.</p><div class="actions">${button("Cancel", "data-close data-safe-focus")}${button("Delete record", 'data-prototype-action="Design-only confirmation; no application request exists."', "danger")}</div></dialog><dialog id="activity" aria-labelledby="activity-title"><div class="dialog-head"><h3 id="activity-title">Scheduled activity</h3>${button("Close", "data-close")}</div><h4>Review v5 — planned inspection 1</h4><dl class="facts section">${fact("Due", "2026-10-18")}${fact("Target", "Review v5 — direct plant 01")}${fact("State", "Planned · overdue is derived")}</dl><div class="actions">${button("Close", "data-close")}</div></dialog><dialog id="add" aria-labelledby="add-title"><div class="dialog-head"><h3 id="add-title">Add to collection</h3>${button("Close", "data-close")}</div><div class="actions">${link("Add seed lot", "form")}${link("Add plant", "form")}${button("Start sowing", 'data-prototype-action="Select an eligible active SeedLot through the existing source chooser."')}${button("Record harvest", 'data-prototype-action="Select an eligible Plant or PlantGroup through the existing source chooser."')}</div></dialog><dialog id="bulk" aria-label="Bulk actions"><h3>Selected records</h3><p class="section">Only current visible eligible records; existing 100-record bound.</p><div class="actions">${button("Move to location", 'data-prototype-action="The existing server preview/apply contract remains authoritative; prototype performs no move."')}${button("Close", "data-close")}</div></dialog><dialog id="mobile-navigation" aria-label="Navigation"><div class="dialog-head"><h3>Navigation</h3>${button("Close navigation", "data-close")}</div>${nav}<div class="rail-footer">${utilities}</div></dialog><dialog id="mobile-inspector" aria-label="Selected record preview"><div id="mobile-inspector-content"></div></dialog>`;
document.querySelector("#app").innerHTML =
  `<h1 class="sr">Florabase · product UX design prototype</h1><div class="mobile-top">${brand}${button(icon("menu") + "Menu", 'data-open="mobile-navigation"', "quiet")}</div><div class="shell"><aside class="rail" aria-label="Application navigation">${brand}<nav aria-label="Primary navigation">${nav}</nav><div class="rail-footer">${utilities}</div></aside><main class="workspace">${main}<footer class="credit">Synthetic review snapshot ·26 October 2026 · main ee34874 · Gate A design, not a production screenshot. <a href="index.html">Review decisions</a> · <a href="credits.html">Image attribution</a></footer></main></div><nav class="mobile-nav" aria-label="Mobile navigation">${[
    ["dashboard", "Home"],
    ["seeds", "Seeds"],
    ["specialized", "Sowings"],
    ["plants", "Plants"],
  ]
    .map(
      ([id, label]) =>
        `<a ${id === activePage ? 'aria-current="page"' : ""} href="${href(id)}">${icon(id === "dashboard" ? "layers" : "leaf")}${label}</a>`,
    )
    .join(
      "",
    )}${button(icon("menu") + "More", 'data-open="mobile-navigation"')}</nav>${dialogs}`;
let activeTrigger = null;
const status = (message) => {
  document.querySelector("#prototype-status").textContent = message;
};
function openDialog(id, trigger) {
  const d = document.getElementById(id);
  activeTrigger = trigger;
  d.showModal();
  (
    d.querySelector("[data-safe-focus]") ||
    d.querySelector("button,input,select,a")
  )?.focus();
}
function closeDialog(d) {
  d.close();
  activeTrigger?.focus();
}
function inspectorContent(r) {
  return `<div class="close-line"><div><p class="small muted">Selected ${esc(r.kind)}</p><h3>${name(r)}</h3></div>${button(icon("close") + "Close", "data-close-inspector", "quiet")}</div><p class="small">${esc(r.label)}</p><dl class="facts section">${fact("Lifecycle", esc(r.state))}${fact("Remaining", r.kind === "seed" ? esc(r.quantity) : "Individual record / managed group")}${fact("Location", esc(r.location))}${fact("Acquired", esc(r.date))}</dl><div class="actions"><a class="button primary" href="${href("record")}&record=${encodeURIComponent(r.key)}&from=${page}">Open details</a><a class="button" href="${href("form", "b")}&mode=edit&record=${encodeURIComponent(r.key)}">Edit</a></div>`;
}
document.addEventListener("click", (event) => {
  const target = event.target.closest("button,a");
  if (!target) return;
  if (target.dataset.open) {
    if (target.dataset.activity) {
      const activity = record(target.dataset.activity);
      const dialog = document.querySelector("#activity");
      dialog.querySelector("h4").textContent = activity.title;
      dialog.querySelector("dl").innerHTML =
        fact("Due", esc(activity.date)) +
        fact("Target", esc(record(activity.target)?.label || "Collection")) +
        fact("State", "Planned · overdue is derived");
    }
    openDialog(target.dataset.open, target);
  }
  if (target.hasAttribute("data-close")) closeDialog(target.closest("dialog"));
  if (target.dataset.prototypeAction) status(target.dataset.prototypeAction);
  if (target.hasAttribute("data-appearance-toggle")) {
    document.documentElement.dataset.appearance =
      document.documentElement.dataset.appearance === "dark" ? "light" : "dark";
    document.querySelector("#appearance").value =
      document.documentElement.dataset.appearance;
  }
  if (target.dataset.inspect) {
    const r = record(target.dataset.inspect);
    document
      .querySelectorAll("[data-record]")
      .forEach((el) =>
        el.classList.toggle("selected", el.dataset.record === r.key),
      );
    activeTrigger = target;
    if (matchMedia("(max-width:760px)").matches) {
      document.querySelector("#mobile-inspector-content").innerHTML =
        inspectorContent(r);
      openDialog("mobile-inspector", target);
    } else {
      document.querySelector("#inspector").innerHTML = inspectorContent(r);
      document.querySelector("#inspector").hidden = false;
      document.querySelector("#directory-frame").classList.add("has-inspector");
      document.querySelector("#inspector [data-close-inspector]").focus();
    }
  }
  if (target.hasAttribute("data-close-inspector")) {
    const dialog = target.closest("dialog");
    if (dialog) closeDialog(dialog);
    else {
      document.querySelector("#inspector").hidden = true;
      document
        .querySelector("#directory-frame")
        .classList.remove("has-inspector");
      activeTrigger?.focus();
    }
  }
  if (target.dataset.tab) {
    document.querySelectorAll("[data-tab]").forEach((t) => {
      t.setAttribute("aria-selected", String(t === target));
      t.tabIndex = t === target ? 0 : -1;
    });
    document
      .querySelectorAll(".tab-panel")
      .forEach((p) => (p.hidden = p.id !== target.dataset.tab));
  }
  if (target.dataset.formPanel) {
    event.preventDefault();
    document
      .querySelectorAll("[data-panel]")
      .forEach(
        (p) => (p.hidden = p.dataset.panel !== target.dataset.formPanel),
      );
    document
      .querySelectorAll("[data-form-panel]")
      .forEach((a) => a.classList.toggle("current", a === target));
    document
      .getElementById(target.dataset.formPanel)
      ?.querySelector("input,select,textarea")
      ?.focus();
  }
  if (target.hasAttribute("data-bulk-toggle")) {
    const bar = document.querySelector("#bulk-bar");
    bar.hidden = !bar.hidden;
    document
      .querySelectorAll(".bulk-choice")
      .forEach((c) => (c.hidden = bar.hidden));
    if (bar.hidden)
      document
        .querySelectorAll(".bulk-choice input")
        .forEach((c) => (c.checked = false));
  }
  if (target.hasAttribute("data-select-visible")) {
    document
      .querySelectorAll("[data-searchable]:not([hidden]) .bulk-choice input")
      .forEach((c) => (c.checked = true));
    updateBulk();
  }
  if (target.dataset.state) {
    document.querySelector("#example-state").innerHTML = {
      empty: "<h3>No matching records</h3><p>Review search and filters.</p>",
      loading: '<p role="status">Loading records…</p>',
      error:
        '<div role="alert"><h3>Could not load records</h3><p>Your current query is retained.</p><button type="button" data-state="empty">Retry</button></div>',
    }[target.dataset.state];
  }
  if (target.dataset.type) {
    const type = target.dataset.type;
    document
      .querySelectorAll("[data-type]")
      .forEach((b) => b.setAttribute("aria-pressed", String(b === target)));
    location.href = href("plants", variant) + "&type=" + type;
  }
  if (target.hasAttribute("data-reset-filters")) {
    document.querySelector("[name=filter-lifecycle]").selectedIndex = 0;
    document.querySelector("[name=filter-identity]").value = "";
    status("Prototype filter reset; search unchanged.");
  }
});
function updateBulk() {
  const n = document.querySelectorAll(".bulk-choice input:checked").length;
  const label = document.querySelector("#bulk-count");
  if (label) label.textContent = `${n} selected`;
}
document.addEventListener("change", (e) => {
  if (e.target.matches(".bulk-choice input")) updateBulk();
});
document
  .querySelectorAll("dialog")
  .forEach((d) => d.addEventListener("cancel", () => activeTrigger?.focus()));
document.querySelector("#example-search")?.addEventListener("input", (e) => {
  const value = e.target.value.toLocaleLowerCase();
  let n = 0;
  document.querySelectorAll("[data-searchable]").forEach((row) => {
    row.hidden = !row.textContent.toLocaleLowerCase().includes(value);
    if (!row.hidden) n++;
  });
  const count = document.querySelector("#example-count");
  if (count) count.textContent = n;
});
document.querySelector("#example-form")?.addEventListener("submit", (e) => {
  e.preventDefault();
  const first = e.target.querySelector(":invalid");
  if (first) {
    document.querySelector("#form-error").textContent =
      "Choose a botanical identity.";
    const panel = first.closest("[data-panel]");
    if (panel) {
      document
        .querySelectorAll("[data-panel]")
        .forEach((p) => (p.hidden = p !== panel));
    }
    first.focus();
  } else {
    document.querySelector("#form-error").textContent = "";
    status("Design preview validated locally. No record was created or saved.");
  }
});
document
  .querySelector("#page-choice")
  .addEventListener("change", (e) => (location.href = href(e.target.value)));
document
  .querySelector("#palette")
  .addEventListener(
    "change",
    (e) => (document.documentElement.dataset.palette = e.target.value),
  );
document
  .querySelector("#appearance")
  .addEventListener(
    "change",
    (e) => (document.documentElement.dataset.appearance = e.target.value),
  );
if (q.get("palette")) {
  document.documentElement.dataset.palette = q.get("palette");
  document.querySelector("#palette").value = q.get("palette");
}
if (q.get("appearance")) {
  document.documentElement.dataset.appearance = q.get("appearance");
  document.querySelector("#appearance").value = q.get("appearance");
}
if (q.get("canvas") === "1") document.querySelector("#studio").hidden = true;

// Design tab keyboard behavior mirrors the shared React contract proposed for Gate B.
document.querySelectorAll("[role=tablist]").forEach((list) =>
  list.addEventListener("keydown", (event) => {
    const tabs = [...list.querySelectorAll("[role=tab]")];
    let index = tabs.indexOf(document.activeElement);
    if (
      !["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key) ||
      index < 0
    )
      return;
    event.preventDefault();
    index =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? tabs.length - 1
          : (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) %
            tabs.length;
    tabs[index].click();
    tabs[index].focus();
  }),
);

document
  .querySelector("[name=knowledge]")
  ?.addEventListener("change", (event) => {
    document.querySelector("#quantity-value").hidden =
      event.target.value === "Unknown";
  });
document
  .querySelector("[name=precision]")
  ?.addEventListener("change", (event) => {
    const input = document.querySelector("[name=date]");
    input.disabled = event.target.value === "Unknown";
    input.placeholder = {
      Unknown: "No date recorded",
      Year: "YYYY",
      "Year and month": "YYYY-MM",
      "Complete date": "YYYY-MM-DD",
    }[event.target.value];
  });
