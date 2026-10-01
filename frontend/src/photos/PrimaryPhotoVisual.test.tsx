import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";

import { PrimaryPhotoVisual } from "./PrimaryPhotoVisual";

afterEach(cleanup);

test("local primary uses only its fixed protected thumbnail and falls back on failure", () => {
  const url = "/api/v1/collection-photos/local/photo-1/thumbnail";
  render(
    <PrimaryPhotoVisual
      photo={{ kind: "local", photo_id: "photo-1", thumbnail_url: url }}
      label="Seed lot A"
      compact
    />,
  );
  const image = screen.getByRole("img", {
    name: "Primary photo for Seed lot A",
  });
  expect(image).toHaveAttribute("src", url);
  expect(image).toHaveAttribute("loading", "lazy");
  fireEvent.error(image);
  expect(screen.getByText("Primary photo unavailable")).toBeVisible();
});

test("external primary remains a neutral indicator with no remote request", () => {
  render(
    <PrimaryPhotoVisual
      photo={{ kind: "external", photo_id: "photo-2", thumbnail_url: null }}
      label="Plant B"
    />,
  );
  expect(screen.getByText("External primary photo")).toBeVisible();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});

test("no primary has no image or inferred fallback", () => {
  const { container } = render(
    <PrimaryPhotoVisual photo={null} label="Group C" />,
  );
  expect(container).toBeEmptyDOMElement();
});

test.each([
  null,
  { kind: "external" as const, photo_id: "external", thumbnail_url: null },
])(
  "neutral directory slot never loads an absent or external image",
  (photo) => {
    const { container } = render(
      <PrimaryPhotoVisual
        photo={photo}
        label="Record"
        compact
        fallback="neutral"
      />,
    );
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(container.querySelector("[aria-hidden=true]")).toBeInTheDocument();
    expect(container).not.toHaveTextContent("External primary photo");
  },
);

test("failed local directory thumbnail keeps its neutral slot", () => {
  const { container } = render(
    <PrimaryPhotoVisual
      photo={{
        kind: "local",
        photo_id: "local",
        thumbnail_url: "/api/v1/photos/local/thumbnail",
      }}
      label="Record"
      compact
      fallback="neutral"
    />,
  );
  fireEvent.error(screen.getByRole("img"));
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  expect(container.querySelector("[aria-hidden=true]")).toBeInTheDocument();
});

test("saved external primary uses its protected snapshot for activity visuals", () => {
  render(
    <PrimaryPhotoVisual
      label="Plant"
      photo={{
        kind: "external",
        photo_id: "external",
        thumbnail_url: "/api/v1/media-assets/external/thumbnail?v=1",
      }}
    />,
  );
  expect(screen.getByRole("img")).toHaveAttribute(
    "src",
    "/api/v1/media-assets/external/thumbnail?v=1",
  );
});
