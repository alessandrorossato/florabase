import { ActionButton } from "../components/Action";
import { useCollectionPageReturnFocus } from "../components/useCollectionPageReturnFocus";
import { RecordIdentities } from "../components/recordPresentation";
import "../components/collection-page.css";
import "./collection-visual.css";
import { useEditRoute } from "../components/useEditRoute";
import {
  closeCollectionPage,
  collectionPageParent,
  openCollectionPage,
  setRecordRoute,
} from "../components/recordNavigation";
import { DirectoryTools } from "../components/DirectoryTools";
import { DirectoryResults } from "../components/DirectoryResults";
import { SavedViews } from "../saved-views/SavedViews";
import { useDirectoryView } from "../saved-views/useDirectoryView";
import { useContext, useEffect, useId, useRef, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import {
  Breadcrumbs,
  DetailContext,
  DetailHeader,
  WorkspaceIntro,
} from "../components/CollectionUI";
import {
  BotanicalName,
  DirectorySearch,
  QuickPreview,
  OverflowMenu,
  PageHeader,
} from "../components/ReferenceUI";
import { TaskDialog } from "../components/TaskDialog";
import { formatPartialDate } from "../events/eventData";
import { PhotosSection } from "../photos/PhotosSection";
import { RecordVisual } from "../photos/RecordVisual";
import {
  StoredMaterialSection,
  StoredMaterialDirectory,
} from "./StoredMaterial";
import { BotanicalIdentityFilter } from "./BotanicalIdentityFilter";
import type { ReferenceChoice } from "../seed-lots/ReferencePicker";
import { inventoryError } from "./inventoryApi";
import { HarvestForm } from "./HarvestForm";
import {
  deleteHarvest,
  getHarvest,
  identityChoices,
  listHarvests,
  materialSummary,
  materials,
  quantityLabel,
  type Harvest,
} from "./api";

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
      fallbackPhoto={harvest.source.primary_photo}
      identity={harvest.source.botanical_identity}
      kind="harvest"
      label={harvest.display_title}
      compact={compact}
    />
  );
}
function Items({ harvest }: { harvest: Harvest }) {
  return (
    <ol className="harvest-items collected-material-items">
      {harvest.items.map((item) => (
        <li key={item.id}>
          <strong>
            {
              materials.find((material) => material.id === item.material_kind)
                ?.label
            }
          </strong>
          <span className="collected-material-quantity">
            <span className="sr-only">Collected: </span>
            {quantityLabel(item)}
          </span>
          {item.description && (
            <p className="preserve-lines">{item.description}</p>
          )}
        </li>
      ))}
    </ol>
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
  const recordIdentities = useContext(RecordIdentities);
  const headingId = useId();
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
    if (storedMode) return;
    const controller = new AbortController();
    const request = initialId
      ? getHarvest(initialId, controller.signal)
      : listHarvests(controller.signal, identity);
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
        if (controller.signal.aborted) return;
        if (failure instanceof ApiError && failure.status === 401)
          auth.sessionExpired();
        else setError("Could not load Harvests. Please retry.");
      });
    return () => {
      controller.abort();
    };
  }, [initialId, storedMode, attempt, identity, auth]);
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
  useCollectionPageReturnFocus(Boolean(records) && !creating && !initialId);
  const selected = filtered?.find((record) => record.id === selectedId);
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
  function choose(record: Harvest) {
    if (window.matchMedia("(max-width: 64rem)").matches)
      window.location.assign(`#/harvests/${record.id}`);
    else setSelectedId(record.id);
  }
  async function remove() {
    if (!detail || pending) return;
    setPending(true);
    setError(null);
    try {
      await deleteHarvest(
        detail.id,
        auth.state.status === "authenticated" ? auth.state.csrfToken : "",
      );
      window.location.assign("#/harvests");
    } catch (failure: unknown) {
      if (failure instanceof ApiError && failure.status === 401)
        auth.sessionExpired();
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
  return (
    <section className="harvest-workspace" aria-labelledby={headingId}>
      <WorkspaceIntro
        eyebrow="Collection"
        title="Harvests"
        titleId={headingId}
        description="Record material collected from Plants and Plant groups."
        contextOnly={Boolean(displayId)}
        actions={
          storedMode && (
            <button
              type="button"
              onClick={() => {
                openEditor("new");
              }}
            >
              Record harvest
            </button>
          )
        }
        tools={
          !displayId &&
          !storedMode && (
            <DirectoryTools
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
                          identities.find((item) => item.id === identity)
                            ?.label ?? "Selected identity",
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
                          materials.find((item) => item.id === material)
                            ?.label ?? material,
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
          )
        }
      />
      {!displayId && (
        <nav className="workspace-view-nav" aria-label="Harvest views">
          <button
            type="button"
            aria-pressed={!storedMode}
            onClick={() => {
              window.location.assign("#/harvests");
            }}
          >
            Harvests
          </button>
          <button
            type="button"
            aria-pressed={storedMode}
            onClick={() => {
              window.location.assign("#/harvests?tab=stored-material");
            }}
          >
            Stored material
          </button>
        </nav>
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
          <article className="collection-detail harvest-detail">
            <Breadcrumbs
              items={[
                { label: "Harvests", href: "#/harvests" },
                { label: detail.display_title },
              ]}
            />
            <DetailHeader
              eyebrow="Harvest"
              title={detail.display_title}
              visual={<Visual harvest={detail} />}
              secondary={
                <DetailContext
                  items={[
                    {
                      label: "Source",
                      value: (
                        <a href={sourceHref(detail)}>
                          {detail.source.display_name}
                        </a>
                      ),
                    },
                    {
                      label: "Botanical identity",
                      value: (
                        <a
                          href={`#/identities/${detail.source.botanical_identity.id}?tab=harvests`}
                        >
                          <BotanicalName
                            label={
                              detail.source.botanical_identity.display_label
                            }
                            scientificName={
                              recordIdentities.get(
                                detail.source.botanical_identity.id,
                              )?.scientific_name
                            }
                          />
                        </a>
                      ),
                    },
                    {
                      label: "Date",
                      value: formatPartialDate(detail.occurred_on),
                    },
                  ]}
                />
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
            <dl className="seed-overview-band" aria-label="Harvest overview">
              <div>
                <dt>Occurrence date</dt>
                <dd>{formatPartialDate(detail.occurred_on)}</dd>
              </div>
              <div>
                <dt>Source</dt>
                <dd>
                  <a href={sourceHref(detail)}>{detail.source.display_name}</a>
                </dd>
              </div>
              <div>
                <dt>Materials</dt>
                <dd>{materialSummary(detail)}</dd>
              </div>
            </dl>
            <section
              className="record-section"
              aria-label="Materials collected"
            >
              <h4>Materials collected</h4>
              <Items harvest={detail} />
            </section>
            <StoredMaterialSection harvest={detail} />
            <div className="record-detail-grid harvest-context-grid">
              <section className="record-section">
                <h4>Notes</h4>
                <p
                  className={
                    detail.notes ? "preserve-lines" : "detail-empty-state"
                  }
                >
                  {detail.notes ?? "No notes recorded."}
                </p>
              </section>
              <section className="record-section">
                <h4>Related history</h4>
                <p>
                  <a
                    href={`${sourceHref(detail)}?tab=events&event=${detail.event_id}`}
                  >
                    View owned harvest Event in source history
                  </a>
                </p>
                <p>
                  <a href="#/events">Journal</a> ·{" "}
                  <a href="#/history">History</a>
                </p>
              </section>
            </div>
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
          </article>
        ) : (
          !error && <p role="status">Loading Harvest detail…</p>
        )
      ) : storedMode ? (
        <StoredMaterialDirectory />
      ) : (
        <>
          {!records && !error && <p role="status">Loading Harvests…</p>}
          {filtered && (
            <div className="harvest-directory-layout">
              <div className="harvest-directory-results">
                <DirectoryResults count={filtered.length} />
                {filtered.length === 0 ? (
                  <p className="empty-state">
                    {identity || records?.length
                      ? "No Harvests match these filters."
                      : "No Harvests recorded yet. Record material collected from a Plant or Plant group."}
                  </p>
                ) : (
                  <ul
                    className="harvest-directory"
                    aria-label="Harvest directory"
                  >
                    {filtered.map((record) => (
                      <li key={record.id}>
                        <button
                          type="button"
                          className={`harvest-directory-row${record.id === selectedId ? " is-selected" : ""}`}
                          aria-pressed={record.id === selectedId}
                          onClick={() => {
                            choose(record);
                          }}
                        >
                          <Visual harvest={record} />
                          <span className="harvest-row-content">
                            <strong>{record.display_title}</strong>
                            <small className="harvest-row-botanical">
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
                            </small>
                          </span>
                          <span className="harvest-row-meta">
                            <time>{formatPartialDate(record.occurred_on)}</time>
                            <small>{directoryMaterialSummary(record)}</small>
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              {selected ? (
                <QuickPreview>
                  <Visual harvest={selected} />
                  <h3>{selected.display_title}</h3>
                  <p>
                    <BotanicalName
                      label={selected.source.botanical_identity.display_label}
                      scientificName={
                        recordIdentities.get(
                          selected.source.botanical_identity.id,
                        )?.scientific_name
                      }
                    />
                  </p>
                  <dl className="record-preview__facts">
                    <div>
                      <dt>Source</dt>
                      <dd>
                        <a href={sourceHref(selected)}>
                          {selected.source.display_name}
                        </a>
                      </dd>
                    </div>
                    <div>
                      <dt>Date</dt>
                      <dd>{formatPartialDate(selected.occurred_on)}</dd>
                    </div>
                  </dl>
                  <p>{directoryMaterialSummary(selected)}</p>
                  <div className="actions record-preview__actions">
                    <a
                      className="button-link"
                      href={`#/harvests/${selected.id}`}
                    >
                      Open details
                    </a>
                    <ActionButton
                      icon="edit"
                      type="button"
                      className="button--secondary"
                      onClick={() => {
                        openEditor(selected);
                      }}
                    >
                      Edit
                    </ActionButton>
                  </div>
                </QuickPreview>
              ) : (
                <aside className="selected-seed seed-detail-empty harvest-preview-empty">
                  <h3>Select a Harvest</h3>
                  <p>
                    Choose a row for a Quick Preview, then open details for
                    photos, history and collection operations.
                  </p>
                </aside>
              )}
            </div>
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
              disabled={pending}
              onClick={() => {
                void remove();
              }}
            >
              {pending ? "Deleting…" : "Delete harvest and Event"}
            </button>
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
          </div>
          {error && <p role="alert">{error}</p>}
        </TaskDialog>
      )}
    </section>
  );
}
