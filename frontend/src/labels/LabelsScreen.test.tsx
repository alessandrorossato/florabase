/// <reference types="node" />
import { readFileSync } from "node:fs";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StrictMode } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App } from "../App";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { SettingsScreen } from "../settings/SettingsScreen";
import { LabelSheet } from "./LabelSheet";
import { LabelsScreen } from "./LabelsScreen";
import {
  composePages,
  isLabelKind,
  labelKinds,
  labelPresets,
  pickerLabel,
  labelTypeNames,
  listLabelRecords,
  recordUrl,
  sourceHref,
  labelComposerHref,
  type LabelRecord,
} from "./labelData";

const id = "01900000-0000-7000-8000-000000000211";
const harvestId = "01900000-0000-7000-8000-000000000212";
const identityId = "01900000-0000-7000-8000-000000000213";
const canonicalOrigin = "https://flora.example";
const sample: LabelRecord = {
  kind: "seed-lot",
  id,
  botanicalName: "Clitoria ternatea",
  cultivar: "Blue butterfly",
  commonName: "Blue pea",
  context: "Packet A",
  metadata: ["Acquired: 2026-10", "About 12 seeds", "Location: Glasshouse"],
};
const identity = {
  id: identityId,
  scientific_name: sample.botanicalName,
  cultivar_name: sample.cultivar,
  common_name: sample.commonName,
  display_label: "Clitoria ternatea ‘Blue butterfly’",
};
const seed = {
  id,
  label: "Packet A",
  botanical_identity: identity,
  acquisition_date: { precision: "month", year: 2026, month: 10 },
  quantity: { kind: "seed_count", value: "12", is_approximate: true },
  supplier: { name: "Local grower" },
};
const plant = {
  id,
  label: "Plant A",
  botanical_identity: identity,
  originating_plant_group: { id: harvestId, label: "Spring group" },
};
const group = {
  id,
  label: "Group A",
  botanical_identity: identity,
  quantity: { value: 0, is_approximate: false },
};
const inventory = {
  id,
  harvest_id: harvestId,
  harvest_item_id: harvestId,
  harvest_title: "Autumn harvest",
  material_kind: "seed",
  state: "active",
  quantity: { kind: "weight", value: "1.50", unit: "g", is_approximate: true },
  source: { id: harvestId, label: "Plant A", botanical_identity: identity },
};
const sessionExpired = vi.fn();
const auth: AuthContextValue = {
  state: { status: "unauthenticated" },
  logIn: vi.fn(),
  logOut: vi.fn(),
  sessionExpired,
  retryRestoration: vi.fn(),
  cancelLogout: vi.fn(),
};
function response(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
function requestPath(input: RequestInfo | URL) {
  return typeof input === "string"
    ? input
    : input instanceof URL
      ? input.toString()
      : input.url;
}
function mockRecords() {
  return vi.spyOn(globalThis, "fetch").mockImplementation((path) =>
    Promise.resolve(
      response(
        requestPath(path).endsWith("application-settings")
          ? {
              public_qr_base_url: canonicalOrigin,
              default_label_preset: "medium",
            }
          : requestPath(path).includes("botanical-identities")
            ? [identity]
            : requestPath(path).endsWith("harvest-inventory")
              ? [inventory]
              : requestPath(path).endsWith("plant-groups")
                ? [group]
                : requestPath(path).endsWith("plants")
                  ? [plant]
                  : [seed],
      ),
    ),
  );
}
function composer(props: { initialKind?: string; initialId?: string } = {}) {
  return render(
    <StrictMode>
      <AuthContext.Provider value={auth}>
        <LabelsScreen {...props} />
      </AuthContext.Provider>
    </StrictMode>,
  );
}
beforeEach(() => {
  Object.defineProperty(document, "fonts", {
    configurable: true,
    value: { ready: Promise.resolve() },
  });
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe = vi.fn();
      disconnect = vi.fn();
    },
  );
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
  localStorage.clear();
  window.history.replaceState(null, "", "/");
});

