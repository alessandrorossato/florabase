import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { RecordIdentities } from "../components/recordPresentation";
import { SeedLotSowingWizard } from "./SeedLotSowingWizard";
import { SowingDescendantWizard } from "./SowingDescendantWizard";

vi.mock("../auth/context", () => ({
  useAuth: () => ({
    state: { status: "authenticated", csrfToken: "csrf" },
    sessionExpired: vi.fn(),
  }),
}));
const identity = {
  id: "identity",
  scientific_name: "Abelmoschus esculentus",
  cultivar_name: "Burgundy",
  common_name: "Okra Burgundy",
  display_label: "Abelmoschus esculentus ‘Burgundy’",
  created_at: "2026-09-01",
  updated_at: "2026-09-01",
};
const lot = {
  id: "lot",
  label: null,
  botanical_identity_id: identity.id,
  botanical_identity: {
    id: identity.id,
    display_label: identity.display_label,
  },
  quantity: {
    kind: "seed_count",
    value: "50",
    unit: null,
    is_approximate: false,
  },
  location_id: null,
  location: null,
  lifecycle: "active",
};
const sowing = {
  id: "sowing",
  label: null,
  seed_lot_id: lot.id,
  seed_lot: {
    id: lot.id,
    label: null,
    botanical_identity_id: identity.id,
    botanical_identity_display_label: identity.display_label,
    lifecycle: "active",
  },
  quantity: {
    kind: "seed_count",
    value: "20",
    unit: null,
    is_approximate: false,
  },
  germinated_count: 12,
  location_id: null,
  lifecycle: "active",
};
function setup(overrides: Record<string, unknown> = {}) {
  const posts: { path: string; body: Record<string, unknown> }[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const path =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    let body: unknown;
    if (init?.method === "POST") {
      posts.push({
        path,
        body: JSON.parse(
          typeof init.body === "string" ? init.body : "{}",
        ) as Record<string, unknown>,
      });
      body = path.includes("plant-group")
        ? { plant_group: { id: "new-group" } }
        : path.includes("plant")
          ? { plant: { id: "new-plant" } }
          : { sowing: { id: "new-sowing" } };
    } else if (path === "/api/v1/seed-lots") body = [{ ...lot, ...overrides }];
    else if (path === "/api/v1/sowings/sowing") body = sowing;
    else if (path === "/api/v1/botanical-identities") body = [identity];
    else if (path === "/api/v1/locations") body = [];
    else throw new Error(`Unexpected request: ${path}`);
    return Promise.resolve(
      new Response(JSON.stringify(body), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
  });
  return { user: userEvent.setup(), posts };
}
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.location.hash = "";
});
function seedWizard() {
  render(
    <RecordIdentities.Provider value={new Map([[identity.id, identity]])}>
      <SeedLotSowingWizard seedLotId="lot" />
    </RecordIdentities.Provider>,
  );
}

test("guided sowing retains shared section values and submits one atomic transition only after seed usage review", async () => {
  const { user, posts } = setup();
  seedWizard();
  await screen.findByRole("heading", { name: "Source seed lot" });
  expect(
    screen.getAllByRole("link", { name: "Okra Burgundy" }).length,
  ).toBeGreaterThan(0);
  await user.type(
    screen.getByLabelText("Sowing label (optional)"),
    "Shared draft",
  );
  await user.click(screen.getByRole("button", { name: "Next" }));
  await user.type(screen.getByLabelText("Amount"), "10");
  await user.click(screen.getByRole("tab", { name: "Cultivation" }));
  await user.type(screen.getByLabelText("Substrate (optional)"), "Coir");
  await user.click(screen.getByRole("button", { name: "Back" }));
  expect(screen.getByLabelText("Amount")).toHaveValue("10");
  await user.click(screen.getByRole("tab", { name: "Essentials" }));
  expect(screen.getByLabelText("Sowing label (optional)")).toHaveValue(
    "Shared draft",
  );
  expect(posts).toHaveLength(0);
  await user.click(screen.getByRole("tab", { name: "Notes" }));
  await user.type(screen.getByLabelText("Notes (optional)"), "Keep moist");
  await user.click(screen.getByRole("button", { name: "Review seed usage" }));
  await user.click(screen.getByLabelText(/Use part of the lot/));
  expect(posts).toHaveLength(0);
  await user.click(screen.getByRole("button", { name: "Start sowing" }));
  await waitFor(() => {
    expect(posts).toHaveLength(1);
  });
  expect(posts[0]).toMatchObject({
    path: "/api/v1/seed-lots/lot/create-sowing",
    body: {
      source_adjustment: { mode: "partial", resulting_quantity: null },
      sowing: {
        label: "Shared draft",
        quantity: {
          kind: "seed_count",
          value: "10",
          unit: null,
          is_approximate: false,
        },
        substrate: "Coir",
        notes: "Keep moist",
        germinated_count: null,
        lifecycle: "active",
      },
    },
  });
});

