import "./media.css";
import { ActionButton } from "../components/Action";
import { FieldLabel } from "../components/FieldLabel";
import { DirectoryTools } from "../components/DirectoryTools";
import { DirectoryResults } from "../components/DirectoryResults";
import { SavedViews } from "../saved-views/SavedViews";
import { useDirectoryView } from "../saved-views/useDirectoryView";
import {
  useEffect,
  useId,
  useRef,
  useState,
  useSyncExternalStore,
  type SyntheticEvent,
} from "react";
import { useAuth } from "../auth/context";
import { ApiError } from "../auth/api";
import {
  Breadcrumbs,
  DetailHeader,
  WorkspaceIntro,
} from "../components/CollectionUI";
import { DirectorySearch } from "../components/ReferenceUI";
import { PhotoDialog } from "../photos/PhotosSection";
import { clearPrimaryPhoto, setPrimaryPhoto } from "../photos/api";
import {
  deleteMedia,
  editMediaLink,
  getMedia,
  listMedia,
  saveLocalCopy,
  refreshLocalCopy,
  removeLocalCopy,
  unlinkMedia,
  type MediaAsset,
  type MediaTargetFilter,
  type MediaDetail,
  type MediaLink,
  type MediaPage,
} from "./api";
import { MediaEditor } from "./MediaEditor";
import { formText, mediaError } from "./helpers";
import { MediaPreview } from "./MediaPreview";
import { MediaQuickPreview } from "./MediaQuickPreview";
import { readDirectoryState } from "../saved-views/state";
import {
  mediaDirectoryHash,
  mediaDetailHash,
  mediaOffset,
  mediaFocusId,
  navigateMedia,
  rememberMediaCard,
  subscribeMediaRoute,
} from "./navigation";
import { MediaLinker } from "./MediaLinker";
import { mediaTargets } from "./targets";

function title(asset: MediaAsset): string {
  return asset.title ?? asset.original_filename ?? "External image reference";
}
function Metadata({ asset }: { asset: MediaAsset }) {
  return (
    <dl className="media-facts">
      <div>
        <dt>Source</dt>
        <dd>
          {asset.kind === "local"
            ? "Local image"
            : asset.content_url
              ? "External reference · local copy saved"
              : "External reference · not stored locally"}
        </dd>
      </div>
      {asset.fetched_at && (
        <div>
          <dt>Saved</dt>
          <dd>{asset.fetched_at.slice(0, 10)}</dd>
        </div>
      )}
      {asset.media_type && (
        <div>
          <dt>File type</dt>
          <dd>{asset.media_type}</dd>
        </div>
      )}
      {asset.width && asset.height && (
        <div>
          <dt>Dimensions</dt>
          <dd>
            {asset.width} × {asset.height} px
          </dd>
        </div>
      )}
      {asset.byte_size !== null && (
        <div>
          <dt>Original size</dt>
          <dd>{(asset.byte_size / 1024).toFixed(1)} KiB</dd>
        </div>
      )}
      <div>
        <dt>Record links</dt>
        <dd>
          {asset.collection_link_count === 0
            ? "Unlinked asset"
            : asset.collection_link_count}
        </dd>
      </div>
      <div>
        <dt>BotanicalIdentity covers</dt>
        <dd>{asset.cover_reference_count}</dd>
      </div>
      {asset.attribution && (
        <div>
          <dt>Attribution</dt>
          <dd>{asset.attribution}</dd>
        </div>
      )}
      {asset.source_url && (
        <div>
          <dt>Source page</dt>
          <dd>
            <a href={asset.source_url} target="_blank" rel="noreferrer">
              Open source page
            </a>
          </dd>
        </div>
      )}
      {asset.licence_label && (
        <div>
          <dt>Licence</dt>
          <dd>{asset.licence_label}</dd>
        </div>
      )}
      {asset.licence_url && (
        <div>
          <dt>Licence source</dt>
          <dd>
            <a href={asset.licence_url} target="_blank" rel="noreferrer">
              Read licence
            </a>
          </dd>
        </div>
      )}
    </dl>
  );
}

