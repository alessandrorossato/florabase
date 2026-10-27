import { selectDirectoryFilter } from "../test/directoryFilters";
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
  window.history.replaceState(null, "", "#/media");
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

test("Gallery distinguishes source and references, uses thumbnails and filters/paginates", async () => {
  window.matchMedia = vi.fn(() => ({ matches: false }) as MediaQueryList);
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
    if (url === `/api/v1/media-assets/${assetId}`)
      return Promise.resolve(
        json(detail({ cover_reference_count: 1, can_delete: false })),
      );
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
  await user.click(screen.getByRole("button", { name: "Close preview" }));
  await selectDirectoryFilter(user, "Record links", "unlinked");
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

test("Quick Preview saves an external reference only on request and refreshes gallery and preview", async () => {
  const user = userEvent.setup();
  window.matchMedia = vi.fn(() => ({ matches: false }) as MediaQueryList);
  const local = asset();
  const alreadySaved = asset({
    id: recordId,
    kind: "external",
    title: "Saved external image",
    image_url: "https://images.example.test/saved.jpg",
    source_url: "https://example.test/saved",
    content_url: `/api/v1/attachments/${recordId}/content`,
    thumbnail_url: `/api/v1/media-assets/${recordId}/thumbnail`,
  });
  const remoteId = "01900000-0000-7000-8000-000000000913";
  let remote = asset({
    id: remoteId,
    kind: "external",
    title: "Unsaved external image",
    image_url: "https://images.example.test/remote.jpg",
    source_url: "https://example.test/remote",
    content_url: null,
    thumbnail_url: null,
    original_filename: null,
    media_type: null,
  });
  const paths: string[] = [];
  const directory =
    "#/media?q=Review+v5&kind=external&association=unlinked&offset=24";
  window.history.replaceState(null, "", directory);
  window.matchMedia = vi.fn(() => ({ matches: false }) as MediaQueryList);
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, options?: RequestInit) => {
      const path = requestUrl(input);
      paths.push(path);
      if (path.startsWith("/api/v1/media-assets?"))
        return Promise.resolve(
          json(page([local, alreadySaved, remote], 27, 24)),
        );
      if (path === `/api/v1/media-assets/${remoteId}/save-local-copy`) {
        expect(options?.method).toBe("POST");
        expect(new Headers(options?.headers).get("X-CSRF-Token")).toBe(
          "test-csrf",
        );
        remote = {
          ...remote,
          content_url: `/api/v1/attachments/${remoteId}/content`,
          thumbnail_url: `/api/v1/media-assets/${remoteId}/thumbnail`,
          fetched_at: "2026-10-01T12:00:00Z",
        };
        return Promise.resolve(json(remote));
      }
      const id = path.split("/").at(-1);
      return Promise.resolve(
        json(detail(id === remoteId ? remote : alreadySaved)),
      );
    }),
  );
  mount(<MediaScreen />);
  const localCard = await waitFor(() => {
    const card = document.getElementById(
      `media-asset-${assetId}`,
    ) as HTMLButtonElement | null;
    expect(card).toBeInTheDocument();
    if (!card) throw new Error("Media card did not render");
    return card;
  });
  await user.click(localCard);
  expect(screen.queryByRole("button", { name: "Save local copy" })).toBeNull();
  await user.click(screen.getByRole("button", { name: "Close preview" }));
  await user.click(
    screen.getByRole("button", { name: /Saved external image/ }),
  );
  expect(screen.queryByRole("button", { name: "Save local copy" })).toBeNull();
  expect(screen.queryByText("Protected local copy saved.")).toBeNull();
  await user.click(screen.getByRole("button", { name: "Close preview" }));

  // Select the no-copy asset by its stable gallery button ID, as its title is shared.
  await user.click(
    await screen.findByRole("button", { name: /Unsaved external image/ }),
  );
  const preview = screen.getByRole("dialog", { name: "Quick Preview" });
  expect(
    within(preview).getByText("External reference · not stored locally"),
  ).toBeVisible();
  expect(
    within(preview).getByRole("button", { name: "Preview once" }),
  ).toBeVisible();
  expect(
    within(preview).getByRole("button", { name: "Save local copy" }),
  ).toBeVisible();
  expect(paths).not.toContain("https://images.example.test/remote.jpg");

  await user.click(
    within(preview).getByRole("button", { name: "Save local copy" }),
  );
  expect(
    await within(preview).findByText("Protected local copy saved."),
  ).toBeVisible();
  expect(
    within(preview).getByText("Protected local copy saved."),
  ).toHaveFocus();
  expect(within(preview).getByRole("img")).toHaveAttribute(
    "src",
    `/api/v1/attachments/${remoteId}/content`,
  );
  expect(
    within(preview).queryByRole("button", { name: "Save local copy" }),
  ).toBeNull();
  expect(window.location.hash).toBe(directory);
  expect(screen.getByRole("searchbox", { name: "Search media" })).toHaveValue(
    "Review v5",
  );
  await waitFor(() => {
    expect(
      paths.filter((path) => path.startsWith("/api/v1/media-assets?")),
    ).toHaveLength(2);
  });
  expect(preview).toBeVisible();
});