test("guided sowing reveals a hidden invalid quantity without persisting", async () => {
  const { user, posts } = setup();
  seedWizard();
  await screen.findByRole("heading", { name: "Source seed lot" });
  await user.click(screen.getByRole("tab", { name: "Notes" }));
  await user.click(screen.getByRole("button", { name: "Review seed usage" }));
  await waitFor(() => {
    expect(
      screen.getByRole("tab", { name: "Material & location" }),
    ).toHaveAttribute("aria-selected", "true");
  });
  expect(screen.getByLabelText("Amount")).toHaveFocus();
  expect(posts).toHaveLength(0);
});

test("guided sowing keeps unknown quantity and explicit no-adjustment semantics", async () => {
  const { user, posts } = setup({ quantity: null });
  seedWizard();
  await screen.findByRole("heading", { name: "Source seed lot" });
  await user.click(screen.getByRole("tab", { name: "Notes" }));
  await user.click(screen.getByRole("button", { name: "Review seed usage" }));
  await user.click(screen.getByRole("button", { name: "Start sowing" }));
  await waitFor(() => {
    expect(posts).toHaveLength(1);
  });
  expect(posts[0].body).toMatchObject({
    sowing: { quantity: null },
    source_adjustment: { mode: "none" },
  });
});

for (const kind of ["plant", "group"] as const)
  test(`guided ${kind} reuses field groups, resolves path names and retains values before atomic creation`, async () => {
    const { user, posts } = setup();
    render(
      <RecordIdentities.Provider value={new Map([[identity.id, identity]])}>
        <SowingDescendantWizard sowingId="sowing" kind={kind} />
      </RecordIdentities.Provider>,
    );
    await screen.findByRole("heading", {
      name: kind === "plant" ? "Create Plant" : "Create Plant group",
    });
    const path = screen.getByRole("region", { name: "Propagation path" });
    expect(within(path).getAllByText("Okra Burgundy")).toHaveLength(2);
    await user.type(screen.getByLabelText("Label (optional)"), "New result");
    if (kind === "group") {
      await user.selectOptions(screen.getByLabelText("Kind"), "approximate");
      await user.type(screen.getByLabelText("Count"), "8");
    }
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText(/Originating Sowing:/)).toHaveTextContent(
      "Okra Burgundy",
    );
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByLabelText("Label (optional)")).toHaveValue("New result");
    expect(posts).toHaveLength(0);
    await user.click(screen.getByRole("tab", { name: "Lifecycle & notes" }));
    await user.type(screen.getByLabelText("Notes (optional)"), "Result note");
    await user.click(screen.getByLabelText(/Complete Sowing/));
    await user.click(
      screen.getByRole("button", {
        name: kind === "plant" ? "Create Plant" : "Create Plant group",
      }),
    );
    await waitFor(() => {
      expect(posts).toHaveLength(1);
    });
    expect(posts[0].body).toMatchObject({
      resulting_sowing_lifecycle: "completed",
      [kind === "plant" ? "plant" : "plant_group"]: {
        botanical_identity_id: identity.id,
        label: "New result",
        notes: "Result note",
        lifecycle: "active",
        ...(kind === "group"
          ? { quantity: { value: 8, is_approximate: true } }
          : {}),
      },
    });
  });
