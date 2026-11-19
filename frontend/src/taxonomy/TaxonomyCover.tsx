import { useState } from "react";
import { Icon } from "../components/Icon";
import { useProtectedImage } from "../photos/useProtectedImage";
import type { Identity } from "./api";

export function TaxonomyCover({
  identity,
  representative = false,
  load = true,
}: {
  identity?: Identity;
  representative?: boolean;
  load?: boolean;
}) {
  const [failed, setFailed] = useState<string | null>(null);
  const cover = identity?.cover;
  const [mediaTarget, media] = useProtectedImage({
    rawUrl: load && cover ? cover.thumbnail_url : null,
    onError: (url) => {
      setFailed(url);
    },
  });
  return (
    <span
      ref={mediaTarget}
      className="taxon-cover"
      title={
        identity
          ? `${representative ? "Representative descendant cover: " : "Identity cover: "}${identity.display_label}${cover?.attribution ? ` · ${cover.attribution}` : ""}`
          : "No eligible identity cover"
      }
    >
      {load &&
      cover &&
      failed !== cover.thumbnail_url &&
      !media.failed &&
      media.src ? (
        <img
          src={media.src}
          alt={`Cover of ${identity.display_label}${representative ? "; representative descendant, not an official taxon image" : ""}`}
          loading="lazy"
          decoding="async"
          referrerPolicy={media.referrerPolicy}
          width="48"
          height="48"
          onError={() => {
            setFailed(cover.thumbnail_url);
          }}
        />
      ) : (
        <Icon name="layers" />
      )}
    </span>
  );
}
