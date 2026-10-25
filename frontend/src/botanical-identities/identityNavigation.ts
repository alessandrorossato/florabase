export function identityDirectory(
  kind: "seeds" | "sowings" | "plants" | "groups" | "harvests",
  id: string,
) {
  const path = kind === "groups" ? "plants" : kind;
  return `#/${path}?identity_id=${id}${path !== "harvests" ? "&lifecycle=all" : ""}${kind === "groups" ? "&type=group" : kind === "plants" ? "&type=plant" : ""}`;
}
