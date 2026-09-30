import { createContext, useContext, useEffect } from "react";
import type { BotanicalIdentityResponse } from "../botanical-identities/api";

type Identity = Pick<BotanicalIdentityResponse, "id" | "display_label"> &
  Partial<BotanicalIdentityResponse>;
export interface NamedRecord {
  label?: string | null;
  botanical_identity?: Identity;
  botanical_identity_id?: string;
  botanical_identity_display_label?: string;
  seed_lot?: {
    botanical_identity_id: string;
    botanical_identity_display_label: string;
  };
}
export const RecordIdentities = createContext<
  ReadonlyMap<string, BotanicalIdentityResponse>
>(new Map());
export function recordIdentity(
  record: NamedRecord | null | undefined,
  identities: ReadonlyMap<string, BotanicalIdentityResponse>,
): Identity | undefined {
  if (!record) return undefined;
  const flattened = record.seed_lot ?? record;
  const summary =
    record.botanical_identity ??
    (flattened.botanical_identity_id
      ? {
          id: flattened.botanical_identity_id,
          display_label: flattened.botanical_identity_display_label ?? "",
        }
      : undefined);
  return summary ? (identities.get(summary.id) ?? summary) : undefined;
}
export function recordDisplayName(
  record: NamedRecord | null | undefined,
  fallback: string,
  identities: ReadonlyMap<string, BotanicalIdentityResponse> = new Map(),
): string {
  const explicit = record?.label?.trim();
  if (explicit) return explicit;
  const identity = recordIdentity(record, identities);
  const scientific = identity?.scientific_name?.trim();
  const cultivar = identity?.cultivar_name?.trim();
  const common = identity?.common_name?.trim();
  if (common) return common;
  if (
    cultivar &&
    cultivar.toLocaleLowerCase() !== scientific?.toLocaleLowerCase()
  )
    return cultivar;
  if (scientific) return scientific;
  const summary = identity?.display_label.trim();
  if (summary) return summary;
  return fallback;
}
export function useRecordName() {
  const identities = useContext(RecordIdentities);
  return (record: NamedRecord | null | undefined, fallback: string) =>
    recordDisplayName(record, fallback, identities);
}

export const RecordIdentityWriter = createContext<
  ((items: BotanicalIdentityResponse[]) => void) | null
>(null);
export function usePublishRecordIdentities(
  items: BotanicalIdentityResponse[] | undefined,
) {
  const publish = useContext(RecordIdentityWriter);
  useEffect(() => {
    if (items && publish) publish(items);
  }, [items, publish]);
}
