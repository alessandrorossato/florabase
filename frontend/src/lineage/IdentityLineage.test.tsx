import type { ReactElement } from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/context";
import { ApiError, requestJson } from "../auth/api";
import { acquireTestAuth } from "../test/auth";
import { IdentityLineage } from "./IdentityLineage";
import { LineageHome } from "./LineageHome";
import {
  buildForest,
  type GraphNode,
  type IdentityLineageGraph,
} from "./identityForest";

let auth: AuthContextValue;
function renderWithAuth(ui: ReactElement) {
  return render(<AuthContext.Provider value={auth}>{ui}</AuthContext.Provider>);
}
beforeEach(async () => {
  auth = (await acquireTestAuth()).auth;
});

vi.mock("../auth/api", async (original) => ({
  ...(await original<typeof import("../auth/api")>()),
  requestJson: vi.fn(),
}));
const request = vi.mocked(requestJson);

const basil = { id: "basil", display_label: "Ocimum basilicum" };
const other = { id: "thai", display_label: "Ocimum thyrsiflorum" };

function node(
  kind: GraphNode["record"]["kind"],
  id: string,
  extra: {
    lifecycle?: string;
    in_identity?: boolean;
    origin?: GraphNode["origin"];
  } = {},
): GraphNode {
  const { lifecycle = "active", in_identity = true, origin = null } = extra;
  const identity = in_identity ? basil : other;
  const record = (
    kind === "sowing" || kind === "propagation_attempt"
      ? { kind, id, label: id, lifecycle }
      : { kind, id, label: id, lifecycle, botanical_identity: identity }
  ) as GraphNode["record"];
  return {
    record,
    origin,
    harvest_conversion: null,
    descendant_count: 0,
    in_identity,
  };
}
const edge = (
  parent: GraphNode,
  child: GraphNode,
): IdentityLineageGraph["edges"][number] => ({
  parent_kind: parent.record.kind,
  parent_id: parent.record.id,
  child_kind: child.record.kind,
  child_id: child.record.id,
});

const packet = node("seed_lot", "Packet A", { origin: "purchased" });
const sowing = node("sowing", "Packet A sowing", { lifecycle: "completed" });
const mother = node("plant", "Mother plant", { lifecycle: "dead" });
const nextLot = node("seed_lot", "Own seed");
const gift = node("plant", "Gifted plant", { origin: "gift_exchange" });
const foreign = node("plant", "Thai mother", { in_identity: false });
const crossLot = node("seed_lot", "Seed from Thai mother");

function graph(
  overrides: Partial<IdentityLineageGraph> = {},
): IdentityLineageGraph {
  return {
    botanical_identity: basil,
    total: 6,
    limit: 500,
    truncated: false,
    nodes: [packet, sowing, mother, nextLot, gift, crossLot, foreign],
    edges: [
      edge(packet, sowing),
      edge(sowing, mother),
      edge(mother, nextLot),
      edge(foreign, crossLot),
    ],
    ...overrides,
  };
}

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

test("forest keeps independent records apart and starts lines at recorded roots", () => {
  const forest = buildForest(graph());
  expect(forest.roots.map((root) => root.record.id)).toEqual([
    "Packet A",
    // A foreign parent starts its own line after the identity's own starts.
    "Thai mother",
  ]);
  expect(forest.independent.map((item) => item.record.id)).toEqual([
    "Gifted plant",
  ]);
  expect(
    forest.children.get("sowing:Packet A sowing")?.map((c) => c.record.id),
  ).toEqual(["Mother plant"]);
});

test("forest still shows records caught in a cycle", () => {
  const a = node("plant", "A");
  const b = node("seed_lot", "B");
  const forest = buildForest(
    graph({ nodes: [a, b], edges: [edge(a, b), edge(b, a)], total: 2 }),
  );
  expect(forest.roots.map((root) => root.record.id)).toEqual(["A"]);
  expect(forest.independent).toEqual([]);
});

