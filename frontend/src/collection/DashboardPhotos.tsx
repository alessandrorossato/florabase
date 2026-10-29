import { useState } from "react";
import type { DashboardResponse } from "./api";
import { EmptyState, SectionHeader } from "../components/WorkspaceUI";
import { Icon } from "../components/Icon";

type Photo = NonNullable<DashboardResponse["photos"]>[number];

function Thumbnail({ photo }: { photo: Photo }) {
  const [broken, setBroken] = useState<ReadonlySet<string>>(new Set());
  const image = [photo.image, photo.reference_image].find(
    (value) =>
      value?.thumbnail_url.startsWith("/api/v1/media-assets/") &&
      !broken.has(value.thumbnail_url),
  );
  const reference = image && image === photo.reference_image;
  return (
    <>
      {image ? (
        <img
          src={image.thumbnail_url}
          alt={photo.title}
          loading="eager"
          decoding="async"
          onError={() => {
            setBroken((current) => new Set([...current, image.thumbnail_url]));
          }}
        />
      ) : (
        <span className="dashboard-photo-fallback">
          <Icon name="plant" />
          <span>No photograph</span>
        </span>
      )}
      <span className="dashboard-photo-source">
        {image
          ? reference
            ? "Identity reference"
            : "Plant primary photo"
          : "No photograph"}
      </span>
    </>
  );
}

export function DashboardPhotos({ photos }: { photos: Photo[] }) {
  return (
    <section
      className="dashboard-photo-section"
      aria-labelledby="dashboard-media-title"
    >
      <SectionHeader
        id="dashboard-media-title"
        title="Plants in your collection"
      >
        <div className="dashboard-photo-tools">
          <a href="#/plants">All Plants</a>
          {photos.some((photo) => photo.image ?? photo.reference_image) && (
            <details className="dashboard-photo-credits">
              <summary>Image attribution</summary>
              <p>
                Explicit Plant primary photos are preferred. Identity references
                illustrate the botanical identity, not the owned specimen.
              </p>
              <ul>
                {photos.map((photo) => (
                  <li key={photo.id}>
                    <strong>{photo.title}</strong>
                    {[photo.image, photo.reference_image].map(
                      (image, index) =>
                        image && (
                          <span key={index}>
                            {index === 0
                              ? " · Plant primary"
                              : " · Identity reference"}
                            {` · ${image.attribution ?? "Attribution not recorded"}`}
                            {image.licence_label &&
                              (image.licence_url ? (
                                <>
                                  {" "}
                                  ·{" "}
                                  <a href={image.licence_url}>
                                    {image.licence_label}
                                  </a>
                                </>
                              ) : (
                                ` · ${image.licence_label}`
                              ))}
                            {image.source_url && (
                              <>
                                {" "}
                                · <a href={image.source_url}>Source</a>
                              </>
                            )}
                          </span>
                        ),
                    )}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      </SectionHeader>
      {photos.length ? (
        <ul
          className="dashboard-photo-grid"
          aria-label="Selected individual Plants"
        >
          {photos.map((photo) => (
            <li key={photo.id}>
              <a href={`#/plants/${photo.id}`} aria-label={photo.title}>
                <span className="dashboard-photo-frame">
                  <Thumbnail photo={photo} />
                </span>
                <span className="dashboard-photo-label" title={photo.title}>
                  {photo.title}
                </span>
              </a>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState>
          No active individual Plants recorded. Add a Plant to start your
          collection.
        </EmptyState>
      )}
    </section>
  );
}
