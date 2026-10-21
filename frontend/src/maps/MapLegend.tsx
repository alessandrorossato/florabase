export function MapLegend({
  label,
  items,
}: {
  label: string;
  items: { label: string; color: string }[];
}) {
  return (
    <div className="maps-legend" role="group" aria-label={label}>
      <strong>{label}</strong>
      <ul>
        {items.map((item) => (
          <li key={item.label}>
            <span aria-hidden="true" style={{ background: item.color }} />
            {item.label}
          </li>
        ))}
      </ul>
    </div>
  );
}
