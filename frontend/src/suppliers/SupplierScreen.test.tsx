import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { SupplierScreen } from "./SupplierScreen";

function requestUrl(input: RequestInfo | URL): string {
  return typeof input === "string"
    ? input
    : input instanceof URL
      ? input.href
      : input.url;
}

const id = "01900000-0000-7000-8000-000000000911";
const photoId = "01900000-0000-7000-8000-000000000912";
const assetId = "01900000-0000-7000-8000-000000000913";
const thumb = `/api/v1/media-assets/${assetId}/thumbnail`;
const auth: AuthContextValue = {
  state: {
    status: "authenticated",
    csrfToken: "csrf",
    session: {
      user_id: id,
      login_name: "owner",
      display_name: "Owner",
      owner: true,
      canonical_origin: "http://localhost:15174",
    },
  },
  logIn: vi.fn(),
  logOut: vi.fn(),
  sessionExpired: vi.fn(),
  retryRestoration: vi.fn(),
  cancelLogout: vi.fn(),
};
const supplier = {
  id,
  name: "Review nursery",
  kind: "nursery",
  website: null,
  email: null,
  phone: null,
  notes: null,
  retired_at: null,
  created_at: "2026-10-05T10:00:00Z",
  updated_at: "2026-10-05T10:00:00Z",
  primary_photo: { kind: "local", photo_id: photoId, thumbnail_url: thumb },
  usage_counts: {
    seed_lots_active: 1,
    seed_lots_total: 2,
    plants_active: 0,
    plants_total: 0,
    plant_groups_active: 0,
    plant_groups_total: 0,
    direct_records_active: 1,
    direct_records_total: 2,
  },
};
function json(value: unknown) {
  return new Response(JSON.stringify(value), {
    headers: { "Content-Type": "application/json" },
  });
}
function mount(props: Parameters<typeof SupplierScreen>[0] = {}) {
  render(
    <AuthContext.Provider value={auth}>
      <SupplierScreen {...props} />
    </AuthContext.Provider>,
  );
}
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.location.hash = "";
});

test("Supplier directory and Quick Preview use protected thumbnails and neutral absence", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    json([
      supplier,
      {
        ...supplier,
        id: assetId,
        name: "No image supplier",
        primary_photo: null,
      },
    ]),
  );
  const user = userEvent.setup();
  mount();
  const row = await screen.findByRole("button", { name: /Review nursery/ });
  expect(
    within(row).getByRole("img", { name: "Primary photo for Review nursery" }),
  ).toHaveAttribute("src", thumb);
  await user.click(row);
  expect(
    screen.getAllByRole("img", { name: "Primary photo for Review nursery" }),
  ).toHaveLength(2);
  expect(
    screen
      .getAllByRole("img")
      .every((image) => image.getAttribute("src") === thumb),
  ).toBe(true);
  await user.click(screen.getByRole("button", { name: /No image supplier/ }));
  expect(screen.getAllByText("Supplier image placeholder")).toHaveLength(2);
  expect(screen.getByRole("link", { name: "Open details" })).toHaveAttribute(
    "href",
    `#/suppliers/${assetId}`,
  );
});

test("reference-only Supplier primary does not contact its external host", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    json([
      {
        ...supplier,
        primary_photo: {
          kind: "external",
          photo_id: photoId,
          thumbnail_url: null,
        },
      },
    ]),
  );
  mount();
  await screen.findByRole("button", { name: /Review nursery/ });
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  expect(
    fetch.mock.calls.every(([url]) =>
      requestUrl(url).startsWith("/api/v1/suppliers"),
    ),
  ).toBe(true);
});

