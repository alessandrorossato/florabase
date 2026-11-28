import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import {
  DetailHeader,
  DetailLoading,
  DetailPage,
  DetailSummary,
  DetailTabs,
  SpecimenPlate,
  WorkspaceIntro,
} from "./CollectionUI";
import { RecordVisual } from "../photos/RecordVisual";
import { OverflowMenu } from "./ReferenceUI";

afterEach(cleanup);

test("a directory heading is declared by the page before any content loads", () => {
  render(
    <WorkspaceIntro
      directory
      eyebrow="Collection"
      title="Seeds"
      titleId="seeds-title"
      description="Your seeds."
    />,
  );
  expect(
    screen.getByRole("heading", { name: "Seeds" }).closest(".page-header"),
  ).toHaveClass("page-header--directory");
});

test("other page headings keep their own presentation", () => {
  render(
    <WorkspaceIntro
      eyebrow="Collection"
      title="Journal"
      titleId="journal-title"
      description="Activity."
    />,
  );
  expect(
    screen.getByRole("heading", { name: "Journal" }).closest(".page-header"),
  ).not.toHaveClass("page-header--directory");
});

test("Details loading keeps the page structure without inventing a record", () => {
  render(
    <DetailLoading
      eyebrow="Supplier"
      label="Loading supplier…"
      parents={[{ label: "Suppliers", href: "#/suppliers" }]}
      className="collection-detail ui-detail-page supplier-detail"
    />,
  );
  expect(screen.getByRole("status")).toHaveTextContent("Loading supplier…");
  expect(screen.getByRole("link", { name: "Suppliers" })).toHaveAttribute(
    "href",
    "#/suppliers",
  );
  expect(screen.getByText("Loading").closest("li")).toHaveAttribute(
    "aria-current",
    "page",
  );
  expect(screen.queryByRole("heading")).not.toBeInTheDocument();
  expect(screen.queryByRole("group")).not.toBeInTheDocument();
});

test("shared Details preserves formatted names, heading focus and domain sections", () => {
  const ref = { current: null as HTMLHeadingElement | null };
  render(
    <DetailPage aria-label="Botanical record">
      <DetailHeader
        eyebrow="Botanical identity"
        title={
          <>
            <i>Acer palmatum</i> ‘Bloodgood’
          </>
        }
        headingLevel={2}
        titleId="record-title"
        headingRef={ref}
        visual={<span>Cover</span>}
      />
      <section aria-label="Taxonomic evidence">Reference codes</section>
    </DetailPage>,
  );
  const heading = screen.getByRole("heading", { level: 2 });
  expect(heading).toHaveTextContent("Acer palmatum ‘Bloodgood’");
  expect(heading.querySelector("i")).toHaveTextContent("Acer palmatum");
  ref.current?.focus();
  expect(heading).toHaveFocus();
  expect(
    screen.getByRole("article", { name: "Botanical record" }),
  ).toContainElement(
    screen.getByRole("region", { name: "Taxonomic evidence" }),
  );
});

test("Details groups the primary, daily secondary, Edit and rare menu actions", async () => {
  const edit = vi.fn();
  render(
    <DetailHeader
      eyebrow="Plant"
      title="Specimen"
      primaryActions={<button>Record harvest</button>}
      secondaryActions={<button className="button--secondary">Transfer</button>}
      onEdit={edit}
      overflow={
        <OverflowMenu ariaLabel="More record actions">
          <a href="#/labels">Print label</a>
        </OverflowMenu>
      }
    />,
  );
  const bar = screen.getByRole("group", { name: "Record actions" });
  expect(
    within(bar)
      .getAllByRole("button")
      .map((button) => button.textContent),
  ).toEqual(["Record harvest", "Transfer", "Edit", "More"]);
  expect(within(bar).getByRole("button", { name: "Transfer" })).toHaveClass(
    "button--secondary",
  );
  const user = userEvent.setup();
  await user.click(within(bar).getByRole("button", { name: "Edit" }));
  expect(edit).toHaveBeenCalledTimes(1);
  expect(
    screen.queryByRole("link", { name: "Print label" }),
  ).not.toBeInTheDocument();
  await user.click(
    within(bar).getByRole("button", { name: "More record actions" }),
  );
  expect(screen.getByRole("link", { name: "Print label" })).toHaveAttribute(
    "href",
    "#/labels",
  );
});

