import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { App } from "./App";

const identity = {
  id: "01900000-0000-7000-8000-000000000099",
  scientific_name: "Abelmoschus esculentus L.",
  cultivar_name: "Okra Burgundy",
  common_name: "Red okra",
  display_label: "Abelmoschus esculentus L. ‘Okra Burgundy’",
  compact_cover_kind: "local",
  collection_counts: { seed_lots: 1, sowings: 1, plants: 2, plant_groups: 0 },
  created_at: "2026-09-01T10:00:00Z",
  updated_at: "2026-09-01T10:00:00Z",
};
const external = {
  ...identity,
  id: "external",
  scientific_name: "Acer palmatum",
  cultivar_name: null,
  display_label: "Acer palmatum",
  compact_cover_kind: "external",
  compact_external_cover_url: "https://images.example.test/acer.jpg",
};
const empty = {
  ...identity,
  id: "empty",
  scientific_name: "Acer rubrum",
  cultivar_name: null,
  display_label: "Acer rubrum",
  compact_cover_kind: null,
};
const externalCover = {
  kind: "external",
  id: "01900000-0000-7000-8000-000000000601",
  image_url: "https://images.example.test/acer.jpg",
  source_url: "https://example.test/acer",
  attribution: "Ada Example",
  licence_label: "CC BY 4.0",
  licence_url: "https://creativecommons.org/licenses/by/4.0/",
  created_at: "2026-09-14T08:00:00Z",
  updated_at: "2026-09-14T08:00:00Z",
};
function json(value: unknown) {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
function setup(hash = "#/identities", mobile = false) {
  window.history.replaceState(null, "", hash);
  vi.spyOn(window, "matchMedia").mockReturnValue({
    matches: mobile,
  } as MediaQueryList);
  const requested: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const path =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    requested.push(path);
    if (path.endsWith("/auth/session"))
      return Promise.resolve(
        json({ user_id: "owner", login_name: "owner", owner: true }),
      );
    if (path.endsWith("/auth/csrf"))
      return Promise.resolve(json({ csrf_token: "csrf" }));
    if (path.endsWith("/health"))
      return Promise.resolve(json({ status: "ok" }));
    if (path === "/api/v1/botanical-identities")
      return Promise.resolve(json([identity, external, empty]));
    if (path.endsWith("/external/cover-image"))
      return Promise.resolve(json(externalCover));
    if (path.endsWith("/cover-image")) return Promise.resolve(json(null));
    if (path.endsWith("/collection"))
      return Promise.resolve(
        json({
          identity,
          seed_lots: [],
          sowings: [],
          plants: [],
          plant_groups: [],
          events: [],
        }),
      );
    if (path.endsWith("/external-taxon-link"))
      return Promise.resolve(json(null));
    if (path.endsWith("/profile"))
      return Promise.resolve(
        new Response(
          JSON.stringify({ detail: { code: "botanical_profile_not_found" } }),
          { status: 404 },
        ),
      );
    if (
      path.endsWith("/profile/native-ranges") ||
      path.endsWith("/geographic-places")
    )
      return Promise.resolve(json([]));
    throw new Error(`Unexpected request ${path}`);
  });
  return requested;
}
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("directory hierarchy renders configured covers and shares them with Quick Preview", async () => {
  const requested = setup();
  const user = userEvent.setup();
  render(<App />);
  const card = await screen.findByRole("button", {
    name: /Abelmoschus.*Okra Burgundy/,
  });
  expect(within(card).getByText("Abelmoschus esculentus L.").tagName).toBe("I");
  expect(within(card).getByText("‘Okra Burgundy’")).toBeInTheDocument();
  expect(card).toHaveTextContent("1 seed lot · 2 plants");
  expect(card).not.toHaveTextContent("Selected");
  expect(within(card).getByRole("img")).toHaveAttribute(
    "src",
    `/api/v1/botanical-identities/${identity.id}/cover-image/thumbnail`,
  );
  const noCover = screen.getByRole("button", { name: /Acer rubrum/ });
  expect(within(noCover).getByText("No cover image")).toBeInTheDocument();
  expect(within(noCover).queryByRole("img")).not.toBeInTheDocument();
  const externalCard = screen.getByRole("button", { name: /Acer palmatum/ });
  const directoryExternalImage = within(externalCard).getByRole("img");
  expect(directoryExternalImage).toHaveAttribute(
    "src",
    externalCover.image_url,
  );
  expect(directoryExternalImage).toHaveAttribute(
    "referrerpolicy",
    "no-referrer",
  );
  expect(directoryExternalImage).toHaveAttribute("loading", "lazy");
  card.focus();
  expect(card).toHaveFocus();
  expect(card).toHaveAttribute("aria-pressed", "false");
  await user.keyboard("{Enter}");
  expect(card).toHaveAttribute("aria-pressed", "true");
  await user.tab();
  expect(card).not.toHaveFocus();
  expect(card).toHaveAttribute("aria-pressed", "true");
  const preview = screen.getByRole("complementary", { name: "Quick preview" });
  expect(
    within(preview).getByRole("link", { name: "Open details" }),
  ).toHaveAttribute("href", `#/identities/${identity.id}`);
  expect(
    within(preview).getByLabelText("Active collection records"),
  ).toHaveTextContent("Seed lots1Sowings1Plants2Plant groups0");
  expect(within(preview).queryByRole("tablist")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /Acer palmatum/ }));
  const externalImage = await within(preview).findByRole("img", {
    name: "Cover for Acer palmatum",
  });
  expect(externalImage).toHaveAttribute("src", externalCover.image_url);
  expect(externalImage).toHaveAttribute("referrerpolicy", "no-referrer");
  expect(externalImage).toHaveAttribute("loading", "lazy");
  expect(within(externalCard).getByRole("img")).toHaveAttribute(
    "src",
    externalCover.image_url,
  );
  expect(within(externalCard).getByRole("img")).toHaveAttribute(
    "referrerpolicy",
    "no-referrer",
  );
  expect(
    requested.filter((path) => path.startsWith("/api/v1/botanical-identities")),
  ).toEqual(["/api/v1/botanical-identities"]);
});

