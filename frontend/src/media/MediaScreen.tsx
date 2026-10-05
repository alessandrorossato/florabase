import { useEffect, useId, useState, type SyntheticEvent } from "react";
import { useAuth } from "../auth/context";
import { ApiError } from "../auth/api";
import {
  Breadcrumbs,
  DetailHeader,
  WorkspaceIntro,
} from "../components/CollectionUI";
import { DirectorySearch, QuickPreview } from "../components/ReferenceUI";
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
import { MediaLinker } from "./MediaLinker";
import { mediaTargets } from "./targets";

function title(asset: MediaAsset): string {
  return asset.title ?? asset.original_filename ?? "External image reference";
}
function Metadata({
  asset,
  compact = false,
}: {
  asset: MediaAsset;
  compact?: boolean;
}) {
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
      {!compact && asset.media_type && (
        <div>
          <dt>File type</dt>
          <dd>{asset.media_type}</dd>
        </div>
      )}
      {!compact && asset.width && asset.height && (
        <div>
          <dt>Dimensions</dt>
          <dd>
            {asset.width} × {asset.height} px
          </dd>
        </div>
      )}
      {!compact && asset.byte_size !== null && (
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
      {!compact && asset.attribution && (
        <div>
          <dt>Attribution</dt>
          <dd>{asset.attribution}</dd>
        </div>
      )}
      {!compact && asset.source_url && (
        <div>
          <dt>Source page</dt>
          <dd>
            <a href={asset.source_url} target="_blank" rel="noreferrer">
              Open source page
            </a>
          </dd>
        </div>
      )}
      {!compact && asset.licence_label && (
        <div>
          <dt>Licence</dt>
          <dd>{asset.licence_label}</dd>
        </div>
      )}
      {!compact && asset.licence_url && (
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
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("");
  const [association, setAssociation] = useState("all");
  const [target, setTarget] = useState<MediaTargetFilter | "">("");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<MediaPage | null>(null);
  const [detail, setDetail] = useState<MediaDetail | null>(null);
  const [selected, setSelected] = useState<MediaAsset | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editor, setEditor] = useState<"new" | MediaAsset | null>(null);
  const [linking, setLinking] = useState(false);
  const [removing, setRemoving] = useState<MediaLink | "asset" | "copy" | null>(
    null,
  );
  const [editingLink, setEditingLink] = useState<MediaLink | null>(null);
  const [pending, setPending] = useState(false);
  useEffect(() => {
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
          if (!controller.signal.aborted) setPage(value);
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
      else setError(mediaError(failure));
    }
  }, [initialId, query, kind, association, target, offset, attempt, auth]);
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
    setOffset(0);
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
    if (window.matchMedia("(max-width: 64rem)").matches)
      window.location.assign(`#/media/${asset.id}`);
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
    <section className="media-workspace" aria-labelledby={headingId}>
      {initialId ? (
        <>
          <Breadcrumbs
            items={[
              { label: "Media", href: "#/media" },
              { label: detail ? title(detail) : "Media detail" },
            ]}
          />
          <h2 id={headingId} className="sr-only">
            Media detail
          </h2>
        </>
      ) : (
        <WorkspaceIntro
          eyebrow="Shared media library"
          title="Media"
          titleId={headingId}
          description="One image, many records. Unlinked assets stay available for future use."
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
              <Metadata asset={detail} />
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
                        <button
                          type="button"
                          className="button--secondary"
                          disabled={pending || detail.deletion_pending}
                          onClick={() => {
                            setEditingLink(link);
                          }}
                        >
                          Edit link details
                        </button>
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
          <div className="media-filters">
            <DirectorySearch
              id="media-search"
              label="Search media"
              placeholder="Title, filename or attribution"
              value={query}
              onChange={(value) => {
                setQuery(value);
                changeFilters();
              }}
            />
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
          </div>
          <p className="field-help">
            Unlinked means no record links. An identity cover may still
            reference the asset.
          </p>
          {!page && !error && <p role="status">Loading media…</p>}
          {page && (
            <div className="media-directory-layout">
              <div className="media-directory-results">
                <div className="media-grid" aria-label="Media assets">
                  {page.items.map((asset) => (
                    <button
                      className="media-choice button--secondary"
                      type="button"
                      key={asset.id}
                      aria-pressed={selected?.id === asset.id}
                      onClick={() => {
                        choose(asset);
                      }}
                    >
                      <MediaPreview asset={asset} />
                      <strong>{title(asset)}</strong>
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
                      setOffset(Math.max(0, offset - page.limit));
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
                      setOffset(offset + page.limit);
                      setPage(null);
                      setSelected(null);
                    }}
                  >
                    Next media
                  </button>
                </div>
              </div>
              {selected ? (
                <QuickPreview>
                  <MediaPreview key={selected.id} asset={selected} />
                  <h3>{title(selected)}</h3>
                  <Metadata asset={selected} compact />
                  <a className="button-link" href={`#/media/${selected.id}`}>
                    Open media details
                  </a>
                </QuickPreview>
              ) : (
                <QuickPreview>
                  <h3>Select media</h3>
                  <p>
                    Inspect its source and reference counts, then open details
                    to manage links.
                  </p>
                </QuickPreview>
              )}
            </div>
          )}
        </>
      )}
      {editor && (
        <MediaEditor
          asset={editor === "new" ? undefined : editor}
          onClose={() => {
            setEditor(null);
          }}
          onSaved={(asset) => {
            setEditor(null);
            if (initialId) refresh("Media details saved.");
            else {
              setOffset(0);
              setSelected(asset);
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
              <label htmlFor="media-edit-order">
                Display order for this record
              </label>
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
              className="button--danger"
              disabled={pending}
              type="button"
              onClick={() => {
                if (removing === "asset")
                  void action(async () => {
                    await deleteMedia(detail.id, token);
                    window.location.hash = "/media";
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
          </div>
        </PhotoDialog>
      )}
    </section>
  );
}
