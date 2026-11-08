import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

import { ApiError, requestJson } from "../auth/api";
import type { components } from "../api/schema";
import { AncestryExplorer } from "./AncestryExplorer";
import { LineagePanel } from "./LineagePanel";

vi.mock("../auth/api", async (original) => ({
  ...(await original<typeof import("../auth/api")>()),
  requestJson: vi.fn(),
}));
const request = vi.mocked(requestJson);
type Node = components["schemas"]["AncestryNode"];
type Children = components["schemas"]["AncestryChildren"];

const identity = { id: "basil", display_label: "Ocimum basilicum" };
function node(
  kind: Node["record"]["kind"],
  id: string,
  extra: Partial<Node> & { lifecycle?: string } = {},
): Node {
  const { lifecycle = "active", ...rest } = extra;
  const record = (
    kind === "sowing"
      ? { kind, id, label: id, lifecycle }
      : { kind, id, label: id, lifecycle, botanical_identity: identity }
  ) as Node["record"];
  return {
    record,
    origin: null,
    harvest_conversion: null,
    descendant_count: 0,
    ...rest,
  };
}
const page = (items: Node[], total = items.length, offset = 0): Children => ({
  total,
  offset,
  limit: 25,
  items,
});

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

test("the recorded chain reads oldest first with origin, generations, evidence and focus links", async () => {
  request.mockResolvedValue({
    focus: node("plant", "Second-generation plant", { descendant_count: 0 }),
    // Nearest first, exactly as the API walks.
    ancestors: [
      node("sowing", "Packet B sowing"),
      node("seed_lot", "Packet B", {
        origin: "collection_produced",
        lifecycle: "reversed",
        harvest_conversion: {
          conversion_id: "conversion",
          status: "reversed",
          harvest_id: "harvest-1",
          harvest_label: "August seed heads",
          harvested_on: { precision: "month", year: 2026, month: 8, day: null },
        },
      }),
      node("plant", "Mother plant", { lifecycle: "dead" }),
      node("sowing", "Packet A sowing", { lifecycle: "completed" }),
      node("seed_lot", "Packet A", { origin: "purchased" }),
    ],
    children: page([]),
  });
  render(<AncestryExplorer kind="plant" id="Second-generation plant" />);
  const chain = await screen.findByRole("list", {
    name: "Recorded upstream path",
  });
  expect(request).toHaveBeenCalledWith(
    "/api/v1/lineage/plant/Second-generation plant?limit=25",
    expect.anything(),
  );
  expect(
    screen.getByRole("heading", { level: 2, name: "Second-generation plant" }),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/Purchased\. Independently acquired/),
  ).toBeInTheDocument();
  const steps = within(chain).getAllByRole("listitem");
  expect(
    steps.map((step) => within(step).getByRole("article").textContent),
  ).toEqual([
    expect.stringMatching(/^Seed lotGeneration 1Packet A/),
    expect.stringMatching(/^SowingGeneration 1Packet A sowing/),
    expect.stringMatching(/^PlantGeneration 1Mother plant.*Dead/),
    expect.stringMatching(/^Seed lotGeneration 2Packet B.*Reversed/),
    expect.stringMatching(/^SowingGeneration 2Packet B sowing/),
    expect.stringMatching(/^This PlantGeneration 2Second-generation plant/),
  ]);
  expect(within(steps[1]).getByText("sown as")).toBeInTheDocument();
  expect(within(steps[3]).getByText("produced")).toBeInTheDocument();
  expect(
    within(steps[3]).getByText(/Reversed harvest conversion from/),
  ).toHaveTextContent("2026-08");
  expect(
    within(steps[3]).getByRole("link", { name: "August seed heads" }),
  ).toHaveAttribute("href", "#/harvests/harvest-1");
  expect(
    within(steps[1]).getByText("Source recorded on this sowing"),
  ).toBeInTheDocument();
  expect(
    within(steps[2]).getByRole("link", { name: "Mother plant" }),
  ).toHaveAttribute("href", "#/plants/Mother plant");
  expect(
    within(steps[2]).getByRole("link", {
      name: "Explore ancestry from Mother plant",
    }),
  ).toHaveAttribute("href", "#/lineage/plant/Mother plant");
  const focus = within(steps[5]).getByRole("article");
  expect(focus).toHaveAttribute("aria-current", "true");
  expect(
    within(focus).queryByRole("link", { name: /Explore ancestry/ }),
  ).not.toBeInTheDocument();
  expect(screen.getByText("No recorded descendants.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open plant" })).toHaveAttribute(
    "href",
    "#/plants/Second-generation plant",
  );
});

test.each([
  [node("plant", "Found plant", { origin: "unknown" }), /Origin not recorded/],
  [
    node("seed_lot", "Orphan packet", { origin: "collection_produced" }),
    /producer was not recorded/,
  ],
  [
    node("plant", "Saved cutting", { origin: "collection_produced" }),
    /source was not recorded/,
  ],
])("an unrecorded parent is stated, never invented", async (focus, text) => {
  request.mockResolvedValue({ focus, ancestors: [], children: page([]) });
  render(<AncestryExplorer kind={focus.record.kind} id={focus.record.id} />);
  expect(await screen.findByText(text)).toBeInTheDocument();
  expect(
    within(
      screen.getByRole("list", { name: "Recorded upstream path" }),
    ).getAllByRole("listitem"),
  ).toHaveLength(1);
});