test("Quick Preview prevents duplicate saves and reports retryable save failures", async () => {
  const user = userEvent.setup();
  const remoteId = "01900000-0000-7000-8000-000000000913";
  const remote = asset({
    id: remoteId,
    kind: "external",
    title: "Unsaved external image",
    image_url: "https://images.example.test/remote.jpg",
    source_url: "https://example.test/remote",
    content_url: null,
    thumbnail_url: null,
    original_filename: null,
    media_type: null,
  });
  let resolveSave: ((response: Response) => void) | undefined;
  let saves = 0;
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: false })),
  );
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const path = requestUrl(input);
      if (path.startsWith("/api/v1/media-assets?"))
        return Promise.resolve(json(page([remote])));
      if (path.endsWith("/save-local-copy")) {
        saves += 1;
        return new Promise<Response>((resolve) => {
          resolveSave = resolve;
        });
      }
      if (path.endsWith(remoteId)) return Promise.resolve(json(detail(remote)));
      return Promise.resolve(json(page([remote])));
    }),
  );
  mount(<MediaScreen />);
  await user.click(
    await screen.findByRole("button", { name: /Unsaved external image/ }),
  );
  const save = screen.getByRole("button", { name: "Save local copy" });
  await user.click(save);
  expect(
    await screen.findByRole("button", { name: "Saving local copy…" }),
  ).toBeDisabled();
  await user.dblClick(
    screen.getByRole("button", { name: "Saving local copy…" }),
  );
  expect(saves).toBe(1);
  resolveSave?.(
    json(
      {
        detail: {
          code: "external_fetch_failed",
          message: "The external image is unavailable. Try again.",
        },
      },
      422,
    ),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "The external image is unavailable.",
  );
  expect(screen.getByRole("dialog", { name: "Quick Preview" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Save local copy" })).toBeEnabled();
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
    vi.fn((input: RequestInfo | URL) =>
      Promise.resolve(
        json(requestUrl(input).includes("?") ? page([stored]) : detail(stored)),
      ),
    ),
  );
  mount(<MediaScreen />);
  await user.click(await screen.findByRole("button", { name: /Garden image/ }));
  const preview = await screen.findByRole("dialog", { name: "Quick Preview" });
  expect(await within(preview).findByRole("img")).toHaveAttribute(
    "src",
    stored.content_url,
  );
  expect(screen.getAllByRole("img")[0]).toHaveAttribute(
    "src",
    stored.thumbnail_url,
  );
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
  await user.click(screen.getByRole("button", { name: /^Filters/ }));
  const filter = screen.getByRole("combobox", { name: "Target" });
  expect(
    within(filter).getByRole("option", { name: "Suppliers" }),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Done" }));
  await selectDirectoryFilter(user, "Target", "collection");
  await screen.findByRole("button", { name: /Plant only/ });
  await waitFor(() => {
    expect(
      screen.queryByRole("button", { name: /Supplier only/ }),
    ).not.toBeInTheDocument();
  });
  expect(
    screen.getByRole("button", { name: /Shared Supplier \+ Plant/ }),
  ).toBeInTheDocument();
  await selectDirectoryFilter(user, "Target", "supplier");
  await screen.findByRole("button", { name: /Supplier only/ });
  expect(
    screen.queryByRole("button", { name: /Plant only/ }),
  ).not.toBeInTheDocument();
  await selectDirectoryFilter(user, "Target", "plant");
  await screen.findByRole("button", { name: /Plant only/ });
  expect(
    screen.queryByRole("button", { name: /Supplier only/ }),
  ).not.toBeInTheDocument();
  await selectDirectoryFilter(user, "Target", "seed_lot");
  await screen.findByText(/No matching media/);
  await selectDirectoryFilter(user, "Target", "");
  await screen.findByRole("button", { name: /Supplier only/ });
  await selectDirectoryFilter(user, "Target", "supplier");
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "Shared" },
  });
  await selectDirectoryFilter(user, "Source", "external");
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

