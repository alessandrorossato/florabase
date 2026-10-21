import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { NativeCoverageMap } from "./NativeCoverageMap";
import { coverageScale } from "./coverageScale";
import { comparisonPalette, reconcileColors } from "./comparison";
import type { RangeIdentity } from "./api";
import geometry from "./data/world-110m.json";
vi.mock("../auth/context", () => ({
  useAuth: () => ({ sessionExpired: vi.fn() }),
}));
const identities: RangeIdentity[] = Array.from({ length: 5 }, (_, index) => ({
  id: `species-${String(index)}`,
  display_label: `Species ${String(index + 1)}`,
  scientific_name: `Species ${String(index + 1)}`,
  cultivar_name: null,
  common_name: null,
  representation: "living",
  retained_records: 2,
  current_records: 2,
  living_records: 2,
  matches_scope: true,
  matches_filters: true,
  native_range_count: 2,
}));
const territories = [
  {
    id: "br",
    name: "Brazil",
    source_code: "BR",
    identity_count: 3,
    identity_ids: identities.slice(0, 3).map((identity) => identity.id),
  },
  {
    id: "ar",
    name: "Argentina",
    source_code: "AR",
    identity_count: 2,
    identity_ids: identities.slice(0, 2).map((identity) => identity.id),
  },
  {
    id: "va",
    name: "Vatican City",
    source_code: "VA",
    identity_count: 1,
    identity_ids: [identities[0].id],
  },
];
afterEach(cleanup);
function show(count?: number) {
  return render(
    <div className="native-ranges">
      <NativeCoverageMap
        territories={
          count
            ? territories.map((unit) => ({
                ...unit,
                identity_count: count,
                identity_ids: identities
                  .slice(0, count)
                  .map((identity) => identity.id),
              }))
            : territories
        }
        geometry={{ status: "ready", data: geometry }}
        retry={vi.fn()}
        identities={identities.slice(0, count ?? 3)}
        colors={
          count
            ? reconcileColors(
                identities.slice(0, count).map((identity) => identity.id),
                {},
              )
            : undefined
        }
        contributors={{
          br: ["Species 1", "Species 2", "Species 3"],
          ar: ["Species 1", "Species 2"],
        }}
      />
    </div>,
  );
}

test("map and textual chooser toggle multiple territories independently, union deduplicates and clear restores focus", async () => {
  const user = userEvent.setup();
  const fetch = vi.spyOn(globalThis, "fetch");
  show();
  const map = screen.getByRole("group", { name: /coverage map/ });
  const inspector = screen.getByRole("complementary");
  const brazil = within(map).getByRole("button", { name: /Brazil/ });
  await user.click(brazil);
  expect(screen.getByRole("status")).toHaveTextContent(
    "3 distinct Botanical Identities",
  );
  await user.click(
    within(inspector).getByRole("button", { name: /Argentina\s*2 identities/ }),
  );
  expect(brazil).toHaveAttribute("aria-pressed", "true");
  expect(
    within(map).getByRole("button", { name: /Argentina/ }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("status")).toHaveTextContent(
    "3 distinct Botanical Identities",
  );
  expect(within(inspector).getAllByRole("link")).toHaveLength(3);
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Match territories" }),
    "all",
  );
  expect(screen.getByRole("status")).toHaveTextContent(
    "2 distinct Botanical Identities",
  );
  await user.click(
    screen.getByRole("button", { name: "Remove territory Argentina" }),
  );
  expect(brazil).toHaveAttribute("aria-pressed", "true");
  await user.click(screen.getByRole("button", { name: "Clear territories" }));
  expect(brazil).toHaveFocus();
  expect(brazil).toHaveAttribute("aria-pressed", "false");
  expect(fetch).not.toHaveBeenCalled();
  fetch.mockRestore();
});

test("roving keys toggle selection without modifier keys and preview never replaces committed territories", async () => {
  const user = userEvent.setup();
  show();
  const map = screen.getByRole("group", { name: /coverage map/ });
  const brazil = within(map).getByRole("button", { name: /Brazil/ });
  const argentina = within(map).getByRole("button", { name: /Argentina/ });
  expect(brazil).toHaveAttribute("tabindex", "0");
  expect(argentina).toHaveAttribute("tabindex", "-1");
  brazil.focus();
  await user.keyboard("{Enter}{ArrowRight} ");
  expect(argentina).toHaveFocus();
  expect(brazil).toHaveAttribute("aria-pressed", "true");
  expect(argentina).toHaveAttribute("aria-pressed", "true");
  await user.keyboard("{Home}{Enter}");
  expect(brazil).toHaveAttribute("aria-pressed", "false");
  await user.hover(brazil);
  expect(screen.getByRole("tooltip")).toHaveTextContent(
    "Brazil3 selected species",
  );
  expect(argentina).toHaveAttribute("aria-pressed", "true");
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  expect(brazil).toHaveFocus();
});