test("metric summaries omit absent values but keep meaningful zero", () => {
  render(
    <DetailSummary
      id="summary-title"
      label="Record state"
      metrics={[
        { label: "Children", value: 0 },
        { label: "Storage", value: "Shelf 3", wide: true },
        { label: "Missing", value: null },
        { label: "Blank", value: "" },
      ]}
      note={<p>Exact values only.</p>}
    />,
  );
  expect(screen.getByRole("region", { name: "At a glance" })).toBeVisible();
  const list = screen.getByLabelText("Record state");
  expect(within(list).getByText("Children")).toBeVisible();
  expect(within(list).getByText("0")).toBeVisible();
  expect(within(list).queryByText("Missing")).not.toBeInTheDocument();
  expect(within(list).queryByText("Blank")).not.toBeInTheDocument();
  expect(list.style.getPropertyValue("--detail-summary-columns")).toBe("3");
  expect(screen.getByText("Exact values only.")).toBeVisible();
});

test("a summary with nothing to report renders nothing", () => {
  const { container } = render(
    <DetailSummary
      id="summary-title"
      label="Record state"
      metrics={[{ label: "Missing", value: undefined }]}
    />,
  );
  expect(container).toBeEmptyDOMElement();
});

test("Details loading uses the canonical record shell", () => {
  const { container } = render(
    <DetailLoading
      eyebrow="Harvest"
      label="Loading Harvest detail…"
      parents={[{ label: "Harvests", href: "#/harvests" }]}
    />,
  );
  expect(container.firstElementChild).toHaveClass(
    "ui-detail-page",
    "detail-loading",
  );
});

test("UI-POLISH-006 B2: key facts sit under the action bar and unknown values read as unknown", () => {
  render(
    <DetailHeader
      eyebrow="Seed lot"
      title="Basil"
      onEdit={() => undefined}
      keyFacts={[
        { label: "remaining", value: "261 seeds" },
        { label: "sowings", value: "2" },
        { label: "viable until", value: "Not recorded" },
      ]}
      lineage={<p>Lineage</p>}
    />,
  );
  const facts = screen.getByLabelText("Key facts");
  expect(facts).toHaveAccessibleName("Key facts");
  expect(
    within(facts)
      .getAllByRole("term")
      .map((term) => term.textContent),
  ).toEqual(["remaining", "sowings", "viable until"]);
  expect(within(facts).getByText("Not recorded")).toHaveClass(
    "detail-key-facts__unknown",
  );
  // Order: actions, then key facts, then lineage.
  const actions = screen.getByRole("group", { name: "Record actions" });
  expect(
    actions.compareDocumentPosition(facts) & Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
  expect(
    facts.compareDocumentPosition(screen.getByText("Lineage")) &
      Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
});

test("UI-POLISH-006 B2: tab counts are visible badges and the tab keeps its name", async () => {
  const onSelect = vi.fn();
  render(
    <DetailTabs
      tabs={[
        { id: "overview", label: "Overview" },
        { id: "sowings", label: "Sowings", count: 2 },
        { id: "photos", label: "Photos", count: 0 },
        { id: "lineage", label: "Lineage", count: null },
      ]}
      selected="overview"
      onSelect={onSelect}
    />,
  );
  const sowings = screen.getByRole("tab", { name: "Sowings" });
  expect(sowings.querySelector(".detail-tab__count")).toHaveTextContent("2");
  expect(
    screen
      .getByRole("tab", { name: "Photos" })
      .querySelector(".detail-tab__count"),
  ).toHaveTextContent("0");
  expect(
    screen
      .getByRole("tab", { name: "Lineage" })
      .querySelector(".detail-tab__count"),
  ).toBeNull();
  await userEvent.click(sowings);
  expect(onSelect).toHaveBeenCalledWith("sowings");
});

test("UI-POLISH-006 B2: an empty plate offers Add photo, which opens the Photos tab in place", async () => {
  window.history.replaceState(null, "", "#/seeds/lot");
  const before = window.history.length;
  const onSelect = vi.fn();
  render(
    <>
      <SpecimenPlate addPhoto={{ href: "#/seeds/lot?tab=photos", onSelect }}>
        <RecordVisual kind="seed" label="Basil" />
      </SpecimenPlate>
      <button type="button" id="tab-photos" role="tab">
        Photos
      </button>
    </>,
  );
  expect(document.querySelector(".record-visual")).toHaveAttribute(
    "data-empty",
  );
  const add = screen.getByRole("link", { name: "Add photo" });
  expect(add).toHaveAttribute("href", "#/seeds/lot?tab=photos");
  await userEvent.click(add);
  expect(onSelect).toHaveBeenCalledOnce();
  // Like a tab click: the route is replaced, not pushed, and focus lands on the tab.
  expect(window.location.hash).toBe("#/seeds/lot?tab=photos");
  expect(window.history.length).toBe(before);
  await vi.waitFor(() => {
    expect(screen.getByRole("tab", { name: "Photos" })).toHaveFocus();
  });
});
