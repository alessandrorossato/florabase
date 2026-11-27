import { useContext, useEffect, useId, useRef, useState } from "react";
import {
  activeCsrfToken,
  ApiError,
  isExpectedAuthCancellation,
} from "../auth/api";
import { useAuth } from "../auth/context";
import { ActionButton } from "../components/Action";
import {
  Breadcrumbs,
  DetailTabs,
  DetailHeader,
  RecordDescendants,
  RecordOverview,
  WorkspaceIntro,
  DetailLoading,
  DetailPage,
  SpecimenLabel,
  SpecimenPlate,
} from "../components/CollectionUI";
import { LifecycleStatus } from "../components/WorkspaceUI";
import {
  DirectoryRecordActions,
  DirectoryRecordContent,
  DirectoryTrigger,
  DirectoryWorkspace,
} from "../components/DirectoryPage";
import { DirectoryResults } from "../components/DirectoryResults";
import { DirectoryTools } from "../components/DirectoryTools";
import {
  BotanicalName,
  DirectorySearch,
  OverflowMenu,
  PageHeader,
} from "../components/ReferenceUI";
import { TaskDialog } from "../components/TaskDialog";
import "../components/collection-page.css";
import {
  closeCollectionPage,
  collectionPageParent,
  openCollectionPage,
  setRecordRoute,
} from "../components/recordNavigation";
import { RecordIdentities } from "../components/recordPresentation";
import { useRecordDetailFocus } from "../components/useRecordDetailFocus";
import { useCollectionPageReturnFocus } from "../components/useCollectionPageReturnFocus";
import { useDirectoryPagination } from "../components/useDirectoryPagination";
import { DirectorySortSelect } from "../components/DirectorySort";
import { sortDirectory } from "../components/directorySort";
import { useEditRoute } from "../components/useEditRoute";
import { formatPartialDate } from "../events/eventData";
import { LineagePanel } from "../lineage/LineagePanel";
import { LineageStrip } from "../lineage/LineageStrip";
import {
  ancestryHref,
  type AncestryChildren,
} from "../lineage/useRecordedLineage";
import { PhotosSection } from "../photos/PhotosSection";
import { RecordVisual } from "../photos/RecordVisual";
import { usePhotoCount } from "../photos/usePhotoCount";
import { SavedViews } from "../saved-views/SavedViews";
import { useDirectoryView } from "../saved-views/useDirectoryView";
import { defaultState, scheduleHash } from "../schedule/state";
import type { ReferenceChoice } from "../seed-lots/ReferencePicker";
import { RecordAlmanac } from "../timeline/RecordAlmanac";
import { BotanicalIdentityFilter } from "./BotanicalIdentityFilter";
import { HarvestForm } from "./HarvestForm";
import {
  StoredMaterialDirectory,
  StoredMaterialSection,
} from "./StoredMaterial";
import {
  deleteHarvest,
  getHarvest,
  identityChoices,
  listHarvests,
  materialSummary,
  materials,
  type Harvest,
} from "./api";
import { listConversions, type Conversion } from "./conversionApi";
import "./collection-visual.css";
import "./directory.css";
import {
  inventoryError,
  inventoryList,
  remainingLabel,
  type Inventory,
} from "./inventoryApi";

