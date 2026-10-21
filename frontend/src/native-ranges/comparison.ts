// Discrete identity colors: fill identity, never abundance or inferred precision.
export const comparisonPalette = [
  "#287c67",
  "#aa562d",
  "#5467b2",
  "#9a477a",
  "#81701f",
];

export function reconcileColors(
  ids: string[],
  previous: Record<string, string>,
) {
  const next = Object.fromEntries(
    ids.filter((id) => previous[id]).map((id) => [id, previous[id]]),
  );
  for (const id of ids) {
    if (!next[id]) {
      const color = comparisonPalette.find(
        (value) => !Object.values(next).includes(value),
      );
      if (color) next[id] = color;
    }
  }
  return next;
}

export function matchingContributors(
  territories: { source_code: string; identity_ids?: string[] }[],
  codes: string[],
  match: "any" | "all",
) {
  const sets = codes.map(
    (code) =>
      new Set(
        territories.find((unit) => unit.source_code === code)?.identity_ids ??
          [],
      ),
  );
  const union = new Set(sets.flatMap((set) => [...set]));
  return [...union].filter(
    (id) => match === "any" || sets.every((set) => set.has(id)),
  );
}
