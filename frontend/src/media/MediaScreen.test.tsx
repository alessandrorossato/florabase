import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { MediaScreen } from "./MediaScreen";
import { MediaPicker } from "./MediaPicker";
import { MediaLinker } from "./MediaLinker";
import { MediaPreview } from "./MediaPreview";
import type { MediaAsset, MediaDetail, MediaLink } from "./api";

const assetId = "01900000-0000-7000-8000-000000000910";
const recordId = "01900000-0000-7000-8000-000000000911";
const linkId = "01900000-0000-7000-8000-000000000912";
const auth: AuthContextValue = {
  state: {
    status: "authenticated",
    session: {
      user_id: recordId,
      login_name: "owner",
      display_name: "Owner",
      owner: true,
      canonical_origin: "http://localhost:5173",
    },
    csrfToken: "test-csrf",
  },
  logIn: vi.fn(),
  logOut: vi.fn(),
  sessionExpired: vi.fn(),
  retryRestoration: vi.fn(),
  cancelLogout: vi.fn(),
};
function requestUrl(input: RequestInfo | URL): string {
  return typeof input === "string"
    ? input
    : input instanceof URL
      ? input.href
      : input.url;
}
function asset(changes: Partial<MediaAsset> = {}): MediaAsset {
  return {
    id: assetId,
    kind: "local",
    title: "Garden image",
    attribution: "Gardener",
    licence_label: null,
    licence_url: null,
    image_url: null,
    source_url: null,
    original_filename: "garden.png",
    media_type: "image/png",
    byte_size: 1024,
    width: 640,
    height: 320,
    fetched_at: null,
    local_copy_cleanup_pending: false,
    deletion_pending: false,
    content_url: `/api/v1/attachments/${assetId}/content`,
    thumbnail_url: `/api/v1/media-assets/${assetId}/thumbnail`,
    collection_link_count: 0,
    cover_reference_count: 0,
    can_delete: true,
    created_at: "2026-10-01T10:00:00Z",
    updated_at: "2026-10-01T10:00:00Z",
    ...changes,
  };
}
function link(changes: Partial<MediaLink> = {}): MediaLink {
  return {
    id: linkId,
    media_asset_id: assetId,
    target_type: "plant",
    target_id: recordId,
    target_label: "Plant A",
    target_url: `#/plants/${recordId}`,
    caption: "In the garden",
    display_order: 2,
    is_primary: false,
    created_at: "2026-10-01T10:00:00Z",
    updated_at: "2026-10-01T10:00:00Z",
    ...changes,
  };
}
function detail(changes: Partial<MediaDetail> = {}): MediaDetail {
  return { ...asset(), links: [], covers: [], ...changes };
}
function json(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
function page(items: MediaAsset[], total = items.length, offset = 0) {
  return { items, total, limit: 24, offset };
}
function mount(node: React.ReactNode) {
  return render(
    <AuthContext.Provider value={auth}>{node}</AuthContext.Provider>,
  );
}
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

test("Gallery distinguishes source and references, uses thumbnails and filters/paginates", async () => {
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: false })),
  );
  const external = asset({
    id: recordId,
    kind: "external",
    title: "Remote reference",
    image_url: "https://images.example.test/image.jpg",
    source_url: "https://example.test/source",
    thumbnail_url: null,
    content_url: null,
    original_filename: null,
    media_type: null,
  });
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = requestUrl(input);
    return Promise.resolve(
      json(
        page(
          url.includes("association=unlinked")
            ? [external]
            : [
                asset({ cover_reference_count: 1, can_delete: false }),
                external,
              ],
          30,
          url.includes("offset=24") ? 24 : 0,
        ),
      ),
    );
  });
  const user = userEvent.setup();
  mount(<MediaScreen />);
  await screen.findByRole("button", { name: /Garden image/ });
  expect(screen.getByLabelText("Directory results")).toHaveTextContent(
    "2 of 30 records",
  );
  expect(screen.getByRole("img", { name: "Garden image" })).toHaveAttribute(
    "src",
    `/api/v1/media-assets/${assetId}/thumbnail`,
  );
  expect(
    screen.queryByRole("img", { name: "Remote reference" }),
  ).not.toBeInTheDocument();
  expect(screen.getByText(/1 cover reference/)).toBeVisible();
  await user.click(screen.getByRole("button", { name: /Garden image/ }));
  expect(
    screen.getByRole("link", { name: "Open media details" }),
  ).toHaveAttribute("href", `#/media/${assetId}`);
  await user.selectOptions(screen.getByLabelText("Record links"), "unlinked");
  await waitFor(() => {
    expect(fetch).toHaveBeenLastCalledWith(
      expect.stringContaining("association=unlinked"),
      expect.anything(),
    );
  });
  expect(await screen.findByText("1 of 30 records")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Next media" }));
  await waitFor(() => {
    expect(fetch).toHaveBeenLastCalledWith(
      expect.stringContaining("offset=24"),
      expect.anything(),
    );
  });
  expect(await screen.findByText("1 of 30 records")).toBeVisible();
  expect(
    fetch.mock.calls.every(([input]) => requestUrl(input).startsWith("/api/")),
  ).toBe(true);
});

