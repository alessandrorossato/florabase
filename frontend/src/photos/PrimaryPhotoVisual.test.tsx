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