export function MediaScreen({ initialId }: { initialId?: string }) {
  const auth = useAuth();
  const headingId = useId();
  const hash = useSyncExternalStore(
    subscribeMediaRoute,
    () => window.location.hash,
  );
  const offset = mediaOffset(hash);
  const directoryHash = mediaDirectoryHash(hash);
  const detailHeading = useRef<HTMLHeadingElement>(null);
  const focusedRoute = useRef<string | null>(null);
  const [pageResult, setPage] = useState<{
    value: MediaPage;
    key: string;
  } | null>(null);
  const [selected, setSelected] = useState<MediaAsset | null>(null);
  const view = useDirectoryView(
    "media",
    undefined,
    initialId ? readDirectoryState("media", directoryHash) : undefined,
  );
  const query = view.state.q;
  const setQuery = (value: string) => {
    view.update("q", value);
  };
  const kind = view.state.kind;
  const setKind = (value: string) => {
    view.update("kind", value);
  };
  const association = view.state.association;
  const setAssociation = (value: string) => {
    view.update("association", value);
  };
  const target = view.state.target;
  const setTarget = (value: MediaTargetFilter | "") => {
    view.update("target", value);
  };

  const pageKey = JSON.stringify([query, kind, association, target, offset]);
  const page =
    !initialId && pageResult?.key === pageKey ? pageResult.value : null;

  const [loadedDetail, setDetail] = useState<MediaDetail | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [requestError, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editor, setEditor] = useState<"new" | MediaAsset | null>(null);
  const [linking, setLinking] = useState(false);
  const [removing, setRemoving] = useState<MediaLink | "asset" | "copy" | null>(
    null,
  );
  const [editingLink, setEditingLink] = useState<MediaLink | null>(null);
  const [pending, setPending] = useState(false);
  const validId =
    !initialId ||
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
      initialId,
    );
  const detail =
    loadedDetail?.id.toLowerCase() === initialId?.toLowerCase()
      ? loadedDetail
      : null;
  const error = validId
    ? requestError
    : "This media link has an invalid ID. Return to Media to choose an asset.";
  useEffect(() => {
    if (!validId) return;
    const controller = new AbortController();
    if (initialId) {
      void getMedia(initialId, controller.signal)
        .then((value) => {
          if (!controller.signal.aborted) setDetail(value);
        })
        .catch((failure: unknown) => {
          if (!controller.signal.aborted) failureHandler(failure);
        });
    } else {
      void listMedia(
        { query, kind, association, target, offset },
        controller.signal,
      )
        .then((value) => {
          if (controller.signal.aborted) return;
          if (offset > 0 && offset >= value.total) {
            const params = new URLSearchParams(
              mediaDirectoryHash().split("?", 2)[1],
            );
            const last =
              Math.floor(Math.max(0, value.total - 1) / value.limit) *
              value.limit;
            if (last) params.set("offset", String(last));
            else params.delete("offset");
            const focusId = mediaFocusId();
            navigateMedia(
              `#/media${params.size ? `?${params}` : ""}`,
              typeof focusId === "string" ? focusId : undefined,
              true,
            );
          } else setPage({ value, key: pageKey });
        })
        .catch((failure: unknown) => {
          if (!controller.signal.aborted) failureHandler(failure);
        });
    }
    return () => {
      controller.abort();
    };
    function failureHandler(failure: unknown) {
      if (failure instanceof ApiError && failure.status === 401)
        auth.sessionExpired();
      else if (failure instanceof ApiError && failure.status === 404)
        setError(
          "This media asset was deleted or could not be found. Return to Media to choose another asset.",
        );
      else setError(mediaError(failure));
    }
  }, [
    initialId,
    validId,
    query,
    kind,
    association,
    target,
    offset,
    attempt,
    pageKey,
    auth,
  ]);
  useEffect(() => {
    if (initialId) {
      if (detail && focusedRoute.current !== `${initialId}:${hash}`) {
        detailHeading.current?.focus();
        focusedRoute.current = `${initialId}:${hash}`;
      }
      return;
    }
    if (!page || focusedRoute.current === hash) return;
    const focusId = mediaFocusId();
    if (typeof focusId === "string") {
      const card = document.getElementById(`media-asset-${focusId}`);
      const target = card ?? document.getElementById(headingId);
      if (target) {
        if (!card) target.tabIndex = -1;
        target.focus();
      }
    }
    focusedRoute.current = hash;
  }, [initialId, detail, page, hash, headingId]);
  useEffect(() => {
    function clearRouteOverlays() {
      setSelected(null);
      setError(null);
    }
    return subscribeMediaRoute(clearRouteOverlays);
  }, []);
  const token =
    auth.state.status === "authenticated" ? auth.state.csrfToken : "";
  function refresh(message: string) {
    setError(null);
    setNotice(message);
    setAttempt((value) => value + 1);
  }
  function changeFilters() {
    setPage(null);
    setSelected(null);
    const params = new URLSearchParams(window.location.hash.split("?", 2)[1]);
    params.delete("offset");
    window.history.replaceState(
      null,
      "",
      `#/media${params.size ? `?${params}` : ""}`,
    );
    setError(null);
  }
  async function action(run: () => Promise<void>, message: string) {
    if (pending) return;
    setPending(true);
    setError(null);
    try {
      await run();
      setRemoving(null);
      setEditingLink(null);
      refresh(message);
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401)
        auth.sessionExpired();
      else setError(mediaError(failure));
    } finally {
      setPending(false);
    }
  }
  function choose(asset: MediaAsset) {
    rememberMediaCard(asset.id);
    if (window.matchMedia("(max-width: 48rem)").matches)
      navigateMedia(mediaDetailHash(asset.id));
    else setSelected(asset);
  }
  async function saveLink(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingLink) return;
    const form = new FormData(event.currentTarget);
    await action(async () => {
      await editMediaLink(
        editingLink.id,
        {
          caption: formText(form, "caption") || null,
          display_order: Number(form.get("display_order")),
        },
        token,
      );
    }, "Record link details saved.");
  }
  return (
    <section
      className="media-workspace"
      aria-labelledby={headingId}
      onClick={(event) => {
        const anchor =
          event.target instanceof Element ? event.target.closest("a") : null;
        if (
          !initialId ||
          anchor?.getAttribute("href") !== directoryHash ||
          event.button ||
          event.metaKey ||
          event.ctrlKey ||
          event.shiftKey ||
          event.altKey
        )
          return;
        event.preventDefault();
        navigateMedia(directoryHash, initialId);
      }}
    >
      {initialId ? (
        <>
          <Breadcrumbs
            items={[
              { label: "Media", href: directoryHash },
              { label: detail ? title(detail) : "Media detail" },
            ]}
          />
          <h2 id={headingId} className="sr-only">
            Media detail
          </h2>
        </>
      ) : (
        <WorkspaceIntro
          eyebrow="Explore"
          title="Media"
          titleId={headingId}
          description="Photographs and image references from your collection."
          tools={
            <DirectoryTools
              onReset={() => {
                view.replace({
                  ...view.state,
                  kind: "",
                  association: "all",
                  target: "",
                });
                changeFilters();
              }}
              name="Media"
              search={
                <DirectorySearch
                  hideLabel
                  id="media-search"
                  label="Search media"
                  placeholder="Title, filename or attribution"
                  value={query}
                  onChange={(value) => {
                    setQuery(value);
                    changeFilters();
                  }}
                />
              }
              savedViews={
                <SavedViews
                  presentation="dialog"
                  surface="media"
                  state={view.savedState}
                />
              }
              actions={
                <button
                  type="button"
                  onClick={() => {
                    setEditor("new");
                  }}
                >
                  Add new media
                </button>
              }
              filters={
                <>
                  <div className="field">
                    <label htmlFor="media-kind">Source</label>
                    <select
                      id="media-kind"
                      value={kind}
                      onChange={(event) => {
                        setKind(event.target.value);
                        changeFilters();
                      }}
                    >
                      <option value="">All sources</option>
                      <option value="local">Local images</option>
                      <option value="external">External references</option>
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="media-association">Record links</label>
                    <select
                      id="media-association"
                      value={association}
                      onChange={(event) => {
                        setAssociation(event.target.value);
                        changeFilters();
                      }}
                    >
                      <option value="all">All media</option>
                      <option value="linked">Linked media</option>
                      <option value="unlinked">Unlinked media</option>
                    </select>
                    <p className="field-help">
                      Unlinked means no record links. An identity cover may
                      still reference the asset.
                    </p>
                  </div>
                  <div className="field">
                    <label htmlFor="media-target-filter">Target</label>
                    <select
                      id="media-target-filter"
                      value={target}
                      onChange={(event) => {
                        setTarget(event.target.value as MediaTargetFilter | "");
                        changeFilters();
                      }}
                    >
                      <option value="">All media</option>
                      <option value="collection">Collection media</option>
                      {mediaTargets.map((type) => (
                        <option key={type.id} value={type.id}>
                          {type.id === "plant_group"
                            ? "Plant groups"
                            : type.id === "seed_lot"
                              ? "Seed lots"
                              : `${type.label}s`}
                        </option>
                      ))}
                    </select>
                  </div>
                </>
              }
              activeFilters={[
                ...(kind
                  ? [
                      {
                        label: "Source",
                        value:
                          kind === "local"
                            ? "Local images"
                            : "External references",
                        onRemove: () => {
                          setKind("");
                          changeFilters();
                        },
                      },
                    ]
                  : []),
                ...(association !== "all"
                  ? [
                      {
                        label: "Record links",
                        value: association === "linked" ? "Linked" : "Unlinked",
                        onRemove: () => {
                          setAssociation("all");
                          changeFilters();
                        },
                      },
                    ]
                  : []),
                ...(target
                  ? [
                      {
                        label: "Target",
                        value: target.replaceAll("_", " "),
                        onRemove: () => {
                          setTarget("");
                          changeFilters();
                        },
                      },
                    ]
                  : []),
              ]}
            />
          }
        />
      )}
      {notice && (
        <p className="notice notice--success" role="status">
          {notice}
        </p>
      )}
      {error && !removing && !editingLink && (
        <div className="notice notice--error" role="alert">
          <p>{error}</p>
          <button
            type="button"
            onClick={() => {
              refresh("");
            }}
          >
            Retry
          </button>
        </div>
      )}
      {initialId ? (
        !detail ? (
          !error && <p role="status">Loading media detail…</p>
        ) : (
          <article className="media-detail" key={detail.id}>
            <DetailHeader
              headingRef={detailHeading}
              eyebrow="Media asset"
              title={title(detail)}
              secondary={
                detail.kind === "local"
                  ? "Managed local image"
                  : "External image reference"
              }
              onEdit={() => {
                setEditor(detail);
              }}
              editLabel="Edit media details"
              primaryActions={
                <button
                  type="button"
                  disabled={detail.deletion_pending}
                  onClick={() => {
                    setLinking(true);
                  }}
                >
                  Link to another record
                </button>
              }
            />
            <div className="media-detail-overview">
              <MediaPreview
                key={`${detail.id}:${detail.content_url ?? "remote"}`}
                asset={detail}
                full
                allowExternal
              />
              <section aria-label="Shared asset metadata">
                <h3>Shared asset metadata</h3>
                <Metadata asset={detail} />
                <p className="field-help">
                  Title, attribution and licence belong to this reusable asset.
                  Captions and display order belong to each record link.
                </p>
                {detail.content_url && !detail.deletion_pending && (
                  <a href={detail.content_url} target="_blank" rel="noreferrer">
                    Open original image
                  </a>
                )}
              </section>
            </div>
            {detail.kind === "external" && (
              <section aria-label="Local copy" className="media-links-section">
                <h3>Local copy</h3>
                <p>
                  {detail.content_url
                    ? "This saved image is stored in Florabase. Refresh contacts the canonical external source again."
                    : "Save the image in Florabase to use it throughout your collection. This explicitly contacts the external source."}
                </p>
                <div className="actions">
                  <button
                    type="button"
                    disabled={pending || detail.deletion_pending}
                    onClick={() => {
                      void action(
                        async () => {
                          await (
                            detail.content_url
                              ? refreshLocalCopy
                              : saveLocalCopy
                          )(detail.id, token);
                        },
                        detail.content_url
                          ? "Local copy refreshed."
                          : "Local copy saved.",
                      );
                    }}
                  >
                    {pending
                      ? "Saving local copy…"
                      : detail.content_url
                        ? "Refresh local copy"
                        : "Save local copy"}
                  </button>
                  {(detail.content_url !== null ||
                    detail.local_copy_cleanup_pending) && (
                    <button
                      type="button"
                      className="button--secondary"
                      disabled={pending || detail.deletion_pending}
                      onClick={() => {
                        setRemoving("copy");
                      }}
                    >
                      Remove local copy
                    </button>
                  )}
                </div>
                {detail.local_copy_cleanup_pending && (
                  <p role="status">
                    Previous local copy cleanup is pending. Retry Remove local
                    copy to complete it.
                  </p>
                )}
              </section>
            )}
            <section className="media-links-section">
              <h3>Linked records</h3>
              <p>
                Each link has its own caption, display order and primary
                designation.
              </p>
              {detail.links.length === 0 ? (
                <p>
                  No record links. This asset remains available in the Gallery.
                </p>
              ) : (
                <ul className="media-link-list">
                  {detail.links.map((link) => (
                    <li key={link.id}>
                      <div>
                        <a href={link.target_url}>{link.target_label}</a>
                        <span className="record-preview__type">
                          {
                            mediaTargets.find(
                              (type) => type.id === link.target_type,
                            )?.label
                          }
                          {link.is_primary && " · Primary image"}
                        </span>
                        {link.caption && <p>{link.caption}</p>}
                        <p>Display order: {link.display_order}</p>
                      </div>
                      <div className="actions">
                        <ActionButton
                          icon="edit"
                          type="button"
                          className="button--secondary"
                          disabled={pending || detail.deletion_pending}
                          onClick={() => {
                            setEditingLink(link);
                          }}
                        >
                          Edit link details
                        </ActionButton>
                        {(link.target_type === "seed_lot" ||
                          link.target_type === "plant" ||
                          link.target_type === "plant_group" ||
                          link.target_type === "harvest" ||
                          link.target_type === "supplier") && (
                          <button
                            type="button"
                            className="button--secondary"
                            disabled={pending || detail.deletion_pending}
                            onClick={() => {
                              const type = link.target_type;
                              if (
                                type !== "seed_lot" &&
                                type !== "plant" &&
                                type !== "plant_group" &&
                                type !== "harvest" &&
                                type !== "supplier"
                              )
                                return;
                              void action(
                                async () => {
                                  if (link.is_primary)
                                    await clearPrimaryPhoto(
                                      type,
                                      link.target_id,
                                      token,
                                    );
                                  else
                                    await setPrimaryPhoto(
                                      type,
                                      link.target_id,
                                      { kind: detail.kind, photo_id: link.id },
                                      token,
                                    );
                                },
                                link.is_primary
                                  ? "Primary designation cleared."
                                  : "Primary image selected for this record.",
                              );
                            }}
                          >
                            {link.is_primary
                              ? "Clear primary"
                              : "Set as primary"}
                          </button>
                        )}
                        <button
                          type="button"
                          className="button--danger"
                          disabled={pending}
                          onClick={() => {
                            setError(null);
                            setRemoving(link);
                          }}
                        >
                          Unlink from this record
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <section className="media-links-section">
              <h3>BotanicalIdentity cover references</h3>
              {detail.covers.length === 0 ? (
                <p>No cover references.</p>
              ) : (
                <ul>
                  {detail.covers.map((cover) => (
                    <li key={cover.id}>
                      <a href={cover.url}>{cover.label}</a> · Current
                      representative cover
                    </li>
                  ))}
                </ul>
              )}
              <p>
                Cover references are separate from record links and also block
                asset deletion.
              </p>
            </section>
            <section className="media-delete-section">
              <h3>Delete media asset</h3>
              <p>
                {detail.can_delete
                  ? "This asset is fully unreferenced. Deleting it permanently removes any stored image and local copy."
                  : `Deletion blocked: ${String(detail.collection_link_count)} record link(s) and ${String(detail.cover_reference_count)} cover reference(s) remain. Remove these references first.`}
              </p>
              <button
                className="button--danger"
                type="button"
                disabled={pending || !detail.can_delete}
                onClick={() => {
                  setError(null);
                  setRemoving("asset");
                }}
              >
                {detail.deletion_pending
                  ? "Retry asset deletion"
                  : "Delete media asset"}
              </button>
            </section>
          </article>
        )
      ) : (
        <>
          {!page && !error && <p role="status">Loading media…</p>}
          {page && (
            <div className="media-directory-layout">
              <div className="media-directory-results">
                <DirectoryResults
                  count={page.items.length}
                  total={page.total}
                />
                <div className="media-grid" aria-label="Media assets">
                  {page.items.map((asset) => (
                    <button
                      className="media-choice button--secondary"
                      type="button"
                      key={asset.id}
                      id={`media-asset-${asset.id}`}
                      aria-pressed={selected?.id === asset.id}
                      onClick={() => {
                        choose(asset);
                      }}
                    >
                      <MediaPreview asset={asset} />
                      <strong title={title(asset)}>{title(asset)}</strong>
                      <span>
                        {asset.kind === "local"
                          ? "Local image"
                          : asset.content_url
                            ? "External reference · local copy saved"
                            : "External reference · not stored locally"}
                      </span>
                      <span>
                        {asset.collection_link_count === 0
                          ? "Unlinked"
                          : `${String(asset.collection_link_count)} record links`}
                        {asset.cover_reference_count > 0 &&
                          ` · ${String(asset.cover_reference_count)} cover reference(s)`}
                      </span>
                    </button>
                  ))}
                </div>
                {page.total === 0 && (
                  <p>
                    No matching media. Add a local image or external reference
                    to begin.
                  </p>
                )}
                <div className="actions media-pagination">
                  <button
                    type="button"
                    disabled={offset === 0}
                    onClick={() => {
                      const params = new URLSearchParams(
                        directoryHash.split("?", 2)[1],
                      );
                      const next = Math.max(0, offset - page.limit);
                      if (next) params.set("offset", String(next));
                      else params.delete("offset");
                      navigateMedia(
                        `#/media${params.size ? `?${params}` : ""}`,
                      );
                      setPage(null);
                      setSelected(null);
                    }}
                  >
                    Previous media
                  </button>
                  <span>
                    {page.total === 0
                      ? "0 assets"
                      : `${String(offset + 1)}–${String(Math.min(offset + page.limit, page.total))} of ${String(page.total)}`}
                  </span>
                  <button
                    type="button"
                    disabled={offset + page.limit >= page.total}
                    onClick={() => {
                      const params = new URLSearchParams(
                        directoryHash.split("?", 2)[1],
                      );
                      params.set("offset", String(offset + page.limit));
                      navigateMedia(`#/media?${params}`);
                      setPage(null);
                      setSelected(null);
                    }}
                  >
                    Next media
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
      {selected && !initialId && (
        <MediaQuickPreview
          key={selected.id}
          asset={selected}
          onSaved={() => {
            refresh("Local copy saved.");
          }}
          onClose={() => {
            setSelected(null);
          }}
        />
      )}
      {editor && (
        <MediaEditor
          asset={editor === "new" ? undefined : editor}
          onClose={() => {
            setEditor(null);
          }}
          onSaved={() => {
            setEditor(null);
            if (initialId) refresh("Media details saved.");
            else {
              changeFilters();
              refresh("Media asset added to the library.");
            }
          }}
        />
      )}
      {linking && detail && (
        <MediaLinker
          asset={detail}
          onClose={() => {
            setLinking(false);
          }}
          onLinked={() => {
            setLinking(false);
            refresh("Media linked to the record.");
          }}
        />
      )}
      {editingLink && (
        <PhotoDialog
          title="Edit record link details"
          onClose={() => {
            if (!pending) {
              setEditingLink(null);
              setError(null);
            }
          }}
        >
          <form onSubmit={(event) => void saveLink(event)}>
            <p>{editingLink.target_label}</p>
            <div className="field">
              <label htmlFor="media-edit-caption">
                Caption for this record
              </label>
              <textarea
                id="media-edit-caption"
                name="caption"
                maxLength={2000}
                defaultValue={editingLink.caption ?? ""}
                disabled={pending}
              />
            </div>
            <div className="field">
              <FieldLabel required htmlFor="media-edit-order">
                Display order for this record
              </FieldLabel>
              <input
                id="media-edit-order"
                name="display_order"
                type="number"
                min={0}
                max={2147483647}
                required
                defaultValue={editingLink.display_order}
                disabled={pending}
              />
            </div>
            {error && (
              <p className="notice notice--error" role="alert">
                {error}
              </p>
            )}
            <div className="actions">
              <button disabled={pending}>Save link details</button>
              <button
                type="button"
                className="button--secondary"
                disabled={pending}
                onClick={() => {
                  setEditingLink(null);
                  setError(null);
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </PhotoDialog>
      )}
      {removing && detail && (
        <PhotoDialog
          title={
            removing === "asset"
              ? "Delete media asset permanently?"
              : removing === "copy"
                ? "Remove local copy?"
                : "Unlink from this record?"
          }
          onClose={() => {
            if (!pending) {
              setRemoving(null);
              setError(null);
            }
          }}
        >
          <p>
            {removing === "asset"
              ? "This removes the fully unreferenced media asset from the library. A local original and its thumbnail are permanently deleted."
              : removing === "copy"
                ? "Remove the saved image from Florabase. The external reference, record links, primary selections and covers remain."
                : `Remove this link from ${removing.target_label}. Its primary designation will be cleared if selected. The asset, other links and cover references remain.`}
          </p>
          {error && (
            <p className="notice notice--error" role="alert">
              {error}
            </p>
          )}
          <div className="actions">
            <button
              className="button--secondary"
              disabled={pending}
              type="button"
              onClick={() => {
                setRemoving(null);
                setError(null);
              }}
            >
              Cancel
            </button>
            <button
              className="button--danger"
              disabled={pending}
              type="button"
              onClick={() => {
                if (removing === "asset")
                  void action(async () => {
                    await deleteMedia(detail.id, token);
                    navigateMedia(directoryHash, detail.id);
                    setDetail(null);
                    setPage(null);
                  }, "Media asset deleted.");
                else if (removing === "copy")
                  void action(async () => {
                    await removeLocalCopy(detail.id, token);
                  }, "Local copy removed. External reference and links retained.");
                else
                  void action(async () => {
                    await unlinkMedia(removing.id, token);
                  }, "Record link removed. Media retained in the library.");
              }}
            >
              {pending
                ? "Working…"
                : removing === "asset"
                  ? "Delete media asset"
                  : removing === "copy"
                    ? "Remove local copy"
                    : "Unlink from this record"}
            </button>
          </div>
        </PhotoDialog>
      )}
    </section>
  );
}
