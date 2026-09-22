# UX-004 BotanicalIdentity reference

Status: implemented; the operator has accepted this reference direction. Remaining entity and map
redesigns are deferred to later scoped increments. No other entity screen is restructured here.

## Visual vocabulary

The audit found a directory selection mounting the full detail, six equally weighted tabs, nested
bordered summary cards, an isolated technical cover panel, and repeated arbitrary colors/spacing.
The reference uses warm paper, botanical green, sage surfaces, editorial serif scientific names,
sans-serif metadata, restrained selection accents, and a shared spacing/radius scale. The global
shell receives only surface, gutter, and header hierarchy polish; lifecycle navigation is unchanged.

`ReferenceUI.tsx` provides PageHeader, QuickPreview, StatStrip, FormSection, and FormActions.
Existing DetailTabs, Breadcrumbs, FieldHelp/InfoDisclosure, creation focus management, and PhotoDialog
are reused. IdentityImage and IdentityName are domain-specific patterns, not a design framework.
Use semantic fieldsets for form groups, a two-column grid for related fields, and secondary Cancel
before the primary submit action. Identity creation uses a compact modal dialog; editing remains an
inline detail task. Both creation and cover dialogs use the existing focus trap, Escape handling and
focus restoration. No framework or remote visual asset was added. The botanical fallback is a local
decorative SVG, not an inferred image of the taxon.

## Navigation and information

- `#/identities`: searchable cards with an integrated thumbnail, separated scientific/cultivar names,
  common name and at most two active collection counts. Keyboard focus and pressed selection differ.
- Desktop selection exposes a compact preview with Open details, Add seed lot and Edit. The directory
  list is the bounded scrolling region; the page header and preview remain in the stable catalog
  frame. The preview uses only the directory response; it does not mount/fetch collection, profile,
  taxon links, maps, or per-record cover metadata. The shell sidebar navigation remains sticky within
  a full-height green band.
- At widths up to 68rem, cards open the dedicated detail directly and the preview is hidden.
- `#/identities/:id`: Overview alone uses the rich cover-and-summary row. Its representative image is
  contained at roughly 240–260px, with botanical name, optional cultivar/common name, collection KPIs,
  Add seed lot, secondary Edit and destructive overflow immediately available before the tabs.
  Collection, Reference and Events replace that hero with a compact work header so the active task is
  visible sooner. Detail content flows below; there is no sticky right rail and the directory is not
  mounted beside or underneath the detail.
- Overview shows record dates and limited recent activity without repeating the rail name and
  collection counts. Collection groups Seeds, Sowings and Plants / Plant groups with a visually
  distinct inner segmented control. Sowings separates source selection in a workflow launcher from
  recorded sowing cards. Reference has a subordinate Profile / Native range / Botanical source /
  Occurrences navigation and mounts only the chosen module. It opens in read mode, then reveals
  profile and native-range controls only on explicit Add/Edit/Manage actions. Provider changes remain
  under More; occurrence maps remain an explicit load. Events retains journal semantics.
- Existing `?tab=seeds`, `sowings`, and `plants` links still select the corresponding Collection
  subsection; `?tab=collection` opens Seeds. Overview, Reference and Events deep links remain valid.
  Tab selection replaces the current history entry; opening a record adds one. Back returns to the
  directory, retaining its search/selection while the screen is mounted. Reload restores the URL's
  record and section. `?tab=edit` opens the inline edit panel.

## Data, privacy and performance

The old directory response had no collection counts. Fetching full collection records just to
populate each preview would defeat the boundary. A narrow additive `collection_counts` summary on
the existing list response now aggregates active SeedLot, Sowing, Plant and PlantGroup records in one
SQL statement, with independently grouped joins to avoid row multiplication. It is a count of
records, not quantities, specimens inside groups, or inferred lineage. Non-directory responses may
omit it. OpenAPI and generated TypeScript declarations are updated; no persistence or migration.

Local cards and Quick Preview use the existing authenticated 320px local-cover thumbnail. The same
directory query now includes the nullable stored external cover URL, so every configured external
cover can render immediately without selection or a per-record metadata request. Those browser image
loads are lazy, decode asynchronously and use a no-referrer policy; there is no backend proxy, cache,
discovery, provider lookup or automatic image choice. Consequently, scrolling a directory can contact
each visible configured external image host. Missing or broken content returns to the local fallback.
The detail summary retains ATTACHMENT-003's acknowledged external-cover behavior, compact
human-facing attribution, and set/change/remove/retry controls. It loads its cover independently of
the selected tab; Reference still does not load collection records. Full collection data is fetched
once per mounted detail when Overview/Collection/Events needs it.
Leaflet and occurrence requests remain lazy and explicit. Collection-wide counts are refreshed
when returning to the directory.

## Deferred follow-ups

- A future occurrence-map increment may evaluate cache or persistence only after it defines
  freshness, invalidation, storage, attribution, licensing and privacy semantics. UX-004 adds none.
- A post-0.1.0 **Retrieve botanical data** action may make reviewed provider enrichment explicitly
  operator initiated. It requires an approved content and provenance contract before implementation;
  UX-004 does not infer, import or overwrite BotanicalProfile data.

## Operator review

The operator has completed repeated browser passes at approximately 1440px desktop, 1024px
compact desktop/tablet, and 390×844 mobile, and accepted the overall direction. The independent final
review verifies behavior and responsive/accessibility details; minor aesthetic refinements may remain
for later increments. Remaining entity and map redesigns and release hardening remain separate work.