test("identity lineage draws only recorded relationships and marks other identities", async () => {
  request.mockResolvedValue(graph());
  renderWithAuth(<IdentityLineage identityId="basil" />);
  expect(
    await screen.findByRole("heading", { name: "Ocimum basilicum" }),
  ).toBeInTheDocument();
  expect(request).toHaveBeenCalledWith(
    "/api/v1/lineage/identities/basil/graph",
    expect.anything(),
  );
  expect(
    screen.getByText(
      "6 records · 4 recorded relationships · 1 without recorded relationships",
    ),
  ).toBeInTheDocument();

  const lines = screen.getByRole("region", { name: "Recorded lines" });
  expect(within(lines).getByText("sown as")).toBeInTheDocument();
  expect(within(lines).getByText("grown into")).toBeInTheDocument();
  expect(within(lines).getAllByText("produced")).toHaveLength(2);
  expect(
    within(lines).getByText(
      "Purchased. Independently acquired; no earlier collection record.",
    ),
  ).toBeInTheDocument();
  // The foreign parent is shown with its own identity, flagged.
  const thai = within(lines)
    .getAllByRole("article")
    .find((card) => card.textContent.includes("Thai mother"));
  expect(thai).toHaveAttribute("data-outside", "true");
  expect(thai).toHaveTextContent("Ocimum thyrsiflorum");
  expect(
    within(lines).getByRole("link", {
      name: "Explore ancestry from Mother plant",
    }),
  ).toHaveAttribute("href", "#/lineage/plant/Mother plant");

  const independent = screen.getByRole("region", {
    name: "Without recorded relationships",
  });
  expect(
    within(independent).getByRole("link", { name: "Gifted plant" }),
  ).toHaveAttribute("href", "#/plants/Gifted plant");
  expect(within(lines).queryByText("Gifted plant")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open identity" })).toHaveAttribute(
    "href",
    "#/identities/basil",
  );
});

test("a record with two recorded parents is drawn once and referenced after", async () => {
  const left = node("plant", "Left");
  const right = node("plant", "Right");
  const shared = node("seed_lot", "Shared");
  request.mockResolvedValue(
    graph({
      total: 3,
      nodes: [left, right, shared],
      edges: [edge(left, shared), edge(right, shared)],
    }),
  );
  renderWithAuth(<IdentityLineage identityId="basil" />);
  expect(await screen.findByText("(shown above)")).toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: "Shared" })).toHaveLength(2);
  expect(screen.getAllByRole("article")).toHaveLength(3);
});

test("truncated, empty, missing and failed graphs say so", async () => {
  request.mockResolvedValueOnce(
    graph({ total: 900, limit: 500, truncated: true }),
  );
  renderWithAuth(<IdentityLineage identityId="basil" />);
  expect(
    await screen.findByText(
      "Showing the first 500 of 900 records. Open a record’s ancestry to follow the rest.",
    ),
  ).toBeInTheDocument();
  cleanup();

  request.mockResolvedValueOnce(graph({ total: 0, nodes: [], edges: [] }));
  renderWithAuth(<IdentityLineage identityId="basil" />);
  expect(
    await screen.findByText("No records use this identity yet."),
  ).toBeInTheDocument();
  cleanup();

  request.mockRejectedValueOnce(new ApiError(404));
  renderWithAuth(<IdentityLineage identityId="nope" />);
  expect(
    await screen.findByText("This botanical identity was not found."),
  ).toBeInTheDocument();
  cleanup();

  request
    .mockRejectedValueOnce(new ApiError(500))
    .mockResolvedValueOnce(graph());
  renderWithAuth(<IdentityLineage identityId="basil" />);
  await userEvent.click(
    await screen.findByRole("button", { name: "Retry lineage" }),
  );
  expect(
    await screen.findByRole("heading", { name: "Ocimum basilicum" }),
  ).toBeInTheDocument();
});

test("lineage home searches identities and lineage records and links to their views", async () => {
  request.mockResolvedValue({
    query: "basil",
    total: 2,
    offset: 0,
    limit: 8,
    groups: [
      {
        kind: "plant",
        total: 1,
        items: [
          {
            kind: "plant",
            id: "p1",
            title: "Windowsill basil",
            context: "Ocimum basilicum",
            href: "#/plants/p1",
          },
        ],
      },
      {
        kind: "botanical_identity",
        total: 1,
        items: [
          {
            kind: "botanical_identity",
            id: "basil",
            title: "Ocimum basilicum",
            context: "Basil",
            href: "#/identities/basil",
          },
        ],
      },
      { kind: "seed_lot", total: 0, items: [] },
    ],
  });
  renderWithAuth(<LineageHome />);
  expect(screen.getByText("Type at least two characters.")).toBeInTheDocument();
  await userEvent.type(
    screen.getByLabelText("Find an identity or record"),
    "basil",
  );
  expect(
    await screen.findByRole("link", { name: "Ocimum basilicum" }),
  ).toHaveAttribute("href", "#/lineage/identity/basil");
  expect(
    screen.getByRole("link", { name: "Windowsill basil" }),
  ).toHaveAttribute("href", "#/lineage/plant/p1");
  expect(
    screen.queryByRole("heading", { name: "Seed lot records" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent),
  ).toEqual(["Botanical identities", "Plant records"]);
  const [path] = request.mock.calls[request.mock.calls.length - 1];
  expect(path).toBe(
    "/api/v1/search?q=basil&limit=8&kind=botanical_identity&kind=plant&kind=plant_group&kind=seed_lot&kind=sowing",
  );
});
