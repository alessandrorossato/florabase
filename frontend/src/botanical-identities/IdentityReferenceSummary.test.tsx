import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import {
  getBotanicalProfile,
  listBotanicalNativeRanges,
} from "../botanical-profiles/api";
import {
  correctBotanicalIdentityAcceptedName,
  getBotanicalIdentityReconciliation,
  getExternalTaxonLink,
  mergeDuplicateBotanicalIdentity,
} from "./api";
import { IdentityReconciliationPanel } from "./IdentityReconciliationPanel";
import { IdentityReferenceSummary } from "./IdentityReferenceSummary";

const auth = { sessionExpired: vi.fn() };
vi.mock("../auth/context", () => ({ useAuth: () => auth }));
vi.mock("../botanical-profiles/api", () => ({
  getBotanicalProfile: vi.fn(),
  listBotanicalNativeRanges: vi.fn(),
}));
vi.mock("./api", () => ({
  getExternalTaxonLink: vi.fn(),
  getBotanicalIdentityReconciliation: vi.fn(),
  correctBotanicalIdentityAcceptedName: vi.fn(),
  mergeDuplicateBotanicalIdentity: vi.fn(),
}));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
test("Overview distinguishes absent reference from recorded collection context and reads only local APIs", async () => {
  vi.mocked(getBotanicalProfile).mockResolvedValue({
    botanical_identity_id: "identity",
    description: "Operator-entered reference description.",
    origin_distribution: null,
    cultivation: null,
    uses: null,
    warnings: null,
  });
  vi.mocked(listBotanicalNativeRanges).mockResolvedValue([]);
  vi.mocked(getExternalTaxonLink).mockResolvedValue(null);
  render(<IdentityReferenceSummary id="identity" />);
  expect(
    await screen.findByText("Operator-entered reference description."),
  ).toBeVisible();
  expect(
    screen.getByText(
      /No confirmed GBIF reference.*0 structured native-range entries/,
    ),
  ).toBeVisible();
  expect(
    screen.getByRole("link", { name: "Read botanical reference" }),
  ).toHaveAttribute("href", "#/identities/identity?tab=reference");
  expect(getBotanicalProfile).toHaveBeenCalledWith(
    "identity",
    expect.any(AbortSignal),
  );
  expect(listBotanicalNativeRanges).toHaveBeenCalledTimes(1);
  expect(getExternalTaxonLink).toHaveBeenCalledTimes(1);
});
test("a failed local summary remains explicit and retryable without claiming reference absence", async () => {
  vi.mocked(getBotanicalProfile).mockRejectedValue(new Error("offline"));
  vi.mocked(listBotanicalNativeRanges).mockResolvedValue([]);
  vi.mocked(getExternalTaxonLink).mockResolvedValue(null);
  const user = userEvent.setup();
  render(<IdentityReferenceSummary id="identity" />);
  expect(
    await screen.findByText("Botanical description unavailable."),
  ).toBeVisible();
  expect(screen.queryByText("No botanical description recorded.")).toBeNull();
  await user.click(
    screen.getByRole("button", { name: "Retry botanical summary" }),
  );
  expect(getBotanicalProfile).toHaveBeenCalledTimes(2);
});

