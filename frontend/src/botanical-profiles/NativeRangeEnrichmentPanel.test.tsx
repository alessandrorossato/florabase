import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { NativeRangeEnrichmentPanel } from "./NativeRangeEnrichmentPanel";

const auth = {
  state: { status: "authenticated", csrfToken: "csrf" },
  sessionExpired: vi.fn(),
};
vi.mock("../auth/context", () => ({ useAuth: () => auth }));
const identityId = "01900000-0000-7000-8000-000000000099";
const bo = "01900000-0000-7000-8000-000000000001";
const pe = "01900000-0000-7000-8000-000000000002";
const it = "01900000-0000-7000-8000-000000000003";
const taxon = {
  external_id: "100",
  name: "Fixture species",
  authorship: "A.Author",
  rank: "Species",
  status: "Accepted",
  accepted_id: "100",
  accepted_name: "Fixture species",
  powo_id: "",
  reviewed: "Y",
};
const source = {
  provider: "kew_wcvp",
  version: "15",
  archive_url:
    "https://sftp.kew.org/pub/data-repositories/WCVP/Archive/wcvp_v15.zip",
  checksum: "a".repeat(64),
  license: "https://creativecommons.org/licenses/by/3.0/",
  citation: "Kew fixture citation",
  retrieved_at: "2026-10-09T00:00:00Z",
  coverage: "complete",
};
const link = {
  version: identityId,
  taxon,
  source,
  stale: false,
  confirmed_at: "2026-10-09T00:00:00Z",
};
const proposal = {
  id: identityId,
  created_at: "2026-10-09T00:00:00Z",
  applied_at: null,
  format_version: 1,
  link_version: identityId,
  identity_snapshot: {},
  destination_version: 3,
  current_ids: [it],
  source,
  taxon,
  retrieved_at: "2026-10-09T00:00:00Z",
  crosswalk_version: "reviewed-crosswalk-v1",
  choices: [
    {
      place_id: bo,
      name: "Bolivia",
      path: "South America → Bolivia",
      code: "BO",
      change: "ADD",
      assertions: ["1"],
    },
    {
      place_id: pe,
      name: "Peru",
      path: "South America → Peru",
      code: "PE",
      change: "ADD",
      assertions: ["2"],
    },
    {
      place_id: it,
      name: "Italy",
      path: "Europe → Italy",
      code: "IT",
      change: "CURRENT-ONLY",
      assertions: [],
    },
  ],
  assertions: [
    {
      assertion_id: "1",
      original: {
        area: "Bolivia",
        area_code_l3: "BOL",
        introduced: "0",
        extinct: "0",
        location_doubtful: "0",
        region_code_l2: "83",
      },
      status: "native",
      mapping: "equivalent",
      note: "Exact mapping",
      place_ids: [bo],
    },
    {
      assertion_id: "3",
      original: {
        area: "Bulgaria",
        area_code_l3: "BUL",
        introduced: "1",
        extinct: "0",
        location_doubtful: "0",
        region_code_l2: "13",
      },
      status: "introduced",
      mapping: "equivalent",
      note: "Context only",
      place_ids: [],
    },
    {
      assertion_id: "4",
      original: {
        area: "Italy",
        area_code_l3: "ITA",
        introduced: "0",
        extinct: "0",
        location_doubtful: "0",
        region_code_l2: "13",
      },
      status: "native",
      mapping: "partial",
      note: "Cannot round to Italy",
      place_ids: [],
    },
  ],
};
function requestUrl(input: RequestInfo | URL): string {
  return typeof input === "string"
    ? input
    : input instanceof URL
      ? input.href
      : input.url;
}
function requestBody(body: BodyInit | null | undefined): string {
  if (typeof body !== "string") throw new Error("Expected JSON request body");
  return body;
}
function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function setup(
  options: { available?: boolean; linked?: boolean; failure?: number } = {},
) {
  const applied = vi.fn();
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((input, init) => {
      const path = requestUrl(input);
      if (path.endsWith("/source"))
        return Promise.resolve(
          json({
            available: options.available ?? true,
            source: options.available === false ? null : source,
            link: options.linked === false ? null : link,
            message: "Snapshot unavailable",
          }),
        );
      if (path.includes("/taxa?"))
        return Promise.resolve(
          json([
            taxon,
            { ...taxon, external_id: "101", status: "Synonym" },
            { ...taxon, external_id: "102", accepted_id: "102" },
          ]),
        );
      if (path.endsWith("/link")) return Promise.resolve(json(link));
      if (path.endsWith("/proposals") && init?.method === "POST")
        return Promise.resolve(
          options.failure === 503
            ? json({ detail: {} }, 503)
            : json(proposal, 201),
        );
      if (path.endsWith("/proposals")) return Promise.resolve(json([]));
      if (path.endsWith("/apply"))
        return Promise.resolve(
          options.failure === 409
            ? json({ detail: {} }, 409)
            : json({
                proposal_id: identityId,
                applied_at: "2026-10-09T01:00:00Z",
                added: [bo],
                kept: [it],
                destination_version: 4,
              }),
        );
      throw new Error(`Unexpected request ${path}`);
    });
  render(
    <NativeRangeEnrichmentPanel identityId={identityId} onApplied={applied} />,
  );
  return { fetch, applied, user: userEvent.setup() };
}

