import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

import { ExternalBotanicalDataPanel } from "./ExternalBotanicalDataPanel";

const identityId = "01900000-0000-7000-8000-000000000099";
const candidate = {
  external_id: "BSJCX",
  scientific_name: "Acacia acuminata Benth.",
  canonical_name: "Acacia acuminata",
  authorship: "Benth.",
  rank: "SPECIES",
  taxonomic_status: "ACCEPTED",
  accepted_external_id: "BSJCX",
  accepted_name: "Acacia acuminata Benth.",
  kingdom: "Plantae",
  phylum: "Tracheophyta",
  class_name: "Magnoliopsida",
  order_name: "Fabales",
  family: "Fabaceae",
  genus: "Acacia",
  match_type: "EXACT",
  confidence: 99,
  issues: [],
};
const linked = {
  ...candidate,
  provider: "gbif",
  provider_display_name: "GBIF",
  provider_url: "https://www.gbif.org/species/BSJCX",
  linked_at: "2026-09-09T10:00:00Z",
  last_refreshed_at: "2026-09-09T10:00:00Z",
  last_refresh_attempt_at: "2026-09-09T10:00:00Z",
  refresh_error: null,
  stale: false,
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function requestPath(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("search exposes ambiguity and requires explicit confirmation before linking", async () => {
  const synonym = {
    ...candidate,
    external_id: "SYN1",
    scientific_name: "Racosperma acuminatum (Benth.) Pedley",
    taxonomic_status: "SYNONYM",
    accepted_external_id: "BSJCX",
    match_type: "FUZZY",
    confidence: 82,
    issues: ["FUZZY_MATCH"],
  };
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((input, init) => {
      const path = requestPath(input);
      if (path.endsWith("external-taxon-link") && !init?.method)
        return Promise.resolve(json(null));
      if (path.includes("external-taxa/search")) {
        return Promise.resolve(
          json({
            provider: "gbif",
            query: "Acacia",
            fetched_at: "2026-09-09T10:00:00Z",
            from_cache: false,
            stale: false,
            provider_error: null,
            candidates: [candidate, synonym],
          }),
        );
      }
      if (path.endsWith("external-taxon-link") && init?.method === "PUT")
        return Promise.resolve(json(linked));
      throw new Error(`Unexpected request ${path}`);
    });
  const user = userEvent.setup();
  render(
    <ExternalBotanicalDataPanel
      identityId={identityId}
      scientificName="Acacia"
      csrfToken="csrf"
    />,
  );
  await screen.findByText(/must explicitly confirm a link/i);
  await user.click(screen.getByRole("button", { name: "Search GBIF" }));
  expect(await screen.findByText(/Racosperma acuminatum/)).toBeInTheDocument();
  expect(screen.getByText(/FUZZY match/)).toBeInTheDocument();
  expect(
    fetch.mock.calls.some(([url]) => requestPath(url).includes("search")),
  ).toBe(true);
  expect(screen.queryByText("Confirmed GBIF link")).not.toBeInTheDocument();
  await user.click(
    screen.getAllByRole("button", { name: "Confirm GBIF link" })[0],
  );
  expect(await screen.findByText("Confirmed GBIF link")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View on GBIF" })).toHaveAttribute(
    "href",
    linked.provider_url,
  );
});

test("linked stale state refreshes, changes, and unlinks without editing identity", async () => {
  const stale = {
    ...linked,
    stale: true,
    refresh_error: "provider_unavailable",
  };
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((input, init) => {
      const path = requestPath(input);
      if (path.endsWith("external-taxon-link") && !init?.method)
        return Promise.resolve(json(stale));
      if (path.endsWith("/refresh")) return Promise.resolve(json(linked));
      if (path.endsWith("external-taxon-link") && init?.method === "DELETE")
        return Promise.resolve(new Response(null, { status: 204 }));
      throw new Error(`Unexpected request ${path}`);
    });
  const user = userEvent.setup();
  render(
    <ExternalBotanicalDataPanel
      identityId={identityId}
      scientificName="Acacia"
      csrfToken="csrf"
    />,
  );
  expect(
    await screen.findByText(/retained cached data is shown/i),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Refresh" }));
  await waitFor(() => {
    expect(screen.queryByText(/retained cached data/i)).not.toBeInTheDocument();
  });
  await user.click(screen.getByRole("button", { name: "Change link" }));
  expect(screen.getByLabelText("Scientific-name search")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Unlink" }));
  expect(
    await screen.findByRole("button", { name: "Search GBIF" }),
  ).toBeInTheDocument();
  expect(fetch.mock.calls.some(([, init]) => init?.method === "DELETE")).toBe(
    true,
  );
});

test("narrow viewport preserves loading, empty-search, failure, and keyboard states", async () => {
  Object.defineProperties(window, {
    innerWidth: { configurable: true, value: 390 },
    innerHeight: { configurable: true, value: 844 },
  });
  let searchCount = 0;
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const path = requestPath(input);
    if (path.endsWith("external-taxon-link"))
      return Promise.resolve(json(null));
    if (path.includes("external-taxa/search")) {
      searchCount += 1;
      if (searchCount === 1) {
        return Promise.resolve(
          json({
            provider: "gbif",
            query: "Unknown plant",
            fetched_at: "2026-09-09T10:00:00Z",
            from_cache: false,
            stale: false,
            provider_error: null,
            candidates: [],
          }),
        );
      }
      return Promise.resolve(
        json(
          {
            detail: {
              code: "provider_unavailable",
              message: "GBIF is temporarily unavailable.",
            },
          },
          503,
        ),
      );
    }
    throw new Error(`Unexpected request ${path}`);
  });
  const user = userEvent.setup();
  render(
    <ExternalBotanicalDataPanel
      identityId={identityId}
      scientificName="Unknown plant"
      csrfToken="csrf"
    />,
  );

  expect(screen.getByRole("status")).toHaveTextContent(
    "Loading external reference",
  );
  const searchButton = await screen.findByRole("button", {
    name: "Search GBIF",
  });
  searchButton.focus();
  await user.keyboard("{Enter}");
  expect(await screen.findByText(/No GBIF candidates found/i)).toBeVisible();
  await user.keyboard("{Enter}");
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /temporarily unavailable/i,
  );
});