test("IdentityReconciliationPanel displays provenance, source conflicts, and requires conflict acknowledgement before confirming accepted-name correction", async () => {
  const identity = {
    id: "id-1",
    scientific_name: "Lycopersicon esculentum",
    cultivar_name: "San Marzano",
    common_name: "Plum tomato",
    display_label: "Lycopersicon esculentum ‘San Marzano’",
    created_at: "2026-10-01T00:00:00Z",
    updated_at: "2026-10-01T00:00:00Z",
  };
  const updatedIdentity = {
    ...identity,
    scientific_name: "Solanum lycopersicum",
    display_label: "Solanum lycopersicum ‘San Marzano’",
    updated_at: "2026-10-02T00:00:00Z",
  };
  vi.mocked(getBotanicalIdentityReconciliation).mockResolvedValue({
    identity,
    original_scientific_name: "Lycopersicon esculentum",
    original_cultivar_name: "San Marzano",
    original_common_name: "Plum tomato",
    original_display_label: "Lycopersicon esculentum ‘San Marzano’",
    former_names: [],
    has_source_conflict: true,
    conflicts: [
      {
        kind: "wcvp_version_conflict",
        message:
          "Local WCVP v15 and v16 releases disagree on the accepted scientific name.",
        sources: ["wcvp:15", "wcvp:16"],
        colliding_identity_id: null,
      },
    ],
    source_assessments: [
      {
        source_provider: "wfo",
        source_label: "World Flora Online (WFO)",
        source_version: "2025-12",
        source_checksum: "abc123",
        linked: true,
        link_version: "link-1",
        stale: false,
        taxon_id: "wfo-0009999999",
        scientific_name: "Lycopersicon esculentum",
        authorship: "Mill.",
        status: "synonym",
        accepted_taxon_id: "wfo-0001020304",
        accepted_scientific_name: "Solanum lycopersicum",
        accepted_authorship: "L.",
        message: "Confirmed WFO synonym.",
      },
    ],
    suggestions: [
      {
        suggestion_id: "wfo:2025-12:wfo-0009999999:wfo-0001020304",
        source_provider: "wfo",
        source_label: "World Flora Online (WFO)",
        source_version: "2025-12",
        source_checksum: "abc123",
        link_version: "link-1",
        matched_taxon_id: "wfo-0009999999",
        matched_scientific_name: "Lycopersicon esculentum",
        matched_authorship: "Mill.",
        matched_status: "synonym",
        accepted_taxon_id: "wfo-0001020304",
        accepted_scientific_name: "Solanum lycopersicum",
        accepted_authorship: "L.",
        accepted_rank: "species",
        stale: false,
        advisory_note: null,
        colliding_identity: null,
      },
    ],
    reconciliations: [],
  });
  vi.mocked(correctBotanicalIdentityAcceptedName).mockResolvedValue({
    identity: updatedIdentity,
    original_scientific_name: "Lycopersicon esculentum",
    original_cultivar_name: "San Marzano",
    original_common_name: "Plum tomato",
    original_display_label: "Lycopersicon esculentum ‘San Marzano’",
    former_names: [
      {
        id: "hist-1",
        scientific_name: "Lycopersicon esculentum",
        cultivar_name: "San Marzano",
        common_name: "Plum tomato",
        display_label: "Lycopersicon esculentum ‘San Marzano’",
        authorship: "Mill.",
        status_kind: "initial_recorded",
        source_provider: "wfo",
        source_version: "2025-12",
        source_taxon_id: "wfo-0009999999",
        accepted_source_taxon_id: "wfo-0001020304",
        origin_identity_id: null,
        effective_from: "2026-10-01T00:00:00Z",
        superseded_at: "2026-10-02T00:00:00Z",
      },
    ],
    has_source_conflict: false,
    conflicts: [],
    source_assessments: [],
    suggestions: [],
    reconciliations: [],
  });

  const onIdentityUpdated = vi.fn().mockResolvedValue(undefined);
  const user = userEvent.setup();
  render(
    <IdentityReconciliationPanel
      identity={identity}
      csrfToken="csrf-123"
      onIdentityUpdated={onIdentityUpdated}
    />,
  );

  expect(
    await screen.findByText(
      "Local WCVP v15 and v16 releases disagree on the accepted scientific name.",
    ),
  ).toBeVisible();

  await user.click(
    screen.getByRole("button", { name: "Review accepted-name correction" }),
  );

  const confirmBtn = screen.getByRole("button", {
    name: "Confirm accepted-name correction",
  });
  expect(confirmBtn).toBeDisabled();

  await user.click(
    screen.getByRole("checkbox", {
      name: /I have reviewed the conflicting source assessments/i,
    }),
  );
  expect(confirmBtn).toBeEnabled();

  await user.click(confirmBtn);

  expect(correctBotanicalIdentityAcceptedName).toHaveBeenCalledWith(
    "id-1",
    expect.objectContaining({
      scientific_name: "Solanum lycopersicum",
      source_provider: "wfo",
      acknowledge_conflict: true,
    }),
    "csrf-123",
  );
  expect(onIdentityUpdated).toHaveBeenCalledWith(updatedIdentity);
  expect(
    await screen.findByText(/Original acquisition \/ recorded name/),
  ).toBeVisible();
});

