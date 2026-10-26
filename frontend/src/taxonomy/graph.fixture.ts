import type { Node, Tree } from "./api";
export function node(
  id: string,
  name: string,
  rank: string,
  parent: string | null,
  ids: string[] = ["identity-a"],
): Node {
  return {
    taxon: {
      source_taxon_id: id,
      scientific_name: name,
      rank,
      parent_source_taxon_id: parent,
      authorship: "L.",
      taxonomic_status: "accepted",
      accepted_source_taxon_id: id,
    },
    parent_id: parent,
    identity_ids: ids,
    counts: {
      represented: ids.length,
      living: ids.length,
      current: ids.length,
      historical: 0,
    },
  };
}
export const ids = {
  root: "wfo-4100001250",
  family: "wfo-9000000001",
  subfamily: "wfo-9000000002",
  genus: "wfo-9000000003",
  species: "wfo-9000000004",
  other: "wfo-9000000005",
};
export const sample: Tree = {
  source_available: true,
  source: {
    provider: "wfo",
    version: "2026-06",
    checksum: "a".repeat(64),
    archive_url: "https://example.org/release",
    license: "https://creativecommons.org/publicdomain/zero/1.0/",
    citation: "Synthetic test fixture",
    retrieved_at: "2026-10-25T12:00:00Z",
    format_version: 1,
  },
  message: null,
  unresolved: 1,
  counts: { represented: 3, living: 2, current: 2, historical: 1 },
  nodes: [
    node(ids.root, "Plantae", "kingdom", null, ["identity-a", "identity-b"]),
    node(ids.family, "Lamiaceae", "family", ids.root, [
      "identity-a",
      "identity-b",
    ]),
    node(ids.subfamily, "Nepetoideae", "subfamily", ids.family, [
      "identity-a",
      "identity-b",
    ]),
    node(ids.genus, "Ocimum", "genus", ids.subfamily, [
      "identity-a",
      "identity-b",
    ]),
    node(ids.species, "Ocimum basilicum", "species", ids.genus, [
      "identity-a",
      "identity-b",
    ]),
    node(ids.other, "Aloe vera", "species", ids.root, ["identity-c"]),
  ],
  identities: ["a", "b", "c"].map((suffix, i) => ({
    id: "identity-" + suffix,
    scientific_name: i < 2 ? "Ocimum basilicum" : "Aloe vera",
    display_label: i < 2 ? "Basil " + suffix : "Aloe vera",
    common_name: null,
    cultivar_name: null,
    representation: i === 1 ? "historical" : "living",
    retained_records: 20,
    current_records: i === 1 ? 0 : 20,
    living_records: i === 1 ? 0 : 20,
    matches_scope: true,
    classification_ids:
      i < 2
        ? [ids.root, ids.family, ids.subfamily, ids.genus, ids.species]
        : [],
    source_taxon_id: i < 2 ? ids.species : null,
    unresolved_reason: i < 2 ? null : "Not linked",
    synonym_of: null,
    cover:
      i === 0
        ? {
            asset_id: "asset-a",
            thumbnail_url: "/api/v1/media-assets/asset-a/thumbnail?v=abc",
            attribution: "Fixture photographer",
            licence_label: "CC0",
            licence_url: "https://creativecommons.org/publicdomain/zero/1.0/",
            source_url: "https://example.org/photo",
          }
        : null,
  })),
};
export function largeGraph(count = 5000): Node[] {
  const result = new Map<string, Node>();
  for (let i = 0; i < count; i++) {
    const family = i % 25,
      genus = i % 125;
    const path: [string, string, string][] = [
      ["wfo-4100001250", "Plantae", "kingdom"],
      ["wfo-9000000001", "Tracheophyta", "phylum"],
      ["wfo-9000000002", "Magnoliopsida", "class"],
      [
        "wfo-" + String(9000000100 + (family % 5)),
        "Order " + String(family % 5),
        "order",
      ],
      [
        "wfo-" + String(9000001000 + family),
        "Family " + String(family),
        "family",
      ],
      [
        "wfo-" + String(9000002000 + family),
        "Subfamily " + String(family),
        "subfamily",
      ],
      ["wfo-" + String(9000010000 + genus), "Genus " + String(genus), "genus"],
      ["wfo-" + String(9000100000 + i), "Species " + String(i), "species"],
    ];
    let parent: string | null = null;
    for (const [id, name, rank] of path) {
      let item = result.get(id);
      if (!item) {
        item = node(id, name, rank, parent, []);
        result.set(id, item);
      }
      item.identity_ids.push("identity-" + String(i));
      item.counts = {
        represented: item.identity_ids.length,
        living: item.identity_ids.length,
        current: item.identity_ids.length,
        historical: 0,
      };
      parent = id;
    }
  }
  return [...result.values()];
}
