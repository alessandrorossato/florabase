import { useEffect, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { getMedia, type MediaDetail } from "../media/api";
import { MediaPreview } from "../media/MediaPreview";
import { listPhotos, type PhotoTarget } from "../photos/api";

export interface IdentityMediaRecord {
  id: string;
  label: string;
  kind: string;
  target: PhotoTarget;
  href: string;
}
interface Image {
  asset: MediaDetail;
  caption: string | null;
  owner: IdentityMediaRecord;
}

/** Read existing owner photo lists in bounded batches; never search the global media library. */
export function IdentityRecordMedia({
  records,
}: {
  records: IdentityMediaRecord[];
}) {
  const auth = useAuth();
  const [limit, setLimit] = useState(6);
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    images: Image[];
    failed: number;
    legacy: number;
  } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    const assets = new Map<string, Promise<MediaDetail>>();
    void Promise.allSettled(
      records.slice(0, limit).map(async (owner) => {
        const photos = await listPhotos(
          owner.target,
          owner.id,
          controller.signal,
        );
        const images = await Promise.all(
          photos.map(async (photo) => {
            if (!photo.media_asset_id) return null;
            let asset = assets.get(photo.media_asset_id);
            if (!asset) {
              asset = getMedia(photo.media_asset_id, controller.signal);
              assets.set(photo.media_asset_id, asset);
            }
            return { asset: await asset, caption: photo.caption, owner };
          }),
        );
        return {
          images,
          legacy: photos.filter((photo) => !photo.media_asset_id).length,
        };
      }),
    ).then((results) => {
      if (controller.signal.aborted) return;
      for (const r of results)
        if (
          r.status === "rejected" &&
          r.reason instanceof ApiError &&
          r.reason.status === 401
        )
          auth.sessionExpired();
      setResult({
        images: results.flatMap((r) =>
          r.status === "fulfilled"
            ? r.value.images.filter((image): image is Image => image !== null)
            : [],
        ),
        failed: results.filter((r) => r.status === "rejected").length,
        legacy: results.reduce(
          (n, r) => n + (r.status === "fulfilled" ? r.value.legacy : 0),
          0,
        ),
      });
    });
    return () => {
      controller.abort();
    };
  }, [records, limit, attempt, auth]);
  return (
    <>
      {!result && <p role="status">Loading images from linked records…</p>}
      {result?.failed ? (
        <div role="alert">
          <p>Images from {result.failed} linked records could not load.</p>
          <button
            className="button--secondary"
            type="button"
            onClick={() => {
              setResult(null);
              setAttempt((n) => n + 1);
            }}
          >
            Retry linked images
          </button>
        </div>
      ) : null}
      {result?.images.length === 0 && !result.failed && !result.legacy && (
        <p className="identity-media-empty">
          No images are attached to these linked records yet. Add photos from
          the source record.
        </p>
      )}
      {result?.legacy ? (
        <p>
          Some older photo entries can be viewed in their linked source records.
        </p>
      ) : null}
      <div className="identity-thumbnail-gallery">
        {result?.images.map(({ asset, caption, owner }) => (
          <figure key={`${owner.target}:${owner.id}:${asset.id}`}>
            <a
              className="identity-thumbnail-link"
              href={`#/media/${asset.id}`}
              aria-label={`Open media details for ${caption ?? asset.title ?? owner.label}`}
            >
              <MediaPreview asset={asset} />
            </a>
            <figcaption>
              <small>
                {asset.kind === "local"
                  ? "Uploaded image"
                  : asset.content_url
                    ? "External image · saved copy"
                    : "External reference"}
              </small>
              <p>
                {caption ??
                  asset.title ??
                  asset.original_filename ??
                  "Untitled image"}
              </p>
              <a href={owner.href}>{owner.label}</a>
              <small>{owner.kind}</small>
              {asset.attribution && <small>{asset.attribution}</small>}
              {asset.licence_label && (
                <small>
                  {asset.licence_url ? (
                    <a
                      href={asset.licence_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {asset.licence_label}
                    </a>
                  ) : (
                    asset.licence_label
                  )}
                </small>
              )}
              {asset.source_url && (
                <a href={asset.source_url} target="_blank" rel="noreferrer">
                  Image source
                </a>
              )}
            </figcaption>
          </figure>
        ))}
      </div>
      {records.length > limit && (
        <button
          className="button--secondary"
          type="button"
          onClick={() => {
            setResult(null);
            setLimit((n) => n + 6);
          }}
        >
          Show images from more linked records
        </button>
      )}
      {records.length > 0 && (
        <p className="field-help">
          Checked {Math.min(limit, records.length)} of {records.length} linked
          records. External references without a saved copy open in Media; no
          remote image is loaded here.
        </p>
      )}
    </>
  );
}
