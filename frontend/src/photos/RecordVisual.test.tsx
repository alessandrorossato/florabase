import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import { RecordVisual } from "./RecordVisual";
import type { BotanicalIdentityResponse } from "../botanical-identities/api";
const identity: BotanicalIdentityResponse = {
  id: "identity",
  display_label: "Okra",
  scientific_name: "Abelmoschus esculentus",
  cultivar_name: "Burgundy",
  common_name: "Okra Burgundy",
  compact_cover_kind: "local",
  created_at: "",
  updated_at: "",
};
afterEach(cleanup);
test("direct local designation wins; a failed direct image falls through to the identity cover then placeholder", () => {
  render(
    <RecordVisual
      label="Packet"
      kind="seed"
      identity={identity}
      photo={{ kind: "local", photo_id: "photo", thumbnail_url: "/direct" }}
    />,
  );
  expect(screen.getByRole("img")).toHaveAttribute("src", "/direct");
  fireEvent.error(screen.getByRole("img"));
  expect(screen.getByRole("img")).toHaveAttribute(
    "src",
    "/api/v1/botanical-identities/identity/cover-image/thumbnail",
  );
  fireEvent.error(screen.getByRole("img"));
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  expect(screen.getByText("Seed image placeholder")).toBeInTheDocument();
});
test("external primary never loads; local identity fallback is still available", () => {
  render(
    <RecordVisual
      label="Group"
      kind="group"
      identity={identity}
      photo={{ kind: "external", photo_id: "external", thumbnail_url: null }}
    />,
  );
  expect(screen.getByRole("img")).toHaveAttribute(
    "src",
    "/api/v1/botanical-identities/identity/cover-image/thumbnail",
  );
});
test("external collection cover requires explicit policy permission; botanical compact cover retains no-referrer", () => {
  const external = {
    ...identity,
    compact_cover_kind: "external" as const,
    compact_external_cover_url: "https://example.test/photo.jpg",
  };
  const { rerender } = render(
    <RecordVisual label="Plant" kind="plant" identity={external} />,
  );
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  expect(screen.getByText("Plant image placeholder")).toBeInTheDocument();
  rerender(
    <RecordVisual
      label="Okra"
      kind="identity"
      identity={external}
      allowExternalCover
    />,
  );
  expect(screen.getByRole("img")).toHaveAttribute(
    "referrerpolicy",
    "no-referrer",
  );
});
test.each(["seed", "sowing", "plant", "group", "identity"] as const)(
  "%s has a type-specific placeholder without metadata",
  (kind) => {
    const { container } = render(<RecordVisual label="Record" kind={kind} />);
    expect(container.querySelector("svg path")).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  },
);

test("saved external primary and cover resolve to protected local content", () => {
  const { rerender } = render(
    <RecordVisual
      label="Plant"
      kind="plant"
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
  rerender(
    <RecordVisual
      label="Plant"
      kind="plant"
      identity={{
        id: "identity",
        display_label: "Flower",
        compact_cover_kind: "local",
        compact_external_cover_url: "/api/v1/media-assets/cover/thumbnail?v=1",
      }}
    />,
  );
  expect(screen.getByRole("img")).toHaveAttribute(
    "src",
    "/api/v1/media-assets/cover/thumbnail?v=1",
  );
});

test("Harvest falls through direct primary, source primary, safe cover and its own placeholder", () => {
  render(
    <RecordVisual
      kind="harvest"
      label="Fruit harvest"
      identity={identity}
      photo={{
        kind: "local",
        photo_id: "harvest",
        thumbnail_url: "/harvest-primary",
      }}
      fallbackPhoto={{
        kind: "local",
        photo_id: "source",
        thumbnail_url: "/source-primary",
      }}
    />,
  );
  expect(screen.getByRole("img")).toHaveAttribute("src", "/harvest-primary");
  fireEvent.error(screen.getByRole("img"));
  expect(screen.getByRole("img")).toHaveAttribute("src", "/source-primary");
  fireEvent.error(screen.getByRole("img"));
  expect(screen.getByRole("img")).toHaveAttribute(
    "src",
    "/api/v1/botanical-identities/identity/cover-image/thumbnail",
  );
  fireEvent.error(screen.getByRole("img"));
  expect(screen.getByText("Harvest image placeholder")).toBeVisible();
});
