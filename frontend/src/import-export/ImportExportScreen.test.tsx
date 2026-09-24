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

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  window.location.hash = "#/dashboard";
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("navigates, validates row issues, retries and explicitly confirms the reviewed file", async () => {
  const user = userEvent.setup();
  let needsAttention = true;
  const requests: { path: string; init?: RequestInit }[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const path =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    requests.push({ path, init });
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
    if (path.endsWith("/imports/seed-lots/preview"))
      return Promise.resolve(
        jsonResponse({
          rows: needsAttention
            ? [
                {
                  row_number: 2,
                  record: "Lot A",
                  outcome: "unresolved_reference",
                  messages: ["supplier: not found: ABC"],
                  references: [],
                  normalized: [],
                  hard_blocker: true,
                  options: [],
                },
              ]
            : [
                {
                  row_number: 2,
                  record: "Lot A",
                  outcome: "ready",
                  messages: [],
                  references: ["identity: Phaseolus vulgaris → id"],
                  normalized: [],
                  hard_blocker: false,
                  options: [],
                },
              ],
          ready: needsAttention ? 0 : 1,
          already_exists: 0,
          needs_attention: needsAttention ? 1 : 0,
          confirmation_token: "reviewed-token",
        }),
      );
    if (path.endsWith("/imports/seed-lots/apply"))
      return Promise.resolve(
        jsonResponse({ created: 1, already_exists: 0, updated: 0 }),
      );
    return Promise.resolve(jsonResponse([]));
  });

  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: "Import / Export" }),
  );
  expect(
    screen.getByRole("heading", { name: "Import & export" }),
  ).toBeVisible();
  const steps = screen.getByRole("list", { name: "Import steps" });
  expect(within(steps).getByText("Template").closest("li")).toHaveAttribute(
    "aria-current",
    "step",
  );
  await user.selectOptions(screen.getByLabelText("Record type"), "seed-lots");
  expect(
    within(screen.getByRole("complementary", { name: "Export CSV" })).getByRole(
      "link",
      { name: "Download Seed lots CSV" },
    ),
  ).toBeVisible();
  expect(screen.getByRole("link", { name: "Blank template" })).toHaveAttribute(
    "href",
    "/api/v1/imports/templates/seed-lots.csv",
  );
  expect(screen.getByRole("link", { name: "Example CSV" })).toHaveAttribute(
    "href",
    "/api/v1/imports/examples/seed-lots.csv",
  );
  const file = new File(["identity_ref\nPhaseolus vulgaris\n"], "lots.csv", {
    type: "text/csv",
  });
  await user.upload(screen.getByLabelText(/CSV file/), file);
  expect(within(steps).getByText("Upload").closest("li")).toHaveAttribute(
    "aria-current",
    "step",
  );
  await user.click(
    screen.getByRole("button", { name: "Validate and preview" }),
  );
  expect(await screen.findByText("supplier: not found: ABC")).toBeVisible();
  expect(within(steps).getByText("Preview").closest("li")).toHaveAttribute(
    "aria-current",
    "step",
  );
  const attentionFilter = screen.getByRole("button", {
    name: "Needs attention",
  });
  attentionFilter.focus();
  await user.keyboard("{Enter}");
  expect(attentionFilter).toHaveAttribute("aria-pressed", "true");
  expect(
    screen.queryByRole("button", { name: "Confirm import" }),
  ).not.toBeInTheDocument();
  needsAttention = false;
  await user.upload(screen.getByLabelText(/CSV file/), file);
  await user.click(
    screen.getByRole("button", { name: "Validate and preview" }),
  );
  expect(await screen.findByText(/identity: Phaseolus vulgaris/)).toBeVisible();
  screen.getByRole("button", { name: "Confirm import" }).focus();
  await user.keyboard("{Enter}");
  expect(await screen.findByRole("status")).toHaveTextContent(
    "Created 1 record",
  );
  expect(within(steps).getByText("Import").closest("li")).toHaveAttribute(
    "aria-current",
    "step",
  );
  await waitFor(() => {
    const apply = requests.find((request) =>
      request.path.endsWith("/imports/seed-lots/apply"),
    );
    const headers = new Headers(apply?.init?.headers);
    expect(headers.get("X-CSRF-Token")).toBe("csrf-value");
    expect(headers.get("X-Import-Confirmation")).toBe("reviewed-token");
    const raw = apply?.init?.body;
    if (typeof raw !== "string") throw new Error("Expected JSON import body");
    const body = JSON.parse(raw) as {
      csv_base64: string;
      decisions: Record<string, Record<string, string>>;
    };
    expect(atob(body.csv_base64)).toContain("Phaseolus vulgaris");
    expect(body.decisions).toEqual({});
  });
});

