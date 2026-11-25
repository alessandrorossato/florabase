import { useId } from "react";
import type { DirectorySort } from "./directorySort";

export function DirectorySortSelect({
  value,
  onChange,
  dateLabel,
}: {
  value: DirectorySort;
  onChange: (value: DirectorySort) => void;
  /** Which date "newest/oldest" uses, e.g. "sowing date". */
  dateLabel: string;
}) {
  const id = useId();
  return (
    <div className="field directory-sort">
      <label className="sr-only" htmlFor={id}>
        Sort by
      </label>
      <select
        id={id}
        value={value}
        onChange={(event) => {
          onChange(event.currentTarget.value as DirectorySort);
        }}
      >
        {[
          { value: "", label: "Default order" },
          { value: "name", label: "Name A–Z" },
          { value: "name_desc", label: "Name Z–A" },
          { value: "newest", label: `Newest ${dateLabel} first` },
          { value: "oldest", label: `Oldest ${dateLabel} first` },
        ].map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
