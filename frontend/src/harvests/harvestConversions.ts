import type { Conversion } from "./conversionApi";

/**
 * One row per converted Seed lot, preferring a live conversion over a reversed one for the
 * same lot (Seed lot conversions are listed per stored-material row).
 */
export function uniqueConversions(rows: readonly Conversion[]): Conversion[] {
  const byLot = new Map<string, Conversion>();
  for (const row of rows) {
    const seen = byLot.get(row.seed_lot_id);
    if (!seen || (seen.status === "reversed" && row.status !== "reversed"))
      byLot.set(row.seed_lot_id, row);
  }
  return [...byLot.values()];
}

/** Seed lots that count as this Harvest's descendants: reversed conversions do not. */
export function countedConversions(rows: readonly Conversion[]): Conversion[] {
  return uniqueConversions(rows).filter((row) => row.status !== "reversed");
}