test("IdentityReconciliationPanel blocks silent merge on collision and enables explicit survivor duplicate reconciliation", async () => {
  const duplicateIdentity = {
    id: "dup-1",
    scientific_name: "Lycopersicon esculentum",
    cultivar_name: null,
    common_name: "Old tomato",
    display_label: "Lycopersicon esculentum",
    created_at: "2026-10-01T00:00:00Z",
    updated_at: "2026-10-01T00:00:00Z",
    collection_counts: {
      seed_lots: 2,
      sowings: 1,
      plants: 1,
      plant_groups: 0,
      vegetative_lots: 0,
      propagation_attempts: 0,
    },
  };
  const survivorSummary = {
    id: "surv-1",
    scientific_name: "Solanum lycopersicum",
    cultivar_name: null,
    common_name: "Garden tomato",
    display_label: "Solanum lycopersicum",
    updated_at: "2026-10-01T00:00:00Z",
    collection_counts: {
      seed_lots: 3,
      sowings: 0,
      plants: 2,
      plant_groups: 1,
      vegetative_lots: 0,
      propagation_attempts: 0,
    },
    has_conflicting_profile_fields: true,
    conflicting_profile_fields: ["description"],
  };
  vi.mocked(getBotanicalIdentityReconciliation).mockResolvedValue({
    identity: duplicateIdentity,
    original_scientific_name: "Lycopersicon esculentum",
    original_cultivar_name: null,
    original_common_name: "Old tomato",
    original_display_label: "Lycopersicon esculentum",
    former_names: [],
    has_source_conflict: false,
    conflicts: [],
    source_assessments: [],
    suggestions: [
      {
        suggestion_id: "wfo:2025-12:wfo-0009999999:wfo-0001020304",
        source_provider: "wfo",
        source_label: "World Flora Online (WFO)",
        source_version: "2025-12",
        source_checksum: "abc123",
        link_version: "link-1",
        matched_taxon_id: "wfo-0009999999",
        matched_scientific_name: "Lycopersicon esculentum",
        matched_authorship: "Mill.",
        matched_status: "synonym",
        accepted_taxon_id: "wfo-0001020304",
        accepted_scientific_name: "Solanum lycopersicum",
        accepted_authorship: "L.",
        accepted_rank: "species",
        stale: false,
        advisory_note: null,
        colliding_identity: survivorSummary,
      },
    ],
    reconciliations: [],
  });
  vi.mocked(mergeDuplicateBotanicalIdentity).mockResolvedValue({
    identity: {
      ...survivorSummary,
      created_at: "2026-10-01T00:00:00Z",
    },
    original_scientific_name: "Solanum lycopersicum",
    original_cultivar_name: null,
    original_common_name: "Garden tomato",
    original_display_label: "Solanum lycopersicum",
    former_names: [],
    has_source_conflict: false,
    conflicts: [],
    source_assessments: [],
    suggestions: [],
    reconciliations: [],
  });

  const onIdentityUpdated = vi.fn().mockResolvedValue(undefined);
  const user = userEvent.setup();
  render(
    <IdentityReconciliationPanel
      identity={duplicateIdentity}
      csrfToken="csrf-123"
      onIdentityUpdated={onIdentityUpdated}
    />,
  );

  expect(
    await screen.findByText(/Duplicate identity collision:/),
  ).toBeVisible();

  await user.click(
    screen.getByRole("button", {
      name: "Review duplicate-identity reconciliation",
    }),
  );

  const mergeBtn = screen.getByRole("button", {
    name: "Confirm duplicate merge and repoint holdings",
  });
  expect(mergeBtn).toBeDisabled();

  await user.click(
    screen.getByRole("checkbox", {
      name: /Keep survivor \(Solanum lycopersicum\) profile text/i,
    }),
  );
  expect(mergeBtn).toBeEnabled();

  await user.click(mergeBtn);

  expect(mergeDuplicateBotanicalIdentity).toHaveBeenCalledWith(
    "dup-1",
    expect.objectContaining({
      survivor_identity_id: "surv-1",
      profile_resolution: "keep_survivor",
    }),
    "csrf-123",
  );
  expect(onIdentityUpdated).toHaveBeenCalledTimes(1);
});
