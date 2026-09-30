import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import type { EventResponse } from "../collection/api";
import { EventFeed } from "./EventFeed";
afterEach(cleanup);

const event: EventResponse = {
  id: "event",
  kind: "observation",
  occurred_on: null,
  notes: null,
  target: {
    type: "plant",
    id: "plant",
    label: "Glasshouse plant",
    lifecycle: "active",
    botanical_identity: { id: "identity", display_label: "Solanum betaceum" },
  },
  destination_location_id: null,
  destination_location: null,
  recipient: null,
  resulting_plant_id: null,
  resulting_plant: null,
  created_at: "2026-09-30T00:00:00Z",
  updated_at: "2026-09-30T00:00:00Z",
};
test("compact Events use the exact target primary thumbnail and retain the target link", () => {
  render(
    <EventFeed
      compact
      showTargetPhoto
      events={[
        {
          ...event,
          target: {
            ...event.target,
            primary_photo: {
              kind: "local",
              photo_id: "photo",
              thumbnail_url: "/api/v1/collection-photos/local/photo/thumbnail",
            },
          },
        },
      ]}
    />,
  );
  const image = screen.getByRole("img", {
    name: "Primary photo for Glasshouse plant",
  });
  expect(image).toHaveAttribute(
    "src",
    "/api/v1/collection-photos/local/photo/thumbnail",
  );
  expect(
    screen.getByRole("link", { name: "Glasshouse plant" }),
  ).toHaveAttribute("href", "#/plants/plant?tab=events");
  fireEvent.error(image);
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  expect(
    screen.queryByText("Primary photo unavailable"),
  ).not.toBeInTheDocument();
});
test("Events with no designation and external designations never request an image", () => {
  const { rerender } = render(
    <EventFeed compact showTargetPhoto events={[event]} />,
  );
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  expect(screen.queryByText(/primary photo/i)).not.toBeInTheDocument();
  rerender(
    <EventFeed
      compact
      showTargetPhoto
      events={[
        {
          ...event,
          target: {
            ...event.target,
            primary_photo: {
              kind: "external",
              photo_id: "external",
              thumbnail_url: null,
            },
          },
        },
      ]}
    />,
  );
  expect(screen.queryByText("External primary photo")).not.toBeInTheDocument();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});

test("other compact Event feeds keep their existing image-free presentation", () => {
  render(
    <EventFeed
      compact
      events={[
        {
          ...event,
          target: {
            ...event.target,
            primary_photo: {
              kind: "local",
              photo_id: "photo",
              thumbnail_url: "/thumb",
            },
          },
        },
      ]}
    />,
  );
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});

test("the full Events list uses the same exact-target thumbnail treatment for groups", () => {
  render(
    <EventFeed
      showTargetPhoto
      events={[
        {
          ...event,
          target: {
            ...event.target,
            type: "plant_group",
            lifecycle: "active",
            primary_photo: {
              kind: "local",
              photo_id: "group-photo",
              thumbnail_url: "/group-thumb",
            },
          },
        },
      ]}
    />,
  );
  expect(
    screen.getByRole("img", { name: "Primary photo for Glasshouse plant" }),
  ).toHaveAttribute("src", "/group-thumb");
  expect(
    screen.getByRole("link", { name: "Glasshouse plant" }),
  ).toHaveAttribute("href", "#/plant-groups/plant?tab=events");
});
