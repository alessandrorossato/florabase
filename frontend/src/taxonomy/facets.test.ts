import { expect, test } from "vitest";
import { sample, ids } from "./graph.fixture";
import { facetTree, identityCounts, identitySubset } from "./facets";
import { readState, taxonomyHash } from "./state";

test("KPI subsets preserve global evidence and agree exactly with distinct counts", () => {
  const rows = [
    sample.identities[0],
    {
      ...sample.identities[1],
      id: "current-only",
      representation: "current" as const,
      current_records: 3,
      living_records: 0,
    },
    sample.identities[1],
  ];
  const counts = identityCounts(rows);
  expect(counts).toEqual({
    represented: 3,
    living: 1,
    current: 2,
    historical: 1,
  });
  for (const key of ["represented", "living", "current", "historical"] as const)
    expect(identitySubset(rows, key)).toHaveLength(counts[key]);
  expect(identitySubset(rows, "current").map((i) => i.id)).toContain(
    sample.identities[0].id,
  );
  expect(identitySubset(rows, "historical").map((i) => i.id)).not.toContain(
    sample.identities[0].id,
  );
});
test("status and stored-thumbnail facets reaggregate source nodes without recategorizing records", () => {
  const linked = { ...sample.identities[1], synonym_of: "Accepted basil" };
  const data = {
    ...sample,
    identities: [sample.identities[0], linked, sample.identities[2]],
  };
  const synonymous = facetTree(data, { status: "synonym" });
  expect(synonymous.identities).toEqual([linked]);
  expect(synonymous.counts).toEqual({
    represented: 1,
    living: 0,
    current: 0,
    historical: 1,
  });
  expect(
    synonymous.nodes.every(
      (n) => n.identity_ids.length === 1 && n.identity_ids[0] === linked.id,
    ),
  ).toBe(true);
  expect(
    synonymous.nodes.find((n) => n.taxon.source_taxon_id === ids.species)
      ?.parent_id,
  ).toBe(ids.genus);
  const covered = facetTree(data, { media: "with" });
  expect(covered.identities).toEqual([sample.identities[0]]);
  expect(covered.counts.living).toBe(1);
  expect(covered.identities[0].living_records).toBe(20);
  expect(facetTree(data, { status: "unlinked" }).nodes).toEqual([]);
  expect(
    facetTree(data, { status: "accepted", media: "without" }).identities,
  ).toEqual([]);
  expect(facetTree(data, {})).toBe(data);
});
test("facets and display preferences round trip without changing search or collection eligibility", () => {
  const state = {
    scope: "historical" as const,
    record: ["seed_lot" as const],
    q: "Basil",
    taxon: ids.species,
    branch: ids.genus,
    view: "tree" as const,
    status: "synonym" as const,
    media: "without" as const,
    photos: "hide" as const,
    ranks: "all" as const,
    through: "species" as const,
  };
  expect(readState(taxonomyHash(state))).toEqual(state);
  expect(
    readState("#/taxonomy?status=fake&media=unsafe&photos=show&ranks=fake"),
  ).not.toHaveProperty("status");
});
