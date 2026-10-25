import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import { Breadcrumbs } from "./Breadcrumbs";
import { workspaceBreadcrumbs } from "./breadcrumbPaths";
afterEach(cleanup);
test.each([
  ["Seeds", "Collection", "#/seeds?q=keep"],
  ["Sowings", "Collection", "#/sowings"],
  ["Plants", "Collection", "#/plants?type=group"],
  ["Harvests", "Collection", "#/harvests"],
  ["Locations", "Collection", "#/locations"],
  ["Journal", "Activity", "#/events"],
  ["History", "Activity", "#/history"],
  ["Schedule", "Activity", "#/schedule"],
  ["Botanical identities", "Explore", "#/identities"],
  ["Taxonomy", "Explore", "#/taxonomy"],
  ["Media", "Explore", "#/media"],
  ["Suppliers", "Sourcing", "#/suppliers"],
  ["Orders", "Sourcing", "#/orders"],
  ["Settings", "Application", "#/settings"],
  ["Labels", "Tools", "#/labels"],
  ["Import / Export", "Tools", "#/import-export"],
])(
  "%s uses a group and current page without an invented group link",
  (title, group, hash) => {
    const items = workspaceBreadcrumbs(title, group, hash);
    if (!items) throw new Error("Expected workspace breadcrumb");
    render(<Breadcrumbs items={items} />);
    const nav = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(within(nav).queryAllByRole("link")).toHaveLength(0);
    expect(
      within(nav)
        .getAllByRole("listitem")
        .map((i) => i.textContent),
    ).toEqual([group, title]);
    expect(within(nav).getAllByRole("listitem")[1]).toHaveAttribute(
      "aria-current",
      "page",
    );
  },
);
test("Dashboard, record and create tasks own their hierarchy rather than duplicating a workspace path", () => {
  expect(
    workspaceBreadcrumbs("Dashboard", "Overview", "#/dashboard"),
  ).toBeNull();
  expect(
    workspaceBreadcrumbs("Seeds", "Collection", "#/seeds/exact-id?tab=photos"),
  ).toBeNull();
  expect(
    workspaceBreadcrumbs("Seeds", "Collection", "#/seeds?action=create"),
  ).toBeNull();
});
test("detail group labels do not pretend Dashboard is their landing and exact parent URLs stay unchanged", () => {
  render(
    <Breadcrumbs
      items={[
        { label: "Collection", href: "#/dashboard" },
        { label: "Seeds", href: "#/seeds?q=retained&scope=historical" },
        { label: "Original packet" },
      ]}
    />,
  );
  expect(
    screen.queryByRole("link", { name: "Collection" }),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Seeds" })).toHaveAttribute(
    "href",
    "#/seeds?q=retained&scope=historical",
  );
});
test("the existing identity detail breadcrumb gains its actual Explore group without changing exact links", () => {
  render(
    <Breadcrumbs
      items={[
        { label: "Botanical identities", href: "#/identities?q=Ocimum" },
        { label: "Ocimum basilicum" },
      ]}
    />,
  );
  expect(
    screen.getByRole("navigation", { name: "Breadcrumb" }),
  ).toHaveTextContent("ExploreBotanical identitiesOcimum basilicum");
  expect(screen.getByRole("link")).toHaveAttribute(
    "href",
    "#/identities?q=Ocimum",
  );
});
