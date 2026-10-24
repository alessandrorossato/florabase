/** Stable main sections; historical URLs remain entry points to the new hub. */
export const identitySections = [
  "overview",
  "reference",
  "taxonomy",
  "maps",
  "media",
  "history",
] as const;
export type IdentitySection = (typeof identitySections)[number];
export function identitySection(tab?: string): IdentitySection {
  if (identitySections.includes(tab as IdentitySection))
    return tab as IdentitySection;
  if (tab === "events") return "history";
  if (tab === "source") return "taxonomy";
  if (tab === "native-range" || tab === "occurrences") return "maps";
  if (tab === "profile") return "reference";
  return "overview";
}
export function identityAnchor(tab?: string): string | undefined {
  if (
    ["collection", "seeds", "sowings", "plants", "harvests"].includes(tab ?? "")
  )
    return "identity-footprint";
  if (tab === "source") return "identity-source";
  if (tab === "native-range" || tab === "occurrences") return `identity-${tab}`;
  return undefined;
}