test.each(["saved", "reference", "retry", "retain"] as const)(
  "new external Media editor copy choice: %s",
  async (outcome) => {
    const { MediaEditor } = await import("./MediaEditor");
    const onSaved = vi.fn<(value: MediaAsset) => void>();
    let created = 0;
    let attempts = 0;
    const reference = asset({
      kind: "external",
      content_url: null,
      thumbnail_url: null,
      image_url: "https://images.example.test/image.jpg",
      source_url: "https://example.test/source",
    });
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      if (requestUrl(input).endsWith("/media-assets/external")) {
        created++;
        return Promise.resolve(json(reference, 201));
      }
      if (requestUrl(input).endsWith("/save-local-copy")) {
        attempts++;
        return Promise.resolve(
          attempts === 1 && ["retry", "retain"].includes(outcome)
            ? json({ detail: "Unavailable" }, 422)
            : json(asset({ kind: "external" })),
        );
      }
      throw new Error(`Unexpected request ${requestUrl(input)}`);
    });
    mount(<MediaEditor onClose={vi.fn()} onSaved={onSaved} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("radio", { name: "External reference" }));
    expect(
      screen.getByRole("checkbox", { name: "Save a local copy in Florabase" }),
    ).toBeChecked();
    await user.type(
      screen.getByLabelText("Image URL"),
      "https://images.example.test/image.jpg",
    );
    await user.type(
      screen.getByLabelText("Source page URL"),
      "https://example.test/source",
    );
    await user.type(screen.getByLabelText("Attribution"), "Gardener");
    if (outcome === "reference")
      await user.click(
        screen.getByRole("checkbox", {
          name: "Save a local copy in Florabase",
        }),
      );
    await user.click(screen.getByRole("button", { name: "Save media" }));
    if (outcome === "retry" || outcome === "retain") {
      expect(await screen.findByRole("alert")).toHaveTextContent(
        "external reference remains saved",
      );
      expect(onSaved).not.toHaveBeenCalled();
      await user.click(
        screen.getByRole("button", {
          name: outcome === "retry" ? "Retry save" : "Keep reference only",
        }),
      );
    }
    await waitFor(() => {
      expect(onSaved).toHaveBeenCalledTimes(1);
    });
    expect(created).toBe(1);
    expect(attempts).toBe(
      outcome === "reference" ? 0 : outcome === "retry" ? 2 : 1,
    );
    expect(onSaved.mock.calls[0][0].content_url).toBe(
      outcome === "reference" || outcome === "retain"
        ? null
        : asset().content_url,
    );
  },
);

test("deliberate preview loads one original and exact shared records, Escape restores the card", async () => {
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: false })),
  );
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation((input) =>
    Promise.resolve(
      json(
        requestUrl(input).includes("?")
          ? page([asset()])
          : detail({
              links: [
                link(),
                link({
                  id: recordId,
                  target_label: "Plant B",
                  is_primary: true,
                }),
              ],
            }),
      ),
    ),
  );
  const user = userEvent.setup();
  mount(<MediaScreen />);
  const card = await screen.findByRole("button", { name: /Garden image/ });
  expect(fetch).toHaveBeenCalledTimes(1);
  card.focus();
  await user.keyboard("{Enter}");
  const preview = screen.getByRole("dialog", { name: "Quick Preview" });
  expect(
    within(preview).getByRole("button", { name: "Close preview" }),
  ).toHaveFocus();
  expect(
    await within(preview).findByRole("link", { name: "Plant B" }),
  ).toBeVisible();
  expect(
    within(preview).getByText("Plant · Primary image for this record"),
  ).toBeVisible();
  expect(within(preview).getByRole("img")).toHaveAttribute(
    "src",
    asset().content_url,
  );
  expect(fetch).toHaveBeenCalledTimes(2);
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(card).toHaveFocus();
});