test("cover-only asset cannot be deleted and cover reference is separate from record links", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    json(
      detail({
        cover_reference_count: 1,
        can_delete: false,
        covers: [
          {
            id: linkId,
            botanical_identity_id: recordId,
            label: "Garden species",
            url: `#/identities/${recordId}`,
          },
        ],
      }),
    ),
  );
  mount(<MediaScreen initialId={assetId} />);
  await screen.findByRole("heading", { name: "Garden image" });
  expect(
    screen.getByRole("button", { name: "Delete media asset" }),
  ).toBeDisabled();
  expect(screen.getByText(/Deletion blocked: 0 record link/)).toBeVisible();
  expect(screen.getByRole("link", { name: "Garden species" })).toHaveAttribute(
    "href",
    `#/identities/${recordId}`,
  );
  expect(screen.getByText(/No record links. This asset remains/)).toBeVisible();
});

test.each(["plant", "supplier"] as const)(
  "detail edits %s link context, selects primary and unlinks only the chosen record",
  async (target) => {
    let value = detail({
      collection_link_count: 2,
      can_delete: false,
      links: [
        link({ target_type: target }),
        link({
          id: recordId,
          target_label: "Plant B",
          target_id: linkId,
          caption: "Second plant",
        }),
      ],
    });
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation((input, init) => {
        const url = requestUrl(input);
        if (init?.method === "PATCH") {
          value.links[0] = {
            ...value.links[0],
            caption: "Changed caption",
            display_order: 7,
          };
          return Promise.resolve(json(value.links[0]));
        }
        if (init?.method === "PUT") {
          value.links[0].is_primary = true;
          return Promise.resolve(
            json({
              kind: "local",
              photo_id: linkId,
              thumbnail_url: asset().thumbnail_url,
            }),
          );
        }
        if (init?.method === "DELETE") {
          value = {
            ...value,
            collection_link_count: 1,
            links: value.links.slice(1),
          };
          return Promise.resolve(new Response(null, { status: 204 }));
        }
        if (url.includes("media-assets")) return Promise.resolve(json(value));
        throw new Error(url);
      });
    const user = userEvent.setup();
    mount(<MediaScreen initialId={assetId} />);
    await screen.findByText("In the garden");
    await user.click(
      screen.getAllByRole("button", { name: "Edit link details" })[0],
    );
    const editor = screen.getByRole("dialog", {
      name: "Edit record link details",
    });
    await user.clear(within(editor).getByLabelText("Caption for this record"));
    await user.type(
      within(editor).getByLabelText("Caption for this record"),
      "Changed caption",
    );
    await user.clear(
      within(editor).getByLabelText("Display order for this record"),
    );
    await user.type(
      within(editor).getByLabelText("Display order for this record"),
      "7",
    );
    await user.click(
      within(editor).getByRole("button", { name: "Save link details" }),
    );
    await screen.findByText("Changed caption");
    expect(fetch).toHaveBeenCalledWith(
      `/api/v1/media-links/${linkId}`,
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ caption: "Changed caption", display_order: 7 }),
      }),
    );
    await user.click(
      screen.getAllByRole("button", { name: "Set as primary" })[0],
    );
    await screen.findByRole("button", { name: "Clear primary" });
    expect(fetch).toHaveBeenCalledWith(
      `/api/v1/collection-records/${target}/${recordId}/primary-photo`,
      expect.objectContaining({ method: "PUT" }),
    );
    await user.click(
      screen.getAllByRole("button", { name: "Unlink from this record" })[0],
    );
    const confirmation = screen.getByRole("dialog", {
      name: "Unlink from this record?",
    });
    expect(
      within(confirmation).getByText(
        /asset, other links and cover references remain/,
      ),
    ).toBeVisible();
    await user.click(
      within(confirmation).getByRole("button", {
        name: "Unlink from this record",
      }),
    );
    await screen.findByText(
      "Record link removed. Media retained in the library.",
    );
    expect(screen.getByRole("link", { name: "Plant B" })).toBeVisible();
    expect(
      screen.queryByRole("link", { name: "Plant A" }),
    ).not.toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalledWith(
      `/api/v1/media-assets/${assetId}`,
      expect.objectContaining({ method: "DELETE" }),
    );
  },
);

