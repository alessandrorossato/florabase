export function describedBy(
  ...ids: (string | null | undefined | false)[]
): string | undefined {
  const value = ids.filter(Boolean).join(" ");
  return value || undefined;
}