test.each(labelKinds)(
  "%s maps existing fields and keeps exact stable source",
  async (kind) => {
    const fetch = mockRecords();
    const [record] = await listLabelRecords(kind, new AbortController().signal);
    expect(record).toMatchObject({
      kind,
      id,
      botanicalName: identity.scientific_name,
      cultivar: identity.cultivar_name,
    });
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(
      fetch.mock.calls.every(([, init]) => init?.credentials === "same-origin"),
    ).toBe(true);
    expect(sourceHref(record)).toBe(
      kind === "stored-material"
        ? `#/harvests/${harvestId}?inventory=${id}`
        : `#/${kind === "seed-lot" ? "seeds" : kind === "plant" ? "plants" : "plant-groups"}/${id}`,
    );
    expect(record.metadata).toEqual(
      kind === "seed-lot"
        ? ["Acquired: 2026-10 · About 12 seeds", "Supplier: Local grower"]
        : kind === "plant"
          ? ["From: Spring group"]
          : kind === "plant-group"
            ? ["0 plants"]
            : ["Seeds · About 1.50 g", "Source: Plant A"],
    );
    expect(labelComposerHref(kind, id)).toBe(
      `#/labels?kind=${kind}&record=${id}`,
    );
  },
);

test("partial dates, unknown quantity and real zero remain distinct", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((path) =>
    Promise.resolve(
      response(
        requestPath(path).includes("botanical-identities")
          ? [identity]
          : [
              {
                ...seed,
                acquisition_date: { precision: "year", year: 2026 },
                quantity: null,
                supplier: null,
              },
            ],
      ),
    ),
  );
  const [record] = await listLabelRecords(
    "seed-lot",
    new AbortController().signal,
  );
  expect(record.metadata).toEqual(["Acquired: 2026"]);
  expect(JSON.stringify(record)).not.toContain("2026-01-01");
});

test("unknown and depleted Stored material use current inventory state, not harvested quantity", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((path) =>
      Promise.resolve(
        response(
          requestPath(path).includes("botanical-identities")
            ? [identity]
            : [{ ...inventory, quantity: null }],
        ),
      ),
    );
  expect(
    (await listLabelRecords("stored-material", new AbortController().signal))[0]
      .metadata[0],
  ).toBe("Seeds · Unknown quantity");
  fetch.mockImplementation((path) =>
    Promise.resolve(
      response(
        requestPath(path).includes("botanical-identities")
          ? [identity]
          : [{ ...inventory, state: "depleted", quantity: null }],
      ),
    ),
  );
  expect(
    (await listLabelRecords("stored-material", new AbortController().signal))[0]
      .metadata[0],
  ).toBe("Seeds · Depleted · no material held");
});

test.each(labelKinds)(
  "contextual %s opens the same composer with one selected copy",
  async (kind) => {
    mockRecords();
    composer({ initialKind: kind, initialId: id });
    expect(
      await screen.findByRole("spinbutton", { name: /^Copies for/ }),
    ).toHaveValue(1);
    const selection = screen.getByRole("list", { name: "Selected material" });
    expect(selection).toHaveTextContent(labelTypeNames[kind]);
    expect(within(selection).getByRole("link")).toHaveAttribute(
      "href",
      kind === "stored-material"
        ? `#/harvests/${harvestId}?inventory=${id}`
        : sourceHref({ kind, id }),
    );
    expect(screen.getByText("1 record · 1 label · 1 A4 sheet")).toBeVisible();
  },
);

test("empty workspace, keyboard add, duplicates, copies, multiple sheets, print and remove", async () => {
  mockRecords();
  const print = vi.spyOn(window, "print").mockImplementation(() => undefined);
  const user = userEvent.setup();
  composer();
  expect(screen.getByRole("button", { name: "Print" })).toBeDisabled();
  expect(screen.getByText(/No material selected/)).toBeVisible();
  const picker = await screen.findByRole("combobox", { name: "Record" });
  await user.click(picker);
  await user.keyboard("{Enter}");
  await user.click(screen.getByRole("button", { name: "Add record" }));
  await user.click(screen.getByRole("button", { name: "Add record" }));
  const copies = screen.getByRole("spinbutton");
  expect(copies).toHaveValue(2);
  fireEvent.change(copies, { target: { value: "37" } });
  expect(screen.getByText("1 record · 37 labels · 2 A4 sheets")).toBeVisible();
  expect(screen.getByText("Sheet 1 · 36 labels · 0 empty cells")).toBeVisible();
  expect(screen.getByText("Sheet 2 · 1 label · 35 empty cells")).toBeVisible();
  fireEvent.change(copies, { target: { value: "0" } });
  expect(screen.getByRole("alert")).toHaveTextContent("whole number");
  expect(copies).toHaveValue(37);
  fireEvent.change(copies, { target: { value: "361" } });
  expect(copies).toHaveValue(37);
  await user.click(screen.getByRole("button", { name: "Print" }));
  expect(print).toHaveBeenCalledTimes(1);
  await user.click(screen.getByRole("button", { name: /^Remove Seed lot/ }));
  expect(screen.getByText(/No material selected/)).toBeVisible();
  expect(screen.getByRole("combobox", { name: "Record type" })).toHaveFocus();
});

