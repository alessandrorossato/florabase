import { useEffect, useState } from "react";
import { ApiError, isExpectedAuthCancellation } from "../auth/api";
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
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const [limit, setLimit] = useState(6);
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    images: Image[];
    failed: number;
    legacy: number;
  } | null>(null);
  useEffect(() => {
    if (!authorized) return;
    const controller = new AbortController();
    const assets = new Map<string, Promise<MediaDetail>>();
    void Promise.allSettled(
      records.slice(0, limit).map(async (owner) => {
        const photos = await listPhotos(
          owner.target,
          owner.id,
          capability,
          controller.signal,
        );
        const images = await Promise.all(
          photos.map(async (photo) => {
            if (!photo.media_asset_id) return null;
            let asset = assets.get(photo.media_asset_id);
            if (!asset) {
              asset = getMedia(
                photo.media_asset_id,
                capability,
                controller.signal,
              );
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
        ) {
          sessionExpired();
          return;
        }
      if (
        results.some(
          (r) =>
            r.status === "rejected" && isExpectedAuthCancellation(r.reason),
        )
      ) {
        return;
      }
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
  }, [records, limit, attempt, authorized, capability, sessionExpired]);
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
        <div className="identity-media-empty">
          <p>No photos on the records of this species yet. Add one to:</p>
          <ul className="identity-media-records">
            {records.slice(0, 12).map((r) => (
              <li key={`${r.kind}:${r.id}`}>
                <a href={r.href}>{r.label}</a>
                <small>{r.kind}</small>
              </li>
            ))}
          </ul>
        </div>
      )}
      {result?.legacy ? (
        <p>
          Some older photo entries can be viewed in their linked source records.
        </p>
      ) : null}
      <ul className="identity-thumbnail-grid">
        {result?.images.map(({ asset, caption, owner }) => (
          <li key={`${owner.target}:${owner.id}:${asset.id}`}>
            <a
              className="identity-thumbnail-link"
              href={`#/media/${asset.id}`}
              aria-label={`Open media details for ${caption ?? asset.title ?? owner.label}`}
            >
              <MediaPreview asset={asset} />
            </a>
            <a className="identity-thumbnail-owner" href={owner.href}>
              {owner.kind} · {owner.label}
            </a>
            {(asset.attribution ?? asset.licence_label) && (
              <small className="identity-thumbnail-credit">
                {asset.attribution}
                {asset.attribution && asset.licence_label && " · "}
                {asset.licence_label &&
                  (asset.licence_url ? (
                    <a
                      href={asset.licence_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {asset.licence_label}
                    </a>
                  ) : (
                    asset.licence_label
                  ))}
              </small>
            )}
          </li>
        ))}
      </ul>
      {records.length > limit && (
        <button
          className="button--secondary"
          type="button"
          onClick={() => {
            setResult(null);
            setLimit((n) => n + 6);
          }}
        >
          Show photos from more records
        </button>
      )}
    </>
  );
}
