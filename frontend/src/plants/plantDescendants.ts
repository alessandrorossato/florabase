/**
 * Where a Plant's harvest count links. No Harvest list filtered by source exists, so one
 * harvest opens directly, several open the species' Harvests, and none is plain text.
 */
export function harvestsHref(
  counts: { harvests: number; singleHarvestId: string | null },
  identityId: string,
): string | undefined {
  if (counts.singleHarvestId) return `#/harvests/${counts.singleHarvestId}`;
  if (counts.harvests > 1) return `#/identities/${identityId}?tab=harvests`;
  return undefined;
}