test("central workspace safely mixes all four record kinds and preserves individual copies", async () => {
  mockRecords();
  const user = userEvent.setup();
  composer();
  for (const kind of labelKinds) {
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Record type" }),
      kind,
    );
    const picker = await screen.findByRole("combobox", { name: "Record" });
    await user.click(picker);
    await user.keyboard("{Enter}");
    await user.click(screen.getByRole("button", { name: "Add record" }));
  }
  expect(screen.getByText("4 records · 4 labels · 1 A4 sheet")).toBeVisible();
  expect(screen.getAllByRole("spinbutton")).toHaveLength(4);
  expect(
    screen.getByRole("list", { name: "Selected material" }).children,
  ).toHaveLength(4);
});

test("retry and unavailable initial references remain actionable; expired auth returns to login", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation((path) =>
    Promise.resolve(
      requestPath(path).endsWith("application-settings")
        ? response({
            public_qr_base_url: canonicalOrigin,
            default_label_preset: "medium",
          })
        : response({}, 500),
    ),
  );
  composer({ initialKind: "location", initialId: id });
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Could not load records",
  );
  fetch.mockImplementation((path) =>
    Promise.resolve(
      requestPath(path).endsWith("application-settings")
        ? response({
            public_qr_base_url: canonicalOrigin,
            default_label_preset: "medium",
          })
        : response([]),
    ),
  );
  await userEvent.setup().click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "requested label source is unavailable",
  );
  cleanup();
  fetch.mockImplementation(() => Promise.resolve(response({}, 401)));
  composer();
  await waitFor(() => {
    expect(sessionExpired).toHaveBeenCalled();
  });
});

test("print failure exposes browser fallback", async () => {
  mockRecords();
  vi.spyOn(window, "print").mockImplementation(() => {
    throw new Error("unavailable");
  });
  composer({ initialKind: "plant", initialId: id });
  await screen.findByRole("spinbutton");
  await userEvent.setup().click(screen.getByRole("button", { name: "Print" }));
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Use your browser’s Print command",
  );
});

test("composition splits at 36, keeps mixed exact sources and bounds allocation", () => {
  const plantRecord = { ...sample, kind: "plant" as const };
  const pages = composePages([
    { record: sample, copies: 36 },
    { record: plantRecord, copies: 2 },
  ]);
  expect(pages.map((page) => page.length)).toEqual([36, 2]);
  expect(pages[1][0]).toBe(plantRecord);
  expect(composePages([])).toEqual([]);
  expect(composePages([{ record: sample, copies: 360 }])).toHaveLength(10);
  for (const copies of [0, -1, 1.5, NaN, Infinity, 361])
    expect(() => composePages([{ record: sample, copies }])).toThrow();
  expect(() =>
    composePages([
      { record: sample, copies: 360 },
      { record: sample, copies: 1 },
    ]),
  ).toThrow();
});

test("physical sheet exposes exact source, botanical italics, roman cultivar, QR and blank cells", () => {
  const record = {
    ...sample,
    botanicalName: "Pelargonium quinquelobatum subsp. quinquelobatum",
    context: "A deliberately long operational accession identifier",
  };
  const { container } = render(
    <LabelSheet pages={[[record]]} baseUrl={canonicalOrigin} />,
  );
  expect(container.querySelectorAll(".physical-label")).toHaveLength(36);
  expect(container.querySelectorAll("article")).toHaveLength(1);
  const lastCell = container.querySelector<HTMLElement>(
    ".physical-label:last-child",
  );
  expect(lastCell?.style.getPropertyValue("--label-column")).toBe("3");
  expect(lastCell?.style.getPropertyValue("--label-row")).toBe("8");
  expect(container.querySelector("article")).toHaveAttribute(
    "data-source",
    sourceHref(sample),
  );
  expect(container.querySelector(".label-scientific-name")).toHaveTextContent(
    record.botanicalName,
  );
  expect(container.querySelector(".label-name-rank")).toHaveTextContent(
    "subsp.",
  );
  expect(container.querySelector(".label-cultivar")?.closest("i")).toBeNull();
  expect(container.querySelector(".physical-label__identifier")).toBeNull();
  expect(
    screen.getByRole("img", { name: /QR to Seed lot/ }),
  ).toBeInTheDocument();
  expect(container.querySelector(".label-qr")).toHaveAttribute(
    "data-destination",
    `${canonicalOrigin}/${sourceHref(sample)}`,
  );
});

