import { RecordVisual, type RecordVisualKind } from "../photos/RecordVisual";
import type { PrimaryPhoto } from "../photos/api";
import type { components } from "../api/schema";

export function EventTargetPhoto({
  photo,
  fallbackPhoto,
  label,
  identity,
  kind,
}: {
  photo: PrimaryPhoto | null | undefined;
  fallbackPhoto?: PrimaryPhoto | null;
  label: string;
  identity: components["schemas"]["BotanicalIdentitySummary"];
  kind: RecordVisualKind;
}) {
  return (
    <div className="event-target-photo">
      <RecordVisual
        photo={photo}
        fallbackPhoto={fallbackPhoto}
        identity={identity}
        kind={kind}
        label={label}
        compact
      />
    </div>
  );
}
