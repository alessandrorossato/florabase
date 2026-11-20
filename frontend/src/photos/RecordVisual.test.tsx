import type { ReactElement } from "react";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { RecordIdentities } from "../components/recordPresentation";
import { acquireTestAuth } from "../test/auth";
import { RecordVisual } from "./RecordVisual";
import type { BotanicalIdentityResponse } from "../botanical-identities/api";
let auth: AuthContextValue;
function wrap(ui: ReactElement) {
  return <AuthContext.Provider value={auth}>{ui}</AuthContext.Provider>;
}
function renderVisual(ui: ReactElement) {
  return render(wrap(ui));
}
function mockImageFetch() {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(() =>
      Promise.resolve(
        new Response(new Blob(["img"], { type: "image/png" }), { status: 200 }),
      ),
    );
}
const identity: BotanicalIdentityResponse = {
  id: "identity",
  display_label: "Okra",
  scientific_name: "Abelmoschus esculentus",
  cultivar_name: "Burgundy",
  common_name: "Okra Burgundy",
  compact_cover_kind: "local",
  created_at: "",
  updated_at: "",
};
beforeEach(async () => {
  auth = (await acquireTestAuth()).auth;
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});
test("direct local designation wins; a failed direct image falls through to the identity cover then placeholder", async () => {
  const fetch = mockImageFetch();
  renderVisual(
    <RecordVisual
      label="Packet"
      kind="seed"
      identity={identity}
      photo={{ kind: "local", photo_id: "photo", thumbnail_url: "/direct" }}
    />,
  );
  const direct = await screen.findByRole("img");
  expect(direct.getAttribute("src")).toMatch(/^blob:/);
  expect(fetch).toHaveBeenLastCalledWith(
    "/direct",
    expect.objectContaining({ credentials: "same-origin" }),
  );
  fireEvent.error(direct);
  await waitFor(() => {
    expect(fetch).toHaveBeenLastCalledWith(
      "/api/v1/botanical-identities/identity/cover-image/thumbnail",
      expect.objectContaining({ credentials: "same-origin" }),
    );
  });
  const cover = await screen.findByRole("img");
  expect(cover.getAttribute("src")).toMatch(/^blob:/);
  fireEvent.error(cover);
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  expect(screen.getByText("Seed image placeholder")).toBeInTheDocument();
});
test("external primary never loads; local identity fallback is still available", async () => {
  const fetch = mockImageFetch();
  renderVisual(
    <RecordVisual
      label="Group"
      kind="group"
      identity={identity}
      photo={{ kind: "external", photo_id: "external", thumbnail_url: null }}
    />,
  );
  const cover = await screen.findByRole("img");
  expect(cover.getAttribute("src")).toMatch(/^blob:/);
  expect(fetch).toHaveBeenCalledWith(
    "/api/v1/botanical-identities/identity/cover-image/thumbnail",
    expect.objectContaining({ credentials: "same-origin" }),
  );
});
test("external collection cover requires explicit policy permission; botanical compact cover retains no-referrer", () => {
  const external = {
    ...identity,
    compact_cover_kind: "external" as const,
    compact_external_cover_url: "https://example.test/photo.jpg",
  };
  const { rerender } = renderVisual(
    <RecordVisual label="Plant" kind="plant" identity={external} />,
  );
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  expect(screen.getByText("Plant image placeholder")).toBeInTheDocument();
  rerender(
    wrap(
      <RecordVisual
        label="Okra"
        kind="identity"
        identity={external}
        allowExternalCover
      />,
    ),
  );
  expect(screen.getByRole("img")).toHaveAttribute(
    "referrerpolicy",
    "no-referrer",
  );
});
test.each([
  "seed",
  "sowing",
  "plant",
  "group",
  "identity",
  "supplier",
  "order",
] as const)("%s has a type-specific placeholder without metadata", (kind) => {
  const { container } = renderVisual(
    <RecordVisual label="Record" kind={kind} />,
  );
  expect(container.querySelector("svg path")).toBeInTheDocument();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});

