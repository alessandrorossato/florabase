export function sidebarWidthLimit(viewport: number) {
  return Math.max(220, Math.min(400, Math.floor(viewport * 0.35)));
}
