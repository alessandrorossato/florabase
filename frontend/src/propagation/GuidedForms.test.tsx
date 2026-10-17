import { openFormSection } from "../test/formSections";
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
  await user.type(screen.getByLabelText("Sowing label"), "Shared draft");
  expect(
    screen.queryByRole("button", { name: "Next" }),
  ).not.toBeInTheDocument();
  expect(screen.getByLabelText("Amount")).toBeRequired();
  await user.type(screen.getByLabelText("Amount"), "10");
  await openFormSection(user, "Cultivation");
  await user.type(screen.getByLabelText("Substrate"), "Coir");
  expect(
    screen.queryByRole("button", { name: "Back" }),
  ).not.toBeInTheDocument();
  expect(screen.getByLabelText("Amount")).toHaveValue("10");
  await openFormSection(user, "Essentials");
  expect(screen.getByLabelText("Sowing label")).toHaveValue("Shared draft");
  expect(posts).toHaveLength(0);
  await openFormSection(user, "Notes");
  await user.type(
    screen.getByLabelText("Notes", { selector: "textarea" }),
    "Keep moist",
  );
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

test("guided sowing focuses an invalid quantity without persisting", async () => {
  const { user, posts } = setup();
  seedWizard();
  await screen.findByRole("heading", { name: "Source seed lot" });
  await openFormSection(user, "Notes");
  await user.click(screen.getByRole("button", { name: "Review seed usage" }));
  await waitFor(() => {
    expect(
      screen.getByRole("region", { name: "Material & location" }),
    ).toBeVisible();
  });
  expect(screen.getByLabelText("Amount")).toHaveFocus();
  expect(posts).toHaveLength(0);
});

test("guided sowing keeps unknown quantity and explicit no-adjustment semantics", async () => {
  const { user, posts } = setup({ quantity: null });
  seedWizard();
  await screen.findByRole("heading", { name: "Source seed lot" });
  await openFormSection(user, "Material & location");
  expect(screen.queryByLabelText("Amount")).not.toBeInTheDocument();
  expect(screen.getByLabelText("Quantity sown kind")).not.toBeRequired();
  await user.selectOptions(
    screen.getByLabelText("Quantity sown kind"),
    "weight",
  );
  expect(screen.getByLabelText("Amount")).toBeRequired();
  expect(screen.getByLabelText("Unit")).toBeRequired();
  await user.selectOptions(
    screen.getByLabelText("Quantity sown kind"),
    "unknown",
  );
  expect(screen.queryByLabelText("Amount")).not.toBeInTheDocument();
  await openFormSection(user, "Notes");
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
    expect(
      screen.queryByRole("region", { name: "Propagation path" }),
    ).not.toBeInTheDocument();
    const source = screen.getByLabelText("Creating from");
    expect(within(source).getAllByText("Okra Burgundy")).toHaveLength(2);
    expect(
      within(source)
        .getAllByRole("link")
        .map((link) => link.getAttribute("href")),
    ).toEqual(["#/seeds/lot", "#/sowings/sowing"]);
    expect(screen.getByLabelText("Botanical identity")).toHaveValue(
      identity.id,
    );
    expect(
      screen.getByRole("group", { name: "Resulting Sowing lifecycle" }),
    ).toHaveClass("sowing-state-options");
    await user.type(screen.getByLabelText("Label"), "New result");
    if (kind === "group") {
      expect(screen.queryByLabelText("Count")).not.toBeInTheDocument();
      await user.selectOptions(
        screen.getByLabelText("Quantity kind"),
        "approximate",
      );
      expect(screen.getByLabelText("Count")).toBeRequired();
      await user.type(screen.getByLabelText("Count"), "8");
    }
    expect(
      screen.queryByRole("button", { name: "Next" }),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Origin" })).getByRole("link", {
        name: "Okra Burgundy",
      }),
    ).toHaveAttribute("href", "#/sowings/sowing");
    const datePrecision = screen.getByLabelText(
      "Collection-entry date precision",
    );
    expect(
      document.querySelector('label[for="plant-entry-date-precision"]'),
    ).toHaveClass("sr-only");
    await user.selectOptions(datePrecision, "year");
    await user.clear(screen.getByLabelText("Year"));
    await user.type(screen.getByLabelText("Year"), "2026");
    expect(
      screen.queryByRole("button", { name: "Back" }),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText("Label")).toHaveValue("New result");
    expect(posts).toHaveLength(0);
    await openFormSection(user, "Lifecycle & notes");
    await user.type(
      screen.getByLabelText("Notes", { selector: "textarea" }),
      "Result note",
    );
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
        collection_entry_date: { precision: "year", year: 2026 },
        location_id: null,
        lifecycle: "active",
        ...(kind === "group"
          ? { quantity: { value: 8, is_approximate: true } }
          : {}),
      },
    });
  });

test("guided Sowing state presents four compact named choices and only the selected consequence", async () => {
  const { user, posts } = setup();
  render(<SowingDescendantWizard sowingId="sowing" kind="plant" />);
  await screen.findByRole("heading", { name: "Create Plant" });
  const group = screen.getByRole("group", {
    name: "Resulting Sowing lifecycle",
  });
  expect(within(group).getAllByRole("radio")).toHaveLength(4);
  expect(
    within(group).getByRole("radio", { name: "Keep active" }),
  ).toBeChecked();
  expect(group.querySelectorAll("small")).toHaveLength(0);
  for (const [name, state] of [
    ["Complete Sowing", "completed"],
    ["Mark failed", "failed"],
    ["Abandon Sowing", "abandoned"],
  ]) {
    await user.click(within(group).getByRole("radio", { name }));
    expect(document.getElementById("descendant-state-help")).toHaveTextContent(
      `The Sowing will be marked ${state} in the same operation.`,
    );
  }
  await user.click(within(group).getByRole("radio", { name: "Keep active" }));
  expect(document.getElementById("descendant-state-help")).toHaveTextContent(
    "counts do not complete it automatically",
  );
  expect(posts).toHaveLength(0);
});
