import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { ApiError } from "../auth/api";
import {
  createBotanicalIdentitySynonym,
  deleteBotanicalIdentitySynonym,
  getBotanicalIdentityReconciliation,
  updateBotanicalIdentitySynonym,
  type BotanicalIdentityResponse,
  type IdentityHistoricalNameResponse,
  type IdentityReconciliationResponse,
} from "./api";
import { IdentityReconciliationPanel } from "./IdentityReconciliationPanel";

const auth = { sessionExpired: vi.fn() };
vi.mock("../auth/context", () => ({ useAuth: () => auth }));
vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    getBotanicalIdentityReconciliation: vi.fn(),
    correctBotanicalIdentityAcceptedName: vi.fn(),
    mergeDuplicateBotanicalIdentity: vi.fn(),
    createBotanicalIdentitySynonym: vi.fn(),
    updateBotanicalIdentitySynonym: vi.fn(),
    deleteBotanicalIdentitySynonym: vi.fn(),
  };
});

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

const baseIdentity: BotanicalIdentityResponse = {
  id: "id-bridgesii",
  scientific_name: "Trichocereus bridgesii",
  cultivar_name: null,
  common_name: "Bolivian torch",
  display_label: "Trichocereus bridgesii",
  synonyms: [],
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
};

function reconciliationFixture(
  overrides: Partial<IdentityReconciliationResponse> = {},
): IdentityReconciliationResponse {
  return {
    identity: baseIdentity,
    original_scientific_name: "Cereus bridgesii",
    original_cultivar_name: null,
    original_common_name: "Bolivian torch",
    original_display_label: "Cereus bridgesii",
    former_names: [
      {
        id: "hist-initial",
        scientific_name: "Cereus bridgesii",
        cultivar_name: null,
        common_name: "Bolivian torch",
        display_label: "Cereus bridgesii",
        authorship: "Salm-Dyck",
        status_kind: "initial_recorded",
        source_provider: "operator",
        source_version: null,
        source_taxon_id: null,
        accepted_source_taxon_id: null,
        origin_identity_id: null,
        effective_from: "2026-10-01T00:00:00Z",
        superseded_at: "2026-10-02T00:00:00Z",
      },
      {
        id: "hist-former",
        scientific_name: "Trichocereus bridgessii",
        cultivar_name: null,
        common_name: null,
        display_label: "Trichocereus bridgessii",
        authorship: null,
        status_kind: "former_accepted",
        source_provider: "operator",
        source_version: null,
        source_taxon_id: null,
        accepted_source_taxon_id: null,
        origin_identity_id: null,
        effective_from: "2026-10-02T00:00:00Z",
        superseded_at: "2026-10-03T00:00:00Z",
      },
    ],
    has_source_conflict: false,
    conflicts: [],
    source_assessments: [],
    suggestions: [],
    reconciliations: [],
    ...overrides,
  };
}