test("shows validation progress and a recoverable file error", async () => {
  const user = userEvent.setup();
  let resolvePreview: (response: Response) => void = () => {
    throw new Error("Preview request was not started");
  };
  const pendingPreview = new Promise<Response>((resolve) => {
    resolvePreview = resolve;
  });
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const path =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
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
    if (path.endsWith("/imports/botanical-identities/preview"))
      return pendingPreview;
    return Promise.resolve(jsonResponse([]));
  });

  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: "Import / Export" }),
  );
  await user.upload(
    screen.getByLabelText(/CSV file/),
    new File(["invalid"], "bad.csv", { type: "text/csv" }),
  );
  await user.click(
    screen.getByRole("button", { name: "Validate and preview" }),
  );
  expect(screen.getByRole("button", { name: "Validating…" })).toBeDisabled();
  resolvePreview(jsonResponse({ detail: "CSV headers differ" }, 422));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "CSV headers differ",
  );
  expect(
    screen.getByRole("button", { name: "Validate and preview" }),
  ).toBeEnabled();
});

test("guides a human Supplier import and requires a reviewed update choice", async () => {
  const user = userEvent.setup();
  const requests: { path: string; init?: RequestInit }[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const path =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    requests.push({ path, init });
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
    if (path.endsWith("/imports/formats/suppliers"))
      return Promise.resolve(
        jsonResponse({
          fields: [
            {
              field: "kind",
              meaning: "Type of Supplier",
              required: true,
              accepted: "seller, nursery",
              example: "nursery",
              notes: "Capitalization and spaces are normalized.",
            },
          ],
        }),
      );
    if (path.endsWith("/imports/suppliers/preview"))
      return Promise.resolve(
        jsonResponse({
          rows: [
            {
              row_number: 2,
              record: "Cercatoridisemì",
              outcome: "needs_choice",
              messages: ["1 exact Supplier candidate found; choose an action"],
              references: [],
              normalized: ["kind: 'Nursery' → nursery"],
              hard_blocker: false,
              options: [
                {
                  key: "record",
                  action: "use_existing",
                  candidate_id: "id",
                  label: "Cercatoridisemì",
                  details: "Type: nursery; CSV values are not applied",
                  changes: [],
                  token: "use-token",
                },
                {
                  key: "record",
                  action: "update_existing",
                  candidate_id: "id",
                  label: "Cercatoridisemì",
                  details: "Blank CSV cells retain current values",
                  changes: [
                    {
                      field: "website",
                      before: "https://old.example",
                      after: "https://new.example",
                    },
                  ],
                  token: "update-token",
                },
                {
                  key: "record",
                  action: "create_separate",
                  candidate_id: "",
                  label: "Cercatoridisemì",
                  details: "Create another Supplier",
                  changes: [],
                  token: "separate-token",
                },
              ],
            },
          ],
          ready: 0,
          already_exists: 0,
          needs_attention: 1,
          confirmation_token: "reviewed-token",
        }),
      );
    if (path.endsWith("/imports/suppliers/apply"))
      return Promise.resolve(
        jsonResponse({ created: 0, already_exists: 0, updated: 1 }),
      );
    return Promise.resolve(jsonResponse([]));
  });

  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: "Import / Export" }),
  );
  await user.selectOptions(screen.getByLabelText("Record type"), "suppliers");
  const guideToggle = screen.getByRole("button", { name: "Field guide" });
  expect(guideToggle).toHaveAttribute("aria-expanded", "false");
  expect(document.getElementById("import-field-guide")).toHaveAttribute(
    "hidden",
  );
  await user.click(guideToggle);
  expect(guideToggle).toHaveAttribute("aria-expanded", "true");
  const guide = await screen.findByRole("table", {
    name: "CSV fields for Suppliers",
  });
  expect(within(guide).getByText("Type of Supplier")).toBeVisible();
  expect(within(guide).getByText("seller · nursery")).toBeVisible();
  await user.upload(
    screen.getByLabelText(/CSV file/),
    new File(
      [
        "name,kind,website,email,phone,notes\nCercatoridisemì,Nursery,https://new.example,,,\n",
      ],
      "suppliers.csv",
      { type: "text/csv" },
    ),
  );
  await user.click(
    screen.getByRole("button", { name: "Validate and preview" }),
  );
  expect(await screen.findByText("kind: 'Nursery' → nursery")).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Confirm import" }),
  ).not.toBeInTheDocument();
  await user.click(
    screen.getByRole("radio", { name: /Update existing: Cercatoridisemì/ }),
  );
  const changes = screen.getByRole("table", { name: "Changes if updated" });
  expect(within(changes).getByText("https://old.example")).toBeVisible();
  expect(within(changes).getByText("https://new.example")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Confirm import" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Updated 1");
  const apply = requests.find((request) =>
    request.path.endsWith("/imports/suppliers/apply"),
  );
  const raw = apply?.init?.body;
  if (typeof raw !== "string") throw new Error("Expected JSON import body");
  const body = JSON.parse(raw) as {
    decisions: Record<string, Record<string, string>>;
  };
  expect(body.decisions).toEqual({ "2": { record: "update-token" } });
});
