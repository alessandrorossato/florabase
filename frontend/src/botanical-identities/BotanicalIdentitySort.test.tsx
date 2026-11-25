import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { acquireTestAuth } from "../test/auth";
import { BotanicalIdentityScreen } from "./BotanicalIdentityScreen";

let auth: AuthContextValue;

function json(value: unknown) {
  return new Response(JSON.stringify(value), {
    headers: { "Content-Type": "application/json" },
  });
}

function makeIdentity(n: number) {
  const padded = String(n).padStart(2, "0");
  return {
    id: `01900000-0000-7000-8000-0000000007${padded}`,
    scientific_name: `Species ${padded}`,
    cultivar_name: null,
    common_name: null,
    display_label: `Species ${padded}`,
    synonyms: [],
    collection_counts: {
      seed_lots: 0,
      sowings: 0,
      plants: 0,
      plant_groups: 0,
    },
    created_at: "2026-10-01T00:00:00Z",
    updated_at: "2026-10-01T00:00:00Z",
  };
}

beforeEach(async () => {
  auth = (
    await acquireTestAuth({
      session: {
        user_id: "01900000-0000-7000-8000-000000000001",
        display_name: "Owner",
        canonical_origin: "http://localhost:15174",
      },
      csrfToken: "csrf",
    })
  ).auth;
  window.history.replaceState(null, "", "#/identities");
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.location.hash = "";
});

test("Botanical identities directory sorts by name before pagination and round-trips URL state (UX-SORT-001)", async () => {
  const items = [
    makeIdentity(7),
    ...Array.from({ length: 25 }, (_, i) => i + 1)
      .filter((n) => n !== 7)
      .map(makeIdentity),
  ];
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.href
          : input.url;
    if (url.includes("/api/v1/saved-views")) return Promise.resolve(json([]));
    return Promise.resolve(json(items));
  });

  const user = userEvent.setup();
  const { unmount } = render(
    <AuthContext.Provider value={auth}>
      <BotanicalIdentityScreen />
    </AuthContext.Provider>,
  );

  const first = () =>
    within(
      screen.getByRole("list", { name: "Botanical identities" }),
    ).getAllByRole("listitem")[0];

  await screen.findByRole("list", { name: "Botanical identities" });
  expect(first()).toHaveTextContent("Species 07");

  const sort = screen.getByRole("combobox", { name: "Sort by" });
  expect(
    within(sort)
      .getAllByRole("option")
      .map((option) => option.textContent),
  ).toEqual(["Default order", "Name A–Z", "Name Z–A"]);

  await user.selectOptions(sort, "name_desc");
  expect(window.location.hash).toContain("sort=name_desc");
  expect(first()).toHaveTextContent("Species 25");

  await user.click(screen.getByRole("button", { name: "Next page" }));
  expect(first()).toHaveTextContent("Species 05");

  await user.selectOptions(sort, "name");
  expect(window.location.hash).toContain("sort=name");
  expect(first()).toHaveTextContent("Species 01");

  // URL round-trip: re-mounting from #/identities?sort=name_desc restores order.
  unmount();
  window.history.replaceState(null, "", "#/identities?sort=name_desc");
  render(
    <AuthContext.Provider value={auth}>
      <BotanicalIdentityScreen />
    </AuthContext.Provider>,
  );
  await screen.findByRole("list", { name: "Botanical identities" });
  expect(screen.getByRole("combobox", { name: "Sort by" })).toHaveValue(
    "name_desc",
  );
  expect(first()).toHaveTextContent("Species 25");
});
