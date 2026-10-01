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
import { PhotosSection } from "./PhotosSection";
import type { CollectionPhoto, PrimaryPhoto } from "./api";

const targetId = "01900000-0000-7000-8000-000000000701";
const localId = "01900000-0000-7000-8000-000000000801";
const externalId = "01900000-0000-7000-8000-000000000802";
const auth: AuthContextValue = {
  state: {
    status: "authenticated",
    session: {
      user_id: "01900000-0000-7000-8000-000000000001",
      login_name: "owner",
      display_name: "Owner",
      owner: true,
      canonical_origin: "http://localhost:5173",
    },
    csrfToken: "csrf-test",
  },
  logIn: vi.fn(),
  logOut: vi.fn(),
  sessionExpired: vi.fn(),
  retryRestoration: vi.fn(),
  cancelLogout: vi.fn(),
};

const photos: CollectionPhoto[] = [
  {
    kind: "local",
    display_order: 0,
    id: localId,
    attachment_id: "01900000-0000-7000-8000-000000000901",
    original_filename: "leaf.png",
    media_type: "image/png",
    caption: null,
    attribution: null,
    deletion_pending: false,
    content_url:
      "/api/v1/attachments/01900000-0000-7000-8000-000000000901/content",
    created_at: "2026-09-13T10:00:00Z",
    updated_at: "2026-09-13T10:00:00Z",
  },
  {
    kind: "external",
    display_order: 1,
    id: externalId,
    image_url: "https://images.example.test/specimen.jpg",
    source_url: "https://example.test/specimen",
    attribution: "Ada Example",
    caption: "Flowering specimen",
    created_at: "2026-09-13T11:00:00Z",
    updated_at: "2026-09-13T11:00:00Z",
  },
];

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderSection(
  primaryPhoto: PrimaryPhoto | null = null,
  onPrimaryChanged?: (photo: PrimaryPhoto | null) => void,
) {
  return render(
    <AuthContext.Provider value={auth}>
      <PhotosSection
        target="plant"
        targetId={targetId}
        targetLabel="Avocado #1"
        primaryPhoto={primaryPhoto}
        onPrimaryChanged={onPrimaryChanged}
      />
    </AuthContext.Provider>,
  );
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("renders uploaded photos lazily and never loads an external image automatically", async () => {
  Object.defineProperties(window, {
    innerWidth: { configurable: true, value: 390 },
    innerHeight: { configurable: true, value: 844 },
  });
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json(photos));
  const user = userEvent.setup();
  renderSection();

  expect(await screen.findByText("Uploaded photo")).toBeVisible();
  const local = screen.getByRole("img", { name: "Photo for Avocado #1" });
  expect(local).toHaveAttribute("loading", "lazy");
  expect(local).toHaveAttribute(
    "src",
    `/api/v1/collection-photos/local/${localId}/thumbnail`,
  );
  expect(
    screen.getByText("External reference · not stored locally"),
  ).toBeVisible();
  expect(
    screen.queryByRole("img", { name: "Flowering specimen" }),
  ).not.toBeInTheDocument();
  expect(screen.getByText(/exposes normal network information/i)).toBeVisible();
  const source = screen.getByRole("link", { name: "Source: example.test" });
  expect(source).toHaveAttribute("rel", "noopener noreferrer");

  await user.click(screen.getByRole("button", { name: "Preview once" }));
  const external = screen.getByRole("img", { name: "Flowering specimen" });
  expect(external).toHaveAttribute("referrerpolicy", "no-referrer");
  expect(external).toHaveAttribute(
    "src",
    "https://images.example.test/specimen.jpg",
  );
  expect(fetch).toHaveBeenCalledTimes(1);
});

