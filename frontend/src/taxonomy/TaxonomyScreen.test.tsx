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
import {
  getTree,
  getIdentityTaxonomy,
  searchCandidates,
  confirmLink,
  unlink,
  type Tree,
  type Taxon,
} from "./api";
import { readState, taxonomyHash } from "./state";
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
  id: "identity-1",
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
  id: "identity-2",
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
  await screen.findByRole("button", { name: "Ocimum genus · 1 identity" });
  expect(
    screen.queryByRole("button", {
      name: "Ocimum basilicum species · 1 identity",
    }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Expand Ocimum" }));
  expect(
    screen.getByRole("button", { name: "Collapse Ocimum" }),
  ).toHaveAttribute("aria-expanded", "true");
  await user.click(
    screen.getByRole("button", { name: "Ocimum genus · 1 identity" }),
  );
  expect(window.location.hash).toContain(`taxon=${genusId}`);
  const detail = screen.getByRole("region", { name: "Selected taxon detail" });
  expect(
    within(detail).getByText(
      "1 represented identities · 1 Living · 1 Current · 0 Historical",
    ),
  ).toBeInTheDocument();
  expect(
    within(detail).getByRole("link", { name: "Local basil" }),
  ).toHaveAttribute("href", "#/identities/identity-1");
  expect(
    screen.getByRole("region", { name: "Unresolved taxonomy" }),
  ).toHaveTextContent("Unknown sage");
  expect(
    screen.getByRole("link", { name: "Link taxonomy source" }),
  ).toHaveAttribute("href", "#/identities/identity-2?tab=taxonomy");
  const before = vi.mocked(getTree).mock.calls.length;
  await user.click(screen.getByRole("button", { name: "Collapse Ocimum" }));
  expect(vi.mocked(getTree).mock.calls).toHaveLength(before);
});

test("scope and category OR filters, search, URL restoration and unavailable selection", async () => {
  const user = userEvent.setup();
  render(<TaxonomyScreen />);
  await screen.findByText("2 represented identities · 1 unresolved taxonomy");
  await user.click(screen.getByRole("button", { name: "Living" }));
  await user.click(screen.getByRole("checkbox", { name: "Seeds" }));
  await user.click(screen.getByRole("checkbox", { name: "Plants" }));
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
  expect(screen.getByRole("button", { name: "Historical" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await screen.findByText(
    "Selected taxon is missing or no longer eligible under these filters.",
  );
  expect(screen.getByRole("checkbox", { name: "Seeds" })).not.toBeChecked();
});

test("optional source absence and empty filter results stay explicit", async () => {
  vi.mocked(getTree).mockResolvedValue({
    ...tree,
    source_available: false,
    source: null,
    nodes: [],
    unresolved: 2,
    message: "Not installed",
    identities: [unresolved, { ...unresolved, id: "identity-3" }],
  });
  render(<TaxonomyScreen />);
  await screen.findByText(/Taxonomy source unavailable/);
  expect(
    screen.getByRole("button", { name: "Retry source" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("region", { name: "Taxonomic tree" }),
  ).not.toBeInTheDocument();
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
