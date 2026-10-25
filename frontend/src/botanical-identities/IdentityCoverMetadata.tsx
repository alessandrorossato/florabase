import { useEffect, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { getMedia, type MediaDetail } from "../media/api";

/** Read the actual cover asset's rights, never infer them from the identity name. */
export function IdentityCoverMetadata({ id }: { id: string }) {
  const auth = useAuth();
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    asset?: MediaDetail;
    failed?: boolean;
  } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    void getMedia(id, controller.signal)
      .then((asset) => {
        if (!controller.signal.aborted) setResult({ asset });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setResult({ failed: true });
      });
    return () => {
      controller.abort();
    };
  }, [id, attempt, auth]);
  if (result?.failed)
    return (
      <div role="alert">
        <p>
          Cover attribution could not load. Open the media record for its source
          details.
        </p>
        <button
          className="button--secondary"
          type="button"
          onClick={() => {
            setResult(null);
            setAttempt((n) => n + 1);
          }}
        >
          Retry cover attribution
        </button>
      </div>
    );
  if (!result?.asset) return <p role="status">Loading cover attribution…</p>;
  const asset = result.asset;
  return (
    <div className="identity-cover__metadata" aria-label="Cover attribution">
      {asset.title && <p>{asset.title}</p>}
      <p>{asset.attribution ?? "Attribution not recorded"}</p>
      {asset.licence_label && (
        <p>
          {asset.licence_url ? (
            <a href={asset.licence_url} target="_blank" rel="noreferrer">
              {asset.licence_label}
            </a>
          ) : (
            asset.licence_label
          )}
        </p>
      )}
      {asset.source_url && (
        <a href={asset.source_url} target="_blank" rel="noreferrer">
          Original image source
        </a>
      )}
    </div>
  );
}