test("displays distinct badges for accepted, original, historical, source, and operator names with immutable provenance", async () => {
  const operatorSyn: IdentityHistoricalNameResponse = {
    id: "syn-op-1",
    scientific_name: "Echinopsis lageniformis",
    cultivar_name: "Monstrose",
    common_name: "Penis cactus",
    display_label: "Echinopsis lageniformis ‘Monstrose’",
    authorship: "(F.Rchb.) Friedrich & G.D.Rowley",
    status_kind: "operator_synonym",
    source_provider: "operator",
    source_version: "Hortus Third",
    source_taxon_id: null,
    accepted_source_taxon_id: null,
    origin_identity_id: null,
    effective_from: "2026-10-05T00:00:00Z",
    superseded_at: null,
  };
  const sourceSyn: IdentityHistoricalNameResponse = {
    id: "syn-src-1",
    scientific_name: "Trichocereus lagenaeformis",
    cultivar_name: null,
    common_name: null,
    display_label: "Trichocereus lagenaeformis",
    authorship: "hort.",
    status_kind: "source_synonym",
    source_provider: "wcvp",
    source_version: "15",
    source_taxon_id: "powo-123",
    accepted_source_taxon_id: "powo-456",
    origin_identity_id: null,
    effective_from: "2026-10-04T00:00:00Z",
    superseded_at: null,
  };

  vi.mocked(getBotanicalIdentityReconciliation).mockResolvedValue(
    reconciliationFixture({
      former_names: [
        ...reconciliationFixture().former_names,
        operatorSyn,
        sourceSyn,
      ],
      source_assessments: [
        {
          source_provider: "wfo",
          source_label: "World Flora Online (WFO)",
          source_version: "2025-12",
          source_checksum: "sum-1",
          linked: true,
          link_version: "v1",
          stale: false,
          taxon_id: "wfo-1",
          scientific_name: "Trichocereus bridgesii",
          authorship: "(Salm-Dyck) Britton & Rose",
          status: "synonym",
          accepted_taxon_id: "wfo-2",
          accepted_scientific_name: "Echinopsis lageniformis",
          accepted_authorship: "Friedrich & G.D.Rowley",
          message: "Confirmed WFO synonym.",
        },
      ],
    }),
  );

  render(
    <IdentityReconciliationPanel
      identity={baseIdentity}
      csrfToken="csrf-1"
      onIdentityUpdated={vi.fn()}
    />,
  );

  expect(await screen.findByText("Accepted name")).toBeVisible();
  expect(
    screen.getAllByText("Original recorded").length,
  ).toBeGreaterThanOrEqual(1);
  expect(screen.getByText("Former accepted")).toBeVisible();
  expect(screen.getByText("Operator synonym")).toBeVisible();
  expect(screen.getByText("Source synonym")).toBeVisible();
  expect(screen.getByText("Source reference")).toBeVisible();

  const historicalSection = screen.getByRole("region", {
    name: "Historical name ledger",
  });
  expect(
    within(historicalSection).queryByRole("button", { name: /edit/i }),
  ).toBeNull();
  expect(
    within(historicalSection).queryByRole("button", { name: /remove/i }),
  ).toBeNull();
  expect(
    within(historicalSection).getByText(/immutable provenance evidence/i),
  ).toBeVisible();

  const sourceSection = screen.getByRole("region", {
    name: "Source-provided names and assessments",
  });
  expect(
    within(sourceSection).queryByRole("button", { name: /edit/i }),
  ).toBeNull();
  expect(
    within(sourceSection).queryByRole("button", { name: /remove/i }),
  ).toBeNull();
});

