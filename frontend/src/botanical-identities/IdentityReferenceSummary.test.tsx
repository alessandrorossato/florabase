import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import {
  getBotanicalProfile,
  listBotanicalNativeRanges,
} from "../botanical-profiles/api";
import { getExternalTaxonLink } from "./api";
import { IdentityReferenceSummary } from "./IdentityReferenceSummary";

const auth = { sessionExpired: vi.fn() };
vi.mock("../auth/context", () => ({ useAuth: () => auth }));
vi.mock("../botanical-profiles/api", () => ({
  getBotanicalProfile: vi.fn(),
  listBotanicalNativeRanges: vi.fn(),
}));
vi.mock("./api", () => ({ getExternalTaxonLink: vi.fn() }));
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
