export function toggleSelection<T extends string>(
  values: readonly T[],
  selected: readonly T[],
  value: T,
): T[] {
  return values.filter((item) =>
    item === value ? !selected.includes(item) : selected.includes(item),
  );
}
export function selectionLabel<T extends string>(
  selected: readonly T[],
  labels: Record<T, string>,
): string {
  return selected.length
    ? `${labels[selected[0]]}${selected.length > 1 ? ` +${String(selected.length - 1)}` : ""}`
    : "";
}
