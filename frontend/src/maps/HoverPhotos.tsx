import { RecordVisual } from "../photos/RecordVisual";
import "./hover-photos.css";

export interface PhotoIdentity {
  id: string;
  display_label: string;
}

export function HoverPhotosToggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="hover-photos-toggle">
      <input
        type="checkbox"
        role="switch"
        checked={checked}
        onChange={(event) => {
          onChange(event.currentTarget.checked);
        }}
      />
      Photos on hover
    </label>
  );
}

/** At most four botanical identity covers, then how many more there are. */
const hoverPhotoLimit = 4;

export function HoverPhotoStrip({
  identities,
  total = identities.length,
}: {
  identities: PhotoIdentity[];
  total?: number;
}) {
  const shown = identities.slice(0, hoverPhotoLimit);
  if (!shown.length) return null;
  const more = total - shown.length;
  return (
    <span className="hover-photos">
      <span className="hover-photos__thumbs">
        {shown.map((identity) => (
          <RecordVisual
            key={identity.id}
            kind="identity"
            compact
            identity={identity}
            label={identity.display_label}
            allowExternalCover
            className="hover-photos__thumb"
          />
        ))}
        {more > 0 && (
          <span className="hover-photos__more">+{String(more)}</span>
        )}
      </span>
      <small className="hover-photos__names">
        {shown.map((identity) => identity.display_label).join(", ")}
        {more > 0 ? ", …" : ""}
      </small>
    </span>
  );
}