test("Supplier detail shares Photos actions and updates/clears its representative image", async () => {
  let primary: object | null = supplier.primary_photo;
  let photos = [
    {
      kind: "local",
      id: photoId,
      media_asset_id: assetId,
      display_order: 0,
      attachment_id: assetId,
      original_filename: "supplier.png",
      media_type: "image/png",
      caption: "Representative",
      attribution: null,
      deletion_pending: false,
      content_url: `/api/v1/attachments/${assetId}/content`,
      created_at: supplier.created_at,
      updated_at: supplier.updated_at,
    },
  ];
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((input, init) => {
      const path = requestUrl(input);
      if (path.endsWith("/primary-photo")) {
        if (init?.method === "DELETE") primary = null;
        else if (init?.method === "PUT") primary = supplier.primary_photo;
        return Promise.resolve(
          init?.method === "DELETE"
            ? new Response(null, { status: 204 })
            : json(primary),
        );
      }
      if (path.endsWith(`/local/${photoId}`) && init?.method === "DELETE") {
        photos = [];
        primary = null;
        return Promise.resolve(new Response(null, { status: 204 }));
      }
      if (path.endsWith("/photos")) return Promise.resolve(json(photos));
      if (path === `/api/v1/suppliers/${id}`)
        return Promise.resolve(
          json({
            ...supplier,
            seed_lots: [],
            plants: [],
            plant_groups: [],
            recent_acquisitions: [],
          }),
        );
      return Promise.resolve(json([supplier]));
    });
  const user = userEvent.setup();
  mount({ initialId: id, initialTab: "photos" });
  await screen.findByRole("heading", { name: "Review nursery" });
  expect(
    screen.getByRole("img", { name: "Primary photo for Review nursery" }),
  ).toHaveAttribute("src", thumb);
  expect(
    await screen.findByRole("button", { name: "Add new media" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Add external image" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Link existing media" }),
  ).toBeInTheDocument();
  await user.click(
    screen.getByRole("button", {
      name: "Remove primary designation from Representative",
    }),
  );
  await waitFor(() => {
    expect(
      screen.queryByRole("img", { name: "Primary photo for Review nursery" }),
    ).not.toBeInTheDocument();
  });
  await user.click(
    screen.getByRole("button", { name: "Set Representative as primary" }),
  );
  await screen.findByRole("img", { name: "Primary photo for Review nursery" });
  const primaryCall = fetch.mock.calls.find(
    ([path, init]) =>
      requestUrl(path).endsWith("/primary-photo") && init?.method === "PUT",
  );
  expect(primaryCall).toBeDefined();
  expect(new Headers(primaryCall?.[1]?.headers).get("X-CSRF-Token")).toBe(
    "csrf",
  );
  await user.click(
    screen.getByRole("button", { name: "Unlink from this record" }),
  );
  const dialog = screen.getByRole("dialog");
  await user.click(
    within(dialog).getByRole("button", { name: "Unlink from this record" }),
  );
  await screen.findByText("No photos or external image references yet.");
  expect(
    screen.queryByRole("img", { name: "Primary photo for Review nursery" }),
  ).not.toBeInTheDocument();
});

test("Supplier detail edit uses the loaded detail while directory is empty", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation((input) =>
    Promise.resolve(
      json(
        requestUrl(input) === "/api/v1/suppliers"
          ? []
          : {
              ...supplier,
              seed_lots: [],
              plants: [],
              plant_groups: [],
              recent_acquisitions: [],
            },
      ),
    ),
  );
  const user = userEvent.setup();
  mount({ initialId: id, initialTab: "edit" });
  await screen.findByDisplayValue("Review nursery");
  await user.click(screen.getByRole("button", { name: "Edit supplier" }));
  await screen.findByRole("button", { name: "Save supplier" });
  fireEvent.change(screen.getByLabelText("Name"), {
    target: { value: "Corrected nursery" },
  });
  await user.click(screen.getByRole("button", { name: "Save supplier" }));
  await waitFor(() => {
    expect(fetch).toHaveBeenCalledWith(
      `/api/v1/suppliers/${id}`,
      expect.objectContaining({ method: "PUT" }),
    );
  });
});
