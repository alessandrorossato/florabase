import type { ComponentProps } from "react";
import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ApiError, AuthRequestLockedError } from "../auth/api";
import {
  AuthContext,
  type AuthContextValue,
  type AuthState,
} from "../auth/context";
import { acquireTestAuth } from "../test/auth";
import { IdentityMaps } from "./IdentityMaps";
import { listBotanicalNativeRanges } from "../botanical-profiles/api";
import { getExternalTaxonLink, type BotanicalIdentityResponse } from "./api";

import { getCollectionProvenanceMap } from "../provenance-map/api";
import { getCachedOccurrenceEvidence } from "../occurrence-map/api";
let authenticatedState: AuthState;
let baseAuth: AuthContextValue;
const sessionExpired = vi.fn();
function buildAuth(state: AuthState = authenticatedState): AuthContextValue {
  return { ...baseAuth, state, sessionExpired };
}
function mapsElement(
  props: ComponentProps<typeof IdentityMaps>,
  state: AuthState = authenticatedState,
) {
  return (
    <AuthContext.Provider value={buildAuth(state)}>
      <IdentityMaps {...props} />
    </AuthContext.Provider>
  );
}
vi.mock("../botanical-profiles/api", () => ({
  listBotanicalNativeRanges: vi.fn(),
}));
vi.mock("../provenance-map/api", () => ({
  getCollectionProvenanceMap: vi.fn(() => Promise.resolve({ sites: [] })),
}));
vi.mock("../occurrence-map/api", () => ({
  getCachedOccurrenceEvidence: vi.fn(),
}));
vi.mock("./api", () => ({ getExternalTaxonLink: vi.fn() }));
vi.mock("./IdentityNativeRange", () => ({
  IdentityNativeRange: () => <p>Native view mounted</p>,
}));
vi.mock("./IdentityOrigins", () => ({
  IdentityOrigins: () => <p>Origin view mounted</p>,
}));
vi.mock("./ExternalBotanicalDataPanel", () => ({
  ExternalBotanicalDataPanel: () => <p>Occurrence view mounted</p>,
}));
const identity = {
  id: "identity",
  scientific_name: "Salvia officinalis",
} as BotanicalIdentityResponse;
beforeEach(async () => {
  const acquired = await acquireTestAuth({ csrfToken: "csrf" });
  baseAuth = acquired.auth;
  authenticatedState = acquired.auth.state;
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
test("Maps reads local availability but mounts only the explicitly selected evidence type", async () => {
  vi.mocked(listBotanicalNativeRanges).mockResolvedValue([]);
  vi.mocked(getExternalTaxonLink).mockResolvedValue(null);
  const edit = vi.fn();
  const user = userEvent.setup();
  render(mapsElement({ identity, csrfToken: "csrf", onEditRange: edit }));
  expect(
    await screen.findByText("0 structured entries recorded"),
  ).toBeVisible();
  expect(screen.getByText("No confirmed GBIF reference")).toBeVisible();
  expect(screen.queryByText(/view mounted/)).toBeNull();
  expect(
    screen.getByText("0 mapped sites · 0 direct record links"),
  ).toBeVisible();
  expect(getCachedOccurrenceEvidence).not.toHaveBeenCalled();
  expect(
    screen.getByRole("link", { name: "Open native ranges for this identity" }),
  ).toHaveAttribute("href", "#/native-ranges?mode=species&identity=identity");
  expect(
    screen.getByRole("link", {
      name: "Open occurrence evidence for this identity",
    }),
  ).toHaveAttribute("href", "#/species-distribution?identity=identity");
  expect(
    screen.getByRole("link", {
      name: "Open collection origins · all identities",
    }),
  ).toHaveAttribute("href", "#/map");
  await user.click(
    screen.getByRole("button", { name: "Inspect native range" }),
  );
  expect(await screen.findByText("Native view mounted")).toBeVisible();
  const inspection = screen.getByRole("region", {
    name: "Native range inspection",
  });
  await waitFor(() => {
    expect(
      within(inspection).getByRole("heading", { name: "Native range" }),
    ).toHaveFocus();
  });
  await user.click(screen.getByRole("button", { name: "Close inspection" }));
  expect(
    screen.getByRole("button", { name: "Inspect native range" }),
  ).toHaveFocus();
  expect(screen.queryByText("Native view mounted")).toBeNull();
  await user.click(
    screen.getByRole("button", { name: "Inspect occurrence evidence" }),
  );
  expect(await screen.findByText("Occurrence view mounted")).toBeVisible();
  expect(screen.queryByText("Native view mounted")).toBeNull();
  await user.click(
    screen.getByRole("button", { name: "Inspect collection origins" }),
  );
  expect(await screen.findByText("Origin view mounted")).toBeVisible();
  expect(screen.queryByText("Occurrence view mounted")).toBeNull();
  await user.click(
    screen.getByRole("button", { name: "Close collection origins" }),
  );
  expect(screen.queryByText(/view mounted/)).toBeNull();
  await user.click(screen.getByRole("button", { name: "Edit native range" }));
  expect(edit).toHaveBeenCalledOnce();
});
test("unknown availability remains an error and can be retried without falsely reporting absence", async () => {
  vi.mocked(listBotanicalNativeRanges).mockRejectedValue(new Error("offline"));
  vi.mocked(getExternalTaxonLink).mockResolvedValue(null);
  const user = userEvent.setup();
  render(mapsElement({ identity, csrfToken: "csrf", onEditRange: vi.fn() }));
  expect(await screen.findByRole("alert")).toHaveTextContent("unavailable");
  expect(screen.queryByText("0 structured entries recorded")).toBeNull();
  vi.mocked(listBotanicalNativeRanges).mockResolvedValue([]);
  await user.click(
    screen.getByRole("button", { name: "Retry geographic summary" }),
  );
  expect(
    await screen.findByText("0 structured entries recorded"),
  ).toBeVisible();
  expect(screen.queryByRole("alert")).toBeNull();
});

test("summary uses only saved occurrence evidence and exact direct provenance membership", async () => {
  vi.mocked(listBotanicalNativeRanges).mockResolvedValue([]);
  vi.mocked(getExternalTaxonLink).mockResolvedValue({
    provider_display_name: "GBIF",
    scientific_name: "Salvia officinalis",
    stale: false,
  } as never);
  vi.mocked(getCachedOccurrenceEvidence).mockResolvedValue({
    stale: true,
    summary: { eligible_mapped_records: 123 },
  } as never);
  vi.mocked(getCollectionProvenanceMap).mockResolvedValue({
    sites: [
      {
        id: "site",
        records: [
          { botanical_identity: { id: "identity" }, record_type: "plant" },
          { botanical_identity: { id: "unrelated" }, record_type: "seed_lot" },
        ],
      },
    ],
  } as never);
  render(mapsElement({ identity, csrfToken: "csrf", onEditRange: vi.fn() }));
  expect(
    await screen.findByText(
      "123 eligible mapped observations · cache needs review",
    ),
  ).toBeVisible();
  expect(
    screen.getByText("1 mapped site · 1 direct record links"),
  ).toBeVisible();
  expect(getCachedOccurrenceEvidence).toHaveBeenCalledWith(
    "identity",
    baseAuth.capability,
    expect.any(AbortSignal),
  );
  expect(screen.queryByText(/view mounted/)).toBeNull();
});

test("session recovery suspends summary loads, preserves valid availability without false unavailability, and refreshes on restore", async () => {
  vi.mocked(listBotanicalNativeRanges).mockResolvedValue([]);
  vi.mocked(getExternalTaxonLink).mockResolvedValue({
    provider_display_name: "GBIF",
    scientific_name: "Salvia officinalis",
    stale: false,
  } as never);
  vi.mocked(getCachedOccurrenceEvidence).mockResolvedValue({
    stale: false,
    summary: { eligible_mapped_records: 42 },
  } as never);
  vi.mocked(getCollectionProvenanceMap).mockResolvedValue({
    sites: [],
    coordinate_less_sites: 0,
    total_provenance_sites: 0,
  });

  const view = render(
    mapsElement({ identity, csrfToken: "csrf", onEditRange: vi.fn() }),
  );

  expect(
    await screen.findByText("0 structured entries recorded"),
  ).toBeVisible();
  expect(
    screen.getByText("42 eligible mapped observations · saved evidence"),
  ).toBeVisible();

  const callsBeforeLock = vi.mocked(listBotanicalNativeRanges).mock.calls
    .length;

  // Enter locked recovery state: effect must suspend without calling protected reads or clobbering valid summary.
  const lockedState: AuthState = {
    status: "unauthenticated",
    retainedIdentity: {
      user_id: "owner",
      login_name: "owner",
      display_name: "Owner",
    },
    message: "Your session expired.",
  };
  view.rerender(
    mapsElement({ identity, csrfToken: "", onEditRange: vi.fn() }, lockedState),
  );
  await Promise.resolve();
  expect(vi.mocked(listBotanicalNativeRanges).mock.calls.length).toBe(
    callsBeforeLock,
  );
  expect(screen.getByText("0 structured entries recorded")).toBeVisible();
  expect(
    screen.getByText("42 eligible mapped observations · saved evidence"),
  ).toBeVisible();
  expect(screen.queryByRole("alert")).toBeNull();

  // Even if an active call rejects locally with AuthRequestLockedError or ApiError(401), valid summary stays preserved.
  vi.mocked(listBotanicalNativeRanges).mockRejectedValueOnce(
    new AuthRequestLockedError(),
  );
  view.rerender(
    mapsElement({ identity, csrfToken: "csrf-2", onEditRange: vi.fn() }),
  );
  await waitFor(() => {
    expect(vi.mocked(listBotanicalNativeRanges).mock.calls.length).toBe(
      callsBeforeLock + 1,
    );
  });
  expect(screen.getByText("0 structured entries recorded")).toBeVisible();
  expect(screen.queryByRole("alert")).toBeNull();

  // Explicit 401 calls sessionExpired() without clobbering previously valid summary, then unlock refreshes to 1 entry.
  vi.mocked(listBotanicalNativeRanges)
    .mockRejectedValueOnce(new ApiError(401))
    .mockResolvedValueOnce([{ id: "r1" }] as never);
  view.rerender(
    mapsElement({ identity, csrfToken: "", onEditRange: vi.fn() }, lockedState),
  );
  view.rerender(
    mapsElement({ identity, csrfToken: "csrf-3", onEditRange: vi.fn() }),
  );
  await waitFor(() => {
    expect(sessionExpired).toHaveBeenCalledTimes(1);
  });
  expect(screen.getByText("0 structured entries recorded")).toBeVisible();
  expect(screen.queryByRole("alert")).toBeNull();

  // After reauth cycle completes cleanly, fresh data loads.
  view.rerender(
    mapsElement({ identity, csrfToken: "", onEditRange: vi.fn() }, lockedState),
  );
  view.rerender(
    mapsElement({ identity, csrfToken: "csrf-4", onEditRange: vi.fn() }),
  );
  expect(await screen.findByText("1 structured entry recorded")).toBeVisible();
  expect(screen.queryByRole("alert")).toBeNull();
});
