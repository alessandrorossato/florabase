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
import type { CollectionPhoto } from "./api";

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

function renderSection() {
  return render(
    <AuthContext.Provider value={auth}>
      <PhotosSection
        target="plant"
        targetId={targetId}
        targetLabel="Avocado #1"
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
    "/api/v1/attachments/01900000-0000-7000-8000-000000000901/content",
  );
  expect(screen.getByText("External image")).toBeVisible();
  expect(
    screen.queryByRole("img", { name: "Flowering specimen" }),
  ).not.toBeInTheDocument();
  expect(screen.getByText(/exposes normal network information/i)).toBeVisible();
  const source = screen.getByRole("link", { name: "Source: example.test" });
  expect(source).toHaveAttribute("rel", "noopener noreferrer");

  await user.click(screen.getByRole("button", { name: "Load external image" }));
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

  await user.click(screen.getByRole("button", { name: "Load external image" }));
  screen
    .getByRole("img", { name: "Flowering specimen" })
    .dispatchEvent(new Event("error"));
  expect(
    await screen.findByText(/external image is unavailable/i),
  ).toBeVisible();
});

test("edits external metadata and confirms metadata-only removal", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((_input, init) => {
      if (init?.method === "PATCH") return Promise.resolve(json(photos[1]));
      if (init?.method === "DELETE")
        return Promise.resolve(new Response(null, { status: 204 }));
      return Promise.resolve(json(photos));
    });
  const user = userEvent.setup();
  renderSection();
  await screen.findByText("External image");
  const externalCard = screen
    .getByText("External image")
    .closest<HTMLElement>("article");
  if (!externalCard) throw new Error("External image card was not rendered");
  await user.click(
    within(externalCard).getByRole("button", { name: "Edit details" }),
  );
  const dialog = screen.getByRole("dialog", { name: "Edit photo details" });
  await user.clear(within(dialog).getByLabelText(/Caption/));
  await user.type(within(dialog).getByLabelText(/Caption/), "Updated caption");
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
    .getByText("External image")
    .closest<HTMLElement>("article");
  if (!refreshedCard) throw new Error("External image card was not refreshed");
  await user.click(
    within(refreshedCard).getByRole("button", { name: "Remove" }),
  );
  const removal = screen.getByRole("dialog", {
    name: "Remove external image reference?",
  });
  expect(removal).toHaveTextContent(/metadata only and does not contact/i);
  await user.click(within(removal).getByRole("button", { name: "Remove" }));
  await waitFor(() => {
    expect(fetch).toHaveBeenCalledWith(
      `/api/v1/collection-photos/external/${externalId}`,
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});

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
  await user.click(screen.getByRole("button", { name: "Upload photo" }));
  const dialog = screen.getByRole("dialog", { name: "Upload photo" });
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