function directoryMaterialSummary(harvest: Harvest): string {
  const labels = materialSummary(harvest).split(" · ");
  return labels.length > 2
    ? `${labels.slice(0, 2).join(" · ")} · +${String(labels.length - 2)} more`
    : labels.join(" · ");
}
function sourceHref(harvest: Harvest): string {
  return `#/${harvest.source.type === "plant" ? "plants" : "plant-groups"}/${harvest.source.id}`;
}
function Visual({
  harvest,
  compact = false,
}: {
  harvest: Harvest;
  compact?: boolean;
}) {
  return (
    <RecordVisual
      photo={harvest.primary_photo}
      identity={harvest.source.botanical_identity}
      kind="harvest"
      label={harvest.display_title}
      compact={compact}
      showSource
    />
  );
}
export function HarvestScreen({
  initialId,
  initialTab,
  startCreating = false,
  sourceType,
  sourceId,
}: {
  initialId?: string;
  initialTab?: string;
  startCreating?: boolean;
  sourceType?: "plant" | "plant_group";
  sourceId?: string;
}) {
  const creating = startCreating;
  const storedMode = !initialId && initialTab === "stored-material";
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const recordIdentities = useContext(RecordIdentities);
  const headingId = useId();
  const directoryList = useRef<HTMLUListElement>(null);
  const detailHeading = useRef<HTMLHeadingElement>(null);
  const [records, setRecords] = useState<Harvest[] | null>(null);
  const [detail, setDetail] = useState<Harvest | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editor, setEditor] = useState<Harvest | null>(null);
  const moreTrigger = useRef<HTMLButtonElement>(null);
  const [deleting, setDeleting] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const view = useDirectoryView("harvests", () => {
    setSelectedId(null);
  });
  const query = view.state.q;
  const setQuery = (value: string) => {
    view.update("q", value);
  };
  const material = view.state.material;
  const setMaterial = (value: string) => {
    view.update("material", value);
  };
  const type = view.state.source_type;
  const setType = (value: string) => {
    view.update("source_type", value);
  };
  const identity = view.state.identity_id;
  const setIdentity = (value: string) => {
    view.update("identity_id", value);
  };

  const [identities, setIdentities] = useState<ReferenceChoice[]>([]);
  useEffect(() => {
    if (storedMode || !authorized) return;
    const controller = new AbortController();
    const request = initialId
      ? getHarvest(initialId, capability, controller.signal)
      : listHarvests(capability, controller.signal, identity);
    void request
      .then((result) => {
        if (controller.signal.aborted) return;
        setError(null);
        if (Array.isArray(result)) {
          setRecords(result);
          if (!identity)
            setIdentities(
              identityChoices(result.map((record) => record.source)),
            );
        } else setDetail(result);
      })
      .catch((failure: unknown) => {
        if (controller.signal.aborted || isExpectedAuthCancellation(failure))
          return;
        if (failure instanceof ApiError && failure.status === 401)
          sessionExpired();
        else setError("Could not load Harvests. Please retry.");
      });
    return () => {
      controller.abort();
    };
  }, [
    initialId,
    storedMode,
    attempt,
    identity,
    authorized,
    capability,
    sessionExpired,
  ]);
  const filtered = records?.filter(
    (record) =>
      (!identity || record.source.botanical_identity.id === identity) &&
      (!type || record.source.type === type) &&
      (!material ||
        record.items.some((item) => item.material_kind === material)) &&
      `${record.display_title} ${record.source.display_name} ${record.source.botanical_identity.display_label}`
        .toLocaleLowerCase()
        .includes(query.trim().toLocaleLowerCase()),
  );
  const matching = filtered ?? [];
  const ordered = sortDirectory(
    matching,
    view.state.sort,
    (record) => record.display_title,
    (record) => record.occurred_on,
  );
  const pageFilterKey = JSON.stringify([
    query,
    identity,
    type,
    material,
    view.state.sort,
  ]);

  const pagination = useDirectoryPagination(ordered, pageFilterKey);
  const { visible: pageRecords } = pagination;
  useCollectionPageReturnFocus(Boolean(records) && !creating && !initialId);
  const [backgroundId, setBackgroundId] = useState<string | undefined>(
    undefined,
  );
  const dismissalRef = useRef<(() => boolean) | null>(null);
  const directEditHandled = useRef(false);
  const edit = useEditRoute({
    routeIsEdit: initialTab === "edit",
    canDismiss: () => dismissalRef.current?.() ?? true,
    onDismiss: () => {
      setEditor(null);
      if (!edit.modal && initialId)
        setRecordRoute(`#/harvests/${initialId}`, true);
    },
  });
  useEffect(() => {
    if (initialTab !== "edit") directEditHandled.current = false;
    else if (detail?.id === initialId && !directEditHandled.current) {
      directEditHandled.current = true;
      setEditor(detail);
    }
  }, [initialTab, detail, initialId]);
  function openEditor(record: Harvest | "new") {
    setError(null);
    if (record === "new") openCollectionPage("#/harvests?action=create");
    else {
      directEditHandled.current = true;
      setBackgroundId(initialId);
      setEditor(record);
      edit.open(`#/harvests/${record.id}?action=edit`);
    }
  }
  const displayId = editor && edit.modal ? backgroundId : initialId;
  const routeTab: "overview" | "photos" | "lineage" =
    initialTab === "photos"
      ? "photos"
      : initialTab === "lineage"
        ? "lineage"
        : "overview";
  const [detailTab, setDetailTab] = useState<"overview" | "photos" | "lineage">(
    routeTab,
  );
  // Each record opens on the tab its route names (a new record or a later ?tab= change).
  const tabRoute = `${initialId ?? ""}:${routeTab}`;
  const [lastTabRoute, setLastTabRoute] = useState(tabRoute);
  if (lastTabRoute !== tabRoute) {
    setLastTabRoute(tabRoute);
    setDetailTab(routeTab);
  }
  const [inventoriesState, setInventoriesState] = useState<{
    harvestId: string;
    rows: Inventory[];
  } | null>(null);
  const [conversionsState, setConversionsState] = useState<{
    key: string;
    rows: Conversion[];
  } | null>(null);
  const [dispositionRequest, setDispositionRequest] = useState<{
    seq: number;
    inventoryId: string;
  } | null>(null);

  const activeDetail = detail && detail.id === displayId ? detail : null;
  const detailId = activeDetail?.id ?? null;
  const detailUpdatedAt = activeDetail?.updated_at ?? null;
  useEffect(() => {
    if (!authorized || !detailId) return;
    const controller = new AbortController();
    void inventoryList(capability, controller.signal, detailId)
      .then((rows) => {
        if (!controller.signal.aborted && Array.isArray(rows)) {
          setInventoriesState({ harvestId: detailId, rows });
        }
      })
      .catch((failure: unknown) => {
        if (controller.signal.aborted || isExpectedAuthCancellation(failure))
          return;
        if (failure instanceof ApiError && failure.status === 401)
          sessionExpired();
      });
    return () => {
      controller.abort();
    };
  }, [authorized, capability, detailId, detailUpdatedAt, sessionExpired]);

  const harvestInventories =
    detailId && inventoriesState?.harvestId === detailId
      ? inventoriesState.rows
      : null;
  const conversionKey = harvestInventories
    ? `${detailId ?? ""}:${harvestInventories
        .filter((inv) => inv.has_dispositions)
        .map((inv) => `${inv.id}:${inv.updated_at}`)
        .join(",")}`
    : "";
  useEffect(() => {
    if (!authorized || !harvestInventories) return;
    const withDispositions = harvestInventories.filter(
      (inv) => inv.has_dispositions,
    );
    if (!withDispositions.length) return;
    const controller = new AbortController();
    void Promise.all(
      withDispositions.map((inv) =>
        listConversions("inventory_id", inv.id, capability, controller.signal)
          .then((list) => (Array.isArray(list) ? list : []))
          .catch(() => [] as Conversion[]),
      ),
    ).then((batches) => {
      if (!controller.signal.aborted) {
        const seen = new Set<string>();
        const rows = batches.flat().filter((conv) => {
          if (seen.has(conv.seed_lot_id)) return false;
          seen.add(conv.seed_lot_id);
          return true;
        });
        setConversionsState({ key: conversionKey, rows });
      }
    });
    return () => {
      controller.abort();
    };
  }, [authorized, capability, conversionKey, harvestInventories]);

  const harvestConversions =
    conversionKey && conversionsState?.key === conversionKey
      ? conversionsState.rows
      : [];
  const harvestDescendants: AncestryChildren = {
    total: harvestConversions.length,
    offset: 0,
    limit: 25,
    items: harvestConversions.map((conv) => ({
      record: {
        kind: "seed_lot" as const,
        id: conv.seed_lot_id,
        label: conv.seed_lot_label ?? null,
        lifecycle: conv.status === "reversed" ? "reversed" : "active",
        botanical_identity: activeDetail?.source.botanical_identity ?? {
          id: "",
          display_label: "",
        },
      },
      origin: null,
      harvest_conversion: null,
      descendant_count: 0,
    })),
  };
  // Reversed conversions stay visible in the Lineage tab but are not counted as descendants.
  const activeConversions = harvestConversions.filter(
    (conv) => conv.status !== "reversed",
  );
  const harvestDescendantsSummary = activeConversions.length
    ? `${String(activeConversions.length)} ${activeConversions.length === 1 ? "seed lot" : "seed lots"}`
    : null;
  const activeInventories =
    harvestInventories?.filter((inv) => inv.state === "active") ?? null;
  const harvestPhotoCount = usePhotoCount("harvest", detailId, detailTab);
  const firstActiveInventory =
    harvestInventories?.find((inv) => inv.state === "active") ?? null;
  const harvestStatus = firstActiveInventory
    ? { state: "active", label: "Active" }
    : harvestInventories && harvestInventories.length > 0
      ? { state: "depleted", label: "Depleted" }
      : { state: "completed", label: "Recorded" };
  useRecordDetailFocus({
    recordKey: displayId ?? null,
    detailReady: Boolean(detail && detail.id === displayId),
    directoryReady: Boolean(records),
    paused: Boolean(editor) || edit.modal || creating || storedMode,
    headingRef: detailHeading,
    directoryRef: directoryList,
    fallbackId: `${headingId}-search`,
  });
  if (creating)
    return (
      <section className="harvest-workspace harvest-create-workspace">
        <Breadcrumbs
          items={[
            {
              label: sourceId ? "Source" : "Harvests",
              href: collectionPageParent(window.location.hash) ?? "#/harvests",
            },
            { label: "New Harvest" },
          ]}
        />
        <PageHeader
          eyebrow="Collection"
          titleId={headingId}
          title="New Harvest"
          description="Record material collected on one occurrence from a Plant or Plant group."
        />
        <div className="seed-creation-panel">
          <HarvestForm
            sourceType={sourceType}
            sourceId={sourceId}
            dismissalRef={dismissalRef}
            onClose={() => {
              if (dismissalRef.current?.() ?? true)
                closeCollectionPage(
                  collectionPageParent(window.location.hash) ?? "#/harvests",
                );
            }}
            onSaved={(record) => {
              setRecordRoute(`#/harvests/${record.id}`, true);
            }}
          />
        </div>
      </section>
    );
  if (editor && !edit.modal)
    return (
      <section className="harvest-workspace harvest-create-workspace">
        <PageHeader
          eyebrow="Collection"
          title="Edit harvest"
          titleId={headingId}
        />
        <HarvestForm
          harvest={editor}
          modal={false}
          dismissalRef={dismissalRef}
          onClose={() => {
            edit.close();
          }}
          onSaved={(record) => {
            setEditor(null);
            setDetail(record);
            setRecordRoute(`#/harvests/${record.id}`, true);
          }}
        />
      </section>
    );
  async function remove() {
    const csrfToken = activeCsrfToken(auth.state);
    if (!detail || pending || !csrfToken) return;
    setPending(true);
    setError(null);
    try {
      await deleteHarvest(detail.id, csrfToken, capability);
      window.location.assign("#/harvests");
    } catch (failure: unknown) {
      if (isExpectedAuthCancellation(failure)) return;
      if (failure instanceof ApiError && failure.status === 401)
        sessionExpired();
      else
        setError(
          failure instanceof ApiError && failure.status === 409
            ? inventoryError(failure)
            : "Could not delete the Harvest. Unlink any media attached directly to its owned Event, then retry.",
        );
    } finally {
      setPending(false);
    }
  }
  // Same place in both views: under the search toolbar, like Cuttings.
  const surfaces = (
    <nav className="directory-surfaces" aria-label="Harvest views">
      <button
        type="button"
        className="button--secondary"
        aria-pressed={!storedMode}
        onClick={() => {
          window.location.assign("#/harvests");
        }}
      >
        Harvests
      </button>
      <button
        type="button"
        className="button--secondary"
        aria-pressed={storedMode}
        onClick={() => {
          window.location.assign("#/harvests?tab=stored-material");
        }}
      >
        Stored material
      </button>
    </nav>
  );
  return (
    <section className="harvest-workspace" aria-labelledby={headingId}>
      <WorkspaceIntro
        eyebrow="Collection"
        title="Harvests"
        titleId={headingId}
        description="Harvests from your collection."
        contextOnly={Boolean(displayId)}
        directory
      />
      {!displayId && !storedMode && (
        <DirectoryTools
          surfaces={surfaces}
          context={
            identity ? (
              <a href={`#/identities/${identity}?tab=overview`}>
                Return to botanical identity
              </a>
            ) : undefined
          }
          onReset={() => {
            view.replace({
              ...view.state,
              material: "",
              source_type: "",
              identity_id: "",
            });
          }}
          name="Harvests"
          search={
            <DirectorySearch
              hideLabel
              id={`${headingId}-search`}
              label="Search Harvests"
              value={query}
              onChange={setQuery}
              placeholder="Source, title or botanical identity"
            />
          }
          sort={
            <DirectorySortSelect
              value={view.state.sort}
              dateLabel="harvest date"
              onChange={(value) => {
                view.update("sort", value);
              }}
            />
          }
          savedViews={
            <SavedViews
              presentation="dialog"
              surface="harvests"
              state={view.savedState}
            />
          }
          actions={
            !displayId && (
              <button
                type="button"
                data-collection-return="create"
                onClick={() => {
                  openEditor("new");
                }}
              >
                Record harvest
              </button>
            )
          }
          filters={
            <>
              <BotanicalIdentityFilter
                choices={identities}
                value={identity}
                onChange={setIdentity}
              />
              <div className="field">
                <label htmlFor={`${headingId}-material`}>Material</label>
                <select
                  id={`${headingId}-material`}
                  value={material}
                  onChange={(event) => {
                    setMaterial(event.currentTarget.value);
                  }}
                >
                  <option value="">All materials</option>
                  {materials.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor={`${headingId}-type`}>Source type</label>
                <select
                  id={`${headingId}-type`}
                  value={type}
                  onChange={(event) => {
                    setType(event.currentTarget.value);
                  }}
                >
                  <option value="">All sources</option>
                  <option value="plant">Plant</option>
                  <option value="plant_group">Plant group</option>
                </select>
              </div>
            </>
          }
          activeFilters={[
            ...(identity
              ? [
                  {
                    label: "Botanical identity",
                    value:
                      identities.find((item) => item.id === identity)?.label ??
                      "Selected identity",
                    onRemove: () => {
                      setIdentity("");
                    },
                  },
                ]
              : []),
            ...(material
              ? [
                  {
                    label: "Material",
                    value:
                      materials.find((item) => item.id === material)?.label ??
                      material,
                    onRemove: () => {
                      setMaterial("");
                    },
                  },
                ]
              : []),
            ...(type
              ? [
                  {
                    label: "Source type",
                    value: type === "plant" ? "Plant" : "Plant group",
                    onRemove: () => {
                      setType("");
                    },
                  },
                ]
              : []),
          ]}
        />
      )}

      {error && (
        <div className="notice notice--error" role="alert">
          <p>{error}</p>
          <button
            type="button"
            onClick={() => {
              setAttempt((value) => value + 1);
            }}
          >
            Retry
          </button>
        </div>
      )}
      {notice && (
        <p role="status" className="notice notice--success">
          {notice}
        </p>
      )}
      {displayId ? (
        detail?.id === displayId ? (
          <DetailPage className="harvest-detail">
            <Breadcrumbs
              items={[
                { label: "Collection", href: "#/dashboard" },
                { label: "Harvests", href: "#/harvests" },
                { label: detail.display_title },
              ]}
            />
            <DetailHeader
              label={
                <SpecimenLabel
                  kind="Harvest"
                  name="Harvest overview"
                  rows={[
                    {
                      label: "Occurrence date",
                      value: formatPartialDate(detail.occurred_on),
                    },
                    { label: "Materials", value: materialSummary(detail) },
                    {
                      label: "Source",
                      wide: true,
                      value: (
                        <a href={sourceHref(detail)}>
                          {detail.source.display_name}
                        </a>
                      ),
                    },
                  ]}
                />
              }
              headingRef={detailHeading}
              eyebrow="Harvest"
              title={detail.display_title}
              keyFacts={[
                {
                  label: "held",
                  value:
                    activeInventories === null
                      ? "…"
                      : activeInventories.length === 1
                        ? remainingLabel(activeInventories[0])
                        : activeInventories.length === 0
                          ? "Nothing held"
                          : `${String(activeInventories.length)} materials`,
                },
                {
                  label:
                    detail.items.length === 1
                      ? "material collected"
                      : "materials collected",
                  value: String(detail.items.length),
                },
                {
                  label:
                    activeConversions.length === 1
                      ? "seed lot converted"
                      : "seed lots converted",
                  value: harvestInventories
                    ? String(activeConversions.length)
                    : "…",
                },
              ]}
              plate={
                <SpecimenPlate
                  addPhoto={{
                    href: `#/harvests/${detail.id}?tab=photos`,
                    onClick: (event) => {
                      event.preventDefault();
                      setDetailTab("photos");
                      window.history.replaceState(
                        null,
                        "",
                        `#/harvests/${detail.id}?tab=photos`,
                      );
                    },
                  }}
                >
                  <Visual harvest={detail} />
                </SpecimenPlate>
              }
              secondary={
                <a
                  href={`#/identities/${detail.source.botanical_identity.id}?tab=harvests`}
                >
                  <BotanicalName
                    label={detail.source.botanical_identity.display_label}
                    scientificName={
                      recordIdentities.get(detail.source.botanical_identity.id)
                        ?.scientific_name
                    }
                  />
                </a>
              }
              status={
                <LifecycleStatus state={harvestStatus.state}>
                  {harvestStatus.label}
                </LifecycleStatus>
              }
              lineage={
                <LineageStrip
                  key={detail.updated_at}
                  kind={
                    detail.source.type === "plant" ? "plants" : "plant-groups"
                  }
                  id={detail.source.id}
                  includeSubject
                  current="This Harvest"
                  currentKind="harvest"
                  descendantsSummary={harvestDescendantsSummary}
                  fullHref={`#/harvests/${detail.id}?tab=lineage`}
                  onLineageTab={detailTab === "lineage"}
                  onFull={(event) => {
                    event.preventDefault();
                    setDetailTab("lineage");
                    window.history.replaceState(
                      null,
                      "",
                      `#/harvests/${detail.id}?tab=lineage`,
                    );
                  }}
                />
              }
              primaryActions={
                firstActiveInventory ? (
                  <button
                    type="button"
                    onClick={() => {
                      setDetailTab("overview");
                      setDispositionRequest((current) => ({
                        seq: (current?.seq ?? 0) + 1,
                        inventoryId: firstActiveInventory.id,
                      }));
                    }}
                  >
                    Record disposition
                  </button>
                ) : undefined
              }
              onEdit={() => {
                openEditor(detail);
              }}
              editLabel="Edit harvest"
              overflow={
                <OverflowMenu
                  ariaLabel="More harvest actions"
                  triggerRef={moreTrigger}
                >
                  <button
                    type="button"
                    className="button--danger"
                    onClick={() => {
                      setDeleting(true);
                    }}
                  >
                    Delete harvest
                  </button>
                </OverflowMenu>
              }
            />
            <DetailTabs
              tabs={[
                { id: "overview", label: "Overview" },
                { id: "photos", label: "Photos", count: harvestPhotoCount },
                { id: "lineage", label: "Lineage" },
              ]}
              selected={detailTab}
              onSelect={(next) => {
                setDetailTab(next);
                window.history.replaceState(
                  null,
                  "",
                  `#/harvests/${detail.id}${next === "overview" ? "" : `?tab=${next}`}`,
                );
              }}
            />
            {detailTab === "overview" && (
              <div
                id="panel-overview"
                role="tabpanel"
                aria-labelledby="tab-overview"
                className="detail-tab-panel"
              >
                <RecordOverview
                  facts={
                    <>
                      <StoredMaterialSection
                        harvest={detail}
                        dispositionRequest={dispositionRequest}
                        onInventoriesLoaded={(rows) => {
                          setInventoriesState({ harvestId: detail.id, rows });
                        }}
                      />
                      <RecordDescendants
                        headingId="harvest-descendants-title"
                        items={[
                          {
                            label: `${String(activeConversions.length)} ${activeConversions.length === 1 ? "seed lot" : "seed lots"}`,
                            href: `#/harvests/${detail.id}?tab=lineage`,
                            onClick: (event) => {
                              event.preventDefault();
                              setDetailTab("lineage");
                              window.history.replaceState(
                                null,
                                "",
                                `#/harvests/${detail.id}?tab=lineage`,
                              );
                            },
                          },
                        ]}
                        lineageHref={`#/harvests/${detail.id}?tab=lineage`}
                        onOpenLineage={(event) => {
                          event.preventDefault();
                          setDetailTab("lineage");
                          window.history.replaceState(
                            null,
                            "",
                            `#/harvests/${detail.id}?tab=lineage`,
                          );
                        }}
                      />
                      {detail.notes && (
                        <section className="record-section">
                          <h4>Notes</h4>
                          <p className="preserve-lines">{detail.notes}</p>
                        </section>
                      )}
                    </>
                  }
                  almanac={
                    <RecordAlmanac
                      kind="harvest"
                      id={detail.id}
                      occurredOn={detail.occurred_on}
                      eventId={detail.event_id}
                      sourceHref={sourceHref(detail)}
                      sourceLabel={detail.source.display_name}
                      sourceScheduleHref={scheduleHash({
                        ...defaultState,
                        target_kind: [detail.source.type],
                        target_id: detail.source.id,
                      })}
                    />
                  }
                />
              </div>
            )}
            {detailTab === "photos" && (
              <div
                id="panel-photos"
                role="tabpanel"
                aria-labelledby="tab-photos"
                className="detail-tab-panel"
              >
                <PhotosSection
                  key={detail.id}
                  target="harvest"
                  targetId={detail.id}
                  targetLabel={detail.display_title}
                  primaryPhoto={detail.primary_photo}
                  onPrimaryChanged={(photo) => {
                    setDetail((current) =>
                      current ? { ...current, primary_photo: photo } : current,
                    );
                  }}
                />
              </div>
            )}
            {detailTab === "lineage" && (
              <div
                id="panel-lineage"
                role="tabpanel"
                aria-labelledby="tab-lineage"
                className="detail-tab-panel"
              >
                <LineagePanel
                  key={detail.updated_at}
                  kind={
                    detail.source.type === "plant" ? "plants" : "plant-groups"
                  }
                  id={detail.source.id}
                  includeSubject
                  subject={{
                    kind: "harvest",
                    id: detail.id,
                    label: detail.display_title,
                    lifecycle: harvestStatus.state,
                  }}
                  descendantsOverride={harvestDescendants}
                  explorerHref={ancestryHref(
                    detail.source.type,
                    detail.source.id,
                  )}
                />
              </div>
            )}
          </DetailPage>
        ) : (
          !error && (
            <DetailLoading
              eyebrow="Harvest"
              label="Loading Harvest detail…"
              parents={[{ label: "Harvests", href: "#/harvests" }]}
              className="harvest-detail"
            />
          )
        )
      ) : storedMode ? (
        <StoredMaterialDirectory
          surfaces={surfaces}
          actions={
            <ActionButton
              icon="add"
              data-collection-return="create"
              onClick={() => {
                openEditor("new");
              }}
            >
              Record harvest
            </ActionButton>
          }
        />
      ) : (
        <>
          {!records && !error && <p role="status">Loading Harvests…</p>}
          {filtered && (
            <DirectoryWorkspace>
              <DirectoryResults
                count={matching.length}
                total={records?.length ?? 0}
                pagination={matching.length > 0 ? pagination : undefined}
              />
              <div className="harvest-directory-results">
                {matching.length === 0 ? (
                  <p className="empty-state">
                    {identity || records?.length
                      ? "No Harvests match these filters."
                      : "No Harvests recorded yet. Record material collected from a Plant or Plant group."}
                  </p>
                ) : (
                  <ul
                    ref={directoryList}
                    tabIndex={0}
                    className="harvest-directory ui-directory-records ui-directory-records--list"
                    aria-label="Harvest directory"
                  >
                    {pageRecords.map((record) => (
                      <li
                        key={record.id}
                        data-preview-id={record.id}
                        className="ui-directory-row ui-directory-row--composed"
                        data-selected={record.id === selectedId || undefined}
                      >
                        <DirectoryTrigger
                          type="button"

                          aria-pressed={record.id === selectedId}
                          onClick={() => {
                            setRecordRoute(`#/harvests/${record.id}`);
                          }}
                        >
                          <DirectoryRecordContent
                            visual={<Visual harvest={record} />}
                            name={record.display_title}
                            secondary={
                              <BotanicalName
                                label={
                                  record.source.botanical_identity.display_label
                                }
                                scientificName={
                                  recordIdentities.get(
                                    record.source.botanical_identity.id,
                                  )?.scientific_name
                                }
                              />
                            }
                            summary={
                              <>
                                <time>
                                  {formatPartialDate(record.occurred_on)}
                                </time>
                                <small>
                                  {directoryMaterialSummary(record)}
                                </small>
                              </>
                            }
                          />
                        </DirectoryTrigger>
                        <DirectoryRecordActions
                          label={record.display_title}
                          onDetails={() => {
                            setRecordRoute(`#/harvests/${record.id}`);
                          }}
                          onEdit={() => {
                            openEditor(record);
                          }}
                        />
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </DirectoryWorkspace>
          )}
        </>
      )}
      {editor && (
        <HarvestForm
          harvest={editor}
          sourceType={sourceType}
          sourceId={sourceId}
          modal={edit.modal}
          dismissalRef={dismissalRef}
          onClose={() => {
            edit.close();
          }}
          onSaved={(record) => {
            edit.close(true);
            setNotice("Harvest saved.");
            setDetail(record);
            setSelectedId(record.id);
            setAttempt((value) => value + 1);
            if (!initialId || record.id !== initialId)
              window.location.assign(`#/harvests/${record.id}`);
          }}
        />
      )}
      {deleting && detail && (
        <TaskDialog
          title="Delete harvest"
          returnFocusTo={moreTrigger}
          onClose={() => {
            if (!pending) setDeleting(false);
          }}
        >
          <h3>Delete harvest?</h3>
          <p>
            This removes the structured Harvest and its owned Event. Linked
            media remain in the Media library. The source record stays
            unchanged.
          </p>
          <div className="actions">
            <button
              type="button"
              className="button--secondary"
              disabled={pending}
              onClick={() => {
                setDeleting(false);
              }}
            >
              Cancel
            </button>

            <button
              type="button"
              className="button--danger"
              disabled={pending}
              onClick={() => {
                void remove();
              }}
            >
              {pending ? "Deleting…" : "Delete harvest and Event"}
            </button>
          </div>
          {error && <p role="alert">{error}</p>}
        </TaskDialog>
      )}
    </section>
  );
}