test("saved external primary and cover resolve to protected local content", async () => {
  const fetch = mockImageFetch();
  const { rerender } = renderVisual(
    <RecordVisual
      label="Plant"
      kind="plant"
      photo={{
        kind: "external",
        photo_id: "external",
        thumbnail_url: "/api/v1/media-assets/external/thumbnail?v=1",
      }}
    />,
  );
  expect((await screen.findByRole("img")).getAttribute("src")).toMatch(
    /^blob:/,
  );
  expect(fetch).toHaveBeenLastCalledWith(
    "/api/v1/media-assets/external/thumbnail?v=1",
    expect.objectContaining({ credentials: "same-origin" }),
  );
  rerender(
    wrap(
      <RecordVisual
        label="Plant"
        kind="plant"
        identity={{
          id: "identity",
          display_label: "Flower",
          compact_cover_kind: "local",
          compact_external_cover_url:
            "/api/v1/media-assets/cover/thumbnail?v=1",
        }}
      />,
    ),
  );
  await waitFor(() => {
    expect(fetch).toHaveBeenLastCalledWith(
      "/api/v1/media-assets/cover/thumbnail?v=1",
      expect.objectContaining({ credentials: "same-origin" }),
    );
  });
  expect((await screen.findByRole("img")).getAttribute("src")).toMatch(
    /^blob:/,
  );
});

test("Harvest falls through its own primary, exact identity cover and its own placeholder", async () => {
  const fetch = mockImageFetch();
  renderVisual(
    <RecordVisual
      kind="harvest"
      label="Fruit harvest"
      identity={identity}
      photo={{
        kind: "local",
        photo_id: "harvest",
        thumbnail_url: "/harvest-primary",
      }}
    />,
  );
  const first = await screen.findByRole("img");
  expect(first.getAttribute("src")).toMatch(/^blob:/);
  expect(fetch).toHaveBeenLastCalledWith(
    "/harvest-primary",
    expect.objectContaining({ credentials: "same-origin" }),
  );
  fireEvent.error(first);
  await waitFor(() => {
    expect(fetch).toHaveBeenLastCalledWith(
      "/api/v1/botanical-identities/identity/cover-image/thumbnail",
      expect.objectContaining({ credentials: "same-origin" }),
    );
  });
  const second = await screen.findByRole("img");
  expect(second.getAttribute("src")).toMatch(/^blob:/);
  fireEvent.error(second);
  expect(screen.getByText("Harvest image placeholder")).toBeVisible();
});

test("gallery source labels follow primary-to-reference fallback and never call an external cover a specimen", async () => {
  mockImageFetch();
  renderVisual(
    <RecordVisual
      kind="plant"
      label="Aloe"
      identity={identity}
      showSource
      photo={{ kind: "local", photo_id: "primary", thumbnail_url: "/primary" }}
    />,
  );
  await screen.findByRole("img");
  expect(screen.getByText("Record primary photo")).toBeVisible();
  fireEvent.error(screen.getByRole("img"));
  await screen.findByRole("img");
  expect(
    screen.getByText("Botanical identity cover · reference"),
  ).toBeVisible();
  fireEvent.error(screen.getByRole("img"));
  expect(screen.getByText("Image unavailable")).toBeVisible();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});

test("photo source stays attached to its image and updates after fallback", async () => {
  mockImageFetch();
  renderVisual(
    <RecordVisual
      showSource
      label="Plant"
      kind="plant"
      identity={identity}
      photo={{ kind: "local", photo_id: "direct", thumbnail_url: "/direct" }}
    />,
  );
  const img = await screen.findByRole("img");
  expect(screen.getByTitle("Record primary photo")).toContainElement(img);
  fireEvent.error(img);
  const fallbackImg = await screen.findByRole("img");
  expect(
    screen.getByTitle("Botanical identity cover · reference"),
  ).toContainElement(fallbackImg);
  expect(
    screen.getByText("Botanical identity cover · reference"),
  ).toBeInTheDocument();
});

test("summary names do not hide cover metadata from the exact referenced identity", async () => {
  const fetch = mockImageFetch();
  renderVisual(
    <RecordIdentities value={new Map([[identity.id, identity]])}>
      <RecordVisual
        kind="seed"
        label="Packet"
        identity={{
          id: identity.id,
          display_label: identity.display_label,
          scientific_name: identity.scientific_name,
        }}
      />
    </RecordIdentities>,
  );
  const img = await screen.findByRole("img", {
    name: "Botanical identity cover for Packet",
  });
  expect(img.getAttribute("src")).toMatch(/^blob:/);
  expect(fetch).toHaveBeenCalledWith(
    "/api/v1/botanical-identities/identity/cover-image/thumbnail",
    expect.objectContaining({ credentials: "same-origin" }),
  );
});

test("missing and ambiguous identity never borrow a cover from other available identities", () => {
  const { rerender } = renderVisual(
    <RecordIdentities value={new Map([[identity.id, identity]])}>
      <RecordVisual kind="group" label="Mixed group" />
    </RecordIdentities>,
  );
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  rerender(
    wrap(
      <RecordIdentities value={new Map([[identity.id, identity]])}>
        <RecordVisual
          kind="plant"
          label="Unknown plant"
          identity={{ id: "different", display_label: "Okra" }}
        />
      </RecordIdentities>,
    ),
  );
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});

