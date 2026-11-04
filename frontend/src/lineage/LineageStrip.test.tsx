import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

import { requestJson } from "../auth/api";
import type { components } from "../api/schema";
import { LineageStrip } from "./LineageStrip";

vi.mock("../auth/api", () => ({ requestJson: vi.fn() }));
const request = vi.mocked(requestJson);
type Response = components["schemas"]["LineageResponse"];
const identity = { id: "identity", display_label: "Ocimum basilicum" };
const plantPath: Response = {
  subject: {
    kind: "plant",
    id: "mother",
    label: "Mother plant",
    lifecycle: "active",
    botanical_identity: identity,
  },
  // Nearest first, as the API walks it.
  ancestors: [
    { kind: "sowing", id: "tray", label: "Spring tray", lifecycle: "active" },
    {
      kind: "seed_lot",
      id: "packet",
      label: null,
      lifecycle: "exhausted",
      botanical_identity: identity,
    },
  ],
};

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

test("shows only the recorded upstream path, oldest first, ending at this record", async () => {
  request.mockResolvedValue(plantPath);
  const onFull = vi.fn((event: { preventDefault: () => void }) => {
    event.preventDefault();
  });
  render(
    <LineageStrip
      kind="plants"
      id="mother"
      current="This Plant"
      fullHref="#/plants/mother?tab=lineage"
      onFull={onFull}
    />,
  );
  const strip = screen.getByRole("navigation", { name: "Recorded lineage" });
  const path = await within(strip).findByRole("list");
  const steps = within(path).getAllByRole("listitem");
  expect(steps.map((step) => step.textContent)).toEqual([
    "Seed lotUnlabelled seed lotexhausted",
    "SowingSpring tray",
    "This Plant",
  ]);
  expect(steps[2]).toHaveAttribute("aria-current", "true");
  expect(within(steps[0]).getByRole("link")).toHaveAttribute(
    "href",
    "#/seeds/packet?tab=lineage",
  );
  expect(within(steps[1]).getByRole("link")).toHaveAttribute(
    "href",
    "#/sowings/tray?tab=lineage",
  );
  // The subject itself is not repeated as a link; the header already names it.
  expect(within(path).queryByRole("link", { name: "Mother plant" })).toBeNull();
  expect(request.mock.calls[0]?.[0]).toBe("/api/v1/plants/mother/lineage");
  await userEvent.click(
    within(strip).getByRole("link", { name: "Full lineage" }),
  );
  expect(onFull).toHaveBeenCalledOnce();
});

test("a Sowing reads its recorded Seed lot's path and includes that Seed lot", async () => {
  request.mockResolvedValue({
    subject: {
      kind: "seed_lot",
      id: "packet",
      label: "Basil packet",
      lifecycle: "active",
      botanical_identity: identity,
    },
    ancestors: [],
  } satisfies Response);
  render(
    <LineageStrip
      kind="seed-lots"
      id="packet"
      includeSubject
      current="This Sowing"
    />,
  );
  const items = await screen.findAllByRole("listitem");
  expect(items.map((item) => item.textContent)).toEqual([
    "Seed lotBasil packet",
    "This Sowing",
  ]);
  expect(request.mock.calls[0]?.[0]).toBe("/api/v1/seed-lots/packet/lineage");
  expect(screen.queryByRole("link", { name: "Full lineage" })).toBeNull();
});

test("no recorded source says so instead of implying one from a shared identity", async () => {
  request.mockResolvedValue({ ...plantPath, ancestors: [] });
  render(<LineageStrip kind="plants" id="mother" current="This Plant" />);
  expect(await screen.findByText("No recorded source material.")).toBeVisible();
  expect(screen.queryByRole("list")).toBeNull();
});

test("a failed load is stated and can be retried", async () => {
  request.mockRejectedValueOnce(new Error("offline"));
  request.mockResolvedValueOnce(plantPath);
  render(<LineageStrip kind="plants" id="mother" current="This Plant" />);
  expect(screen.getByText("Loading recorded lineage…")).toBeVisible();
  await userEvent.click(
    await screen.findByRole("button", { name: "Retry lineage" }),
  );
  expect(
    await screen.findByRole("link", { name: "Spring tray" }),
  ).toBeVisible();
  expect(request).toHaveBeenCalledTimes(2);
});