test("opening a native range does not fetch or write provider state", () => {
  const { fetch } = setup();
  expect(fetch).not.toHaveBeenCalled();
});
test("exact taxon selection distinguishes duplicates and synonym and requires confirmation", async () => {
  const { fetch, user } = setup({ linked: false });
  await user.click(
    screen.getByRole("button", { name: "Check trusted source" }),
  );
  await user.type(
    await screen.findByLabelText(/WCVP scientific name/),
    "Fixture",
  );
  await user.click(screen.getByRole("button", { name: "Search WCVP taxa" }));
  const choices = await screen.findAllByRole("radio");
  expect(choices).toHaveLength(3);
  expect(choices[1]).toBeDisabled();
  await user.click(choices[2]);
  expect(fetch.mock.calls.some(([, init]) => init?.method === "PUT")).toBe(
    false,
  );
  await user.click(screen.getByRole("button", { name: "Confirm this taxon" }));
  await screen.findByText(/WCVP taxon confirmed/);
  const call = fetch.mock.calls.find(([, init]) => init?.method === "PUT");
  expect(JSON.parse(requestBody(call?.[1]?.body))).toEqual({
    external_id: "102",
    checksum: source.checksum,
  });
});
test("selective Apply is confirmed, keeps manual ranges and exposes source limitations", async () => {
  const { fetch, applied, user } = setup();
  await user.click(
    screen.getByRole("button", { name: "Check trusted source" }),
  );
  await user.click(
    await screen.findByRole("button", { name: "Retrieve source proposal" }),
  );
  await user.click(await screen.findByRole("checkbox", { name: /ADD: Peru/ }));
  expect(
    screen.getByRole("checkbox", { name: /CURRENT-ONLY: Italy/ }),
  ).toBeDisabled();
  await user.click(screen.getByText(/Original source evidence/));
  expect(screen.getByText(/Introduced — context only/)).toBeVisible();
  expect(screen.getByText(/UNMAPPED SOURCE/)).toBeVisible();
  await user.click(
    screen.getByRole("button", { name: "Apply reviewed changes" }),
  );
  expect(
    fetch.mock.calls.some(([url]) => requestUrl(url).endsWith("/apply")),
  ).toBe(false);
  expect(
    screen.getByText(
      /Add 1 selected ranges. Keep all 1 existing ranges. Remove none./,
    ),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Confirm Apply" }));
  await screen.findByText(/Applied 1 additions. Kept 1 existing ranges./);
  const call = fetch.mock.calls.find(([url]) =>
    requestUrl(url).endsWith("/apply"),
  );
  expect(JSON.parse(requestBody(call?.[1]?.body))).toEqual({
    selected_place_ids: [bo],
  });
  expect(applied).toHaveBeenCalledOnce();
});
test("stale Apply shows a focused conflict and does not refresh canonical ranges as success", async () => {
  const { applied, user } = setup({ failure: 409 });
  await user.click(
    screen.getByRole("button", { name: "Check trusted source" }),
  );
  await user.click(
    await screen.findByRole("button", { name: "Retrieve source proposal" }),
  );
  await user.click(
    await screen.findByRole("button", { name: "Apply reviewed changes" }),
  );
  await user.click(screen.getByRole("button", { name: "Confirm Apply" }));
  const error = await screen.findByRole("alert");
  await waitFor(() => {
    expect(error).toHaveFocus();
  });
  expect(error).toHaveTextContent(/changed/);
  expect(applied).not.toHaveBeenCalled();
});
test("source failure retains current workflow and gives retryable feedback", async () => {
  const { user, applied } = setup({ failure: 503 });
  await user.click(
    screen.getByRole("button", { name: "Check trusted source" }),
  );
  await user.click(
    await screen.findByRole("button", { name: "Retrieve source proposal" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /recorded ranges and previous evidence remain/,
  );
  expect(applied).not.toHaveBeenCalled();
});
test("missing snapshot does not prevent viewing recorded ranges", async () => {
  const { user } = setup({ available: false });
  await user.click(
    screen.getByRole("button", { name: "Check trusted source" }),
  );
  expect(
    await screen.findByText(/Recorded ranges remain usable/),
  ).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Search WCVP taxa" }),
  ).not.toBeInTheDocument();
});
