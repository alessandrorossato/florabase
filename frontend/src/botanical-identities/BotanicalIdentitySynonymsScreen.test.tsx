import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { App } from "../App";
import { createMediaQueryList } from "../test/mediaQuery";
import "./BotanicalIdentityScreen";

const activeIdentity = {
  id: "01900000-0000-7000-8000-000000000701",
  scientific_name: "Trichocereus bridgesii",
  cultivar_name: null,
  common_name: "Bolivian torch",
  display_label: "Trichocereus bridgesii",
  synonyms: ["Echinopsis lageniformis"],
  collection_counts: {
    seed_lots: 1,
    sowings: 0,
    plants: 2,
    plant_groups: 0,
  },
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
};

const otherIdentity = {
  id: "01900000-0000-7000-8000-000000000702",
  scientific_name: "Echinopsis pachanoi",
  cultivar_name: null,
  common_name: "San Pedro",
  display_label: "Echinopsis pachanoi",
  synonyms: [],
  collection_counts: {
    seed_lots: 0,
    sowings: 0,
    plants: 1,
    plant_groups: 0,
  },
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
};

const mergedTombstone = {
  id: "01900000-0000-7000-8000-000000000709",
  scientific_name: "Lycopersicon esculentum",
  cultivar_name: null,
  common_name: "Old tomato",
  display_label: "Lycopersicon esculentum",
  synonyms: [],
  merged_into_id: otherIdentity.id,
  merged_at: "2026-10-05T00:00:00Z",
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-05T00:00:00Z",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function mockIdentityAppFetch(
  custom?: (path: string, init?: RequestInit) => Response | undefined,
) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const path =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    if (custom) {
      const handled = custom(path, init);
      if (handled !== undefined) return Promise.resolve(handled);
    }
    if (path.endsWith("/auth/session"))
      return Promise.resolve(
        json({
          user_id: "user",
          login_name: "owner",
          display_name: "Owner",
          owner: true,
        }),
      );
    if (path.endsWith("/auth/csrf"))
      return Promise.resolve(json({ csrf_token: "csrf-token" }));
    if (path.endsWith("/health"))
      return Promise.resolve(json({ status: "ok" }));
    if (path === "/api/v1/saved-views?surface=botanical_identities")
      return Promise.resolve(json([]));
    if (path === "/api/v1/botanical-identities")
      return Promise.resolve(json([activeIdentity, otherIdentity]));
    if (path === `/api/v1/botanical-identities/${activeIdentity.id}/collection`)
      return Promise.resolve(
        json({
          identity: activeIdentity,
          seed_lots: [],
          sowings: [],
          plants: [],
          plant_groups: [],
          harvests: [],
          events: [],
        }),
      );
    if (path === `/api/v1/botanical-identities/${activeIdentity.id}/profile`)
      return Promise.resolve(
        json({ detail: { code: "botanical_profile_not_found" } }, 404),
      );
    if (
      path ===
      `/api/v1/botanical-identities/${activeIdentity.id}/profile/native-ranges`
    )
      return Promise.resolve(json([]));
    if (
      path ===
      `/api/v1/botanical-identities/${activeIdentity.id}/external-taxon-link`
    )
      return Promise.resolve(json(null));
    if (path === `/api/v1/botanical-identities/${activeIdentity.id}/taxonomy`)
      return Promise.resolve(json(null));
    if (path === "/api/v1/provenance-sites") return Promise.resolve(json([]));
    return Promise.resolve(json({}));
  });
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.localStorage.clear();
  window.history.replaceState(null, "", "#/");
});

test("directory filters by synonyms, preserves URL query and Saved Views state, and opens identity without creating duplicates", async () => {
  const posts: string[] = [];
  mockIdentityAppFetch((path, init) => {
    if (init?.method === "POST" && !path.endsWith("/auth/csrf"))
      posts.push(path);
    return undefined;
  });

  window.history.replaceState(null, "", "#/identities");
  const user = userEvent.setup();
  render(<App />);
  await vi.dynamicImportSettled();

  expect(await screen.findByText("Trichocereus bridgesii")).toBeVisible();
  expect(screen.getByText("Echinopsis pachanoi")).toBeVisible();

  const searchInput = screen.getByLabelText("Search botanical identities");
  await user.type(searchInput, "lageniformis");

  await waitFor(() => {
    expect(screen.queryByText("Echinopsis pachanoi")).toBeNull();
  });
  expect(screen.getByText("Trichocereus bridgesii")).toBeVisible();
  expect(screen.getByText(/Synonym: Echinopsis lageniformis/)).toBeVisible();
  expect(window.location.hash).toContain("q=lageniformis");

  await user.click(
    screen.getByRole("button", {
      name: /^Open details Trichocereus bridgesii/,
    }),
  );

  expect(window.location.hash).toBe(`#/identities/${activeIdentity.id}`);
  expect(
    await screen.findByRole("heading", {
      name: /Trichocereus bridgesii/,
      level: 2,
    }),
  ).toBeVisible();
  expect(screen.getByText(/Synonyms & former names:/)).toBeVisible();
  const breadcrumb = screen.getByRole("navigation", { name: "Breadcrumb" });
  expect(
    within(breadcrumb).getByRole("link", { name: "Botanical identities" }),
  ).toHaveAttribute("href", "#/identities?q=lageniformis");
  expect(posts).toEqual([]);
});