test("safe initial Cancel, Escape and retry deletion preserve reference conflict and pending safeguards", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((_input, init) =>
      Promise.resolve(
        init?.method === "DELETE"
          ? json({ detail: { message: "Still referenced" } }, 409)
          : json(detail({ deletion_pending: true })),
      ),
    );
  const user = userEvent.setup();
  mount(<MediaScreen initialId={assetId} />);
  const trigger = await screen.findByRole("button", {
    name: "Retry asset deletion",
  });
  expect(screen.getByRole("heading", { name: "Garden image" })).toHaveFocus();
  trigger.focus();
  await user.keyboard("{Enter}");
  let dialog = screen.getByRole("dialog");
  expect(within(dialog).getByRole("button", { name: "Cancel" })).toHaveFocus();
  await user.keyboard("{Escape}");
  expect(trigger).toHaveFocus();
  await user.click(trigger);
  dialog = screen.getByRole("dialog");
  expect(within(dialog).getByRole("button", { name: "Cancel" })).toHaveFocus();
  await user.click(
    within(dialog).getByRole("button", { name: "Delete media asset" }),
  );
  expect(await within(dialog).findByRole("alert")).toHaveTextContent(
    "Still referenced",
  );
  await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
  expect(trigger).toHaveFocus();
  expect(
    fetch.mock.calls.filter(([, init]) => init?.method === "DELETE"),
  ).toHaveLength(1);
  expect(screen.queryByRole("img")).toBeNull();
});

test("detail return preserves filters and page, restores initiating card and falls back when absent", async () => {
  const directory =
    "#/media?q=leaf&kind=local&association=linked&target=plant&offset=24";
  window.history.replaceState(
    { mediaFocus: assetId },
    "",
    directory.replace("#/media", `#/media/${assetId}`),
  );
  let exists = true;
  vi.spyOn(globalThis, "fetch").mockImplementation((input) =>
    Promise.resolve(
      json(
        requestUrl(input).includes("?")
          ? page(exists ? [asset()] : [], exists ? 25 : 0, 24)
          : detail(),
      ),
    ),
  );
  const user = userEvent.setup();
  const view = mount(<MediaScreen initialId={assetId} />);
  await screen.findByRole("heading", { name: "Garden image" });
  const back = screen.getByRole("link", { name: "Media" });
  expect(back).toHaveAttribute("href", directory);
  await user.click(back);
  view.rerender(
    <AuthContext.Provider value={auth}>
      <MediaScreen />
    </AuthContext.Provider>,
  );
  const card = await screen.findByRole("button", { name: /Garden image/ });
  await waitFor(() => {
    expect(card).toHaveFocus();
  });
  expect(screen.getByRole("searchbox")).toHaveValue("leaf");
  expect(window.location.hash).toBe(directory);
  expect(screen.getByText("25–25 of 25")).toBeVisible();
  exists = false;
  view.unmount();
  mount(<MediaScreen />);
  await screen.findByText(/No matching media/);
  expect(screen.getByRole("heading", { name: "Media" })).toHaveFocus();
});

test("mobile activation carries exact filters and offset straight to details without an inspector", async () => {
  window.history.replaceState(
    null,
    "",
    "#/media?kind=local&target=plant&offset=24",
  );
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: true })),
  );
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    json(page([asset()], 25, 24)),
  );
  const user = userEvent.setup();
  mount(<MediaScreen />);
  await user.click(await screen.findByRole("button", { name: /Garden image/ }));
  expect(window.location.hash).toBe(
    `#/media/${assetId}?kind=local&target=plant&offset=24`,
  );
  expect(screen.queryByRole("dialog")).toBeNull();
});