test("shows understandable local and external image failure states", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json(photos));
  const user = userEvent.setup();
  renderSection();
  const local = await screen.findByRole("img", {
    name: "Photo for Avocado #1",
  });
  local.dispatchEvent(new Event("error"));
  expect(
    await screen.findByText("The uploaded image content is unavailable."),
  ).toBeVisible();

  await user.click(screen.getByRole("button", { name: "Preview once" }));
  screen
    .getByRole("img", { name: "Flowering specimen" })
    .dispatchEvent(new Event("error"));
  expect(
    await screen.findByText(/external image is unavailable/i),
  ).toBeVisible();
});

test.each([false, true])(
  "primary photo deletion clears displayed designation even if refresh fails: %s",
  async (refreshFails) => {
    let deleted = false;
    const onPrimaryChanged = vi.fn();
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation((input, init) => {
        if (init?.method === "PATCH") return Promise.resolve(json(photos[1]));
        if (init?.method === "DELETE") {
          deleted = true;
          return Promise.resolve(new Response(null, { status: 204 }));
        }
        if (typeof input === "string" && input.endsWith("/primary-photo"))
          return refreshFails
            ? Promise.reject(new Error("Primary metadata request failed"))
            : Promise.resolve(json(null));
        return Promise.resolve(json(deleted ? [photos[0]] : photos));
      });
    const user = userEvent.setup();
    renderSection(
      { kind: "external", photo_id: externalId, thumbnail_url: null },
      onPrimaryChanged,
    );
    await screen.findByText("External reference · not stored locally");
    const externalCard = screen
      .getByText("External reference · not stored locally")
      .closest<HTMLElement>("article");
    if (!externalCard) throw new Error("External image card was not rendered");
    await user.click(
      within(externalCard).getByRole("button", { name: "Edit details" }),
    );
    const dialog = screen.getByRole("dialog", { name: "Edit photo details" });
    await user.clear(within(dialog).getByLabelText(/Caption/));
    await user.type(
      within(dialog).getByLabelText(/Caption/),
      "Updated caption",
    );
    const form = dialog.querySelector("form");
    if (!form) throw new Error("External image edit form was not rendered");
    fireEvent.submit(form);
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        `/api/v1/collection-photos/external/${externalId}`,
        expect.objectContaining({
          method: "PATCH",
          credentials: "same-origin",
        }),
      );
    });

    const refreshedCard = screen
      .getByText("External reference · not stored locally")
      .closest<HTMLElement>("article");
    if (!refreshedCard)
      throw new Error("External image card was not refreshed");
    expect(within(refreshedCard).getByText("Primary")).toBeVisible();
    await user.click(
      within(refreshedCard).getByRole("button", {
        name: "Unlink from this record",
      }),
    );
    const removal = screen.getByRole("dialog", {
      name: "Unlink external image reference?",
    });
    expect(removal).toHaveTextContent(
      /media asset, other record links, and identity cover references remain/i,
    );
    await user.click(
      within(removal).getByRole("button", { name: "Unlink from this record" }),
    );
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        `/api/v1/collection-photos/external/${externalId}`,
        expect.objectContaining({ method: "DELETE" }),
      );
    });
    await waitFor(() => {
      expect(onPrimaryChanged).toHaveBeenCalledWith(null);
    });
    expect(screen.queryByText("Primary")).not.toBeInTheDocument();
    expect(
      screen.queryByText("External reference · not stored locally"),
    ).not.toBeInTheDocument();
    if (refreshFails)
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Media was unlinked, but Photos could not be refreshed.",
      );
  },
);

