// Inclusive, non-overlapping integer bins. The legend and polygons consume the same bins.
const colors = [
  "var(--native-count-low)",
  "var(--native-count-mid)",
  "var(--native-count-high)",
];
export function coverageScale(maximum: number) {
  const count = Math.min(3, maximum);
  return Array.from({ length: count }, (_, index) => {
    const from = Math.floor((index * maximum) / count) + 1;
    const to = Math.floor(((index + 1) * maximum) / count);
    return {
      from,
      to,
      label: from === to ? String(from) : `${String(from)}–${String(to)}`,
      color: colors[count === 1 ? 2 : index],
    };
  });
}