test("restores synonym filter from URL query on narrow viewport and preserves Saved views control", async () => {
  vi.spyOn(window, "matchMedia").mockReturnValue(
    createMediaQueryList("(max-width: 40rem)", true),
  );
  mockIdentityAppFetch();

  window.history.replaceState(null, "", "#/identities?q=lageniformis");
  render(<App />);
  await vi.dynamicImportSettled();

  expect(await screen.findByText("Trichocereus bridgesii")).toBeVisible();
  expect(screen.queryByText("Echinopsis pachanoi")).toBeNull();
  expect(screen.getByText(/Synonym: Echinopsis lageniformis/)).toBeVisible();
  expect(screen.getByRole("button", { name: "Saved views" })).toBeVisible();
});

test("navigating directly to a retired merged tombstone renders merged banner and locks synonym edits", async () => {
  mockIdentityAppFetch((path) => {
    if (path === "/api/v1/botanical-identities") return json([otherIdentity]);
    if (path === `/api/v1/botanical-identities/${mergedTombstone.id}`)
      return json(mergedTombstone);
    if (path === `/api/v1/botanical-identities/${mergedTombstone.id}/taxonomy`)
      return json(null);
    if (
      path ===
      `/api/v1/botanical-identities/${mergedTombstone.id}/reconciliation`
    )
      return json({
        identity: mergedTombstone,
        original_scientific_name: mergedTombstone.scientific_name,
        original_cultivar_name: null,
        original_common_name: "Old tomato",
        original_display_label: "Lycopersicon esculentum",
        former_names: [],
        has_source_conflict: false,
        conflicts: [],
        source_assessments: [],
        suggestions: [],
        reconciliations: [],
      });
    if (
      path ===
      `/api/v1/botanical-identities/${mergedTombstone.id}/external-taxon-link`
    )
      return json(null);
    return undefined;
  });

  window.history.replaceState(
    null,
    "",
    `#/identities/${mergedTombstone.id}?tab=taxonomy`,
  );
  render(<App />);
  await vi.dynamicImportSettled();

  expect(
    await screen.findByText(
      /This botanical identity has been reconciled and merged into/,
    ),
  ).toBeVisible();
  expect(
    await screen.findByText(/retired after duplicate reconciliation/i),
  ).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Add operator synonym" }),
  ).toBeNull();
});

test("adding an operator synonym in the taxonomy tab updates the directory filter without creating a duplicate identity", async () => {
  let directoryIdentities = [activeIdentity, otherIdentity];
  const createdSynonym = {
    id: "syn-e2e-1",
    scientific_name: "Cereus lageniformis",
    cultivar_name: null,
    common_name: "Flask cactus",
    display_label: "Cereus lageniformis",
    authorship: "Salm-Dyck",
    status_kind: "operator_synonym",
    source_provider: "operator",
    source_version: "Herbarium note",
    source_taxon_id: null,
    accepted_source_taxon_id: null,
    origin_identity_id: null,
    effective_from: "2026-10-12T00:00:00Z",
    superseded_at: null,
  };
  const updatedIdentity = {
    ...activeIdentity,
    synonyms: [...activeIdentity.synonyms, "Cereus lageniformis"],
    updated_at: "2026-10-12T00:00:00Z",
  };
  let savedSynonyms = [] as (typeof createdSynonym)[];

  mockIdentityAppFetch((path, init) => {
    if (path === "/api/v1/botanical-identities") {
      if (init?.method === "POST") {
        throw new Error("Unexpected POST /api/v1/botanical-identities");
      }
      return json(directoryIdentities);
    }
    if (
      path ===
      `/api/v1/botanical-identities/${activeIdentity.id}/reconciliation`
    ) {
      return json({
        identity: savedSynonyms.length ? updatedIdentity : activeIdentity,
        original_scientific_name: activeIdentity.scientific_name,
        original_cultivar_name: null,
        original_common_name: "Bolivian torch",
        original_display_label: activeIdentity.display_label,
        former_names: savedSynonyms,
        has_source_conflict: false,
        conflicts: [],
        source_assessments: [],
        suggestions: [],
        reconciliations: [],
      });
    }
    if (
      path === `/api/v1/botanical-identities/${activeIdentity.id}/synonyms` &&
      init?.method === "POST"
    ) {
      savedSynonyms = [createdSynonym];
      directoryIdentities = [updatedIdentity, otherIdentity];
      return json(createdSynonym, 201);
    }
    return undefined;
  });

  window.history.replaceState(
    null,
    "",
    `#/identities/${activeIdentity.id}?tab=taxonomy`,
  );
  const user = userEvent.setup();
  render(<App />);
  await vi.dynamicImportSettled();

  await user.click(
    await screen.findByRole("button", { name: "Add operator synonym" }),
  );
  await user.type(
    screen.getByLabelText(/Synonym scientific name/),
    "Cereus lageniformis",
  );
  await user.type(screen.getByLabelText(/Source citation/), "Herbarium note");
  await user.click(
    screen.getByRole("button", { name: "Save operator synonym" }),
  );

  expect(
    await screen.findByText("Operator synonym Cereus lageniformis added."),
  ).toBeVisible();

  const breadcrumb = screen.getByRole("navigation", { name: "Breadcrumb" });
  await user.click(
    within(breadcrumb).getByRole("link", { name: "Botanical identities" }),
  );

  const searchInput = await screen.findByLabelText(
    "Search botanical identities",
  );
  await user.type(searchInput, "Cereus lageniformis");
  await waitFor(() => {
    expect(screen.queryByText("Echinopsis pachanoi")).toBeNull();
  });
  expect(screen.getByText("Trichocereus bridgesii")).toBeVisible();
  expect(screen.getByText(/Synonym: Cereus lageniformis/)).toBeVisible();
});
