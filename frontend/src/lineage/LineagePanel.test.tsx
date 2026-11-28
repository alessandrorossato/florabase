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

type AncestryNode = components["schemas"]["AncestryNode"];
type Children = components["schemas"]["AncestryChildren"];
function page(items: AncestryNode[] = [], total = items.length): Children {
  return { items, total, offset: 0, limit: 25 };
}
/** Serves the record lineage endpoint and the ancestry endpoint used for descendants. */
function serve(
  lineage: (url: string) => Promise<unknown>,
  children: AncestryNode[] | (() => Promise<Children>) = [],
) {
  request.mockImplementation((url: string) =>
    url.startsWith("/api/v1/lineage/")
      ? typeof children === "function"
        ? children()
        : Promise.resolve(page(children))
      : lineage(url),
  );
}

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

test("recorded ancestry keeps reversed ancestors explicit and correctly linked", async () => {
  serve(() => Promise.resolve(extracted));
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
  serve((url) => {
    if (url.includes("pending-old"))
      return new Promise((resolve) => {
        resolveOld = resolve;
      });
    if (url.includes("independent"))
      return new Promise((resolve) => {
        resolveNew = resolve;
      });
    return Promise.resolve(extracted);
  });
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
    serve(() =>
      Promise.resolve({
        subject: { ...extracted.subject, kind: "seed_lot", id: "material" },
        ancestors: producer ? [extracted.ancestors[0]] : [],
      }),
    );
    renderWithAuth(<LineagePanel kind="seed-lots" id="material" />);
    if (producer) {
      expect(
        await screen.findByRole("link", { name: /Original group/ }),
      ).toHaveAttribute("href", "#/plant-groups/original?tab=lineage");
      expect(screen.getAllByRole("listitem")).toHaveLength(2);
      expect(
        screen.getByRole("link", { name: /This Seed lot/ }),
      ).toHaveAttribute("aria-current", "page");
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
    serve(() =>
      Promise.resolve({
        subject: { ...extracted.subject, kind, label: "Current record" },
        ancestors: [extracted.ancestors[1], extracted.ancestors[2]],
      }),
    );
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

test("a Seed lot that starts its line shows what was recorded from it", async () => {
  const sowing = (id: string, label: string, count: number): AncestryNode => ({
    record: { kind: "sowing", id, label, lifecycle: "active" },
    origin: null,
    harvest_conversion: null,
    descendant_count: count,
  });
  serve(
    () =>
      Promise.resolve({
        subject: { ...extracted.subject, kind: "seed_lot", id: "packet" },
        ancestors: [],
      }),
    [sowing("s0", "Spring tray", 2), sowing("s1", "Autumn tray", 0)],
  );
  renderWithAuth(<LineagePanel kind="seed-lots" id="packet" />);
  const next = await screen.findByRole("region", {
    name: "Recorded from this record",
  });
  expect(
    within(next).getByRole("heading", {
      level: 4,
      name: "Recorded from this record",
    }),
  ).toBeVisible();
  expect(
    screen.getByText("No recorded source: this record starts its line."),
  ).toBeVisible();
  expect(screen.queryByText("No recorded lineage.")).not.toBeInTheDocument();
  const items = within(next).getAllByRole("listitem");
  expect(items).toHaveLength(2);
  expect(within(items[0]).getByText("sown as")).toBeVisible();
  expect(
    within(items[0]).getByRole("link", { name: "Spring tray" }),
  ).toHaveAttribute("href", "#/sowings/s0?tab=lineage");
  expect(
    within(items[0]).getByRole("link", { name: "2 recorded from it" }),
  ).toHaveAttribute("href", "#/lineage/sowing/s0");
  expect(
    within(items[1]).queryByText(/recorded from it/),
  ).not.toBeInTheDocument();
  expect(request).toHaveBeenCalledWith(
    "/api/v1/lineage/seed_lot/packet/children?offset=0&limit=25",
    expect.objectContaining({ signal: expect.any(AbortSignal) as unknown }),
  );
});

const sowingNode = (index: number): AncestryNode => ({
  record: {
    kind: "sowing",
    id: `s${String(index)}`,
    label: `Tray ${String(index)}`,
    lifecycle: "active",
  },
  origin: null,
  harvest_conversion: null,
  descendant_count: 0,
});

test("a failed descendants request keeps the loaded upstream path and retries on its own", async () => {
  let fail = true;
  serve(
    () => Promise.resolve(extracted),
    () =>
      fail
        ? Promise.reject(new Error("offline"))
        : Promise.resolve(page([sowingNode(1)])),
  );
  renderWithAuth(<LineagePanel kind="plants" id="extracted" />);
  expect(
    await screen.findByRole("list", { name: "Recorded upstream path" }),
  ).toBeVisible();
  expect(screen.getByRole("alert")).toHaveTextContent(
    "could not load what was recorded from this record",
  );
  fail = false;
  screen.getByRole("button", { name: "Retry recorded descendants" }).click();
  expect(await screen.findByRole("link", { name: "Tray 1" })).toBeVisible();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(
    screen.getByRole("list", { name: "Recorded upstream path" }),
  ).toBeVisible();
});

test("more descendants than the first page point to the explorer", async () => {
  serve(
    () => Promise.resolve({ ...extracted, ancestors: [] }),
    () =>
      Promise.resolve(
        page(
          Array.from({ length: 25 }, (_, index) => sowingNode(index)),
          31,
        ),
      ),
  );
  renderWithAuth(<LineagePanel kind="plants" id="extracted" />);
  expect(await screen.findByText(/Showing 25 of 31/)).toBeVisible();
  expect(
    screen.getAllByRole("link", { name: "Explore material ancestry" })[1],
  ).toHaveAttribute("href", "#/lineage/plant/extracted");
});