test("open details, browser back and forward preserve the directory and dedicated record boundary", async () => {
  setup();
  const user = userEvent.setup();
  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: /Abelmoschus.*Okra Burgundy/ }),
  );
  await user.click(screen.getByRole("link", { name: "Open details" }));
  const title = await screen.findByRole("heading", {
    level: 2,
    name: identity.display_label,
  });
  expect(title).toHaveFocus();
  expect(
    screen.queryByRole("region", { name: "Identity directory" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("tablist", { name: "Record sections" }),
  ).toHaveTextContent("OverviewCollectionReferenceEvents");
  expect(
    screen.getByRole("region", { name: identity.display_label }),
  ).toContainElement(title);
  expect(document.querySelectorAll(".entity-hero")).toHaveLength(0);
  act(() => {
    window.history.back();
  });
  const card = await screen.findByRole("button", {
    name: /Abelmoschus.*Okra Burgundy/,
  });
  expect(card).toHaveAttribute("aria-pressed", "true");
  expect(card).toHaveFocus();
  act(() => {
    window.history.forward();
  });
  expect(
    await screen.findByRole("heading", {
      level: 2,
      name: identity.display_label,
    }),
  ).toBeInTheDocument();
});

test("mobile card activation opens the dedicated detail directly", async () => {
  setup("#/identities", true);
  const user = userEvent.setup();
  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: /Abelmoschus.*Okra Burgundy/ }),
  );
  expect(
    await screen.findByRole("heading", {
      level: 2,
      name: identity.display_label,
    }),
  ).toBeInTheDocument();
  expect(window.location.hash).toBe(`#/identities/${identity.id}`);
  expect(
    screen.queryByRole("complementary", { name: "Quick preview" }),
  ).not.toBeInTheDocument();
});

