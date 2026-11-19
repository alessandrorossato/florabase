import type { ReactElement } from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/context";
import { requestJson } from "../auth/api";
import type { components } from "../api/schema";
import { acquireTestAuth } from "../test/auth";
import { LineagePanel } from "./LineagePanel";

vi.mock("../auth/api", async (original) => ({
  ...(await original<typeof import("../auth/api")>()),
  requestJson: vi.fn(),
}));
const request = vi.mocked(requestJson);
let auth: AuthContextValue;
function renderWithAuth(ui: ReactElement) {
  return render(<AuthContext.Provider value={auth}>{ui}</AuthContext.Provider>);
}
beforeEach(async () => {
  auth = (await acquireTestAuth()).auth;
});
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
  renderWithAuth(<LineagePanel kind="plants" id="extracted" />);
  const path = await screen.findByRole("list", {
    name: "Recorded upstream path",
  });
  const nodes = within(path).getAllByRole("listitem");
  expect(nodes).toHaveLength(4);
  expect(within(nodes[2]).getByText(/^reversed$/i)).toBeInTheDocument();
  expect(within(nodes[1]).getByText(/^reversed$/i)).toBeInTheDocument();
  expect(within(nodes[0]).getByText("exhausted")).toBeInTheDocument();
  expect(
    within(nodes[2]).getByRole("link", { name: /Original group/ }),
  ).toHaveAttribute("href", "#/plant-groups/original?tab=lineage");
  expect(
    within(nodes[3]).getByRole("link", { name: /This Plant.*Individual/ }),
  ).toHaveAttribute("aria-current", "page");
  expect(
    screen.queryByText(/How this path is recorded/),
  ).not.toBeInTheDocument();
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
  const view = renderWithAuth(<LineagePanel kind="plants" id="extracted" />);
  await screen.findByRole("link", { name: /Original group/ });
  view.rerender(
    <AuthContext.Provider value={auth}>
      <LineagePanel kind="plants" id="pending-old" />
    </AuthContext.Provider>,
  );
  expect(screen.getByRole("status")).toHaveTextContent(
    "Loading recorded lineage",
  );
  expect(
    screen.queryByRole("link", { name: /Original group/ }),
  ).not.toBeInTheDocument();
  view.rerender(
    <AuthContext.Provider value={auth}>
      <LineagePanel kind="plants" id="independent" />
    </AuthContext.Provider>,
  );
  resolveNew({
    ...extracted,
    subject: { ...extracted.subject, id: "independent" },
    ancestors: [],
  });
  await screen.findByText("No recorded lineage.");
  resolveOld(extracted);
  await Promise.resolve();
  expect(
    screen.queryByRole("link", { name: /Original group/ }),
  ).not.toBeInTheDocument();
  expect(screen.getByText("No recorded lineage.")).toBeInTheDocument();
});

test.each([false, true])(
  "SeedLot renders only explicit producer ancestry (producer=%s)",
  async (producer) => {
    request.mockResolvedValue({
      subject: { ...extracted.subject, kind: "seed_lot", id: "material" },
      ancestors: producer ? [extracted.ancestors[0]] : [],
    });
    renderWithAuth(<LineagePanel kind="seed-lots" id="material" />);
    if (producer) {
      expect(
        await screen.findByRole("link", { name: /Original group/ }),
      ).toHaveAttribute("href", "#/plant-groups/original?tab=lineage");
      expect(screen.getAllByRole("listitem")).toHaveLength(1);
    } else {
      expect(await screen.findByText("No recorded lineage.")).toBeVisible();
      expect(screen.queryByRole("list")).not.toBeInTheDocument();
      expect(
        screen.getByText("No recorded lineage.").closest(".empty-state"),
      ).toBeNull();
    }
    expect(request.mock.calls[0]?.[0]).toBe(
      "/api/v1/seed-lots/material/lineage",
    );
    expect(request.mock.calls[0]?.[1]?.signal).toBeInstanceOf(AbortSignal);
  },
);

test.each(["plant", "plant_group"] as const)(
  "%s material path reads SeedLot, Sowing, then this record",
  async (kind) => {
    request.mockResolvedValue({
      subject: { ...extracted.subject, kind, label: "Current record" },
      ancestors: [extracted.ancestors[1], extracted.ancestors[2]],
    });
    renderWithAuth(
      <LineagePanel
        kind={kind === "plant" ? "plants" : "plant-groups"}
        id="extracted"
      />,
    );
    const list = await screen.findByRole("list", {
      name: "Recorded upstream path",
    });
    const nodes = within(list).getAllByRole("listitem");
    expect(nodes.map((n) => n.textContent)).toEqual([
      expect.stringContaining("Packet"),
      expect.stringContaining("Original sowing"),
      expect.stringContaining("Current record"),
    ]);
    expect(within(nodes[2]).getByRole("link")).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(
      screen.queryByText("Same botanical identity"),
    ).not.toBeInTheDocument();
  },
);
