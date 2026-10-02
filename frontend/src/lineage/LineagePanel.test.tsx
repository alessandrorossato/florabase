import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { requestJson } from "../auth/api";
import type { components } from "../api/schema";
import { LineagePanel } from "./LineagePanel";

vi.mock("../auth/api", () => ({ requestJson: vi.fn() }));
const request = vi.mocked(requestJson);
type Response = components["schemas"]["LineageResponse"];
const identity = {
  id: "same-identity",
  display_label: "Same botanical identity",
};
const extracted: Response = {
  subject: {
    kind: "plant",
    id: "extracted",
    label: "Individual",
    lifecycle: "reintegrated",
    botanical_identity: identity,
  },
  ancestors: [
    {
      kind: "plant_group",
      id: "original",
      label: "Original group",
      lifecycle: "reversed",
      botanical_identity: identity,
    },
    {
      kind: "sowing",
      id: "sowing",
      label: "Original sowing",
      lifecycle: "reversed",
    },
    {
      kind: "seed_lot",
      id: "lot",
      label: "Packet",
      lifecycle: "exhausted",
      botanical_identity: identity,
    },
  ],
};

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

test("recorded ancestry keeps reversed ancestors explicit and correctly linked", async () => {
  request.mockResolvedValue(extracted);
  render(<LineagePanel kind="plants" id="extracted" />);
  const path = await screen.findByRole("list", {
    name: "Recorded upstream path",
  });
  const nodes = within(path).getAllByRole("listitem");
  expect(nodes).toHaveLength(3);
  expect(within(nodes[0]).getByText("reversed")).toBeInTheDocument();
  expect(within(nodes[1]).getByText("reversed")).toBeInTheDocument();
  expect(within(nodes[2]).getByText("exhausted")).toBeInTheDocument();
  expect(
    within(nodes[0]).getByRole("link", { name: "Original group" }),
  ).toHaveAttribute("href", "#/plant-groups/original?tab=lineage");
});

test("navigation cannot show or restore a previous record's lineage during loading", async () => {
  let resolveOld!: (value: Response) => void;
  let resolveNew!: (value: Response) => void;
  request
    .mockResolvedValueOnce(extracted)
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveOld = resolve;
        }),
    )
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveNew = resolve;
        }),
    );
  const view = render(<LineagePanel kind="plants" id="extracted" />);
  await screen.findByRole("link", { name: "Original group" });
  view.rerender(<LineagePanel kind="plants" id="pending-old" />);
  expect(screen.getByRole("status")).toHaveTextContent(
    "Loading recorded lineage",
  );
  expect(
    screen.queryByRole("link", { name: "Original group" }),
  ).not.toBeInTheDocument();
  view.rerender(<LineagePanel kind="plants" id="independent" />);
  resolveNew({
    ...extracted,
    subject: { ...extracted.subject, id: "independent" },
    ancestors: [],
  });
  await screen.findByText("No explicit upstream lineage is recorded.");
  resolveOld(extracted);
  await Promise.resolve();
  expect(
    screen.queryByRole("link", { name: "Original group" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByText("No explicit upstream lineage is recorded."),
  ).toBeInTheDocument();
});