test("Gallery uploads an unlinked original and keeps failure input recoverable", async () => {
  let saved = false;
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((_input, init) => {
      if (init?.method === "POST") {
        saved = true;
        return Promise.resolve(json(asset(), 201));
      }
      return Promise.resolve(json(page(saved ? [asset()] : [])));
    });
  const user = userEvent.setup();
  mount(<MediaScreen />);
  await screen.findByText(/No matching media/);
  await user.click(screen.getByRole("button", { name: "Add new media" }));
  const editor = screen.getByRole("dialog", { name: "Add new media" });
  await user.upload(
    within(editor).getByLabelText("Image file"),
    new File(["image"], "garden.png", { type: "image/png" }),
  );
  await user.type(within(editor).getByLabelText("Title"), "Garden image");
  const form = editor.querySelector("form");
  if (!form) throw new Error("Media upload form missing");
  fireEvent.submit(form);
  await screen.findByText("Media asset added to the library.");
  const upload = fetch.mock.calls.find(([, init]) => init?.method === "POST");
  expect(upload?.[0]).toBe("/api/v1/media-assets/local");
  expect(upload?.[1]?.body).toBeInstanceOf(FormData);
  expect((upload?.[1]?.body as FormData).get("file")).toBeInstanceOf(File);
  expect(new Headers(upload?.[1]?.headers).get("X-CSRF-Token")).toBe(
    "test-csrf",
  );
  expect(new Headers(upload?.[1]?.headers).get("Content-Type")).toBeNull();
});

test("Link existing picker reuses the asset ID with independent caption/order and duplicate errors", async () => {
  const onLinked = vi.fn();
  let conflict = true;
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((_input, init) =>
      init?.method === "POST"
        ? Promise.resolve(
            conflict
              ? json(
                  {
                    detail: {
                      message: "This record already links to that media asset.",
                    },
                  },
                  409,
                )
              : json(link(), 201),
          )
        : Promise.resolve(json(page([asset()]))),
    );
  const user = userEvent.setup();
  mount(
    <MediaPicker
      target="plant"
      targetId={recordId}
      targetLabel="Plant A"
      onClose={vi.fn()}
      onLinked={onLinked}
    />,
  );
  await user.click(await screen.findByRole("button", { name: /Garden image/ }));
  await user.type(
    screen.getByLabelText("Caption for this record"),
    "Evidence for A",
  );
  await user.click(screen.getByRole("button", { name: "Link to this record" }));
  await screen.findByText("This record already links to that media asset.");
  expect(onLinked).not.toHaveBeenCalled();
  conflict = false;
  await user.click(screen.getByRole("button", { name: "Link to this record" }));
  await waitFor(() => {
    expect(onLinked).toHaveBeenCalledOnce();
  });
  expect(fetch).toHaveBeenCalledWith(
    `/api/v1/collection-records/plant/${recordId}/media-links`,
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        caption: "Evidence for A",
        display_order: 0,
        media_asset_id: assetId,
      }),
    }),
  );
  expect(
    fetch.mock.calls.some(([, init]) => init?.body instanceof FormData),
  ).toBe(false);
});