test("supports loading failure retry and full operator synonym add, edit, confirmation cancel, and remove flows", async () => {
  vi.mocked(getBotanicalIdentityReconciliation)
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce(reconciliationFixture());

  const createdRow: IdentityHistoricalNameResponse = {
    id: "syn-new-1",
    scientific_name: "Echinopsis lageniformis",
    cultivar_name: "Monstrose",
    common_name: "Penis cactus",
    display_label: "Echinopsis lageniformis ‘Monstrose’",
    authorship: "(F.Rchb.) Friedrich & G.D.Rowley",
    status_kind: "operator_synonym",
    source_provider: "operator",
    source_version: "Hortus Third",
    source_taxon_id: null,
    accepted_source_taxon_id: null,
    origin_identity_id: null,
    effective_from: "2026-10-10T00:00:00Z",
    superseded_at: null,
  };
  const updatedRow: IdentityHistoricalNameResponse = {
    ...createdRow,
    cultivar_name: "Inermis",
    common_name: "Smooth torch",
    display_label: "Echinopsis lageniformis ‘Inermis’",
    source_version: "RHS Index 2026",
  };
  vi.mocked(createBotanicalIdentitySynonym).mockResolvedValue(createdRow);
  vi.mocked(updateBotanicalIdentitySynonym).mockResolvedValue(updatedRow);
  vi.mocked(deleteBotanicalIdentitySynonym).mockResolvedValue(undefined);

  const onIdentityUpdated = vi.fn().mockResolvedValue(undefined);
  const user = userEvent.setup();

  render(
    <IdentityReconciliationPanel
      identity={baseIdentity}
      csrfToken="csrf-xyz"
      onIdentityUpdated={onIdentityUpdated}
    />,
  );

  expect(
    await screen.findByText(/Could not load accepted-name reconciliation/),
  ).toBeVisible();
  await user.click(
    screen.getByRole("button", { name: "Retry reconciliation check" }),
  );

  expect(
    await screen.findByText("No operator-managed synonyms recorded."),
  ).toBeVisible();

  await user.click(
    screen.getByRole("button", { name: "Add operator synonym" }),
  );
  await user.type(
    screen.getByLabelText(/Synonym scientific name/),
    "  Echinopsis lageniformis ",
  );
  await user.type(screen.getByLabelText(/Cultivar/), "Monstrose");
  await user.type(screen.getByLabelText(/Common name/), "Penis cactus");
  await user.type(
    screen.getByLabelText(/Taxonomic authorship/),
    "(F.Rchb.) Friedrich & G.D.Rowley",
  );
  await user.type(screen.getByLabelText(/Source citation/), "Hortus Third");
  await user.click(
    screen.getByRole("button", { name: "Save operator synonym" }),
  );

  expect(createBotanicalIdentitySynonym).toHaveBeenCalledWith(
    "id-bridgesii",
    {
      scientific_name: "Echinopsis lageniformis",
      cultivar_name: "Monstrose",
      common_name: "Penis cactus",
      authorship: "(F.Rchb.) Friedrich & G.D.Rowley",
      source_citation: "Hortus Third",
    },
    "csrf-xyz",
  );
  expect(
    await screen.findByText(
      /Operator synonym Echinopsis lageniformis ‘Monstrose’ added\./,
    ),
  ).toBeVisible();
  expect(onIdentityUpdated).toHaveBeenLastCalledWith(
    expect.objectContaining({
      synonyms: [
        "Cereus bridgesii",
        "Trichocereus bridgessii",
        "Echinopsis lageniformis",
      ],
    }),
  );

  await user.click(
    screen.getByRole("button", {
      name: "Edit synonym Echinopsis lageniformis ‘Monstrose’",
    }),
  );
  const cultivarInput = screen.getByLabelText(/Cultivar/);
  await user.clear(cultivarInput);
  await user.type(cultivarInput, "Inermis");
  const commonInput = screen.getByLabelText(/Common name/);
  await user.clear(commonInput);
  await user.type(commonInput, "Smooth torch");
  const citationInput = screen.getByLabelText(/Source citation/);
  await user.clear(citationInput);
  await user.type(citationInput, "RHS Index 2026");
  await user.click(
    screen.getByRole("button", { name: "Save synonym changes" }),
  );

  expect(updateBotanicalIdentitySynonym).toHaveBeenCalledWith(
    "id-bridgesii",
    "syn-new-1",
    {
      scientific_name: "Echinopsis lageniformis",
      cultivar_name: "Inermis",
      common_name: "Smooth torch",
      authorship: "(F.Rchb.) Friedrich & G.D.Rowley",
      source_citation: "RHS Index 2026",
    },
    "csrf-xyz",
  );
  expect(
    await screen.findByText(
      /Operator synonym Echinopsis lageniformis ‘Inermis’ updated\./,
    ),
  ).toBeVisible();

  await user.click(
    screen.getByRole("button", {
      name: "Remove synonym Echinopsis lageniformis ‘Inermis’",
    }),
  );
  const dialog = screen.getByRole("alertdialog", {
    name: "Confirm removal of Echinopsis lageniformis ‘Inermis’",
  });
  expect(dialog).toBeVisible();
  const dialogCancelBtn = within(dialog).getByRole("button", {
    name: "Cancel",
  });
  expect(dialogCancelBtn).toHaveFocus();
  await user.keyboard("{Escape}");
  expect(deleteBotanicalIdentitySynonym).not.toHaveBeenCalled();
  expect(screen.getByText(/RHS Index 2026/)).toBeVisible();

  await user.click(
    screen.getByRole("button", {
      name: "Remove synonym Echinopsis lageniformis ‘Inermis’",
    }),
  );
  await user.click(screen.getByRole("button", { name: "Confirm removal" }));
  expect(deleteBotanicalIdentitySynonym).toHaveBeenCalledWith(
    "id-bridgesii",
    "syn-new-1",
    "csrf-xyz",
  );
  expect(
    await screen.findByText(
      /Operator synonym Echinopsis lageniformis ‘Inermis’ removed\./,
    ),
  ).toBeVisible();
  expect(
    screen.getByText("No operator-managed synonyms recorded."),
  ).toBeVisible();
});