test("print contract uses A4 millimetres and resets screen transforms, isolating app UI", () => {
  const css = readFileSync("src/labels/labels.css", "utf8");
  for (const contract of [
    "width: var(--label-width)",
    "height: var(--label-height)",
    "repeat(var(--label-columns), var(--label-width))",
    "repeat(var(--label-rows), var(--label-height))",
    "size: A4 portrait",
    "margin: 13.5mm 5mm",
    "width: calc(var(--label-width) * var(--label-columns))",
    "height: calc(var(--label-height) * var(--label-rows))",
    "transform: none",
    "break-after: page",
    "break-inside: avoid",
    "body:has(> .label-print-root) > :not(.label-print-root)",
  ])
    expect(css).toContain(contract);
});

test.each(labelKinds)(
  "canonical QR URL for %s uses configured origin without secrets",
  (kind) => {
    window.history.replaceState(
      null,
      "",
      "/?token=never-copy#/dashboard?csrf=never-copy",
    );
    const url = recordUrl(kind, id, canonicalOrigin, harvestId);
    expect(url).toBe(
      `${canonicalOrigin}/${sourceHref({ kind, id, harvestId })}`,
    );
    expect(url).not.toMatch(/token|csrf|session|cookie|bearer/i);
  },
);
test.each([
  null,
  "",
  "https://user:secret@flora.example",
  "https://@flora.example",
  "https://flora.example/..",
  "https://flora.example/other",
  "https://flora.example/?token=secret",
  "https://flora.example/#token=secret",
  "javascript:alert(1)",
])("invalid public QR origin %s is rejected", (origin) => {
  expect(() => recordUrl("plant", id, origin)).toThrow();
});
test("unsupported or injected source references are rejected", () => {
  expect(isLabelKind("location")).toBe(false);
  expect(() => sourceHref({ ...sample, id: `${id}?token=secret` })).toThrow();
  expect(() => sourceHref({ ...sample, kind: "stored-material" })).toThrow();
});

test("direct composer URL survives authentication and uses saved QR origin independently of login origin", async () => {
  window.history.replaceState(null, "", labelComposerHref("seed-lot", id));
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const path = requestPath(input);
    return Promise.resolve(
      response(
        path.endsWith("/session")
          ? {
              user_id: id,
              login_name: "owner",
              owner: true,
              canonical_origin: null,
            }
          : path.endsWith("/csrf")
            ? { csrf_token: "test" }
            : path.endsWith("application-settings")
              ? {
                  public_qr_base_url: canonicalOrigin,
                  default_label_preset: "medium",
                }
              : path.endsWith("/health")
                ? { status: "ok" }
                : path.includes("botanical-identities")
                  ? [identity]
                  : [seed],
      ),
    );
  });
  render(<App />);
  await screen.findByRole("spinbutton");
  expect(screen.getByRole("button", { name: "Print" })).toBeEnabled();
  expect(
    within(
      screen.getByRole("navigation", { name: "Primary navigation" }),
    ).queryByRole("link", { name: "Labels" }),
  ).not.toBeInTheDocument();
});

test("full label content remains readable when fixed paper capacity is exceeded", async () => {
  mockRecords();
  composer({ initialKind: "seed-lot", initialId: id });
  await screen.findByRole("spinbutton");
  await userEvent
    .setup()
    .click(screen.getByText("Label content", { exact: true }));
  const details = screen
    .getByRole("list", { name: "Selected material" })
    .querySelector("details");
  expect(details).toHaveTextContent("Acquired: 2026-10");
  expect(details).toHaveTextContent("About 12 seeds");
  expect(details).toHaveTextContent(id);
});

