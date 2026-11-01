import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import { EventTargetPhoto } from "./EventTargetPhoto";

afterEach(cleanup);
const identity = { id: "identity", display_label: "Species" };

test("Dashboard and Events target imagery uses a saved external primary locally", () => {
  render(
    <EventTargetPhoto
      kind="plant"
      label="Plant"
      identity={identity}
      photo={{
        kind: "external",
        photo_id: "link",
        thumbnail_url: "/api/v1/media-assets/snapshot/thumbnail?v=1",
      }}
    />,
  );
  expect(screen.getByRole("img")).toHaveAttribute(
    "src",
    "/api/v1/media-assets/snapshot/thumbnail?v=1",
  );
});

test("reference-only activity target stays a placeholder without remote loading", () => {
  render(
    <EventTargetPhoto
      kind="plant"
      label="Plant"
      identity={identity}
      photo={{ kind: "external", photo_id: "link", thumbnail_url: null }}
    />,
  );
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});

test("activity retains its explicitly supplied source-photo evidence", () => {
  render(
    <EventTargetPhoto
      kind="harvest"
      label="Harvest Event"
      identity={identity}
      photo={null}
      fallbackPhoto={{
        kind: "local",
        photo_id: "source",
        thumbnail_url: "/source-evidence",
      }}
    />,
  );
  expect(
    screen.getByRole("img", { name: "Source primary photo for Harvest Event" }),
  ).toHaveAttribute("src", "/source-evidence");
});