test("descendants branch progressively with bounded pages and keyboard focus", async () => {
  const user = userEvent.setup();
  const sowing = node("sowing", "Spring sowing", { descendant_count: 2 });
  const first = Array.from({ length: 25 }, (_, index) =>
    node("seed_lot", `Packet ${String(index + 1)}`),
  );
  request.mockResolvedValueOnce({
    focus: node("seed_lot", "Root packet", {
      origin: "gift_exchange",
      descendant_count: 30,
    }),
    ancestors: [],
    children: page([sowing], 1),
  });
  render(<AncestryExplorer kind="seed_lot" id="Root packet" />);
  const toggle = await screen.findByRole("button", {
    name: "Show 2 recorded descendants of Spring sowing",
  });
  expect(toggle).toHaveAttribute("aria-expanded", "false");

  request.mockResolvedValueOnce(
    page([
      node("plant_group", "Seedling tray", { descendant_count: 30 }),
      node("plant", "Keeper", { lifecycle: "transferred" }),
    ]),
  );
  await user.click(toggle);
  expect(toggle).toHaveAttribute("aria-expanded", "true");
  expect(request).toHaveBeenLastCalledWith(
    "/api/v1/lineage/sowing/Spring sowing/children?offset=0&limit=25",
    expect.anything(),
  );
  const tray = await screen.findByRole("link", { name: "Seedling tray" });
  expect(screen.getAllByText("grown into")).toHaveLength(2);
  expect(screen.getByText("Transferred")).toBeInTheDocument();

  request.mockResolvedValueOnce(page(first, 30));
  await user.click(
    screen.getByRole("button", {
      name: "Show 30 recorded descendants of Seedling tray",
    }),
  );
  expect(
    await screen.findByRole("link", { name: "Packet 25" }),
  ).toBeInTheDocument();
  // A recorded production step starts the next material generation.
  expect(
    screen.getByRole("link", { name: "Packet 1" }).closest("article"),
  ).toHaveTextContent("Generation 2");
  expect(tray.closest("article")).toHaveTextContent("Generation 1");

  // An overlapping page (a record added meanwhile shifted the offset) keeps each record once.
  request.mockResolvedValueOnce(
    page(
      [
        first[24],
        ...Array.from({ length: 5 }, (_, index) =>
          node("seed_lot", `Packet ${String(index + 26)}`),
        ),
      ],
      30,
      25,
    ),
  );
  await user.click(screen.getByRole("button", { name: "Show 5 more" }));
  expect(request).toHaveBeenLastCalledWith(
    "/api/v1/lineage/plant_group/Seedling tray/children?offset=25&limit=25",
  );
  const next = await screen.findByRole("link", { name: "Packet 26" });
  expect(next).toHaveFocus();
  expect(
    screen.queryByRole("button", { name: /^Show \d+ more/ }),
  ).not.toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: "Packet 25" })).toHaveLength(1);

  // Collapsing hides, and reopening restores, every loaded page without refetching.
  const calls = request.mock.calls.length;
  const trayToggle = screen.getByRole("button", {
    name: "Hide 30 recorded descendants of Seedling tray",
  });
  await user.click(trayToggle);
  expect(
    screen.queryByRole("link", { name: "Packet 26" }),
  ).not.toBeInTheDocument();
  await user.click(trayToggle);
  expect(screen.getByRole("link", { name: "Packet 30" })).toBeVisible();
  expect(request.mock.calls.length).toBe(calls);
});

test("missing, failed and failed-expansion states are explicit and retryable", async () => {
  const user = userEvent.setup();
  request.mockRejectedValueOnce(new ApiError(404));
  const { unmount } = render(<AncestryExplorer kind="plant" id="gone" />);
  expect(
    await screen.findByText("This record was not found."),
  ).toBeInTheDocument();
  unmount();
  // A malformed address is not a retryable failure.
  request.mockRejectedValueOnce(new ApiError(422));
  render(<AncestryExplorer kind="plant" id="not-a-uuid" />);
  expect(
    await screen.findByText("This record was not found."),
  ).toBeInTheDocument();
  cleanup();

  request.mockRejectedValueOnce(new ApiError(500));
  render(<AncestryExplorer kind="sowing" id="sowing" />);
  request.mockResolvedValueOnce({
    focus: node("sowing", "sowing", { descendant_count: 1 }),
    ancestors: [node("seed_lot", "lot", { origin: "unknown" })],
    children: page([node("plant", "child", { descendant_count: 1 })]),
  });
  await user.click(
    await screen.findByRole("button", { name: "Retry ancestry" }),
  );
  request.mockRejectedValueOnce(new Error("offline"));
  await user.click(
    await screen.findByRole("button", {
      name: "Show 1 recorded descendant of child",
    }),
  );
  expect(
    await screen.findByText(/Descendants could not be loaded/),
  ).toBeInTheDocument();
  request.mockResolvedValueOnce(page([node("seed_lot", "grandchild")]));
  await user.click(screen.getByRole("button", { name: "Retry" }));
  expect(
    await screen.findByRole("link", { name: "grandchild" }),
  ).toBeInTheDocument();
});

test("each record's Lineage tab opens the explorer centred on it", () => {
  request.mockReturnValue(new Promise(() => undefined));
  render(<LineagePanel kind="plant-groups" id="group" />);
  expect(
    screen.getByRole("link", { name: "Explore material ancestry" }),
  ).toHaveAttribute("href", "#/lineage/plant_group/group");
});