test("supports zero-photo state and an accessible upload workflow", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json([]))
    .mockResolvedValueOnce(json(photos[0], 201))
    .mockResolvedValueOnce(json([photos[0]]));
  const user = userEvent.setup();
  renderSection();
  expect(
    await screen.findByText("No photos or external image references yet."),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Add new media" }));
  const dialog = screen.getByRole("dialog", { name: "Add new media" });
  const file = new File(["png"], "leaf.png", { type: "image/png" });
  await user.upload(within(dialog).getByLabelText("Image file"), file);
  await user.type(within(dialog).getByLabelText(/Caption/), "New leaf");
  const uploadForm = dialog.querySelector("form");
  if (!uploadForm) throw new Error("Photo upload form was not rendered");
  fireEvent.submit(uploadForm);
  expect(await screen.findByText("Photo was added.")).toBeVisible();
  const uploadCall = fetch.mock.calls.find(
    ([, init]) => init?.method === "POST",
  );
  expect(uploadCall?.[1]?.body).toBeInstanceOf(FormData);
  expect(uploadCall?.[1]?.headers).toBeInstanceOf(Headers);
  expect((uploadCall?.[1]?.headers as Headers).get("Content-Type")).toBeNull();
});

test("primary selection is explicit and removing designation retains gallery photos", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((input, init) => {
      const path =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.href
            : input.url;
      if (path.endsWith("/primary-photo") && init?.method === "PUT") {
        if (typeof init.body !== "string")
          throw new Error("Primary selection must use a JSON request body");
        const body = JSON.parse(init.body) as {
          kind: string;
          photo_id: string;
        };
        return Promise.resolve(
          json({
            ...body,
            thumbnail_url:
              body.kind === "local"
                ? `/api/v1/collection-photos/local/${body.photo_id}/thumbnail`
                : null,
          }),
        );
      }
      if (path.endsWith("/primary-photo") && init?.method === "DELETE")
        return Promise.resolve(new Response(null, { status: 204 }));
      return Promise.resolve(json(photos));
    });
  const user = userEvent.setup();
  renderSection();
  await screen.findByText("Uploaded photo");
  expect(screen.queryByText("Primary")).not.toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: "Set local photo as primary" }),
  );
  expect(await screen.findByText("Primary")).toBeVisible();
  expect(fetch).toHaveBeenCalledWith(
    `/api/v1/collection-records/plant/${targetId}/primary-photo`,
    expect.objectContaining({ method: "PUT" }),
  );
  await user.click(
    screen.getByRole("button", { name: "Set Flowering specimen as primary" }),
  );
  expect(screen.getByText("Primary").closest("article")).toHaveTextContent(
    "External reference · not stored locally",
  );
  expect(
    screen.queryByRole("img", { name: "Flowering specimen" }),
  ).not.toBeInTheDocument();
  await user.click(
    screen.getByRole("button", {
      name: "Remove primary designation from Flowering specimen",
    }),
  );
  expect(await screen.findByText(/designation was removed/i)).toBeVisible();
  expect(screen.getAllByRole("article")).toHaveLength(2);
  expect(
    fetch.mock.calls.filter(([, init]) => init?.method === "DELETE"),
  ).toHaveLength(1);
});

test.each(["sowing", "event"] as const)(
  "%s Photos do not expose primary actions",
  async (target) => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json(photos));
    render(
      <AuthContext.Provider value={auth}>
        <PhotosSection
          target={target}
          targetId={targetId}
          targetLabel="Evidence"
        />
      </AuthContext.Provider>,
    );
    await screen.findByText("Uploaded photo");
    expect(
      screen.queryByRole("button", { name: /primary/i }),
    ).not.toBeInTheDocument();
  },
);

test("record-linked external media renders its saved local thumbnail without previewing remotely", async () => {
  const stored = photos.map((photo) =>
    photo.kind === "external"
      ? {
          ...photo,
          thumbnail_url: "/api/v1/media-assets/saved/thumbnail?v=1",
          content_url: "/api/v1/attachments/saved/content",
          fetched_at: "2026-10-01T12:00:00Z",
        }
      : photo,
  );
  vi.spyOn(globalThis, "fetch").mockResolvedValue(json(stored));
  renderSection();
  const image = await screen.findByRole("img", { name: "Flowering specimen" });
  expect(image).toHaveAttribute(
    "src",
    "/api/v1/media-assets/saved/thumbnail?v=1",
  );
  expect(
    screen.queryByRole("button", { name: "Preview once" }),
  ).not.toBeInTheDocument();
});