test("validates blank names, accepted-name collisions, duplicate synonyms, and active collection collisions with survivor link", async () => {
  vi.mocked(getBotanicalIdentityReconciliation).mockResolvedValue(
    reconciliationFixture({ former_names: [] }),
  );
  vi.mocked(createBotanicalIdentitySynonym)
    .mockRejectedValueOnce(
      new ApiError(409, null, {
        detail: {
          code: "synonym_equals_accepted_name",
          message:
            "Proposed synonym matches the current accepted name for this botanical identity.",
        },
      }),
    )
    .mockRejectedValueOnce(
      new ApiError(409, null, {
        detail: {
          code: "duplicate_botanical_identity",
          message:
            "A botanical identity for 'Echinopsis pachanoi' already exists in your collection.",
          existing_id: "id-pachanoi",
        },
      }),
    );

  const user = userEvent.setup();
  render(
    <IdentityReconciliationPanel
      identity={baseIdentity}
      csrfToken="csrf-val"
      onIdentityUpdated={vi.fn()}
    />,
  );

  await user.click(
    await screen.findByRole("button", { name: "Add operator synonym" }),
  );

  await user.click(
    screen.getByRole("button", { name: "Save operator synonym" }),
  );
  expect(
    await screen.findByText("Synonym scientific name cannot be blank."),
  ).toBeVisible();
  expect(screen.getByLabelText(/Synonym scientific name/)).toHaveAttribute(
    "aria-invalid",
    "true",
  );
  expect(createBotanicalIdentitySynonym).not.toHaveBeenCalled();

  await user.type(
    screen.getByLabelText(/Synonym scientific name/),
    "Trichocereus bridgesii",
  );
  await user.click(
    screen.getByRole("button", { name: "Save operator synonym" }),
  );
  expect(
    await screen.findByText(/matches the current accepted name/),
  ).toBeVisible();

  await user.clear(screen.getByLabelText(/Synonym scientific name/));
  await user.type(
    screen.getByLabelText(/Synonym scientific name/),
    "Echinopsis pachanoi",
  );
  await user.click(
    screen.getByRole("button", { name: "Save operator synonym" }),
  );
  expect(
    await screen.findByText(/already exists in your collection/),
  ).toBeVisible();
  const link = screen.getByRole("link", {
    name: "Inspect colliding botanical identity",
  });
  expect(link).toHaveAttribute("href", "#/identities/id-pachanoi?tab=taxonomy");
});

test("source assessment prefills operator synonym form without automatic acceptance, and locks edits on merged tombstones", async () => {
  vi.mocked(getBotanicalIdentityReconciliation).mockResolvedValue(
    reconciliationFixture({
      former_names: [],
      source_assessments: [
        {
          source_provider: "wcvp",
          source_label: "Kew WCVP",
          source_version: "15",
          source_checksum: "wcvp-15",
          linked: true,
          link_version: "1",
          stale: false,
          taxon_id: "powo-100",
          scientific_name: "Trichocereus bridgesii",
          authorship: "(Salm-Dyck) Britton & Rose",
          status: "synonym",
          accepted_taxon_id: "powo-200",
          accepted_scientific_name: "Echinopsis lageniformis",
          accepted_authorship: "Friedrich & G.D.Rowley",
          message: "WCVP synonym assessment.",
        },
      ],
    }),
  );

  const user = userEvent.setup();
  const { rerender } = render(
    <IdentityReconciliationPanel
      identity={baseIdentity}
      csrfToken="csrf-prefill"
      onIdentityUpdated={vi.fn()}
    />,
  );

  await user.click(
    await screen.findByRole("button", { name: "Add as operator synonym" }),
  );
  expect(screen.getByLabelText(/Synonym scientific name/)).toHaveValue(
    "Echinopsis lageniformis",
  );
  expect(screen.getByLabelText(/Taxonomic authorship/)).toHaveValue(
    "Friedrich & G.D.Rowley",
  );
  expect(screen.getByLabelText(/Source citation/)).toHaveValue("WCVP 15");
  expect(createBotanicalIdentitySynonym).not.toHaveBeenCalled();

  const mergedIdentity: BotanicalIdentityResponse = {
    ...baseIdentity,
    merged_into_id: "id-survivor",
    merged_at: "2026-10-15T00:00:00Z",
    updated_at: "2026-10-15T00:00:00Z",
  };
  vi.mocked(getBotanicalIdentityReconciliation).mockResolvedValue(
    reconciliationFixture({
      identity: mergedIdentity,
    }),
  );
  rerender(
    <IdentityReconciliationPanel
      identity={mergedIdentity}
      csrfToken="csrf-prefill"
      onIdentityUpdated={vi.fn()}
    />,
  );

  expect(
    await screen.findByText(/retired after duplicate reconciliation/),
  ).toBeVisible();
  expect(
    screen.getByRole("link", { name: "survivor botanical identity" }),
  ).toHaveAttribute("href", "#/identities/id-survivor?tab=taxonomy");
  expect(
    screen.queryByRole("button", { name: "Add operator synonym" }),
  ).toBeNull();
  expect(
    screen.queryByRole("button", {
      name: "Record manual accepted-name correction",
    }),
  ).toBeNull();
});