test("detail linker supports one-record-at-a-time selection without unsupported targets", async () => {
  const onLinked = vi.fn();
  vi.spyOn(globalThis, "fetch").mockImplementation((_input, init) =>
    Promise.resolve(
      json(
        init?.method === "POST"
          ? link()
          : {
              items: [{ id: recordId, label: "Plant A" }],
              total: 1,
              limit: 20,
              offset: 0,
            },
      ),
    ),
  );
  const user = userEvent.setup();
  mount(<MediaLinker asset={asset()} onClose={vi.fn()} onLinked={onLinked} />);
  await user.click(await screen.findByRole("radio", { name: "Plant A" }));
  expect(screen.getByRole("option", { name: "Supplier" })).toBeInTheDocument();
  expect(
    screen.queryByRole("option", { name: "BotanicalIdentity" }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Link media" }));
  await waitFor(() => {
    expect(onLinked).toHaveBeenCalledOnce();
  });
});

test("external reference stays unloaded until explicit opt-in and failures show a placeholder", async () => {
  const external = asset({
    kind: "external",
    image_url: "https://images.example.test/photo.jpg",
    thumbnail_url: null,
    content_url: null,
  });
  const user = userEvent.setup();
  mount(<MediaPreview asset={external} full allowExternal />);
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  expect(screen.getByText(/including your IP address/)).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Preview once" }));
  const image = screen.getByRole("img", { name: "Garden image" });
  expect(image).toHaveAttribute("referrerpolicy", "no-referrer");
  expect(image).toHaveAttribute("src", external.image_url);
});

test("asset deletion is separate, confirmed and server reference guards stay visible", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((_input, init) =>
      Promise.resolve(
        init?.method === "DELETE"
          ? json(
              {
                detail: {
                  message: "Cannot delete: 1 cover reference remains.",
                },
              },
              409,
            )
          : json(detail()),
      ),
    );
  const user = userEvent.setup();
  mount(<MediaScreen initialId={assetId} />);
  await user.click(
    await screen.findByRole("button", { name: "Delete media asset" }),
  );
  const confirmation = screen.getByRole("dialog", {
    name: "Delete media asset permanently?",
  });
  expect(within(confirmation).getByText(/permanently deleted/)).toBeVisible();
  await user.click(
    within(confirmation).getByRole("button", { name: "Delete media asset" }),
  );
  expect(await within(confirmation).findByRole("alert")).toHaveTextContent(
    "Cannot delete: 1 cover reference remains.",
  );
  expect(fetch).toHaveBeenCalledWith(
    `/api/v1/media-assets/${assetId}`,
    expect.objectContaining({ method: "DELETE" }),
  );
});

test("external detail explicitly saves, refreshes and removes the persistent local copy", async () => {
  const user = userEvent.setup();
  let current = detail({
    kind: "external",
    image_url: "https://images.example.test/image.png",
    source_url: "https://example.test/source",
    content_url: null,
    thumbnail_url: null,
    links: [link()],
    can_delete: false,
  });
  const mutations: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, options?: RequestInit) => {
      const path = requestUrl(input);
      if (options?.method === "POST") {
        mutations.push(path);
        current = {
          ...current,
          content_url: `/api/v1/attachments/${String(mutations.length)}/content`,
          thumbnail_url: `/api/v1/media-assets/${assetId}/thumbnail?v=${String(mutations.length)}`,
          fetched_at: "2026-10-01T12:00:00Z",
        };
      }
      if (options?.method === "DELETE") {
        mutations.push(path);
        current = {
          ...current,
          content_url: null,
          thumbnail_url: null,
          fetched_at: null,
        };
      }
      return Promise.resolve(json(current));
    }),
  );
  mount(<MediaScreen initialId={assetId} />);
  expect(
    await screen.findByRole("button", { name: "Save local copy" }),
  ).toBeVisible();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Preview once" })).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Save local copy" }));
  expect(
    await screen.findByText("External reference · local copy saved"),
  ).toBeVisible();
  expect(screen.getByText("2026-10-01")).toBeVisible();
  expect(screen.getByRole("img")).toHaveAttribute(
    "src",
    "/api/v1/attachments/1/content",
  );
  expect(
    screen.queryByRole("button", { name: "Preview once" }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Refresh local copy" }));
  await waitFor(() => {
    expect(screen.getByRole("img")).toHaveAttribute(
      "src",
      "/api/v1/attachments/2/content",
    );
  });
  await user.click(screen.getByRole("button", { name: "Remove local copy" }));
  const dialog = screen.getByRole("dialog", { name: "Remove local copy?" });
  expect(
    within(dialog).getByText(
      /record links, primary selections and covers remain/,
    ),
  ).toBeVisible();
  await user.click(
    within(dialog).getByRole("button", { name: "Remove local copy" }),
  );
  expect(
    await screen.findByRole("button", { name: "Save local copy" }),
  ).toBeVisible();
  expect(screen.getByRole("link", { name: "Plant A" })).toBeVisible();
  expect(mutations).toEqual([
    `/api/v1/media-assets/${assetId}/save-local-copy`,
    `/api/v1/media-assets/${assetId}/refresh-local-copy`,
    `/api/v1/media-assets/${assetId}/local-copy`,
  ]);
});