test.each(labelKinds)(
  "%s picker and selected row omit technical IDs; context distinguishes material",
  async (kind) => {
    mockRecords();
    composer({ initialKind: kind, initialId: id });
    await screen.findByRole("spinbutton");
    const user = userEvent.setup();
    await user.click(screen.getByRole("combobox", { name: "Record" }));
    for (const option of screen
      .getAllByRole("option")
      .filter((item) => item.closest("[role=listbox]")))
      expect(option).not.toHaveTextContent(id);
    const row = screen.getByRole("list", {
      name: "Selected material",
    }).firstElementChild;
    expect(row?.querySelector(".label-source-meta")).not.toHaveTextContent(id);
    expect(
      within(row as HTMLElement).getByText(`Record ID: ${id}`),
    ).not.toBeVisible();
    const first = {
      ...sample,
      context: "North greenhouse",
      metadata: ["Acquired: 2026-10"],
    };
    const second = {
      ...sample,
      id: harvestId,
      context: "South greenhouse",
      metadata: ["Acquired: 2025"],
    };
    expect(pickerLabel(first)).not.toContain(id);
    expect(pickerLabel(first)).not.toBe(pickerLabel(second));
  },
);

test.each(Object.values(labelPresets))(
  "$id preset composes exact full/partial/multiple sheets with botanical-only physical content",
  (preset) => {
    const perSheet = preset.columns * preset.rows;
    const pages = composePages(
      [{ record: sample, copies: perSheet + 1 }],
      preset,
    );
    expect(pages.map((page) => page.length)).toEqual([perSheet, 1]);
    const { container } = render(
      <LabelSheet pages={pages} preset={preset} baseUrl={canonicalOrigin} />,
    );
    expect(container.querySelectorAll(".physical-label--empty")).toHaveLength(
      perSheet - 1,
    );
    expect(container.querySelectorAll(".label-page")).toHaveLength(2);
    const article = container.querySelector("article");
    expect(
      article?.querySelectorAll(".physical-label__metadata > span"),
    ).toHaveLength(0);
    expect(article).toHaveTextContent(sample.commonName ?? "");
    expect(article).not.toHaveTextContent(
      /Acquired:|About 12 seeds|Location:|Packet A/,
    );
    expect(article?.querySelector(".label-qr")).toHaveAttribute(
      "data-glyph-placement",
      preset.id === "small" ? "adjacent" : "inset",
    );
  },
);

test("workspace size override changes pages immediately without writing global settings", async () => {
  const fetch = mockRecords();
  composer({ initialKind: "seed-lot", initialId: id });
  const copies = await screen.findByRole("spinbutton");
  fireEvent.change(copies, { target: { value: "66" } });
  const user = userEvent.setup();
  const size = screen.getByRole("combobox", { name: "Label size" });
  await user.selectOptions(size, "small");
  expect(screen.getByText("Sheet 1 · 65 labels · 0 empty cells")).toBeVisible();
  await user.selectOptions(size, "large");
  expect(screen.getByText("1 record · 66 labels · 5 A4 sheets")).toBeVisible();
  expect(
    fetch.mock.calls.every(
      ([, init]) => !init?.method || init.method === "GET",
    ),
  ).toBe(true);
});

test("unconfigured QR destination permits inspection but both print entry paths are safely blocked", async () => {
  const fetch = mockRecords();
  const original = fetch.getMockImplementation();
  if (!original) throw new Error("Missing record fixture");
  fetch.mockImplementation((path, init) =>
    requestPath(path).endsWith("application-settings")
      ? Promise.resolve(
          response({ public_qr_base_url: null, default_label_preset: "small" }),
        )
      : original(path, init),
  );
  composer({ initialKind: "seed-lot", initialId: id });
  await screen.findByRole("spinbutton");
  expect(screen.getByText(/QR destination is not configured/)).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Edit QR destination" }),
  ).toBeEnabled();
  expect(screen.getByRole("button", { name: "Print" })).toBeDisabled();
  expect(
    document.querySelector(".label-print-root .label-print-blocked"),
  ).toHaveTextContent("cannot be printed");
  expect(document.querySelector(".label-print-root .label-qr")).toBeNull();
  expect(screen.getByRole("combobox", { name: "Label size" })).toHaveValue(
    "small",
  );
});

