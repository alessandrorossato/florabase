import { useId } from "react";
import type { DirectoryNameSort, DirectorySort } from "./directorySort";

type DirectorySortSelectProps =
  | {
      value: DirectorySort;
      onChange: (value: DirectorySort) => void;
      /** Which date "newest/oldest" uses, e.g. "sowing date". Omit for name-only directories. */
      dateLabel: string;
    }
  | {
      value: DirectoryNameSort;
      onChange: (value: DirectoryNameSort) => void;
      dateLabel?: undefined;
    };

export function DirectorySortSelect({
  value,
  onChange,
  dateLabel,
}: DirectorySortSelectProps) {
  const id = useId();
  const options = dateLabel
    ? [
        { value: "", label: "Default order" },
        { value: "name", label: "Name A–Z" },
        { value: "name_desc", label: "Name Z–A" },
        { value: "newest", label: `Newest ${dateLabel} first` },
        { value: "oldest", label: `Oldest ${dateLabel} first` },
      ]
    : [
        { value: "", label: "Default order" },
        { value: "name", label: "Name A–Z" },
        { value: "name_desc", label: "Name Z–A" },
      ];
  return (
    <div className="field directory-sort">
      <label className="sr-only" htmlFor={id}>
        Sort by
      </label>
      <select
        id={id}
        value={value}
        onChange={(event) => {
          (onChange as (value: DirectorySort) => void)(
            event.currentTarget.value as DirectorySort,
          );
        }}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
