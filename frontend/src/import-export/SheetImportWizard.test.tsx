import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { App } from "../App";
import { openSection } from "../test/navigation";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const parentId = "01900000-0000-7000-8000-0000000000aa";
const plantId = "01900000-0000-7000-8000-0000000000bb";

function inspectBody(form: FormData) {
  const sheet = form.get("sheet_name") ?? "Foglio1";
  const italian = sheet === "Piante";
  return {
    format: "xlsx",
    sheets: ["Foglio1", "Piante"],
    selected_sheet: sheet,
    detected_header_row: italian ? 2 : 1,
    header_row: Number(form.get("header_row") ?? (italian ? 2 : 1)),
    row_count: 1,
    columns: [
      {
        index: 0,
        key: "c0",
        header: "Nome scientifico",
        samples: ["Ocimum basilicum"],
        suggested_field: italian ? "scientific_name" : null,
      },
      {
        index: 1,
        key: "c1",
        header: "Posizione",
        samples: ["Serra"],
        suggested_field: italian ? "location" : null,
      },
      {
        index: 2,
        key: "c2",
        header: "Extra",
        samples: ["x"],
        suggested_field: null,
      },
    ],
    sample_rows: [["Ocimum basilicum", "Serra", "x"]],
    allowed_fields: ["scientific_name", "location", "label", "notes"],
  };
}

function previewBody(ready: boolean) {
  return {
    record_type: "plants",
    identities: [
      {
        key: "ocimum basilicum",
        scientific_name: "Ocimum basilicum",
        cultivar_name: null,
        common_name: null,
        row_count: 1,
        status: "new",
        action: "create",
        candidates: [],
        messages: [],
      },
    ],
    locations: [
      {
        key: "Serra",
        raw_value: "Serra",
        row_count: 1,
        status: "new",
        action: "create",
        create_name: "Serra",
        parent_id: null,
        candidates: [],
        messages: [],
      },
    ],
    suppliers: [],
    rows: [
      {
        row_number: 3,
        record: "Ocimum basilicum",
        outcome: ready ? "ready" : "invalid",
        messages: ready ? [] : ["collection_entry_date: invalid date"],
        references: [`location: ${parentId} → Greenhouse (Current)`],
        normalized: [],
        hard_blocker: !ready,
      },
    ],
    ready: ready ? 1 : 0,
    needs_attention: 0,
    invalid: ready ? 0 : 1,
    will_create_identities: 1,
    will_create_locations: 1,
    will_create_suppliers: 0,
    can_apply: ready,
    confirmation_token: "sheet-token",
  };
}

interface Recorded {
  path: string;
  init?: RequestInit;
}

function mockServer(handlers: {
  inspect?: (form: FormData) => Response;
  preview?: (form: FormData) => Response;
  apply?: (form: FormData) => Response;
}) {
  const requests: Recorded[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const path =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    requests.push({ path, init });
    const form = init?.body instanceof FormData ? init.body : new FormData();
    if (path.endsWith("/auth/session"))
      return Promise.resolve(
        jsonResponse({
          user_id: "01900000-0000-7000-8000-000000000001",
          login_name: "owner",
          display_name: "Owner",
          owner: true,
        }),
      );
    if (path.endsWith("/auth/csrf"))
      return Promise.resolve(jsonResponse({ csrf_token: "csrf-value" }));
    if (path.endsWith("/health"))
      return Promise.resolve(jsonResponse({ status: "ok" }));
    if (path.endsWith("/sheet-imports/inspect"))
      return Promise.resolve(
        handlers.inspect?.(form) ?? jsonResponse(inspectBody(form)),
      );
    if (path.endsWith("/sheet-imports/preview"))
      return Promise.resolve(
        handlers.preview?.(form) ?? jsonResponse(previewBody(true)),
      );
    if (path.endsWith("/sheet-imports/apply"))
      return Promise.resolve(
        handlers.apply?.(form) ??
          jsonResponse({
            record_type: "plants",
            records_created: 1,
            identities_created: 1,
            locations_created: 1,
            suppliers_created: 0,
            created_records: [
              {
                id: plantId,
                label: "P-1",
                identity_label: "Ocimum basilicum",
              },
            ],
          }),
      );
    if (path.endsWith("/api/v1/locations"))
      return Promise.resolve(
        jsonResponse([
          {
            id: parentId,
            name: "Greenhouse",
            display_path: "Greenhouse",
            retired_at: null,
          },
        ]),
      );
    return Promise.resolve(jsonResponse([]));
  });
  return requests;
}

