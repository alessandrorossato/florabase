import { useState } from "react";
import type { DashboardResponse } from "./api";

type Photo = NonNullable<DashboardResponse["photos"]>[number];

/** Today never draws an empty tile: a Plant appears only while one of its images loads. */
export function DashboardPhotos({ photos }: { photos: Photo[] }) {
  const [broken, setBroken] = useState<ReadonlySet<string>>(new Set());
  const shown = photos
    .flatMap((photo) => {
      // Only protected local thumbnails; a remote URL is never loaded.
      const image = [photo.image, photo.reference_image].find(
        (value) =>
          value?.thumbnail_url.startsWith("/api/v1/media-assets/") &&
          !broken.has(value.thumbnail_url),
      );
      return image ? [{ photo, image }] : [];
    })
    .slice(0, 4);
  if (!shown.length)
    return (
      <p className="today-photo-line">
        {photos.length
          ? "None of the sampled Plants has a photo that can be shown yet. "
          : "No active individual Plants recorded yet. "}
        <a href="#/plants">
          {photos.length ? "Add photos in Plants" : "Add a Plant"}
        </a>
      </p>
    );
  return (
    <section
      className="today-panel today-specimens"
      aria-labelledby="dashboard-media-title"
    >
      <header className="today-panel__header">
        <h3 id="dashboard-media-title">Plants in your collection</h3>
        <a href="#/plants">All Plants</a>
      </header>
      <p className="today-provenance">Sampled active Plants with a photo</p>
      <ul className="today-plates" aria-label="Selected individual Plants">
        {shown.map(({ photo, image }) => (
          <li key={photo.id}>
            <a href={`#/plants/${photo.id}`} aria-label={photo.title}>
              <span className="today-plate__frame">
                <img
                  src={image.thumbnail_url}
                  alt={photo.title}
                  loading="eager"
                  decoding="async"
                  onError={() => {
                    setBroken(
                      (current) => new Set([...current, image.thumbnail_url]),
                    );
                  }}
                />
                <span className="today-plate__source">
                  {image === photo.reference_image
                    ? "Identity reference"
                    : "Plant primary photo"}
                </span>
              </span>
              <span className="today-plate__title" title={photo.title}>
                {photo.title}
              </span>
              <i className="scientific-name today-plate__name">
                {photo.scientific_name}
              </i>
            </a>
          </li>
        ))}
      </ul>
      <details className="today-credits">
        <summary>Image attribution</summary>
        <p>
          Explicit Plant primary photos are preferred. Identity references
          illustrate the botanical identity, not the owned specimen.
        </p>
        <ul>
          {shown.map(({ photo }) => (
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
    </section>
  );
}
