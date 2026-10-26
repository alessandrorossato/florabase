import {
  act,
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { TaxonomyScreen } from "./TaxonomyScreen";
import { IdentityTaxonomyPanel } from "./IdentityTaxonomyPanel";
import { ApiError } from "../auth/api";
import { getBotanicalIdentity } from "../botanical-identities/api";
import {
  getTree,
  getIdentityTaxonomy,
  searchCandidates,
  confirmLink,
  unlink,
  type Tree,
  type Taxon,
} from "./api";
import {
  readState,
  taxonomyHash,
  taxonomyIdentityHash,
  taxonomyReturnHash,
} from "./state";
vi.mock("../botanical-identities/api", () => ({
  getBotanicalIdentity: vi.fn(),
}));
vi.mock("./api", () => ({
  getTree: vi.fn(),
  getIdentityTaxonomy: vi.fn(),
  searchCandidates: vi.fn(),
  confirmLink: vi.fn(),
  unlink: vi.fn(),
}));
vi.mock("../auth/context", () => ({ useAuth: () => auth }));
const auth = { state: { csrfToken: "csrf" }, sessionExpired: vi.fn() };
const rootId = "wfo-4100001250",
  genusId = "wfo-4000000001",
  speciesId = "wfo-0000000001";
const identityId = "019a0000-0000-7000-8000-000000000001";
const unresolvedId = "019a0000-0000-7000-8000-000000000002";
const taxon = (
  id: string,
  name: string,
  rank: string,
  parent: string | null,
): Taxon => ({
  source_taxon_id: id,
  scientific_name: name,
  authorship: "L.",
  rank,
  parent_source_taxon_id: parent,
  taxonomic_status: "accepted",
  accepted_source_taxon_id: id,
});
const root = taxon(rootId, "Plantae", "kingdom", "wfo-9971000003"),
  genus = taxon(genusId, "Ocimum", "genus", rootId),
  species = taxon(speciesId, "Ocimum basilicum", "species", genusId);
const source = {
  provider: "wfo" as const,
  version: "2026-06" as const,
  checksum:
    "75f1ad1f371978c9e46f3044152c07ed276fe57be9fb9a15b3621b19cf231987" as const,
  archive_url: "https://zenodo.org/records/20782718",
  license: "https://creativecommons.org/publicdomain/zero/1.0/",
  citation: "World Flora Online",
  retrieved_at: "2026-10-09T14:48:29Z",
  format_version: 1 as const,
};
const counts = { represented: 1, living: 1, current: 1, historical: 0 };
const linked = {
  id: identityId,
  display_label: "Local basil",
  scientific_name: "Local basil",
  common_name: "Basil",
  cultivar_name: null,
  representation: "living" as const,
  retained_records: 3,
  current_records: 3,
  living_records: 1,
  matches_scope: true,
  source_taxon_id: speciesId,
  classification_ids: [rootId, genusId, speciesId],
  unresolved_reason: null,
  synonym_of: null,
};
const unresolved = {
  ...linked,
  id: unresolvedId,
  display_label: "Unknown sage",
  scientific_name: "Unknown sage",
  common_name: null,
  source_taxon_id: null,
  classification_ids: [],
  unresolved_reason: "Not linked to taxonomy source",
};
const tree: Tree = {
  source,
  source_available: true,
  message: null,
  identities: [linked, unresolved],
  nodes: [root, genus, species].map((taxon) => ({
    taxon,
    parent_id:
      taxon.source_taxon_id === rootId ? null : taxon.parent_source_taxon_id,
    counts,
    identity_ids: [linked.id],
  })),
  counts: { ...counts, represented: 2 },
  unresolved: 1,
};
const link = {
  version: "version-1",
  evidence: {
    source,
    taxon: species,
    classification: [root, genus, species],
    identity_updated_at: "2026-10-09T00:00:00Z",
  },
  confirmed_at: "2026-10-09T14:48:29Z",
  stale: false,
};
afterEach(cleanup);
beforeEach(() => {
  vi.resetAllMocks();
  window.history.replaceState(null, "", "#/taxonomy");
  vi.mocked(getTree).mockResolvedValue(tree);
  vi.mocked(getBotanicalIdentity).mockResolvedValue({
    ...unresolved,
    id: unresolvedId,
    created_at: "2026-10-09T00:00:00Z",
    updated_at: "2026-10-09T00:00:00Z",
  });
  vi.mocked(getIdentityTaxonomy).mockResolvedValue({
    source_available: true,
    source,
    link: null,
    related: [],
  });
});

test("classification expansion, selection, distinct counts and unresolved identities", async () => {
  const user = userEvent.setup();
  render(<TaxonomyScreen />);
  await screen.findByRole("button", { name: "Ocimum genus 1 identity" });
  expect(
    screen.getByRole("heading", { name: "Collection taxonomy", level: 2 }),
  ).toBeVisible();
  expect(screen.getByRole("region", { name: "Taxonomic tree" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Needs review 1" })).toBeVisible();
  expect(
    screen.queryByRole("button", {
      name: "Ocimum basilicum species 1 identity",
    }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Expand Ocimum" }));
  expect(
    screen.getByRole("button", { name: "Collapse Ocimum" }),
  ).toHaveAttribute("aria-expanded", "true");
  await user.click(
    screen.getByRole("button", { name: "Ocimum genus 1 identity" }),
  );
  expect(window.location.hash).toContain(`taxon=${genusId}`);
  const detail = screen.getByRole("region", { name: "Selected taxon detail" });
  expect(
    within(detail).getByRole("region", {
      name: "Collection representation counts",
    }),
  ).toHaveTextContent("Historical");
  for (const label of [
    "Identities: 1",
    "Living: 1",
    "Current: 1",
    "Historical: 0",
  ])
    expect(within(detail).getByRole("button", { name: label })).toBeVisible();
  await user.click(
    within(detail).getByRole("button", { name: "Identities: 1" }),
  );
  expect(screen.getByRole("link", { name: "Local basil" })).toHaveAttribute(
    "href",
    taxonomyIdentityHash(identityId, readState()),
  );
  await user.keyboard("{Escape}");
  const before = vi.mocked(getTree).mock.calls.length;
  await user.click(screen.getByRole("button", { name: "Collapse Ocimum" }));
  expect(vi.mocked(getTree).mock.calls).toHaveLength(before);
  await user.click(screen.getByRole("button", { name: "Needs review 1" }));
  expect(
    screen.getByRole("list", { name: "Unresolved taxonomy" }),
  ).toHaveTextContent("Unknown sage");
  expect(
    await screen.findByRole("link", { name: "Open botanical identity →" }),
  ).toHaveAttribute(
    "href",
    taxonomyIdentityHash(unresolvedId, readState(), true),
  );
  expect(getBotanicalIdentity).toHaveBeenCalledWith(
    unresolvedId,
    expect.any(AbortSignal),
  );
});

test("compressed intermediate ranks remain in the full path and can be restored in the hierarchy", async () => {
  const bridge = taxon("wfo-4000000002", "Nepetoideae", "subfamily", rootId);
  vi.mocked(getTree).mockResolvedValue({
    ...tree,
    nodes: [
      tree.nodes[0],
      { taxon: bridge, parent_id: rootId, counts, identity_ids: [identityId] },
      { ...tree.nodes[1], parent_id: bridge.source_taxon_id },
      tree.nodes[2],
    ],
  });
  window.history.replaceState(null, "", `#/taxonomy?taxon=${speciesId}`);
  const user = userEvent.setup();
  render(<TaxonomyScreen />);
  const path = await screen.findByRole("navigation", {
    name: "Source classification",
  });
  expect(
    within(path).getByRole("button", { name: "Nepetoideae subfamily" }),
  ).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Nepetoideae subfamily 1 identity" }),
  ).toBeNull();
  await user.click(screen.getByRole("button", { name: "Filters" }));
  await user.click(
    screen.getByRole("checkbox", { name: "Show every source rank" }),
  );
  await user.click(screen.getByRole("button", { name: "Done" }));
  expect(
    screen.getByRole("button", { name: "Nepetoideae subfamily 1 identity" }),
  ).toBeVisible();
});

test("scope and category OR filters, search, URL restoration and unavailable selection", async () => {
  const user = userEvent.setup();
  render(<TaxonomyScreen />);
  await screen.findByText("2 represented identities · 1 unresolved taxonomy");
  await user.click(screen.getByRole("button", { name: "Filters" }));
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Collection representation" }),
    "living",
  );
  await user.click(screen.getByRole("checkbox", { name: "Seeds" }));
  await user.click(screen.getByRole("checkbox", { name: "Plants" }));
  await user.click(screen.getByRole("button", { name: "Done" }));
  await user.type(
    screen.getByRole("searchbox", { name: "Search collection taxonomy" }),
    "Basil",
  );
  await waitFor(() => {
    expect(getTree).toHaveBeenLastCalledWith(
      expect.objectContaining({
        scope: "living",
        record: ["seed_lot", "plant"],
        q: "Basil",
      }),
      expect.any(AbortSignal),
    );
  });
  expect(window.location.hash).toContain(
    "record=seed_lot&record=plant&q=Basil",
  );
  act(() => {
    window.history.replaceState(
      null,
      "",
      "#/taxonomy?scope=historical&taxon=wfo-9999999999",
    );
    window.dispatchEvent(new PopStateEvent("popstate"));
  });
  await screen.findByText(
    "Selected taxon is missing or no longer eligible under these filters.",
  );
  await user.click(screen.getByRole("button", { name: "Filters (1)" }));
  expect(
    screen.getByRole("combobox", { name: "Collection representation" }),
  ).toHaveValue("historical");
  expect(screen.getByRole("checkbox", { name: "Seeds" })).not.toBeChecked();
});

test("optional source absence and empty filter results stay explicit", async () => {
  vi.mocked(getIdentityTaxonomy).mockResolvedValue({
    source_available: false,
    source: null,
    link: null,
    related: [],
    message: "Not installed",
  });
  vi.mocked(getTree).mockResolvedValue({
    ...tree,
    source_available: false,
    source: null,
    nodes: [],
    unresolved: 2,
    message: "The reviewed WFO taxonomy source is not installed.",
    identities: [unresolved, { ...unresolved, id: "identity-3" }],
  });
  render(<TaxonomyScreen />);
  await screen.findByText("WFO source not installed");
  expect(
    screen.getByRole("button", { name: "Retry source" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Classification —" }),
  ).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Local identities 2" }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(
    screen.getByRole("list", { name: "Unresolved taxonomy" }),
  ).toHaveTextContent("Unknown sage");
  expect(
    await screen.findByText(/Taxonomy source unavailable/),
  ).toBeInTheDocument();
});

test("Retry source refreshes the selected identity editor when the configured source becomes available", async () => {
  window.history.replaceState(
    null,
    "",
    `#/taxonomy?panel=unresolved&identity=${unresolvedId}`,
  );
  vi.mocked(getTree)
    .mockResolvedValueOnce({
      ...tree,
      source_available: false,
      source: null,
      nodes: [],
      message: "WFO source is not installed",
    })
    .mockResolvedValue(tree);
  vi.mocked(getIdentityTaxonomy)
    .mockResolvedValueOnce({
      source_available: false,
      source: null,
      link: null,
      related: [],
      message: "WFO source is not installed",
    })
    .mockResolvedValue({
      source_available: true,
      source,
      link: null,
      related: [],
    });
  const user = userEvent.setup();
  render(<TaxonomyScreen />);
  await screen.findByText(/Taxonomy source unavailable/);
  expect(
    screen.queryByRole("textbox", { name: "Search WFO names" }),
  ).toBeNull();
  await user.click(screen.getByRole("button", { name: "Retry source" }));
  expect(
    await screen.findByRole("textbox", { name: "Search WFO names" }),
  ).toBeVisible();
  expect(getBotanicalIdentity).toHaveBeenCalledTimes(2);
  expect(getIdentityTaxonomy).toHaveBeenCalledTimes(2);
  expect(confirmLink).not.toHaveBeenCalled();
});

test("canonical taxonomy URL excludes transient expansion state", () => {
  const state = readState(
    "#/taxonomy?scope=living&record=plant&record=seed_lot&record=plant&q=%25_&taxon=wfo-0000000001&expanded=foo",
  );
  expect(taxonomyHash(state)).toBe(
    "#/taxonomy?scope=living&record=seed_lot&record=plant&q=%25_&taxon=wfo-0000000001",
  );
  expect(readState("#/taxonomy?scope=bogus&record=bogus&taxon=bogus")).toEqual({
    scope: "all",
    record: [],
    q: "",
    taxon: "",
  });
});

test("explicit search, candidate inspection and confirmation preserve literal source identity", async () => {
  const user = userEvent.setup();
  vi.mocked(searchCandidates).mockResolvedValue([
    { taxon: species, classification: [root, genus, species] },
  ]);
  render(
    <IdentityTaxonomyPanel
      identityId="identity-1"
      updatedAt="2026-10-09T00:00:00Z"
    />,
  );
  await screen.findByText("No taxonomy source is linked.");
  await user.type(
    screen.getByRole("textbox", { name: "Search WFO names" }),
    "Ocimum",
  );
  expect(searchCandidates).not.toHaveBeenCalled();
  await user.click(
    screen.getByRole("button", { name: "Search taxonomy source" }),
  );
  await user.click(
    await screen.findByRole("button", {
      name: /Ocimum basilicum L\. · species · accepted/,
    }),
  );
  expect(confirmLink).not.toHaveBeenCalled();
  await user.click(
    screen.getByRole("button", { name: "Confirm taxonomy link" }),
  );
  await waitFor(() => {
    expect(confirmLink).toHaveBeenCalledWith(
      "identity-1",
      {
        source_taxon_id: speciesId,
        checksum: source.checksum,
        expected_version: null,
        identity_updated_at: "2026-10-09T00:00:00Z",
      },
      "csrf",
    );
  });
});

test("confirming the default review identity preserves its inspector while the queue updates", async () => {
  window.history.replaceState(null, "", "#/taxonomy?panel=unresolved");
  vi.mocked(getTree)
    .mockResolvedValueOnce(tree)
    .mockResolvedValue({
      ...tree,
      identities: [
        linked,
        {
          ...unresolved,
          classification_ids: linked.classification_ids,
          unresolved_reason: null,
        },
      ],
      unresolved: 0,
    });
  vi.mocked(searchCandidates).mockResolvedValue([
    { taxon: species, classification: [root, genus, species] },
  ]);
  const user = userEvent.setup();
  render(<TaxonomyScreen />);
  await user.type(
    await screen.findByRole("textbox", { name: "Search WFO names" }),
    "Ocimum",
  );
  await user.click(
    screen.getByRole("button", { name: "Search taxonomy source" }),
  );
  await user.click(
    await screen.findByRole("button", {
      name: /Ocimum basilicum L\. · species · accepted/,
    }),
  );
  await user.click(
    screen.getByRole("button", { name: "Confirm taxonomy link" }),
  );
  expect(
    await screen.findByText(
      "Taxonomy link confirmed. Botanical identity names are unchanged.",
    ),
  ).toBeVisible();
  await screen.findByText("No unresolved identities match these filters.");
  expect(
    screen.getByRole("heading", { name: "Unknown sage", level: 3 }),
  ).toBeVisible();
  expect(readState().identity).toBe(unresolvedId);
  expect(confirmLink).toHaveBeenCalledTimes(1);
});

test("breadcrumb and Related in my collection remain read-only", async () => {
  vi.mocked(getIdentityTaxonomy).mockResolvedValue({
    source_available: true,
    source,
    link,
    related: [
      {
        identity: { ...linked, id: "peer", display_label: "Holy basil" },
        relation: "Same genus",
      },
    ],
  });
  render(
    <IdentityTaxonomyPanel
      identityId="identity-1"
      updatedAt="2026-10-09T00:00:00Z"
      summary
    />,
  );
  const path = await screen.findByRole("navigation", {
    name: "Taxonomy classification",
  });
  expect(within(path).getByRole("link", { name: "Ocimum" })).toHaveAttribute(
    "href",
    `#/taxonomy?taxon=${genusId}`,
  );
  expect(
    screen.getByRole("region", { name: "Related in my collection" }),
  ).toHaveTextContent("Same genus");
  expect(screen.getByRole("link", { name: "Holy basil" })).toHaveAttribute(
    "href",
    "#/identities/peer",
  );
  expect(confirmLink).not.toHaveBeenCalled();
  expect(unlink).not.toHaveBeenCalled();
});

test("reloading an unavailable source discards previously inspected candidates", async () => {
  const user = userEvent.setup();
  vi.mocked(searchCandidates).mockResolvedValue([
    { taxon: species, classification: [root, genus, species] },
  ]);
  render(
    <IdentityTaxonomyPanel
      identityId="identity-1"
      updatedAt="2026-10-09T00:00:00Z"
    />,
  );
  await screen.findByText("No taxonomy source is linked.");
  await user.type(
    screen.getByRole("textbox", { name: "Search WFO names" }),
    "Ocimum",
  );
  await user.click(
    screen.getByRole("button", { name: "Search taxonomy source" }),
  );
  await user.click(
    await screen.findByRole("button", {
      name: /Ocimum basilicum L\. · species · accepted/,
    }),
  );
  expect(
    screen.getByRole("button", { name: "Confirm taxonomy link" }),
  ).toBeEnabled();
  vi.mocked(getIdentityTaxonomy).mockResolvedValue({
    source_available: false,
    source: null,
    link: null,
    message: "Not installed",
    related: [],
  });
  await user.click(screen.getByRole("button", { name: "Reload taxonomy" }));
  await screen.findByText(/Taxonomy source unavailable/);
  expect(
    screen.queryByRole("button", { name: "Confirm taxonomy link" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText("Searching local source…")).not.toBeInTheDocument();
  expect(confirmLink).not.toHaveBeenCalled();
});

test("source matching rejects a whitespace-only prefix before searching", async () => {
  const user = userEvent.setup();
  render(
    <IdentityTaxonomyPanel
      identityId={identityId}
      updatedAt="2026-10-09T00:00:00Z"
    />,
  );
  await screen.findByText("No taxonomy source is linked.");
  await user.type(
    screen.getByRole("textbox", { name: "Search WFO names" }),
    "  ",
  );
  await user.click(
    screen.getByRole("button", { name: "Search taxonomy source" }),
  );
  expect(screen.getByRole("alert")).toHaveTextContent("at least 2 characters");
  expect(searchCandidates).not.toHaveBeenCalled();
});

test("a 409 refreshes the authoritative identity and requires new candidate review", async () => {
  const user = userEvent.setup();
  const updatedAt = "2026-10-10T00:00:00Z";
  vi.mocked(searchCandidates).mockResolvedValue([
    { taxon: species, classification: [root, genus, species] },
  ]);
  vi.mocked(confirmLink)
    .mockRejectedValueOnce(new ApiError(409))
    .mockResolvedValue(undefined);
  vi.mocked(getBotanicalIdentity).mockResolvedValue({
    ...linked,
    id: identityId,
    display_label: "Updated local basil",
    scientific_name: "Updated local basil",
    created_at: "2026-10-09T00:00:00Z",
    updated_at: updatedAt,
  });
  render(
    <IdentityTaxonomyPanel
      identityId={identityId}
      updatedAt="2026-10-09T00:00:00Z"
    />,
  );
  await screen.findByText("No taxonomy source is linked.");
  await user.type(
    screen.getByRole("textbox", { name: "Search WFO names" }),
    "Ocimum",
  );
  await user.click(
    screen.getByRole("button", { name: "Search taxonomy source" }),
  );
  await user.click(
    await screen.findByRole("button", {
      name: /Ocimum basilicum L\. · species · accepted/,
    }),
  );
  await user.click(
    screen.getByRole("button", { name: "Confirm taxonomy link" }),
  );
  await screen.findByText(/This identity or source link changed/);
  expect(
    screen.getByRole("button", { name: "Confirm taxonomy link" }),
  ).toBeDisabled();
  await user.click(
    screen.getByRole("button", { name: "Refresh identity and review again" }),
  );
  expect(getBotanicalIdentity).toHaveBeenCalledWith(identityId);
  await screen.findByText("Updated local basil");
  expect(
    screen.queryByRole("button", { name: "Confirm taxonomy link" }),
  ).not.toBeInTheDocument();
  expect(confirmLink).toHaveBeenCalledTimes(1);
  await user.clear(screen.getByRole("textbox", { name: "Search WFO names" }));
  await user.type(
    screen.getByRole("textbox", { name: "Search WFO names" }),
    "Ocimum",
  );
  await user.click(
    screen.getByRole("button", { name: "Search taxonomy source" }),
  );
  await user.click(
    await screen.findByRole("button", {
      name: /Ocimum basilicum L\. · species · accepted/,
    }),
  );
  expect(confirmLink).toHaveBeenCalledTimes(1);
  await user.click(
    screen.getByRole("button", { name: "Confirm taxonomy link" }),
  );
  await waitFor(() => {
    expect(confirmLink).toHaveBeenLastCalledWith(
      identityId,
      expect.objectContaining({
        identity_updated_at: updatedAt,
        expected_version: null,
      }),
      "csrf",
    );
  });
});

test("request failure can retry without treating source absence as an API error", async () => {
  const user = userEvent.setup();
  vi.mocked(getTree)
    .mockRejectedValueOnce(new ApiError(500))
    .mockResolvedValue(tree);
  render(<TaxonomyScreen />);
  await screen.findByRole("alert");
  await user.click(screen.getByRole("button", { name: "Retry taxonomy" }));
  await screen.findByRole("button", { name: "Needs review 1" });
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test("review selection and return context are canonical and cannot redirect externally", () => {
  const hash = `#/taxonomy?scope=current&record=seed_lot&taxon=${genusId}&panel=unresolved&identity=${unresolvedId}`;
  const state = readState(hash);
  expect(taxonomyHash(state)).toBe(hash);
  const identityHash = taxonomyIdentityHash(unresolvedId, state, true);
  expect(taxonomyReturnHash(identityHash)).toBe(hash);
  expect(
    taxonomyReturnHash(
      "#/identities/example?taxonomy_return=https%3A%2F%2Fevil.example",
    ),
  ).toBeNull();
  expect(
    taxonomyReturnHash(
      "#/identities/example?taxonomy_return=%23%2Ftaxonomy-fake",
    ),
  ).toBeNull();
  expect(
    readState("#/taxonomy?panel=unresolved&identity=invalid").identity,
  ).toBeUndefined();
});

test("inspector jump controls move keyboard focus and the filter drawer restores focus", async () => {
  const user = userEvent.setup();
  render(<TaxonomyScreen />);
  await screen.findByRole("button", { name: "Needs review 1" });
  await user.click(screen.getByRole("button", { name: "Inspect selection ↓" }));
  expect(
    screen.getByRole("region", { name: "Selected taxon detail" }),
  ).toHaveFocus();
  await user.click(screen.getByRole("button", { name: "↑ Back to hierarchy" }));
  expect(screen.getByRole("region", { name: "Taxonomic tree" })).toHaveFocus();
  await user.click(screen.getByRole("button", { name: "Filters" }));
  await user.keyboard("{Escape}");
  expect(screen.getByRole("button", { name: "Filters" })).toHaveFocus();
});

test("Tree Explorer mode preserves filters/selection, restores URL state and keeps missing-source local review", async () => {
  const user = userEvent.setup();
  window.history.replaceState(
    null,
    "",
    `#/taxonomy?scope=current&record=plant&taxon=${speciesId}&view=tree`,
  );
  render(<TaxonomyScreen />);
  expect(
    await screen.findByRole("region", { name: "Interactive taxonomy diagram" }),
  ).toBeVisible();
  expect(getTree).toHaveBeenLastCalledWith(
    expect.objectContaining({
      scope: "current",
      record: ["plant"],
    }),
    expect.any(AbortSignal),
  );
  await user.click(screen.getByRole("button", { name: "List" }));
  expect(
    await screen.findByRole("list", { name: "Taxonomic classification" }),
  ).toBeVisible();
  expect(readState()).toMatchObject({
    scope: "current",
    record: ["plant"],
    taxon: speciesId,
  });
  expect(window.location.hash).not.toContain("view=tree");
  vi.mocked(getTree).mockResolvedValue({
    ...tree,
    source_available: false,
    source: null,
    nodes: [],
    message: "WFO source is not installed",
  });
  vi.mocked(getIdentityTaxonomy).mockResolvedValue({
    source_available: false,
    source: null,
    link: null,
    related: [],
  });
  await user.click(screen.getByRole("button", { name: "Tree explorer" }));
  cleanup();
  render(<TaxonomyScreen />);
  expect(
    await screen.findByText(/The diagram needs the configured WFO source/),
  ).toBeVisible();
  expect(
    screen.queryByRole("region", { name: "Interactive taxonomy diagram" }),
  ).toBeNull();
  expect(
    screen.getByRole("list", { name: "Unresolved taxonomy" }),
  ).toBeVisible();
});

test("compressed directory header and fullscreen fallback preserve the same graph camera and restore focus", async () => {
  window.history.replaceState(
    null,
    "",
    `#/taxonomy?view=tree&taxon=${speciesId}`,
  );
  const user = userEvent.setup();
  const { unmount } = render(<TaxonomyScreen />);
  const diagram = await screen.findByRole("region", {
    name: "Interactive taxonomy diagram",
  });
  expect(
    screen
      .getByRole("searchbox", { name: "Search collection taxonomy" })
      .closest("header"),
  ).toContainElement(screen.getByRole("button", { name: "List" }));
  await user.click(screen.getByRole("button", { name: "Zoom in" }));
  const world = diagram.querySelector(".tree-world"),
    camera = world?.getAttribute("style");
  const trigger = screen.getByRole("button", { name: "Fullscreen" });
  await user.click(trigger);
  const immersive = screen.getByRole("dialog", {
    name: "Collection taxonomy workspace",
  });
  expect(immersive).toHaveClass("taxonomy-stage--fullscreen");
  expect(screen.getByText(/Browser fullscreen unavailable/)).toBeVisible();
  expect(
    screen.getByRole("region", { name: "Interactive taxonomy diagram" }),
  ).toBe(diagram);
  expect(diagram.querySelector(".tree-world")).toBe(world);
  expect(world?.getAttribute("style")).toBe(camera);
  await user.click(screen.getByRole("button", { name: "Hide details" }));
  expect(
    screen.queryByRole("region", { name: "Selected taxon detail" }),
  ).toBeNull();
  await user.click(screen.getByRole("button", { name: "Show details" }));
  await user.click(screen.getByRole("button", { name: "Identities: 1" }));
  await user.keyboard("{Escape}");
  expect(
    screen.getByRole("dialog", { name: "Collection taxonomy workspace" }),
  ).toBeVisible();
  await user.keyboard("{Escape}");
  expect(
    screen.queryByRole("dialog", { name: "Collection taxonomy workspace" }),
  ).toBeNull();
  expect(trigger).toHaveFocus();
  expect(world?.getAttribute("style")).toBe(camera);
  expect(window.location.hash).toContain(`taxon=${speciesId}`);
  unmount();
  expect(document.body.style.overflow).toBe("");
});

test("native fullscreen external exit, denied request and navigation cleanup leave the workspace usable", async () => {
  let active: Element | null = null;
  const request = vi.fn(() => {
    active = document.querySelector(".taxonomy-screen");
    document.dispatchEvent(new Event("fullscreenchange"));
    return Promise.resolve();
  });
  const exit = vi.fn(() => {
    active = null;
    document.dispatchEvent(new Event("fullscreenchange"));
    return Promise.resolve();
  });
  Object.defineProperty(HTMLElement.prototype, "requestFullscreen", {
    configurable: true,
    value: request,
  });
  Object.defineProperty(document, "exitFullscreen", {
    configurable: true,
    value: exit,
  });
  Object.defineProperty(document, "fullscreenElement", {
    configurable: true,
    get: () => active,
  });
  try {
    window.history.replaceState(
      null,
      "",
      `#/taxonomy?view=tree&taxon=${speciesId}`,
    );
    const user = userEvent.setup(),
      { unmount } = render(<TaxonomyScreen />);
    await screen.findByRole("region", { name: "Interactive taxonomy diagram" });
    let finishRequest: (() => void) | undefined;
    request.mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          finishRequest = resolve;
        }),
    );
    await user.click(screen.getByRole("button", { name: "Fullscreen" }));
    expect(request).toHaveBeenCalledTimes(1);
    expect(
      screen.queryByRole("dialog", { name: "Collection taxonomy workspace" }),
    ).toBeNull();
    await act(async () => {
      active = document.querySelector(".taxonomy-screen");
      document.dispatchEvent(new Event("fullscreenchange"));
      finishRequest?.();
      await Promise.resolve();
    });
    expect(
      await screen.findByRole("dialog", {
        name: "Collection taxonomy workspace",
      }),
    ).toBeVisible();
    act(() => {
      active = null;
      document.dispatchEvent(new Event("fullscreenchange"));
    });
    expect(
      screen.queryByRole("dialog", { name: "Collection taxonomy workspace" }),
    ).toBeNull();
    request.mockRejectedValueOnce(new Error("Denied"));
    await user.click(screen.getByRole("button", { name: "Fullscreen" }));
    expect(
      await screen.findByText(/Browser fullscreen unavailable/),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Exit fullscreen" }));
    await user.click(screen.getByRole("button", { name: "Fullscreen" }));
    exit.mockRejectedValueOnce(new Error("Native exit failed"));
    await user.click(screen.getByRole("button", { name: "Exit fullscreen" }));
    expect(
      await screen.findByText("Use your browser's fullscreen control to exit."),
    ).toBeVisible();
    unmount();
    expect(exit).toHaveBeenCalled();
  } finally {
    delete (HTMLElement.prototype as Partial<HTMLElement>).requestFullscreen;
    delete (document as Partial<Document>).exitFullscreen;
    Reflect.deleteProperty(document, "fullscreenElement");
  }
});
