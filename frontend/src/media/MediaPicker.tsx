import { useEffect, useState, type SyntheticEvent } from "react";
import { PhotoDialog } from "../photos/PhotosSection";
import { DirectorySearch } from "../components/ReferenceUI";
import { useAuth } from "../auth/context";
import { ApiError } from "../auth/api";
import type { PhotoTarget } from "../photos/api";
import { linkMedia, listMedia, type MediaAsset, type MediaPage } from "./api";
import { MediaPreview } from "./MediaPreview";
import { formText, mediaError } from "./helpers";

export function MediaPicker({
  target,
  targetId,
  targetLabel,
  onClose,
  onLinked,
}: {
  target: PhotoTarget;
  targetId: string;
  targetLabel: string;
  onClose: () => void;
  onLinked: () => void;
}) {
  const auth = useAuth();
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<MediaPage | null>(null);
  const [selected, setSelected] = useState<MediaAsset | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    void listMedia({ query, offset }, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setPage(value);
      })
      .catch((failure: unknown) => {
        if (!controller.signal.aborted) {
          if (failure instanceof ApiError && failure.status === 401)
            auth.sessionExpired();
          else setError(mediaError(failure));
        }
      });
    return () => {
      controller.abort();
    };
  }, [query, offset, attempt, auth]);
  const token =
    auth.state.status === "authenticated" ? auth.state.csrfToken : "";
  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected || pending) return;
    const form = new FormData(event.currentTarget);
    setPending(true);
    setError(null);
    try {
      await linkMedia(
        target,
        targetId,
        selected.id,
        {
          caption: formText(form, "caption") || null,
          display_order: Number(form.get("display_order")),
        },
        token,
      );
      onLinked();
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401)
        auth.sessionExpired();
      else setError(mediaError(failure));
    } finally {
      setPending(false);
    }
  }
  return (
    <PhotoDialog
      title="Link existing media"
      className="media-picker-dialog"
      onClose={() => {
        if (!pending) onClose();
      }}
    >
      <p>
        Reuse a library asset for {targetLabel}. The original file stays stored
        once.
      </p>
      <DirectorySearch
        id="media-picker-search"
        label="Search media"
        placeholder="Title, filename or attribution"
        value={query}
        onChange={(value) => {
          setQuery(value);
          setOffset(0);
          setPage(null);
          setSelected(null);
          setError(null);
        }}
        disabled={pending}
      />
      {!page && !error && <p role="status">Loading media…</p>}
      {page && (
        <>
          <div className="media-picker-grid" aria-label="Available media">
            {page.items.map((asset) => (
              <button
                key={asset.id}
                type="button"
                className="media-choice button--secondary"
                aria-pressed={selected?.id === asset.id}
                disabled={pending || asset.deletion_pending}
                onClick={() => {
                  setSelected(asset);
                }}
              >
                <MediaPreview key={asset.id} asset={asset} />
                <strong>
                  {asset.title ??
                    asset.original_filename ??
                    "External image reference"}
                </strong>
                <span>
                  {asset.kind === "local"
                    ? "Local image"
                    : "External reference"}{" "}
                  · {asset.collection_link_count} collection links
                </span>
              </button>
            ))}
          </div>
          {page.total === 0 && (
            <p>
              No matching media. Add new media from this record or the Gallery.
            </p>
          )}
          <div className="actions media-pagination">
            <button
              type="button"
              disabled={pending || offset === 0}
              onClick={() => {
                setOffset(Math.max(0, offset - page.limit));
                setPage(null);
                setSelected(null);
              }}
            >
              Previous
            </button>
            <span>{page.total} media assets</span>
            <button
              type="button"
              disabled={pending || offset + page.limit >= page.total}
              onClick={() => {
                setOffset(offset + page.limit);
                setPage(null);
                setSelected(null);
              }}
            >
              Next
            </button>
          </div>
        </>
      )}
      <form onSubmit={(event) => void submit(event)}>
        <p>
          {selected
            ? `Selected: ${selected.title ?? selected.original_filename ?? "External reference"}`
            : "Choose an asset above."}
        </p>
        <div className="field">
          <label htmlFor="media-link-caption">Caption for this record</label>
          <textarea
            id="media-link-caption"
            name="caption"
            maxLength={2000}
            disabled={pending}
          />
        </div>
        <div className="field">
          <label htmlFor="media-link-order">
            Display order for this record
          </label>
          <input
            id="media-link-order"
            name="display_order"
            type="number"
            min={0}
            max={2147483647}
            defaultValue={0}
            required
            disabled={pending}
          />
        </div>
        <p>
          Primary selection is a separate action after linking, where supported.
        </p>
        {error && (
          <div className="notice notice--error" role="alert">
            <p>{error}</p>
            <button
              type="button"
              onClick={() => {
                setError(null);
                setAttempt(attempt + 1);
              }}
              disabled={pending}
            >
              Retry loading media
            </button>
          </div>
        )}
        <div className="actions">
          <button disabled={!selected || pending}>
            {pending ? "Linking…" : "Link to this record"}
          </button>
          <button
            type="button"
            className="button--secondary"
            disabled={pending}
            onClick={onClose}
          >
            Cancel
          </button>
        </div>
      </form>
    </PhotoDialog>
  );
}