test("a newly designated own photo immediately supersedes the botanical reference", async () => {
  const fetch = mockImageFetch();
  const { rerender } = renderVisual(
    <RecordVisual
      kind="plant"
      label="Specimen"
      identity={identity}
      showSource
    />,
  );
  expect(await screen.findByRole("img")).toHaveAccessibleName(
    "Botanical identity cover for Specimen",
  );
  rerender(
    wrap(
      <RecordVisual
        kind="plant"
        label="Specimen"
        identity={identity}
        showSource
        photo={{ kind: "local", photo_id: "new", thumbnail_url: "/new-own" }}
      />,
    ),
  );
  await waitFor(() => {
    expect(fetch).toHaveBeenLastCalledWith(
      "/new-own",
      expect.objectContaining({ credentials: "same-origin" }),
    );
  });
  const own = await screen.findByRole("img", {
    name: "Primary photo for Specimen",
  });
  expect(own.getAttribute("src")).toMatch(/^blob:/);
  expect(
    screen.queryByText("Botanical identity cover · reference"),
  ).not.toBeInTheDocument();
});

test("an explicit cover removal wins over older shared reference metadata", () => {
  render(
    <RecordIdentities value={new Map([[identity.id, identity]])}>
      <RecordVisual
        kind="seed"
        label="Packet"
        identity={{ ...identity, compact_cover_kind: null }}
      />
    </RecordIdentities>,
  );
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});

test("lazy protected image defers fetch until IntersectionObserver intersects and revokes blob URLs on unmount/error", async () => {
  const callbacks: IntersectionObserverCallback[] = [];
  class MockObserver {
    constructor(cb: IntersectionObserverCallback) {
      callbacks.push(cb);
    }
    observe = vi.fn();
    disconnect = vi.fn();
    unobserve = vi.fn();
  }
  vi.stubGlobal("IntersectionObserver", MockObserver);
  const fetchSpy = mockImageFetch();
  const revokeSpy = vi.spyOn(URL, "revokeObjectURL");

  const view = renderVisual(
    <RecordVisual
      kind="plant"
      label="Specimen"
      identity={identity}
      photo={{
        kind: "local",
        photo_id: "lazy-1",
        thumbnail_url: "/lazy-thumb",
      }}
    />,
  );
  expect(fetchSpy).not.toHaveBeenCalled();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();

  for (const cb of callbacks) {
    cb(
      [{ isIntersecting: true } as IntersectionObserverEntry],
      {} as IntersectionObserver,
    );
  }
  const img = await screen.findByRole("img", {
    name: "Primary photo for Specimen",
  });
  const blobUrl = img.getAttribute("src") ?? "";
  expect(blobUrl).toMatch(/^blob:/);
  expect(fetchSpy).toHaveBeenCalledWith(
    "/lazy-thumb",
    expect.objectContaining({ credentials: "same-origin" }),
  );

  view.unmount();
  expect(revokeSpy).toHaveBeenCalledWith(blobUrl);
});

test("protected image revokes blob URLs immediately on workspace owner switch", async () => {
  const first = await acquireTestAuth({ session: { user_id: "owner-a" } });
  const ownerAuth = { ...auth, capability: first.capability };
  const fetchSpy = mockImageFetch();
  const revokeSpy = vi.spyOn(URL, "revokeObjectURL");

  const view = render(
    <AuthContext.Provider value={ownerAuth}>
      <RecordVisual
        kind="plant"
        label="Specimen"
        identity={identity}
        photo={{
          kind: "local",
          photo_id: "switch-1",
          thumbnail_url: "/switch-thumb",
        }}
      />
    </AuthContext.Provider>,
  );
  const img = await screen.findByRole("img", {
    name: "Primary photo for Specimen",
  });
  const blobUrl = img.getAttribute("src") ?? "";
  expect(blobUrl).toMatch(/^blob:/);
  expect(fetchSpy).toHaveBeenCalledTimes(1);

  // Switch owner workspace to owner-b with a new workspace capability -> previous blob URL is immediately revoked.
  const second = await acquireTestAuth({ session: { user_id: "owner-b" } });
  view.rerender(
    <AuthContext.Provider
      value={{ ...second.auth, state: { status: "unauthenticated" } }}
    >
      <RecordVisual
        kind="plant"
        label="Specimen"
        identity={identity}
        photo={{
          kind: "local",
          photo_id: "switch-1",
          thumbnail_url: "/switch-thumb",
        }}
      />
    </AuthContext.Provider>,
  );
  await waitFor(() => {
    expect(revokeSpy).toHaveBeenCalledWith(blobUrl);
  });
  first.unmount();
  second.unmount();
});
