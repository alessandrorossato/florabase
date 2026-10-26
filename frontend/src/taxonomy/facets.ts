import type { Identity, Tree } from "./api";
import type { TaxonomyState } from "./state";

// These counts remain global evidence from the authoritative collection projection.
export function identityCounts(identities: Identity[]) {
  return {
    represented: identities.length,
    living: identities.filter((i) => i.living_records > 0).length,
    current: identities.filter((i) => i.current_records > 0).length,
    historical: identities.filter((i) => i.current_records === 0).length,
  };
}
export function identitySubset(
  identities: Identity[],
  key: keyof ReturnType<typeof identityCounts>,
) {
  return identities.filter(
    (i) =>
      key === "represented" ||
      (key === "living"
        ? i.living_records > 0
        : key === "current"
          ? i.current_records > 0
          : i.current_records === 0),
  );
}

/** Narrow the existing bounded projection; never reclassify identities from category records. */
export function facetTree(
  data: Tree,
  state: Pick<TaxonomyState, "status" | "media">,
): Tree {
  if (!state.status && !state.media) return data;
  const identities = data.identities.filter(
    (i) =>
      (!state.status ||
        (state.status === "unlinked"
          ? !i.classification_ids?.length
          : state.status === "synonym"
            ? Boolean(i.classification_ids?.length && i.synonym_of)
            : Boolean(i.classification_ids?.length && !i.synonym_of))) &&
      (!state.media || (state.media === "with" ? Boolean(i.cover) : !i.cover)),
  );
  const contributions = new Map<string, Identity[]>();
  for (const identity of identities)
    for (const id of identity.classification_ids ?? []) {
      const rows = contributions.get(id) ?? [];
      rows.push(identity);
      contributions.set(id, rows);
    }
  return {
    ...data,
    identities,
    counts: identityCounts(identities),
    unresolved: identities.filter((i) => !i.classification_ids?.length).length,
    nodes: data.nodes
      .filter((n) => contributions.has(n.taxon.source_taxon_id))
      .map((n) => {
        const rows = contributions.get(n.taxon.source_taxon_id) ?? [];
        return {
          ...n,
          identity_ids: rows.map((i) => i.id),
          counts: identityCounts(rows),
        };
      }),
  };
}