test("preview failure is recoverable and does not load an external reference without opt-in", async () => {
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: false })),
  );
  const external = asset({
    kind: "external",
    content_url: null,
    thumbnail_url: null,
    image_url: "https://images.example.test/image.jpg",
  });
  let reads = 0;
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    if (requestUrl(input).includes("?"))
      return Promise.resolve(json(page([external])));
    return Promise.resolve(
      ++reads === 1
        ? json({ detail: { message: "Unavailable" } }, 503)
        : json(detail(external)),
    );
  });
  const user = userEvent.setup();
  mount(<MediaScreen />);
  await user.click(await screen.findByRole("button", { name: /Garden image/ }));
  const preview = screen.getByRole("dialog");
  expect(await within(preview).findByRole("alert")).toBeVisible();
  await user.click(
    within(preview).getByRole("button", { name: "Retry preview" }),
  );
  expect(
    await within(preview).findByRole("button", { name: "Preview once" }),
  ).toBeVisible();
  expect(screen.queryByRole("img")).toBeNull();
  await user.click(
    within(preview).getByRole("button", { name: "Close preview" }),
  );
});

test("a deleted last page clamps to the final existing page and safely focuses the heading", async () => {
  window.history.replaceState(
    { mediaFocus: assetId },
    "",
    "#/media?kind=local&offset=24",
  );
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((input) =>
      Promise.resolve(
        json(page([], 0, requestUrl(input).includes("offset=24") ? 24 : 0)),
      ),
    );
  mount(<MediaScreen />);
  await screen.findByText(/No matching media/);
  expect(window.location.hash).toBe("#/media?kind=local");
  await waitFor(() => {
    expect(screen.getByRole("heading", { name: "Media" })).toHaveFocus();
  });
  expect(fetch).toHaveBeenCalledWith(
    expect.stringContaining("offset=0"),
    expect.anything(),
  );
});

test("confirmation success retains filtered directory context without touching other media", async () => {
  window.history.replaceState(null, "", `#/media/${assetId}?q=leaf&kind=local`);
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((_input, init) =>
      Promise.resolve(
        init?.method === "DELETE"
          ? new Response(null, { status: 204 })
          : json(detail()),
      ),
    );
  const user = userEvent.setup();
  mount(<MediaScreen initialId={assetId} />);
  await user.click(
    await screen.findByRole("button", { name: "Delete media asset" }),
  );
  const dialog = screen.getByRole("dialog");
  expect(within(dialog).getByRole("button", { name: "Cancel" })).toHaveFocus();
  await user.click(
    within(dialog).getByRole("button", { name: "Delete media asset" }),
  );
  await waitFor(() => {
    expect(window.location.hash).toBe("#/media?q=leaf&kind=local");
  });
  expect(
    fetch.mock.calls
      .filter(([, init]) => init?.method === "DELETE")
      .map(([input]) => input),
  ).toEqual([`/api/v1/media-assets/${assetId}`]);
});

test("a missing thumbnail falls back without trying an original or remote URL", () => {
  mount(<MediaPreview asset={asset()} />);
  fireEvent.error(screen.getByRole("img"));
  expect(screen.getByRole("status")).toHaveTextContent("Image unavailable");
  expect(screen.queryByRole("img")).toBeNull();
});

test("closing a loading preview aborts its request and ignores a late detail response", async () => {
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: false })),
  );
  let finish: ((value: Response) => void) | undefined;
  let signal: AbortSignal | null | undefined;
  vi.spyOn(globalThis, "fetch").mockImplementation((input, options) => {
    if (requestUrl(input).includes("?"))
      return Promise.resolve(json(page([asset()])));
    signal = options?.signal;
    return new Promise<Response>((resolve) => {
      finish = resolve;
    });
  });
  const user = userEvent.setup();
  mount(<MediaScreen />);
  const card = await screen.findByRole("button", { name: /Garden image/ });
  await user.click(card);
  expect(await screen.findByText("Loading preview…")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Close preview" }));
  expect(signal?.aborted).toBe(true);
  finish?.(json(detail()));
  await waitFor(() => {
    expect(screen.queryByRole("dialog")).toBeNull();
  });
  expect(card).toHaveFocus();
  expect(screen.getByRole("img")).toHaveAttribute("src", asset().thumbnail_url);
});