test("failed refresh explains the error and keeps the saved image", async () => {
  const user = userEvent.setup();
  const current = detail({
    kind: "external",
    image_url: "https://images.example.test/image.png",
    fetched_at: "2026-10-01T12:00:00Z",
  });
  vi.stubGlobal(
    "fetch",
    vi.fn((_input: RequestInfo | URL, options?: RequestInit) =>
      Promise.resolve(
        options?.method === "POST"
          ? json(
              {
                detail: {
                  code: "external_fetch_failed",
                  message: "The external image is unavailable. Try again.",
                },
              },
              422,
            )
          : json(current),
      ),
    ),
  );
  mount(<MediaScreen initialId={assetId} />);
  await user.click(
    await screen.findByRole("button", { name: "Refresh local copy" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "The external image is unavailable.",
  );
  expect(screen.getByRole("img")).toHaveAttribute("src", current.content_url);
});

test("Gallery and Quick Preview use only the protected snapshot of an external asset", async () => {
  const user = userEvent.setup();
  const stored = asset({
    kind: "external",
    image_url: "https://images.example.test/image.png",
    fetched_at: "2026-10-01T12:00:00Z",
  });
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: false })),
  );
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(json(page([stored])))),
  );
  mount(<MediaScreen />);
  await user.click(await screen.findByRole("button", { name: /Garden image/ }));
  expect(
    screen
      .getAllByRole("img")
      .every((image) => image.getAttribute("src") === stored.thumbnail_url),
  ).toBe(true);
  expect(
    screen.queryByRole("button", { name: "Preview once" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getAllByText("External reference · local copy saved"),
  ).toHaveLength(2);
});

test("Target presets compose with source/search/pagination and keep explicit shared contexts", async () => {
  const onlySupplier = asset({
    title: "Supplier only",
    collection_link_count: 1,
  });
  const shared = asset({
    id: recordId,
    title: "Shared Supplier + Plant",
    collection_link_count: 3,
  });
  const onlyPlant = asset({
    id: linkId,
    title: "Plant only",
    collection_link_count: 1,
  });
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const params = new URL(requestUrl(input), "http://localhost").searchParams;
    const target = params.get("target");
    const items =
      target === "supplier"
        ? [onlySupplier, shared]
        : target === "collection" || target === "plant"
          ? [shared, onlyPlant]
          : target
            ? []
            : [onlySupplier, shared, onlyPlant];
    return Promise.resolve(json(page(items, items.length)));
  });
  const user = userEvent.setup();
  mount(<MediaScreen />);
  await screen.findByRole("button", { name: /Supplier only/ });
  const filter = screen.getByRole("combobox", { name: "Target" });
  expect(
    within(filter).getByRole("option", { name: "Suppliers" }),
  ).toBeInTheDocument();
  await user.selectOptions(filter, "collection");
  await screen.findByRole("button", { name: /Plant only/ });
  await waitFor(() => {
    expect(
      screen.queryByRole("button", { name: /Supplier only/ }),
    ).not.toBeInTheDocument();
  });
  expect(
    screen.getByRole("button", { name: /Shared Supplier \+ Plant/ }),
  ).toBeInTheDocument();
  await user.selectOptions(filter, "supplier");
  await screen.findByRole("button", { name: /Supplier only/ });
  expect(
    screen.queryByRole("button", { name: /Plant only/ }),
  ).not.toBeInTheDocument();
  await user.selectOptions(filter, "plant");
  await screen.findByRole("button", { name: /Plant only/ });
  expect(
    screen.queryByRole("button", { name: /Supplier only/ }),
  ).not.toBeInTheDocument();
  await user.selectOptions(filter, "seed_lot");
  await screen.findByText(/No matching media/);
  await user.selectOptions(filter, "");
  await screen.findByRole("button", { name: /Supplier only/ });
  await user.selectOptions(filter, "supplier");
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "Shared" },
  });
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Source" }),
    "external",
  );
  await waitFor(() => {
    expect(
      fetch.mock.calls.some(([input]) => {
        const p = new URL(requestUrl(input), "http://localhost").searchParams;
        return (
          p.get("query") === "Shared" &&
          p.get("target") === "supplier" &&
          p.get("kind") === "external" &&
          p.get("offset") === "0"
        );
      }),
    ).toBe(true);
  });
});

