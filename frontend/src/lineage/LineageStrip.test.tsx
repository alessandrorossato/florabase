import type { ReactElement } from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/context";
import { requestJson } from "../auth/api";
import type { components } from "../api/schema";
import { acquireTestAuth } from "../test/auth";
import { LineageStrip } from "./LineageStrip";

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
type Response = components["schemas"]["LineageResponse"];
const identity = { id: "identity", display_label: "Ocimum basilicum" };
const plantPath: Response = {
  subject: {
    kind: "plant",
    id: "mother",
    label: "Mother plant",
    lifecycle: "active",
    botanical_identity: identity,
  },
  // Nearest first, as the API walks it.
  ancestors: [
    { kind: "sowing", id: "tray", label: "Spring tray", lifecycle: "active" },
    {
      kind: "seed_lot",
      id: "packet",
      label: null,
      lifecycle: "exhausted",
      botanical_identity: identity,
    },
  ],
};

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

test("shows only the recorded upstream path, oldest first, ending at this record", async () => {
  request.mockResolvedValue(plantPath);
  const onFull = vi.fn((event: { preventDefault: () => void }) => {
    event.preventDefault();
  });
  renderWithAuth(
    <LineageStrip
      kind="plants"
      id="mother"
      current="This Plant"
      currentKind="plant"
      fullHref="#/plants/mother?tab=lineage"
      onFull={onFull}
    />,
  );
  const strip = screen.getByRole("navigation", { name: "Recorded lineage" });
  const path = await within(strip).findByRole("list");
  const steps = within(path).getAllByRole("listitem");
  expect(steps.map((step) => step.textContent)).toEqual([
    "Seed lotUnlabelled seed lotexhausted",
    // Each relationship is written as text, named only from the recorded kinds.
    "sown asSowingSpring tray",
    "grown intoThis Plant",
  ]);
  expect(steps[2]).toHaveAttribute("aria-current", "true");
  expect(within(steps[0]).getByRole("link")).toHaveAttribute(
    "href",
    "#/seeds/packet?tab=lineage",
  );
  expect(within(steps[1]).getByRole("link")).toHaveAttribute(
    "href",
    "#/sowings/tray?tab=lineage",
  );
  // The subject itself is not repeated as a link; the header already names it.
  expect(within(path).queryByRole("link", { name: "Mother plant" })).toBeNull();
  expect(request.mock.calls[0]?.[0]).toBe("/api/v1/plants/mother/lineage");
  await userEvent.click(
    within(strip).getByRole("link", { name: "Full lineage" }),
  );
  expect(onFull).toHaveBeenCalledOnce();
});

test("a Sowing reads its recorded Seed lot's path and includes that Seed lot", async () => {
  request.mockResolvedValue({
    subject: {
      kind: "seed_lot",
      id: "packet",
      label: "Basil packet",
      lifecycle: "active",
      botanical_identity: identity,
    },
    ancestors: [],
  } satisfies Response);
  renderWithAuth(
    <LineageStrip
      kind="seed-lots"
      id="packet"
      includeSubject
      current="This Sowing"
    />,
  );
  const items = await screen.findAllByRole("listitem");
  expect(items.map((item) => item.textContent)).toEqual([
    "Seed lotBasil packet",
    "This Sowing",
  ]);
  expect(request.mock.calls[0]?.[0]).toBe("/api/v1/seed-lots/packet/lineage");
  expect(screen.queryByRole("link", { name: "Full lineage" })).toBeNull();
});

test("no recorded source says so instead of implying one from a shared identity", async () => {
  request.mockResolvedValue({ ...plantPath, ancestors: [] });
  renderWithAuth(
    <LineageStrip kind="plants" id="mother" current="This Plant" />,
  );
  expect(await screen.findByText("No recorded source material.")).toBeVisible();
  expect(screen.queryByRole("list")).toBeNull();
});

test("a failed load is stated and can be retried", async () => {
  request.mockRejectedValueOnce(new Error("offline"));
  request.mockResolvedValueOnce(plantPath);
  renderWithAuth(
    <LineageStrip kind="plants" id="mother" current="This Plant" />,
  );
  expect(screen.getByText("Loading recorded lineage…")).toBeVisible();
  await userEvent.click(
    await screen.findByRole("button", { name: "Retry lineage" }),
  );
  expect(
    await screen.findByRole("link", { name: "Spring tray" }),
  ).toBeVisible();
  expect(request).toHaveBeenCalledTimes(2);
});

test("keeps Full lineage pinned on the Lineage tab, shows Harvest verb, and appends compact descendants summary", async () => {
  request.mockImplementation((url: string) => {
    if (url === "/api/v1/seed-lots/lot1/lineage") {
      return Promise.resolve({
        subject: {
          kind: "seed_lot",
          id: "lot1",
          label: "Tomato packet",
          lifecycle: "active",
          botanical_identity: identity,
        },
        ancestors: [],
      } satisfies Response);
    }
    if (url.startsWith("/api/v1/lineage/seed_lot/lot1/children")) {
      return Promise.resolve({
        items: [
          {
            record: {
              kind: "sowing",
              id: "s1",
              label: "Sowing 1",
              lifecycle: "active",
            },
            origin: null,
            harvest_conversion: null,
            descendant_count: 0,
          },
          {
            record: {
              kind: "sowing",
              id: "s2",
              label: "Sowing 2",
              lifecycle: "completed",
            },
            origin: null,
            harvest_conversion: null,
            descendant_count: 0,
          },
        ],
        total: 2,
        offset: 0,
        limit: 25,
      });
    }
    return Promise.resolve(plantPath);
  });

  const view = renderWithAuth(
    <LineageStrip
      kind="seed-lots"
      id="lot1"
      current="This Seed lot"
      currentKind="seed_lot"
      fullHref="#/seeds/lot1?tab=lineage"
      onLineageTab
    />,
  );
  const full = screen.getByRole("link", { name: "Full lineage" });
  expect(full).toHaveAttribute("aria-current", "page");
  expect(
    await screen.findByRole("link", { name: "2 sowings" }),
  ).toHaveAttribute("href", "#/seeds/lot1?tab=lineage");
  view.unmount();

  renderWithAuth(
    <LineageStrip
      kind="plants"
      id="mother"
      includeSubject
      current="This Harvest"
      currentKind="harvest"
      fullHref="#/harvests/h1?tab=lineage"
      descendantsSummary="1 seed lot"
    />,
  );
  const steps = await screen.findAllByRole("listitem");
  expect(steps.at(-2)?.textContent).toContain("harvested as");
  expect(steps.at(-2)?.textContent).toContain("This Harvest");
  expect(steps.at(-1)?.textContent).toContain("1 seed lot");
});
