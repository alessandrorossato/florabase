// Add a delivered canonical route here when another recording workflow is ready.
// Target-dependent workflows reuse their own detail route, never a small copy of their form.
export const recordWorkflows = [
  { label: "Record harvest", href: "#/harvests?action=create" },
  { label: "Record sowing", href: "#/sowings?action=create" },
  { label: "Take or add cuttings", href: "#/cuttings/new" },
  { label: "Move plants / groups", href: "#/plants" },
  { label: "Complete scheduled work", href: "#/schedule" },
] as const;