test("legacy collection deep links and same-record navigation restore the right accessible panel", async () => {
  setup(`#/identities/${identity.id}?tab=sowings`);
  const user = userEvent.setup();
  render(<App />);
  expect(
    await screen.findByRole("tab", { name: "Collection" }),
  ).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("tab", { name: "Sowings" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await user.click(screen.getByRole("tab", { name: "Plants / Plant groups" }));
  expect(
    await screen.findByRole("tabpanel", { name: "Plants / Plant groups" }),
  ).toBeInTheDocument();
  act(() => {
    window.history.pushState(
      null,
      "",
      `#/identities/${identity.id}?tab=events`,
    );
    window.dispatchEvent(new PopStateEvent("popstate"));
  });
  expect(await screen.findByRole("tab", { name: "Events" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(
    await screen.findByRole("tabpanel", { name: "Events" }),
  ).toBeInTheDocument();
});

test("Reference stays lazy and exposes one read-first module at a time", async () => {
  const requested = setup(`#/identities/${identity.id}`);
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", {
    level: 2,
    name: identity.display_label,
  });
  expect(
    screen.getByRole("link", { name: "Add seed lot" }),
  ).toBeInTheDocument();
  expect(
    requested.some((path) => /profile|external-taxon|occurrence/.test(path)),
  ).toBe(false);
  await user.click(
    await screen.findByText("Add cover", { selector: "summary" }),
  );
  await user.click(screen.getByRole("button", { name: "Set cover image" }));
  expect(screen.getByRole("dialog")).toHaveTextContent("Upload image");
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Set cover image" })).toHaveFocus();
  await user.click(screen.getByRole("tab", { name: "Reference" }));
  expect(document.querySelector(".identity-summary")).not.toBeInTheDocument();
  expect(document.querySelector(".identity-work-header")).toBeInTheDocument();
  expect(
    screen.getByRole("tablist", { name: "Reference sections" }),
  ).toHaveTextContent("ProfileNative rangeBotanical sourceOccurrences");
  await screen.findByText("No botanical profile yet.");
  expect(screen.queryByRole("heading", { name: "Native range" })).toBeNull();
  expect(
    screen.queryByRole("heading", { name: "External botanical source" }),
  ).toBeNull();
  expect(screen.queryByRole("textbox", { name: "Description" })).toBeNull();
  expect(screen.queryByLabelText("Geographic place")).toBeNull();
  await user.click(screen.getByRole("button", { name: "Add profile" }));
  expect(screen.getByRole("textbox", { name: "Description" })).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Cancel" }));
  expect(screen.queryByRole("textbox", { name: "Description" })).toBeNull();
  await waitFor(() => {
    expect(screen.getByRole("button", { name: "Add profile" })).toHaveFocus();
  });
  await user.click(screen.getByRole("tab", { name: "Native range" }));
  expect(screen.queryByText("No botanical profile yet.")).toBeNull();
  await user.click(screen.getByRole("button", { name: "Manage native range" }));
  expect(screen.getByLabelText("Geographic place")).toBeVisible();
  await waitFor(() => {
    expect(screen.getByRole("button", { name: "Done" })).toHaveFocus();
  });
  await user.click(screen.getByRole("button", { name: "Done" }));
  await waitFor(() => {
    expect(
      screen.getByRole("button", { name: "Manage native range" }),
    ).toHaveFocus();
  });
  expect(requested.some((path) => path.endsWith("/profile"))).toBe(true);
  expect(requested.some((path) => path.includes("occurrence"))).toBe(false);
  await user.click(screen.getByRole("tab", { name: "Botanical source" }));
  expect(
    await screen.findByRole("heading", { name: "External botanical source" }),
  ).toBeInTheDocument();
  expect(screen.queryByText("Occurrence evidence")).toBeNull();
  await user.click(screen.getByRole("tab", { name: "Occurrences" }));
  expect(
    await screen.findByRole("heading", { name: "Occurrences" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Occurrence evidence")).toBeInTheDocument();
  expect(screen.queryByText("No botanical profile yet.")).toBeNull();
  expect(requested.some((path) => path.includes("occurrence"))).toBe(false);
});

test("work tabs replace the rich Overview summary with compact identity context", async () => {
  setup(`#/identities/${identity.id}`);
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", {
    level: 2,
    name: identity.display_label,
  });
  expect(document.querySelector(".identity-summary")).toBeInTheDocument();
  expect(document.querySelector(".identity-work-header")).toBeNull();
  await user.click(screen.getByRole("tab", { name: "Collection" }));
  expect(document.querySelector(".identity-summary")).toBeNull();
  expect(document.querySelector(".identity-work-header")).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Seeds" })).toBeInTheDocument();
  await user.click(screen.getByRole("tab", { name: "Events" }));
  expect(document.querySelector(".identity-summary")).toBeNull();
  expect(document.querySelector(".identity-work-header")).toBeInTheDocument();
});

test("identity forms use named grouping with existing help and close with predictable focus", async () => {
  setup();
  const user = userEvent.setup();
  render(<App />);
  const create = await screen.findByRole("button", {
    name: "+ New botanical identity",
  });
  await user.click(create);
  const dialog = screen.getByRole("dialog", {
    name: "Create a botanical identity",
  });
  const fields = screen.getByRole("group", { name: "Botanical name" });
  expect(dialog).toContainElement(fields);
  expect(within(fields).getByLabelText("Scientific name")).toHaveFocus();
  expect(
    within(fields).getByLabelText("Scientific name"),
  ).toHaveAccessibleDescription(/without implying.*lineage/);
  expect(within(fields).getByLabelText("Cultivar")).toHaveAccessibleDescription(
    /without quotation marks/,
  );
  await user.click(screen.getByRole("button", { name: "Cancel" }));
  await waitFor(() => {
    expect(create).toHaveFocus();
  });
  await user.click(create);
  await user.keyboard("{Escape}");
  expect(
    screen.queryByRole("dialog", { name: "Create a botanical identity" }),
  ).not.toBeInTheDocument();
  expect(create).toHaveFocus();
});

test("broken thumbnails have an intentional local fallback", async () => {
  setup();
  render(<App />);
  const card = await screen.findByRole("button", {
    name: /Abelmoschus.*Okra Burgundy/,
  });
  fireEvent.error(within(card).getByRole("img"));
  expect(within(card).queryByRole("img")).not.toBeInTheDocument();
  expect(within(card).getByText("Cover unavailable")).toBeInTheDocument();
});

test("broken configured external covers fall back inside their directory card", async () => {
  setup();
  render(<App />);
  const card = await screen.findByRole("button", { name: /Acer palmatum/ });
  fireEvent.error(within(card).getByRole("img"));
  expect(within(card).queryByRole("img")).not.toBeInTheDocument();
  expect(within(card).getByText("Cover unavailable")).toBeInTheDocument();
});

test("identity overflow keeps delete anchored and restores trigger focus on Escape", async () => {
  setup(`#/identities/${identity.id}`);
  const user = userEvent.setup();
  render(<App />);
  const more = await screen.findByLabelText("More botanical identity actions");
  await user.click(more);
  expect(screen.getByRole("button", { name: "Delete" })).toBeVisible();
  await user.keyboard("{Escape}");
  expect(more).toHaveFocus();
  expect(more.closest("details")).not.toHaveAttribute("open");
});

test("edit validation stays linked to the field and retains contextual help", async () => {
  setup(`#/identities/${identity.id}?tab=edit`);
  const original = vi.mocked(globalThis.fetch).getMockImplementation();
  if (!original) throw new Error("Missing request fixture");
  vi.mocked(globalThis.fetch).mockImplementation((input, init) => {
    if (init?.method === "PUT")
      return Promise.resolve(
        new Response(
          JSON.stringify({
            detail: [
              {
                loc: ["body", "scientific_name"],
                type: "value_error",
                msg: "Value must not be blank",
              },
            ],
          }),
          { status: 422 },
        ),
      );
    return original(input, init);
  });
  const user = userEvent.setup();
  render(<App />);
  const scientificName = await screen.findByLabelText("Scientific name");
  await user.clear(scientificName);
  await user.type(scientificName, "   ");
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Scientific name cannot be blank.",
  );
  expect(scientificName).toHaveAttribute("aria-invalid", "true");
  expect(scientificName).toHaveAccessibleDescription(
    /without implying.*lineage.*Scientific name cannot be blank/,
  );
  expect(screen.getByRole("button", { name: "Save changes" })).toBeEnabled();
});
