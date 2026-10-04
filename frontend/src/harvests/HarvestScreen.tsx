import { useEffect, useId, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import {
  Breadcrumbs,
  DetailContext,
  DetailHeader,
  WorkspaceIntro,
} from "../components/CollectionUI";
import { DirectorySearch, QuickPreview } from "../components/ReferenceUI";
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
    <ol className="harvest-items">
      {harvest.items.map((item) => (
        <li key={item.id}>
          <strong>
            {
              materials.find((material) => material.id === item.material_kind)
                ?.label
            }
          </strong>
          <span>Collected: {quantityLabel(item)}</span>
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
  const storedMode = !initialId && initialTab === "stored-material";
  const auth = useAuth();
  const headingId = useId();
  const [records, setRecords] = useState<Harvest[] | null>(null);
  const [detail, setDetail] = useState<Harvest | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editor, setEditor] = useState<Harvest | "new" | null>(
    startCreating ? "new" : null,
  );
  const [deleting, setDeleting] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [query, setQuery] = useState("");
  const [material, setMaterial] = useState("");
  const [type, setType] = useState("");
  const [identity, setIdentity] = useState("");
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
  const selected = filtered?.find((record) => record.id === selectedId);
  function openEditor(record: Harvest | "new") {
    setEditor(record);
    setError(null);
  }
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
        eyebrow="Collection history"
        title="Harvests"
        titleId={headingId}
        description="Record material collected from Plants and Plant groups."
        contextOnly={Boolean(initialId)}
        actions={
          !initialId && (
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
      />
      {!initialId && (
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
      {initialId ? (
        detail ? (
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
                          {detail.source.botanical_identity.display_label}
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
                <button
                  type="button"
                  className="button--secondary"
                  onClick={() => {
                    setDeleting(true);
                  }}
                >
                  Delete harvest
                </button>
              }
            />
            <section aria-label="Harvest overview">
              <h4>Harvested materials</h4>
              <Items harvest={detail} />
              {detail.notes && (
                <>
                  <h4>Notes</h4>
                  <p className="preserve-lines">{detail.notes}</p>
                </>
              )}
            </section>
            <p>
              <a
                href={`${sourceHref(detail)}?tab=events&event=${detail.event_id}`}
              >
                View owned harvest Event in source history
              </a>{" "}
              · <a href="#/events">Event journal</a>
            </p>
            <StoredMaterialSection harvest={detail} />
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
          <div className="harvest-filters">
            <DirectorySearch
              id={`${headingId}-search`}
              label="Search Harvests"
              value={query}
              onChange={setQuery}
              placeholder="Source, title or botanical identity"
            />
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
          </div>
          {!records && !error && <p role="status">Loading Harvests…</p>}
          {filtered && (
            <div className="harvest-directory-layout">
              <div className="harvest-directory-results">
                <p className="directory-summary">
                  {filtered.length}{" "}
                  {filtered.length === 1 ? "harvest" : "harvests"}
                </p>
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
                          <Visual harvest={record} compact />
                          <span className="harvest-row-content">
                            <strong>{record.display_title}</strong>
                            <span>
                              {record.source.botanical_identity.display_label}
                            </span>
                            <span>
                              {materialSummary(record)} ·{" "}
                              {record.items.length === 1
                                ? quantityLabel(record.items[0])
                                : `${String(record.items.length)} material lines`}
                            </span>
                          </span>
                          <span className="harvest-row-meta">
                            <time>{formatPartialDate(record.occurred_on)}</time>
                            <small>
                              {record.source.type === "plant"
                                ? "Plant"
                                : "Plant group"}
                            </small>
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
                  <p>{selected.source.botanical_identity.display_label}</p>
                  <dl className="record-preview__facts">
                    <div>
                      <dt>Source</dt>
                      <dd>{selected.source.display_name}</dd>
                    </div>
                    <div>
                      <dt>Date</dt>
                      <dd>{formatPartialDate(selected.occurred_on)}</dd>
                    </div>
                  </dl>
                  <Items harvest={selected} />
                  <div className="actions record-preview__actions">
                    <a
                      className="button-link"
                      href={`#/harvests/${selected.id}`}
                    >
                      Open details
                    </a>
                    <button
                      type="button"
                      className="button--secondary"
                      onClick={() => {
                        openEditor(selected);
                      }}
                    >
                      Edit
                    </button>
                  </div>
                </QuickPreview>
              ) : (
                <aside className="quick-preview harvest-preview-empty">
                  <p>Select a Harvest for a quick preview.</p>
                </aside>
              )}
            </div>
          )}
        </>
      )}
      {editor && (
        <HarvestForm
          harvest={editor === "new" ? undefined : editor}
          sourceType={sourceType}
          sourceId={sourceId}
          onClose={() => {
            setEditor(null);
          }}
          onSaved={(record) => {
            setEditor(null);
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
