import type { ReactElement } from "react";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { acquireTestAuth } from "../test/auth";
import { TaxonomyKpis } from "./TaxonomyKpis";
import { sample, ids } from "./graph.fixture";
const state = {
  scope: "all" as const,
  record: [],
  q: "Basil",
  taxon: ids.species,
};
let auth: AuthContextValue;
function renderWithAuth(ui: ReactElement) {
  const result = render(
    <AuthContext.Provider value={auth}>{ui}</AuthContext.Provider>,
  );
  return {
    ...result,
    rerender: (next: ReactElement) => {
      result.rerender(
        <AuthContext.Provider value={auth}>{next}</AuthContext.Provider>,
      );
    },
  };
}
beforeEach(async () => {
  auth = (await acquireTestAuth()).auth;
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
test("KPI popovers inspect exact subsets, toggle/outside/Escape dismiss and retain canonical links", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(() =>
      Promise.resolve(
        new Response(new Blob(["img"], { type: "image/png" }), { status: 200 }),
      ),
    );
  const user = userEvent.setup();
  const rows = [
    sample.identities[0],
    {
      ...sample.identities[1],
      id: "current",
      display_label: "Current only",
      representation: "current" as const,
      current_records: 1,
      living_records: 0,
    },
    sample.identities[1],
  ];
  renderWithAuth(
    <>
      <TaxonomyKpis identities={rows} state={state} />
      <button>Outside</button>
    </>,
  );
  expect(screen.queryByRole("link")).toBeNull();
  const all = screen.getByRole("button", { name: "Identities: 3" });
  await user.click(all);
  expect(
    screen.getAllByRole("link", { name: /Basil|Current only/ }),
  ).toHaveLength(3);
  expect(screen.getByRole("link", { name: "Basil a" })).toHaveAttribute(
    "href",
    expect.stringContaining("taxonomy_return="),
  );
  const cover = await screen.findByRole("img", { name: "Cover of Basil a" });
  expect(cover.getAttribute("src")).toMatch(/^blob:/);
  expect(fetch).toHaveBeenCalledWith(
    sample.identities[0].cover?.thumbnail_url,
    expect.objectContaining({ credentials: "same-origin" }),
  );
  await user.click(all);
  expect(screen.queryByRole("link")).toBeNull();
  await user.click(screen.getByRole("button", { name: "Living: 1" }));
  expect(
    screen.getByRole("group", { name: "Living: 1 menu" }),
  ).toHaveTextContent("Basil a");
  expect(screen.queryByRole("link", { name: "Current only" })).toBeNull();
  await user.click(screen.getByRole("button", { name: "Current: 2" }));
  expect(
    screen.getByRole("group", { name: "Current: 2 menu" }),
  ).toHaveTextContent("Current only");
  expect(screen.queryByRole("group", { name: "Living: 1 menu" })).toBeNull();
  await user.keyboard("{Escape}");
  expect(screen.getByRole("button", { name: "Current: 2" })).toHaveFocus();
  await user.click(screen.getByRole("button", { name: "Historical: 1" }));
  expect(
    screen.getByRole("group", { name: "Historical: 1 menu" }),
  ).toHaveTextContent("Basil b");
  await user.click(screen.getByRole("button", { name: "Outside" }));
  expect(screen.queryByRole("link")).toBeNull();
});
test("empty KPI and bounded identity pagination remain explicit", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(() =>
    Promise.resolve(
      new Response(new Blob(["img"], { type: "image/png" }), { status: 200 }),
    ),
  );
  const user = userEvent.setup();
  const { rerender } = renderWithAuth(
    <TaxonomyKpis identities={[sample.identities[0]]} state={state} />,
  );
  await user.click(screen.getByRole("button", { name: "Historical: 0" }));
  expect(screen.getByText(/No historical identities/)).toBeVisible();
  await user.keyboard("{Escape}");
  const rows = Array.from({ length: 60 }, (_, i) => ({
    ...sample.identities[0],
    id: "row-" + String(i),
    display_label: "Basil " + String(i),
  }));
  rerender(<TaxonomyKpis identities={rows} state={state} />);
  await user.click(screen.getByRole("button", { name: "Identities: 60" }));
  const panel = screen.getByRole("group", { name: "Identities: 60 menu" });
  expect(await within(panel).findAllByRole("img")).toHaveLength(24);
  await user.click(
    screen.getByRole("button", { name: "Show more identities (24 of 60)" }),
  );
  await waitFor(() => {
    expect(within(panel).getAllByRole("img")).toHaveLength(48);
  });
  expect(
    screen.getByRole("group", { name: "Identities: 60 menu" }),
  ).toBeVisible();
  fireEvent.pointerDown(document.body);
  expect(
    screen.queryByRole("group", { name: "Identities: 60 menu" }),
  ).toBeNull();
});
