import "./breadcrumbs.css";
import { breadcrumbGroups, type BreadcrumbItem } from "./breadcrumbPaths";
/** Group labels have no landing route; never send a group crumb to Dashboard. */
export function Breadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  const first = items[0]?.label ?? "";
  const group = ["Botanical identities", "Media"].includes(first)
    ? "Explore"
    : ["Harvests", "Locations"].includes(first)
      ? "Collection"
      : null;
  const path = group ? [{ label: group }, ...items] : items;
  return (
    <nav aria-label="Breadcrumb" className="breadcrumbs">
      <ol>
        {path.map((item, index) => {
          const href =
            breadcrumbGroups.has(item.label) && item.href === "#/dashboard"
              ? undefined
              : item.href;
          return (
            <li
              key={`${item.label}:${String(index)}`}
              aria-current={
                index === path.length - 1 && !href ? "page" : undefined
              }
            >
              {href ? <a href={href}>{item.label}</a> : item.label}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
