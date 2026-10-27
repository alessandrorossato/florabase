import {
  act,
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { App } from "../App";
import type { MediaDetail } from "./api";

const id = "01900000-0000-7000-8000-000000000910";
const photo: MediaDetail = {
  id,
  kind: "local",
  title: "Navigation photograph",
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
  content_url: `/api/v1/attachments/${id}/content`,
  thumbnail_url: `/api/v1/media-assets/${id}/thumbnail`,
  collection_link_count: 0,
  cover_reference_count: 0,
  can_delete: true,
  created_at: "2026-10-01T10:00:00Z",
  updated_at: "2026-10-01T10:00:00Z",
  links: [],
  covers: [],
};
function fixture() {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const path =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.href
          : input.url;
    const body = path.endsWith("/auth/session")
      ? {
          user_id: id,
          login_name: "owner",
          display_name: "Owner",
          owner: true,
          canonical_origin: "http://localhost:5173",
        }
      : path.endsWith("/auth/csrf")
        ? { csrf_token: "csrf" }
        : path.endsWith("/health")
          ? { status: "ok" }
          : path.startsWith("/api/v1/media-assets?")
            ? { items: [photo], total: 25, limit: 24, offset: 24 }
            : path === `/api/v1/media-assets/${id}`
              ? photo
              : [];
    return Promise.resolve(
      new Response(JSON.stringify(body), {
        headers: { "Content-Type": "application/json" },
      }),
    );
  });
}
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  localStorage.clear();
  window.history.replaceState(null, "", "#/media");
});

test("real App remounts preserve Media filters/page, breadcrumb focus, Back/Forward and direct reload", async () => {
  const directory =
    "#/media?q=garden&kind=local&association=unlinked&target=plant&offset=24";
  window.history.replaceState(null, "", directory);
  fixture();
  // This regression covers real routing/focus, not cold chunk compilation latency.
  await import("./MediaScreen");
  const user = userEvent.setup();
  const view = render(<App />);
  await screen.findByRole("complementary", { name: "Application sidebar" });
  await vi.dynamicImportSettled();
  let card = await screen.findByRole("button", {
    name: /Navigation photograph/,
  });
  await user.click(card);
  const preview = screen.getByRole("dialog", { name: "Quick Preview" });
  await within(preview).findByRole("img");
  await user.click(
    within(preview).getByRole("link", { name: "Open media details" }),
  );
  let heading = await screen.findByRole("heading", {
    name: "Navigation photograph",
  });
  await waitFor(() => {
    expect(heading).toHaveFocus();
  });
  expect(window.location.hash).toBe(
    directory.replace("#/media", `#/media/${id}`),
  );
  await user.click(
    within(screen.getByRole("navigation", { name: "Breadcrumb" })).getByRole(
      "link",
      { name: "Media" },
    ),
  );
  card = await screen.findByRole("button", { name: /Navigation photograph/ });
  await waitFor(() => {
    expect(card).toHaveFocus();
  });
  expect(window.location.hash).toBe(directory);
  act(() => {
    window.history.back();
  });
  heading = await screen.findByRole("heading", {
    name: "Navigation photograph",
  });
  await waitFor(() => {
    expect(heading).toHaveFocus();
  });
  act(() => {
    window.history.forward();
  });
  card = await screen.findByRole("button", { name: /Navigation photograph/ });
  await waitFor(() => {
    expect(card).toHaveFocus();
  });
  expect(window.location.hash).toBe(directory);
  view.unmount();
  render(<App />);
  await screen.findByRole("complementary", { name: "Application sidebar" });
  await vi.dynamicImportSettled();
  card = await screen.findByRole("button", { name: /Navigation photograph/ });
  await waitFor(() => {
    expect(card).toHaveFocus();
  });
  expect(screen.getByRole("searchbox", { name: "Search media" })).toHaveValue(
    "garden",
  );
  expect(screen.getByText("25–25 of 25")).toBeVisible();
  act(() => {
    window.history.pushState(null, "", "#/media");
    window.dispatchEvent(new PopStateEvent("popstate"));
  });
  await waitFor(() => {
    expect(screen.getByRole("searchbox", { name: "Search media" })).toHaveValue(
      "",
    );
  });
  expect(screen.queryByRole("group", { name: "Active filters" })).toBeNull();
  act(() => {
    window.history.back();
  });
  await waitFor(() => {
    expect(screen.getByRole("searchbox", { name: "Search media" })).toHaveValue(
      "garden",
    );
  });
  expect(window.location.hash).toBe(directory);
});