test.each([1, 2, 3, 5])(
  "%i contributors use exact palette members in solid or striped fills, never last layer wins",
  (count) => {
    const { container } = show(count);
    const fill = within(
      screen.getByRole("group", { name: /coverage map/ }),
    ).getByRole("button", { name: /Brazil/ });
    const legend = screen.getByRole("list", {
      name: "Comparison species and colors",
    });
    expect(within(legend).getAllByRole("listitem")).toHaveLength(count);
    if (count === 1) {
      expect(fill).toHaveAttribute("fill", comparisonPalette[0]);
      expect(container.querySelector("pattern")).toBeNull();
    } else {
      expect(fill.getAttribute("fill")).toMatch(/^url\(#.+-overlap-BR\)$/);
      const stripes = container
        .querySelector("pattern")
        ?.querySelectorAll("rect");
      expect(stripes).toHaveLength(count);
      expect(
        Array.from(stripes ?? []).map((rect) => rect.getAttribute("fill")),
      ).toEqual(comparisonPalette.slice(0, count));
      expect(screen.getByText(/Stripes combine/)).toBeVisible();
    }
  },
);

test("color reconciliation preserves surviving layers and reuses only freed colors", () => {
  const first = reconcileColors(["a", "b", "c"], {});
  const second = reconcileColors(["a", "c", "d"], first);
  expect(second.a).toBe(first.a);
  expect(second.c).toBe(first.c);
  expect(second.d).toBe(first.b);
  expect(
    new Set(Object.values(reconcileColors(["a", "b", "c", "d", "e"], {}))).size,
  ).toBe(5);
});

test("selected outlines remain inert and inward clipped above fixed boundaries", async () => {
  const user = userEvent.setup();
  const { container } = show(3);
  const map = screen.getByRole("group", { name: /coverage map/ });
  await user.click(within(map).getByRole("button", { name: /Brazil/ }));
  await user.click(within(map).getByRole("button", { name: /Argentina/ }));
  const fills = container.querySelector(".native-coverage-layer");
  const borders = container.querySelector(".native-boundary-layer");
  const emphasis = container.querySelector(".native-emphasis-layer");
  if (!fills || !borders || !emphasis)
    throw new Error("Missing rendering layer");
  expect(
    fills.compareDocumentPosition(borders) & Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
  expect(
    borders.compareDocumentPosition(emphasis) &
      Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
  expect(emphasis).toHaveAttribute("pointer-events", "none");
  expect(emphasis).toHaveAttribute("aria-hidden", "true");
  expect(emphasis.querySelectorAll(".native-selected-outline")).toHaveLength(2);
  expect(
    emphasis
      .querySelector(".native-selected-outline")
      ?.parentElement?.getAttribute("clip-path"),
  ).toMatch(/^url\(#.+-clip-BR\)$/);
  expect(container.querySelector("clipPath path")).toHaveAttribute(
    "d",
    geometry.units.BR,
  );
  expect(within(map).getAllByRole("button")).toHaveLength(2);
});

test("unsupported territory remains selectable textually and limits stay accessible without false absence", async () => {
  const user = userEvent.setup();
  show();
  const map = screen.getByRole("group", { name: /coverage map/ });
  expect(
    within(map).queryByRole("button", { name: /Vatican/ }),
  ).not.toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: /Vatican City.*1 identity/ }),
  );
  expect(
    screen.getByRole("button", { name: "Remove territory Vatican City" }),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: /About this map/ }));
  expect(screen.getByRole("dialog")).toHaveTextContent(
    "Map boundary unavailable · 1 territories",
  );
  expect(screen.getByRole("dialog")).toHaveTextContent(
    "Custom places never inherit",
  );
});

test("integer overview bins cover each count exactly once", () => {
  expect(coverageScale(0)).toEqual([]);
  expect(coverageScale(1).map((bin) => bin.label)).toEqual(["1"]);
  for (const maximum of [2, 3, 7, 20, 250, 1001])
    for (let count = 1; count <= maximum; count++)
      expect(
        coverageScale(maximum).filter(
          (bin) => bin.from <= count && count <= bin.to,
        ),
      ).toHaveLength(1);
});

test("a retained territory with no coverage stays neutral and removable after scope changes", () => {
  const state = { codes: ["BR"], onChange: vi.fn() };
  render(
    <NativeCoverageMap
      territories={[]}
      geometry={{ status: "ready", data: geometry }}
      retry={vi.fn()}
      territorySelection={state}
    />,
  );
  const brazil = within(
    screen.getByRole("group", { name: /coverage map/ }),
  ).getByRole("button", { name: "Brazil · 0 identities" });
  expect(brazil).toHaveAttribute("aria-pressed", "true");
  expect(brazil).toHaveAttribute("fill", "var(--native-land)");
  expect(
    screen.getByRole("button", { name: "Remove territory Brazil" }),
  ).toBeVisible();
  expect(screen.getByRole("status")).toHaveTextContent(
    "0 distinct Botanical Identities",
  );
  expect(screen.getByText(/Unshaded means no mapped coverage/)).toBeVisible();
});

test("map/inspector controls keep both panels mounted, focus and chosen territories", async () => {
  const user = userEvent.setup();
  const { container } = show(2);
  const map = screen.getByRole("group", { name: /coverage map/ });
  await user.click(within(map).getByRole("button", { name: /Brazil/ }));
  const inspectorButton = screen.getByRole("button", {
    name: "Show territory inspector (1)",
  });
  await user.click(inspectorButton);
  expect(inspectorButton).toHaveFocus();
  expect(inspectorButton).toHaveAttribute("aria-pressed", "true");
  expect(container.querySelector(".native-spatial-workspace")).toHaveAttribute(
    "data-mobile-pane",
    "inspector",
  );
  expect(
    screen.getByRole("button", { name: "Remove territory Brazil" }),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Show map" }));
  expect(within(map).getByRole("button", { name: /Brazil/ })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});