test("Supplier is available in bounded Link to record choices", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((input, init) => {
      const path = requestUrl(input);
      if (init?.method === "POST")
        return Promise.resolve(
          json(
            link({
              target_type: "supplier",
              target_label: "Review nursery",
              target_url: `#/suppliers/${recordId}`,
            }),
          ),
        );
      return Promise.resolve(
        json({
          items: path.includes("/supplier")
            ? [{ id: recordId, label: "Review nursery" }]
            : [],
          total: path.includes("/supplier") ? 1 : 0,
          limit: 20,
          offset: 0,
        }),
      );
    });
  const linked = vi.fn();
  const user = userEvent.setup();
  mount(<MediaLinker asset={asset()} onClose={vi.fn()} onLinked={linked} />);
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Record type" }),
    "supplier",
  );
  await user.click(
    await screen.findByRole("radio", { name: "Review nursery" }),
  );
  await user.click(screen.getByRole("button", { name: "Link media" }));
  await waitFor(() => {
    expect(linked).toHaveBeenCalled();
  });
  expect(fetch).toHaveBeenCalledWith(
    `/api/v1/collection-records/supplier/${recordId}/media-links`,
    expect.objectContaining({ method: "POST" }),
  );
});

test("exact media detail reports a missing asset with a safe return link", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(
      json({ detail: { message: "Media asset not found" } }, 404),
    );
  mount(<MediaScreen initialId={assetId} />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "This media asset was deleted or could not be found",
  );
  expect(screen.getByRole("link", { name: "Media" })).toHaveAttribute(
    "href",
    "#/media",
  );
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole("img")).toBeNull();
});

test("exact media detail accepts case-insensitive UUID spelling", async () => {
  const lowerId = "01900000-0000-7000-8000-000000000abc";
  const upperId = lowerId.toUpperCase();
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(json(detail({ id: lowerId })));
  mount(<MediaScreen initialId={upperId} />);
  expect(
    await screen.findByRole("heading", { name: "Garden image" }),
  ).toBeVisible();
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(requestUrl(fetch.mock.calls[0]?.[0] ?? "")).toBe(
    `/api/v1/media-assets/${upperId}`,
  );
});

test("invalid media deep link is rejected before an API request", async () => {
  const fetch = vi.spyOn(globalThis, "fetch");
  mount(<MediaScreen initialId="not-a-uuid" />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "This media link has an invalid ID",
  );
  expect(fetch).not.toHaveBeenCalled();
});

test("changing the exact media target cancels a stale detail response", async () => {
  let finishFirst: ((response: Response) => void) | undefined;
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    if (requestUrl(input).endsWith(assetId))
      return new Promise<Response>((resolve) => {
        finishFirst = resolve;
      });
    return Promise.resolve(
      json(detail({ id: recordId, title: "Second target" })),
    );
  });
  const view = mount(<MediaScreen initialId={assetId} />);
  await waitFor(() => {
    expect(finishFirst).toBeDefined();
  });
  view.rerender(
    <AuthContext.Provider value={auth}>
      <MediaScreen initialId={recordId} />
    </AuthContext.Provider>,
  );
  expect(
    await screen.findByRole("heading", { name: "Second target" }),
  ).toBeInTheDocument();
  finishFirst?.(json(detail({ title: "Stale target" })));
  await waitFor(() => {
    expect(screen.queryByRole("heading", { name: "Stale target" })).toBeNull();
  });
});
