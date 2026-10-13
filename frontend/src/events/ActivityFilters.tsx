import { toggleSelection } from "./filterSelection";
export function ActivityChoices<T extends string>({
  title,
  labels,
  selected,
  onChange,
}: {
  title: string;
  labels: Record<T, string>;
  selected: readonly T[];
  onChange: (selected: T[]) => void;
}) {
  const values = Object.keys(labels) as T[];
  return (
    <fieldset className="dashboard-filter-group activity-choice-group">
      <legend>{title}</legend>
      <div className="activity-choice-grid">
        {values.map((value) => (
          <label key={value}>
            <input
              type="checkbox"
              checked={selected.includes(value)}
              onChange={() => {
                onChange(toggleSelection(values, selected, value));
              }}
            />
            {labels[value]}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
