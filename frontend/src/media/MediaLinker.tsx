import { useEffect, useState, type SyntheticEvent } from "react";
import { useAuth } from "../auth/context";
import { ApiError } from "../auth/api";
import { DirectorySearch } from "../components/ReferenceUI";
import { PhotoDialog } from "../photos/PhotosSection";
import type { PhotoTarget } from "../photos/api";
import {
  linkMedia,
  listTargets,
  type MediaAsset,
  type TargetPage,
} from "./api";
import { formText, mediaError } from "./helpers";
import { mediaTargets } from "./targets";

export function MediaLinker({
  asset,
  onClose,
  onLinked,
}: {
  asset: MediaAsset;
  onClose: () => void;
  onLinked: () => void;
}) {
  const auth = useAuth();
  const [target, setTarget] = useState<PhotoTarget>("plant");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<TargetPage | null>(null);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    void listTargets(target, query, offset, controller.signal)
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
  }, [target, query, offset, attempt, auth]);
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
        selected,
        asset.id,
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
  function reset() {
    setSelected("");
    setOffset(0);
    setPage(null);
    setPage(null);
    setError(null);
  }
  return (
    <PhotoDialog
      title="Link media to another record"
      onClose={() => {
        if (!pending) onClose();
      }}
    >
      <form onSubmit={(event) => void submit(event)}>
        <p>
          Reuse{" "}
          {asset.title ?? asset.original_filename ?? "this external reference"}{" "}
          without copying it.
        </p>
        <div className="field">
          <label htmlFor="media-target-type">Record type</label>
          <select
            id="media-target-type"
            value={target}
            disabled={pending}
            onChange={(event) => {
              setTarget(event.target.value as PhotoTarget);
              reset();
            }}
          >
            {mediaTargets.map((type) => (
              <option key={type.id} value={type.id}>
                {type.label}
              </option>
            ))}
          </select>
        </div>
        <DirectorySearch
          id="media-record-query"
          label="Search records"
          placeholder="Record label, botanical name or ID"
          value={query}
          disabled={pending}
          onChange={(value) => {
            setQuery(value);
            reset();
          }}
        />
        {!page && !error && <p role="status">Loading records…</p>}
        {page && (
          <>
            <div className="media-target-choices">
              {page.items.map((record) => (
                <label key={record.id}>
                  <input
                    type="radio"
                    name="record"
                    value={record.id}
                    checked={selected === record.id}
                    disabled={pending}
                    onChange={() => {
                      setSelected(record.id);
                    }}
                  />
                  {record.label}
                </label>
              ))}
            </div>
            {page.total === 0 && <p>No matching records.</p>}
            <div className="actions media-pagination">
              <button
                type="button"
                disabled={pending || offset === 0}
                onClick={() => {
                  setOffset(Math.max(0, offset - page.limit));
                  setPage(null);
                  setSelected("");
                }}
              >
                Previous records
              </button>
              <span>{page.total} records</span>
              <button
                type="button"
                disabled={pending || offset + page.limit >= page.total}
                onClick={() => {
                  setOffset(offset + page.limit);
                  setPage(null);
                  setSelected("");
                }}
              >
                Next records
              </button>
            </div>
          </>
        )}
        <div className="field">
          <label htmlFor="media-record-caption">Caption for this record</label>
          <textarea
            id="media-record-caption"
            name="caption"
            maxLength={2000}
            disabled={pending}
          />
        </div>
        <div className="field">
          <label htmlFor="media-record-order">
            Display order for this record
          </label>
          <input
            id="media-record-order"
            name="display_order"
            type="number"
            min={0}
            max={2147483647}
            defaultValue={0}
            required
            disabled={pending}
          />
        </div>
        {error && (
          <div className="notice notice--error" role="alert">
            <p>{error}</p>
            <button
              type="button"
              disabled={pending}
              onClick={() => {
                setError(null);
                setAttempt(attempt + 1);
              }}
            >
              Retry loading records
            </button>
          </div>
        )}
        <div className="actions">
          <button disabled={!selected || pending}>
            {pending ? "Linking…" : "Link media"}
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