test("dense QR blocks the smaller preset and a larger size restores safe printing", async () => {
  const fetch = mockRecords();
  const original = fetch.getMockImplementation();
  if (!original) throw new Error("Missing record fixture");
  const longOrigin = `https://${"a".repeat(60)}.${"b".repeat(60)}.${"c".repeat(45)}.example`;
  fetch.mockImplementation((path, init) =>
    requestPath(path).endsWith("application-settings")
      ? Promise.resolve(
          response({
            public_qr_base_url: longOrigin,
            default_label_preset: "small",
          }),
        )
      : original(path, init),
  );
  composer({ initialKind: "seed-lot", initialId: id });
  await screen.findByRole("spinbutton");
  expect(screen.getByRole("alert")).toHaveTextContent("too dense");
  expect(screen.getByRole("button", { name: "Print" })).toBeDisabled();
  await userEvent
    .setup()
    .selectOptions(
      screen.getByRole("combobox", { name: "Label size" }),
      "large",
    );
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Print" })).toBeEnabled();
});

const authenticated: AuthContextValue = {
  ...auth,
  state: {
    status: "authenticated",
    csrfToken: "labels-csrf",
    session: {
      user_id: id,
      login_name: "owner",
      display_name: "Owner",
      owner: true,
      canonical_origin: canonicalOrigin,
    },
  },
};
function authenticatedComposer() {
  return render(
    <AuthContext.Provider value={authenticated}>
      <LabelsScreen initialKind="seed-lot" initialId={id} />
    </AuthContext.Provider>,
  );
}

test("Set as default is explicit, preserves the current QR origin and survives remount", async () => {
  let saved = {
    public_qr_base_url: canonicalOrigin,
    default_label_preset: "medium",
  };
  const fetch = mockRecords();
  const records = fetch.getMockImplementation();
  if (!records) throw new Error("Missing fixture");
  fetch.mockImplementation((path, init) => {
    if (!requestPath(path).endsWith("application-settings"))
      return records(path, init);
    if (init?.method === "PUT")
      saved = JSON.parse(init.body as string) as typeof saved;
    return Promise.resolve(response(saved));
  });
  const user = userEvent.setup();
  const first = authenticatedComposer();
  await screen.findByRole("spinbutton");
  expect(screen.getByText("Default", { exact: true })).toBeVisible();
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Label size" }),
    "large",
  );
  expect(saved.default_label_preset).toBe("medium");
  expect(fetch.mock.calls.some(([, init]) => init?.method === "PUT")).toBe(
    false,
  );
  // Settings may have updated the QR origin since the composer mounted.
  saved.public_qr_base_url = "https://updated.example";
  await user.click(screen.getByRole("button", { name: "Set as default" }));
  expect(await screen.findByText("Default label size saved.")).toBeVisible();
  expect(saved).toEqual({
    public_qr_base_url: "https://updated.example",
    default_label_preset: "large",
  });
  const request = fetch.mock.calls.find(
    ([, init]) => init?.method === "PUT",
  )?.[1];
  expect(new Headers(request?.headers).get("X-CSRF-Token")).toBe("labels-csrf");
  expect(
    screen.queryByRole("button", { name: "Set as default" }),
  ).not.toBeInTheDocument();
  expect(document.querySelector(".label-qr")).toHaveAttribute(
    "data-destination",
    `https://updated.example/#/seeds/${id}`,
  );
  first.unmount();
  authenticatedComposer();
  await waitFor(() => {
    expect(screen.getByRole("combobox", { name: "Label size" })).toHaveValue(
      "large",
    );
  });
});

