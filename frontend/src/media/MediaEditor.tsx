import { FieldLabel } from "../components/FieldLabel";
import { useRef, useState, type SyntheticEvent } from "react";
import { ExternalCopyChoice } from "./ExternalCopyChoice";
import { PhotoDialog } from "../photos/PhotosSection";
import { useAuth } from "../auth/context";
import { ApiError } from "../auth/api";
import { formText, mediaError } from "./helpers";
import {
  createExternalMedia,
  saveLocalCopy,
  updateMedia,
  uploadMedia,
  type MediaAsset,
} from "./api";

export function MediaEditor({
  asset,
  onClose,
  onSaved,
}: {
  asset?: MediaAsset;
  onClose: () => void;
  onSaved: (asset: MediaAsset) => void;
}) {
  const auth = useAuth();
  const fileInput = useRef<HTMLInputElement>(null);
  const [kind, setKind] = useState<"local" | "external">(
    asset?.kind ?? "local",
  );
  const [pending, setPending] = useState(false);
  const [createdReference, setCreatedReference] = useState<MediaAsset | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const token =
    auth.state.status === "authenticated" ? auth.state.csrfToken : "";
  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    const form = new FormData(event.currentTarget);
    const text = (key: string) => formText(form, key);
    setPending(true);
    setError(null);
    try {
      const metadata = {
        title: text("title") || null,
        attribution: text("attribution") || null,
        licence_label: text("licence_label") || null,
        licence_url: text("licence_url") || null,
      };
      let result: MediaAsset;
      if (asset) result = await updateMedia(asset.id, metadata, token);
      else if (kind === "external") {
        result = await createExternalMedia(
          {
            ...metadata,
            attribution: text("attribution"),
            image_url: text("image_url"),
            source_url: text("source_url"),
          },
          token,
        );
        if (form.get("save_local_copy") === "on") {
          setCreatedReference(result);
          result = await saveLocalCopy(result.id, token);
        }
      } else {
        const file = fileInput.current?.files?.[0];
        if (!(file instanceof File) || file.size === 0) {
          setError("Choose a JPEG, PNG or WebP image.");
          return;
        }
        result = await uploadMedia(
          file,
          text("title"),
          text("attribution"),
          token,
        );
      }
      onSaved(result);
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401)
        auth.sessionExpired();
      else setError(mediaError(failure));
    } finally {
      setPending(false);
    }
  }
  if (createdReference && error)
    return (
      <PhotoDialog
        title="External reference saved"
        onClose={() => {
          if (!pending) onSaved(createdReference);
        }}
      >
        <p role="alert">
          Local copy could not be downloaded. The external reference remains
          saved.
        </p>
        <div className="actions">
          <button
            type="button"
            disabled={pending}
            onClick={() => {
              setPending(true);
              void saveLocalCopy(createdReference.id, token)
                .then(onSaved)
                .catch((failure: unknown) => {
                  if (failure instanceof ApiError && failure.status === 401)
                    auth.sessionExpired();
                  else setError(mediaError(failure));
                })
                .finally(() => {
                  setPending(false);
                });
            }}
          >
            {pending ? "Saving…" : "Retry save"}
          </button>
          <button
            type="button"
            className="button--secondary"
            disabled={pending}
            onClick={() => {
              onSaved(createdReference);
            }}
          >
            Keep reference only
          </button>
        </div>
      </PhotoDialog>
    );
  return (
    <PhotoDialog
      title={asset ? "Edit media details" : "Add new media"}
      onClose={() => {
        if (!pending) onClose();
      }}
    >
      <form onSubmit={(event) => void submit(event)}>
        {!asset && (
          <fieldset className="media-kind-choice">
            <legend>Media source</legend>
            <label>
              <input
                type="radio"
                name="kind"
                checked={kind === "local"}
                onChange={() => {
                  setKind("local");
                }}
                disabled={pending}
              />{" "}
              Local image
            </label>
            <label>
              <input
                type="radio"
                name="kind"
                checked={kind === "external"}
                onChange={() => {
                  setKind("external");
                }}
                disabled={pending}
              />{" "}
              External reference
            </label>
          </fieldset>
        )}
        <div className="field">
          <label htmlFor="media-title">Title</label>
          <input
            id="media-title"
            name="title"
            maxLength={2000}
            defaultValue={asset?.title ?? ""}
            disabled={pending}
          />
        </div>
        {!asset && kind === "local" && (
          <div className="field">
            <FieldLabel required htmlFor="media-file">
              Image file
            </FieldLabel>
            <input
              ref={fileInput}
              id="media-file"
              name="file"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              required
              disabled={pending}
            />
            <p>
              JPEG, PNG or WebP, up to 25 MiB. Stored once and reusable across
              records.
            </p>
          </div>
        )}
        {!asset && kind === "external" && (
          <>
            <div className="field">
              <FieldLabel required htmlFor="media-image-url">
                Image URL
              </FieldLabel>
              <input
                id="media-image-url"
                name="image_url"
                type="url"
                required
                maxLength={2048}
                disabled={pending}
              />
            </div>
            <div className="field">
              <FieldLabel required htmlFor="media-source-url">
                Source page URL
              </FieldLabel>
              <input
                id="media-source-url"
                name="source_url"
                type="url"
                required
                maxLength={2048}
                disabled={pending}
              />
            </div>
            <ExternalCopyChoice disabled={pending} />
          </>
        )}
        <div className="field">
          <FieldLabel
            required={kind === "external"}
            htmlFor="media-attribution"
          >
            Attribution
          </FieldLabel>
          <textarea
            id="media-attribution"
            name="attribution"
            maxLength={2000}
            required={kind === "external"}
            defaultValue={asset?.attribution ?? ""}
            disabled={pending}
          />
        </div>
        {(asset !== undefined || kind === "external") && (
          <>
            <div className="field">
              <label htmlFor="media-licence">Licence label</label>
              <input
                id="media-licence"
                name="licence_label"
                maxLength={2000}
                defaultValue={asset?.licence_label ?? ""}
                disabled={pending}
              />
            </div>
            <div className="field">
              <label htmlFor="media-licence-url">Licence URL</label>
              <input
                id="media-licence-url"
                name="licence_url"
                type="url"
                maxLength={2048}
                defaultValue={asset?.licence_url ?? ""}
                disabled={pending}
              />
            </div>
          </>
        )}
        {asset && (
          <p>
            Asset details apply everywhere this media is used. Captions and
            order belong to each record link.
          </p>
        )}
        {error && (
          <p className="notice notice--error" role="alert">
            {error}
          </p>
        )}
        <div className="actions">
          <button disabled={pending}>
            {pending ? "Saving…" : "Save media"}
          </button>
          <button
            type="button"
            className="button--secondary"
            onClick={onClose}
            disabled={pending}
          >
            Cancel
          </button>
        </div>
      </form>
    </PhotoDialog>
  );
}