function lastOptions(requests: Recorded[], suffix: string) {
  const request = requests.filter((item) => item.path.endsWith(suffix)).at(-1);
  const body = request?.init?.body;
  if (!(body instanceof FormData)) throw new Error(`No ${suffix} request`);
  return JSON.parse(body.get("options") as string) as {
    sheet_name: string;
    header_row: number;
    mapping: { columns: Record<string, string | null> };
    choices: { locations: Record<string, { parent_id?: string }> };
  };
}

async function openWizard(user: ReturnType<typeof userEvent.setup>) {
  render(<App />);
  await openSection(user, "Import / Export");
  await user.click(
    await screen.findByRole(
      "button",
      { name: "Import a spreadsheet" },
      { timeout: 5000 },
    ),
  );
  return screen.getByRole("list", { name: "Spreadsheet import steps" });
}

const sheetFile = () =>
  new File(["xlsx-bytes"], "collection.xlsx", {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });

beforeEach(() => {
  window.location.hash = "#/dashboard";
  window.localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("walks every step from an Italian sheet to a created record", async () => {
  const user = userEvent.setup();
  let ready = false;
  const requests = mockServer({
    preview: () => jsonResponse(previewBody(ready)),
  });
  const steps = await openWizard(user);

  await user.upload(screen.getByLabelText("Spreadsheet"), sheetFile());
  await user.selectOptions(await screen.findByLabelText("Sheet"), "Piante");
  await waitFor(() => {
    expect(screen.getByLabelText("Header row")).toHaveValue("2");
  });
  expect(
    screen.getByRole("option", { name: "Row 2 (detected)" }),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Next" }));

  expect(within(steps).getByText("Row type").closest("li")).toHaveAttribute(
    "aria-current",
    "step",
  );
  await user.click(
    screen.getByRole("radio", { name: /one individual specimen/ }),
  );
  await user.click(screen.getByRole("button", { name: "Next" }));

  const scientific = await screen.findByLabelText(
    "Field for column Nome scientifico",
  );
  expect(scientific).toHaveValue("scientific_name");
  expect(screen.getByLabelText("Field for column Posizione")).toHaveValue(
    "location",
  );
  await user.click(
    screen.getByRole("checkbox", { name: /Add ignored columns to notes/ }),
  );
  await user.click(
    screen.getByRole("button", { name: "Check names and places" }),
  );

  expect(
    await screen.findByText(/0 match existing identities · 1 new/),
  ).toBeVisible();
  expect(screen.getByLabelText("New scientific name")).toHaveValue(
    "Ocimum basilicum",
  );
  await user.selectOptions(
    await screen.findByLabelText("Create under"),
    await screen.findByRole("option", { name: "Greenhouse" }),
  );
  await user.click(screen.getByRole("button", { name: "Check rows" }));

  expect(
    await screen.findByText("collection_entry_date: invalid date"),
  ).toBeVisible();
  expect(screen.getByText("location: Greenhouse (Current)")).toBeVisible();
  expect(screen.getByRole("button", { name: "Import" })).toBeDisabled();
  const options = lastOptions(requests, "/sheet-imports/preview");
  expect(options.sheet_name).toBe("Piante");
  expect(options.header_row).toBe(2);
  expect(options.mapping).toEqual({
    columns: { c0: "scientific_name", c1: "location", c2: null },
    append_unmapped_to_notes: true,
  });
  expect(options.choices.locations.Serra).toEqual({
    action: "create",
    parent_id: parentId,
  });

  await user.click(screen.getByRole("checkbox", { name: "Only problems" }));
  expect(
    screen.getByRole("article", { name: "Spreadsheet row 3" }),
  ).toBeVisible();

  ready = true;
  await user.click(screen.getByRole("button", { name: "Back" }));
  await user.click(screen.getByRole("button", { name: "Check rows" }));
  await user.click(await screen.findByRole("button", { name: "Import" }));

  expect(
    await screen.findByText(
      "Created 1 Plants, 1 identities, 1 locations and 0 suppliers.",
    ),
  ).toBeVisible();
  expect(screen.getByRole("link", { name: "P-1" })).toHaveAttribute(
    "href",
    `#/plants/${plantId}`,
  );
  const apply = requests.find((item) =>
    item.path.endsWith("/sheet-imports/apply"),
  );
  const headers = new Headers(apply?.init?.headers);
  expect(headers.get("X-CSRF-Token")).toBe("csrf-value");
  expect(headers.get("X-Import-Confirmation")).toBe("sheet-token");
  expect(lastOptions(requests, "/sheet-imports/apply")).toEqual(
    lastOptions(requests, "/sheet-imports/preview"),
  );
});

test("reports a rejected file and keeps the wizard on upload", async () => {
  const user = userEvent.setup();
  mockServer({
    inspect: () =>
      jsonResponse({ detail: "Spreadsheet exceeds 60 columns" }, 422),
  });
  await openWizard(user);
  await user.upload(screen.getByLabelText("Spreadsheet"), sheetFile());
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Spreadsheet exceeds 60 columns",
  );
  expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
});

test("requires a scientific name column and remembers the mapping", async () => {
  const user = userEvent.setup();
  mockServer({});
  await openWizard(user);
  await user.upload(screen.getByLabelText("Spreadsheet"), sheetFile());
  await user.click(await screen.findByRole("button", { name: "Next" }));
  await user.click(screen.getByRole("button", { name: "Next" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Map one column to Scientific name.",
  );
  const check = screen.getByRole("button", { name: "Check names and places" });
  expect(check).toBeDisabled();
  await user.selectOptions(
    screen.getByLabelText("Field for column Extra"),
    "scientific_name",
  );
  await user.selectOptions(
    screen.getByLabelText("Field for column Posizione"),
    "scientific_name",
  );
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Scientific name is mapped to more than one column.",
  );
  await user.selectOptions(
    screen.getByLabelText("Field for column Posizione"),
    "location",
  );
  await user.click(check);
  await screen.findByText(/match existing identities/);
  cleanup();

  // The same header set gets the remembered mapping instead of the suggestions.
  await openWizard(user);
  await user.upload(screen.getByLabelText("Spreadsheet"), sheetFile());
  await user.click(await screen.findByRole("button", { name: "Next" }));
  await user.click(screen.getByRole("button", { name: "Next" }));
  expect(await screen.findByLabelText("Field for column Extra")).toHaveValue(
    "scientific_name",
  );
  expect(screen.getByLabelText("Field for column Posizione")).toHaveValue(
    "location",
  );
});

test("returns to review when the import is refused", async () => {
  const user = userEvent.setup();
  const requests = mockServer({
    apply: () =>
      jsonResponse(
        {
          detail:
            "Preview expired or spreadsheet/options changed; validate again",
        },
        409,
      ),
  });
  const steps = await openWizard(user);
  await user.upload(screen.getByLabelText("Spreadsheet"), sheetFile());
  await user.selectOptions(await screen.findByLabelText("Sheet"), "Piante");
  await waitFor(() => {
    expect(screen.getByLabelText("Header row")).toHaveValue("2");
  });
  await user.click(screen.getByRole("button", { name: "Next" }));
  await user.click(screen.getByRole("button", { name: "Next" }));
  await user.click(
    await screen.findByRole("button", { name: "Check names and places" }),
  );
  await user.click(await screen.findByRole("button", { name: "Check rows" }));
  await user.click(await screen.findByRole("button", { name: "Import" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    /validate again Nothing was imported/,
  );
  expect(
    within(steps).getByText("Names and places").closest("li"),
  ).toHaveAttribute("aria-current", "step");
  expect(
    requests.filter((item) => item.path.endsWith("/sheet-imports/apply")),
  ).toHaveLength(1);
});
