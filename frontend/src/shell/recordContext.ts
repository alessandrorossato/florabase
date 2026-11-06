import { entryHref } from "../events/entryRequest";
import { labelComposerHref } from "../labels/labelData";
import type { IconName } from "../components/Icon";

export interface ContextAction {
  label: string;
  href: string;
  icon: IconName;
}
export interface RecordContext {
  /** "Plant", "Plant group", "Sowing" or "Seed lot". */
  noun: string;
  actions: ContextAction[];
}

const id = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Actions for the record whose detail page is open. Each is an existing route the page itself
 * offers regardless of lifecycle (Journal and germination entries, lineage, label), so the
 * shell never shows an action the page would withhold. Lifecycle-dependent actions (Start
 * sowing, Create Plant, Schedule activity) stay on the page.
 */
export function recordContext(hash: string): RecordContext | null {
  const [path] = hash.split("?", 1);
  const [, route, recordId] = path.split("/");
  if (!recordId || !id.test(recordId)) return null;
  const lineage = { label: "Open recorded lineage", icon: "layers" } as const;
  if (route === "plants" || route === "plant-groups") {
    const base = `#/${route}/${recordId}`;
    return {
      noun: route === "plants" ? "Plant" : "Plant group",
      actions: [
        {
          label: "Add Journal entry",
          href: entryHref(`${base}?tab=events`),
          icon: "journal",
        },
        { ...lineage, href: `${base}?tab=lineage` },
        {
          label: "Print label",
          href: labelComposerHref(
            route === "plants" ? "plant" : "plant-group",
            recordId,
          ),
          icon: "print",
        },
      ],
    };
  }
  if (route === "sowings") {
    const base = `#/sowings/${recordId}`;
    return {
      noun: "Sowing",
      actions: [
        {
          label: "Add germination observation",
          href: entryHref(`${base}?tab=germination`),
          icon: "sprout",
        },
        { ...lineage, href: `${base}?tab=lineage` },
      ],
    };
  }
  if (route === "seeds") {
    const base = `#/seeds/${recordId}`;
    return {
      noun: "Seed lot",
      actions: [
        { ...lineage, href: `${base}?tab=lineage` },
        {
          label: "Print label",
          href: labelComposerHref("seed-lot", recordId),
          icon: "print",
        },
      ],
    };
  }
  return null;
}
