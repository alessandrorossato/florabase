import {
  cleanup,
  render,
  screen,
  within,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { GeographyOverview } from "./GeographyOverview";
import { SiteSourceRecords } from "./SiteSourceRecords";

const { auth } = vi.hoisted(() => ({ auth: { sessionExpired: vi.fn() } }));
vi.mock("../auth/context", () => ({ useAuth: () => auth }));

const identity = "01900000-0000-7000-8000-000000000001";
const siteId = "01900000-0000-7000-8000-000000000002";
const recordId = "01900000-0000-7000-8000-000000000003";
const site = {
  id: siteId,
  name: "Recorded mountain site",
  records: [
    {
      id: recordId,
      record_type: "seed_lot",
      label: "Original packet",
      lifecycle: "exhausted",
      is_active: false,
      botanical_identity: { id: identity, display_label: "Ocimum basilicum" },
    },
  ],
};
function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
function localEvidence({
  empty = false,
  failNative = false,
  status = 200,
} = {}) {
  const reply = (body: unknown, code = 200) =>
    Promise.resolve(json(body, code));
  return vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const path =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    if (status !== 200) return reply({}, status);
    if (path.includes("native-ranges/overview"))
      return failNative
        ? reply({}, 503)
        : reply({
            represented: empty ? 0 : 2,
            with_range: empty ? 0 : 1,
            without_range: empty ? 0 : 1,
            places_total: empty ? 0 : 1,
          });
    if (path.includes("native-ranges/identities"))
      return reply({
        items: empty
          ? []
          : [{ id: identity, display_label: "Ocimum basilicum" }],
      });
    if (path.includes("species-distribution/identities"))
      return reply({
        total: empty ? 0 : 2,
        occurrence_ready: empty ? 0 : 1,
        items: [],
      });
    if (path === "/api/v1/provenance-sites/map")
      return reply({
        sites: empty ? [] : [site],
        total_provenance_sites: empty ? 0 : 2,
        coordinate_less_sites: empty ? 0 : 1,
      });
    throw new Error(`Unexpected or external request: ${path}`);
  });
}
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  auth.sessionExpired.mockClear();
});

test("overview reads local evidence only and links exact identities, sites and source records", async () => {
  const fetch = localEvidence();
  render(<GeographyOverview />);
  expect(screen.getAllByRole("status")).toHaveLength(3);
  await screen.findByText("represented identities with structured ranges");
  await userEvent.click(screen.getByText("Linked Botanical Identities"));
  expect(
    screen.getByRole("region", { name: "Native ranges" }),
  ).toHaveTextContent("represented identities with structured ranges");
  const native = screen.getByRole("region", { name: "Native ranges" });
  expect(
    within(native).getByRole("link", { name: "Ocimum basilicum" }),
  ).toHaveAttribute("href", `#/identities/${identity}?tab=reference`);
  expect(
    within(native).getByRole("link", { name: "Explore range" }),
  ).toHaveAttribute(
    "href",
    `#/geography/native-ranges?mode=species&identity=${identity}`,
  );
  await userEvent.click(
    await screen.findByText("Linked sites and source records"),
  );
  expect(await screen.findByRole("link", { name: site.name })).toHaveAttribute(
    "href",
    `#/geography/${siteId}`,
  );
  expect(screen.getByRole("link", { name: "Original packet" })).toHaveAttribute(
    "href",
    `#/seeds/${recordId}`,
  );
  const distribution = screen.getByRole("region", {
    name: "Species distribution",
  });
  expect(
    distribution.querySelector(".geography-coverage strong"),
  ).toHaveTextContent("1 of 2");
  expect(screen.getByText("Not checked here")).toBeInTheDocument();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  expect(fetch).toHaveBeenCalledTimes(4);
  for (const [path] of fetch.mock.calls)
    expect(
      typeof path === "string"
        ? path
        : path instanceof URL
          ? path.toString()
          : path.url,
    ).toMatch(
      /^\/api\/v1\/(explore\/(native-ranges|species-distribution)|provenance-sites\/map)/,
    );
});

test("empty evidence keeps all destinations available and explains missing data", async () => {
  localEvidence({ empty: true });
  render(<GeographyOverview />);
  await screen.findByText(/No structured native ranges recorded/);
  expect(
    await screen.findByText(/No collection identities represented yet/),
  ).toBeInTheDocument();
  expect(
    await screen.findByText(/No provenance sites recorded/),
  ).toBeInTheDocument();
  for (const name of [
    "Explore native ranges",
    "Explore species distribution",
    "Explore collection origins",
  ])
    expect(screen.getByRole("link", { name })).toBeInTheDocument();
});

test("a failed summary does not hide successful evidence or navigation and can retry", async () => {
  const user = userEvent.setup();
  const fetch = localEvidence({ failNative: true });
  render(<GeographyOverview />);
  await screen.findByRole("alert");
  await user.click(await screen.findByText("Linked sites and source records"));
  expect(
    await screen.findByRole("link", { name: site.name }),
  ).toBeInTheDocument();
  fetch.mockRestore();
  localEvidence();
  await user.click(screen.getByRole("button", { name: "Retry summary" }));
  await screen.findByText("represented identities with structured ranges");
  expect(
    screen.getByRole("region", { name: "Native ranges" }),
  ).toHaveTextContent("represented identities with structured ranges");
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test("summary authentication failures use the session expiry flow", async () => {
  localEvidence({ status: 401 });
  render(<GeographyOverview />);
  await waitFor(() => {
    expect(auth.sessionExpired).toHaveBeenCalled();
  });
});

test("site details use the exact site's record IDs, including historical material", async () => {
  const fetch = localEvidence();
  render(<SiteSourceRecords siteId={siteId} hasCoordinates />);
  expect(
    await screen.findByRole("link", { name: "Original packet" }),
  ).toHaveAttribute("href", `#/seeds/${recordId}`);
  expect(screen.getByText("Exhausted")).toBeInTheDocument();
  expect(fetch).toHaveBeenCalledTimes(1);
});

test("coordinate-less sites report the missing record contract without a map request", () => {
  const fetch = localEvidence();
  render(<SiteSourceRecords siteId={siteId} hasCoordinates={false} />);
  expect(
    screen.getByText(
      /Exact record links are currently available only for sites with coordinates/,
    ),
  ).toBeInTheDocument();
  expect(fetch).not.toHaveBeenCalled();
});

test("source-record failure is retryable and does not substitute records from another site", async () => {
  const user = userEvent.setup();
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json({}, 503))
    .mockResolvedValue(json({ sites: [{ ...site, id: "another-site" }] }));
  render(<SiteSourceRecords siteId={siteId} hasCoordinates />);
  await screen.findByRole("alert");
  await user.click(
    screen.getByRole("button", { name: "Retry source records" }),
  );
  await screen.findByText(
    "No directly linked source records in Collection origins.",
  );
  expect(
    screen.queryByRole("link", { name: "Original packet" }),
  ).not.toBeInTheDocument();
  expect(fetch).toHaveBeenCalledTimes(2);
});