test("failed default save preserves batch, selected size and previous persisted default; retry succeeds", async () => {
  let failed = true;
  const fetch = mockRecords();
  const records = fetch.getMockImplementation();
  if (!records) throw new Error("Missing fixture");
  fetch.mockImplementation((path, init) =>
    init?.method === "PUT"
      ? Promise.resolve(
          response(
            failed ? {} : (JSON.parse(init.body as string) as unknown),
            failed ? 500 : 200,
          ),
        )
      : records(path, init),
  );
  authenticatedComposer();
  const user = userEvent.setup();
  await screen.findByRole("spinbutton");
  const size = screen.getByRole("combobox", { name: "Label size" });
  await user.selectOptions(size, "small");
  await user.click(screen.getByRole("button", { name: "Set as default" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Your batch is unchanged",
  );
  expect(size).toHaveValue("small");
  expect(screen.getByRole("spinbutton")).toHaveValue(1);
  await user.selectOptions(size, "medium");
  expect(screen.getByText("Default", { exact: true })).toBeVisible();
  await user.selectOptions(size, "small");
  failed = false;
  await user.click(screen.getByRole("button", { name: "Set as default" }));
  expect(await screen.findByText("Default label size saved.")).toBeVisible();
});

test("physical labels render botanical names without material text, record context, classification or UUID", async () => {
  const fetch = mockRecords();
  const records = fetch.getMockImplementation();
  if (!records) throw new Error("Missing fixture");
  fetch.mockImplementation((path, init) =>
    requestPath(path).includes("botanical-identities")
      ? Promise.resolve(
          response([
            {
              ...identity,
              kingdom: "Plantae",
              order: "Fabales",
              family: "Fabaceae",
              genus: "Clitoria",
              display_label: "Plantae / Fabales / Fabaceae / Clitoria ternatea",
            },
          ]),
        )
      : records(path, init),
  );
  composer({ initialKind: "seed-lot", initialId: id });
  await screen.findByRole("spinbutton");
  const label = document.querySelector(".label-sheet-preview .physical-label");
  expect(label).toHaveTextContent("Clitoria ternatea");
  expect(label).toHaveTextContent("Blue butterfly");
  expect(label).toHaveTextContent("Blue pea");
  expect(label).not.toHaveTextContent(/Seed lot|Packet A/);
  expect(label).not.toHaveTextContent(/Plantae|Fabales|Fabaceae|01900000/);
  expect(label?.querySelector(".scientific-name")).toHaveTextContent(
    "Clitoria ternatea",
  );
  expect(label?.querySelector(".label-qr")).toHaveAttribute(
    "data-destination",
    `${canonicalOrigin}/#/seeds/${id}`,
  );
});

function persistedSettingsFixture() {
  let saved = {
    public_qr_base_url: canonicalOrigin as string | null,
    default_label_preset: "medium",
  };
  const fetch = mockRecords();
  const records = fetch.getMockImplementation();
  if (!records) throw new Error("Missing fixture");
  fetch.mockImplementation((path, init) => {
    if (!requestPath(path).endsWith("application-settings"))
      return records(path, init);
    if (init?.method === "PUT") {
      const sent = JSON.parse(init.body as string) as typeof saved;
      saved = {
        ...sent,
        public_qr_base_url:
          sent.public_qr_base_url?.replace(/\/$/, "").toLowerCase() ?? null,
      };
    }
    return Promise.resolve(response(saved));
  });
  return { fetch, saved: () => saved };
}

test("QR dialog pristine Cancel and Escape restore Edit focus without saving", async () => {
  const fixture = persistedSettingsFixture();
  authenticatedComposer();
  await screen.findByRole("spinbutton");
  const user = userEvent.setup();
  const edit = screen.getByRole("button", { name: "Edit QR destination" });
  await user.click(edit);
  expect(
    screen.getByRole("textbox", { name: "Public / QR base URL" }),
  ).toHaveValue(canonicalOrigin);
  expect(screen.getByRole("textbox")).toHaveFocus();
  await user.click(screen.getByRole("button", { name: "Cancel" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(edit).toHaveFocus();
  await user.click(edit);
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(edit).toHaveFocus();
  expect(
    fixture.fetch.mock.calls.some(([, init]) => init?.method === "PUT"),
  ).toBe(false);
});

test("QR dialog saves normalized shared setting and regenerates QR without losing copies, preset or sources", async () => {
  const fixture = persistedSettingsFixture();
  authenticatedComposer();
  const copies = await screen.findByRole("spinbutton");
  const user = userEvent.setup();
  fireEvent.change(copies, { target: { value: "3" } });
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Label size" }),
    "large",
  );
  const edit = screen.getByRole("button", { name: "Edit QR destination" });
  await user.click(edit);
  const input = screen.getByRole("textbox", { name: "Public / QR base URL" });
  await user.clear(input);
  await user.type(input, "https://NEW.example/");
  await user.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => {
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
  expect(edit).toHaveFocus();
  expect(copies).toHaveValue(3);
  expect(screen.getByRole("combobox", { name: "Label size" })).toHaveValue(
    "large",
  );
  expect(fixture.saved()).toEqual({
    public_qr_base_url: "https://new.example",
    default_label_preset: "medium",
  });
  expect(screen.getByText("QR destination: https://new.example")).toBeVisible();
  for (const qr of document.querySelectorAll(".label-qr"))
    expect(qr).toHaveAttribute(
      "data-destination",
      `https://new.example/#/seeds/${id}`,
    );
  const request = fixture.fetch.mock.calls.find(
    ([, init]) => init?.method === "PUT",
  )?.[1];
  expect(new Headers(request?.headers).get("X-CSRF-Token")).toBe("labels-csrf");
  cleanup();
  render(
    <AuthContext.Provider value={authenticated}>
      <SettingsScreen />
    </AuthContext.Provider>,
  );
  expect(
    await screen.findByRole("textbox", { name: "Public / QR base URL" }),
  ).toHaveValue("https://new.example");
});

test("QR dialog server validation retains edits and dirty Escape/backdrop require explicit discard", async () => {
  const fixture = persistedSettingsFixture();
  const original = fixture.fetch.getMockImplementation();
  if (!original) throw new Error("Missing fixture");
  fixture.fetch.mockImplementation((path, init) =>
    init?.method === "PUT"
      ? Promise.resolve(response({}, 422))
      : original(path, init),
  );
  authenticatedComposer();
  await screen.findByRole("spinbutton");
  const user = userEvent.setup();
  const edit = screen.getByRole("button", { name: "Edit QR destination" });
  await user.click(edit);
  const input = screen.getByRole("textbox", { name: "Public / QR base URL" });
  await user.clear(input);
  await user.type(input, "https://flora.example/path");
  await user.click(screen.getByRole("button", { name: "Save" }));
  expect(await screen.findByText(/Use an HTTP\(S\) scheme/)).toBeVisible();
  expect(input).toHaveValue("https://flora.example/path");
  await user.keyboard("{Escape}");
  expect(
    screen.getByText("Discard unsaved QR destination changes?"),
  ).toBeVisible();
  expect(
    screen.getByRole("dialog", { name: "QR destination" }),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Continue editing" }));
  fireEvent.click(screen.getByRole("dialog"), { clientX: -1, clientY: -1 });
  expect(
    screen.getByText("Discard unsaved QR destination changes?"),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Discard changes" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(edit).toHaveFocus();
  expect(fixture.saved().public_qr_base_url).toBe(canonicalOrigin);
});

test("clearing QR destination preserves composition and safely disables printing", async () => {
  persistedSettingsFixture();
  authenticatedComposer();
  const copies = await screen.findByRole("spinbutton");
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Edit QR destination" }));
  await user.clear(
    screen.getByRole("textbox", { name: "Public / QR base URL" }),
  );
  await user.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => {
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
  expect(copies).toHaveValue(1);
  expect(screen.getByRole("button", { name: "Print" })).toBeDisabled();
  expect(document.querySelector(".label-print-blocked")).toHaveTextContent(
    "cannot be printed",
  );
});

test.each(labelKinds)(
  "%s physical output is exclusively botanical names and exact QR for every preset/name combination",
  (kind) => {
    for (const preset of Object.values(labelPresets))
      for (const [cultivar, commonName] of [
        [null, null],
        ["Genovese", null],
        [null, "Sweet basil"],
        ["Genovese", "Sweet basil"],
      ]) {
        const record: LabelRecord = {
          ...sample,
          kind,
          harvestId,
          botanicalName: "Ocimum basilicum",
          cultivar,
          commonName,
          context: "Preview — Basil seedlings",
          metadata: [
            "Location: Glasshouse",
            "Source: Plant A",
            "Acquired: 2026",
            "12 seeds",
          ],
        };
        const view = render(
          <LabelSheet
            pages={[[record]]}
            preset={preset}
            baseUrl={canonicalOrigin}
          />,
        );
        const label = view.container.querySelector("article");
        expect(label).toHaveTextContent("Ocimum basilicum");
        expect(
          label?.querySelector(".physical-label__cultivar")?.textContent ??
            null,
        ).toBe(cultivar ? `‘${cultivar}’` : null);
        expect(
          label?.querySelector(".physical-label__common-name")?.textContent ??
            null,
        ).toBe(commonName);
        expect(label).not.toHaveTextContent(
          /Location|Source:|Acquired|12 seeds|Preview|01900000|Seed lot|Plant group|Stored material/,
        );
        expect(label?.querySelector(".label-qr")).toHaveAttribute(
          "data-destination",
          recordUrl(kind, id, canonicalOrigin, harvestId),
        );
        expect(
          label?.querySelector(".label-cultivar")?.closest("i") ?? null,
        ).toBeNull();
        expect(label?.querySelector(".physical-label__metadata")).toBeNull();
        view.unmount();
      }
  },
);
