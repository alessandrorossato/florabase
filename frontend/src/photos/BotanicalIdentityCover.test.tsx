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

import { BotanicalIdentityCover } from "./BotanicalIdentityCover";
import type { BotanicalIdentityCover as Cover } from "../botanical-identities/api";

const identityId = "01900000-0000-7000-8000-000000000501";
const external: Cover = {
  kind: "external",
  id: "01900000-0000-7000-8000-000000000601",
  image_url: "https://images.example.test/flower.jpg",
  source_url: "https://example.test/flower",
  attribution: "Ada Example",
  licence_label: "CC BY 4.0",
  licence_url: "https://creativecommons.org/licenses/by/4.0/",
  created_at: "2026-09-14T08:00:00Z",
  updated_at: "2026-09-14T08:00:00Z",
};
const local: Cover = {
  kind: "local",
  id: "01900000-0000-7000-8000-000000000601",
  attachment_id: "01900000-0000-7000-8000-000000000602",
  original_filename: "flower.png",
  media_type: "image/png",
  deletion_pending: false,
  content_url:
    "/api/v1/attachments/01900000-0000-7000-8000-000000000602/content",
  created_at: "2026-09-14T08:00:00Z",
  updated_at: "2026-09-14T08:00:00Z",
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderCover() {
  return render(
    <BotanicalIdentityCover
      csrfToken="csrf-test"
      identityId={identityId}
      identityLabel="Passiflora edulis"
    />,
  );
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("requires explicit privacy approval then automatically renders an external cover safely", async () => {
  Object.defineProperties(window, {
    innerWidth: { configurable: true, value: 390 },
    innerHeight: { configurable: true, value: 844 },
  });
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json(null))
    .mockResolvedValueOnce(json(external));
  const user = userEvent.setup();
  renderCover();
  expect(
    await screen.findByText("No representative cover image is set."),
  ).toBeVisible();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();

  const opener = screen.getByRole("button", { name: "Set cover image" });
  await user.click(opener);
  await user.click(screen.getByRole("button", { name: "Use external image" }));
  const dialog = screen.getByRole("dialog", { name: "Set identity cover" });
  expect(dialog).toHaveTextContent(
    /host can see normal network information.*IP address/is,
  );
  await user.type(
    within(dialog).getByLabelText("Image URL"),
    external.image_url,
  );
  await user.type(
    within(dialog).getByLabelText("Source/page URL"),
    external.source_url,
  );
  await user.type(
    within(dialog).getByLabelText("Attribution"),
    external.attribution,
  );
  const form = dialog.querySelector("form");
  if (!form) throw new Error("External cover form was not rendered");
  fireEvent.submit(form);
  expect(
    within(dialog).getByText(/confirm the external-image privacy notice/i),
  ).toBeVisible();
  await user.click(within(dialog).getByRole("checkbox"));
  fireEvent.submit(form);

  const image = await screen.findByRole("img", {
    name: "Representative image for Passiflora edulis",
  });
  expect(image).toHaveAttribute("src", external.image_url);
  expect(image).toHaveAttribute("referrerpolicy", "no-referrer");
  expect(image).toHaveAttribute("loading", "lazy");
  expect(screen.getByText("Ada Example")).toBeVisible();
  expect(screen.getByRole("link", { name: "Source" })).toHaveAttribute(
    "rel",
    "noopener noreferrer",
  );
  expect(
    screen.getByRole("link", { name: "Licence: CC BY 4.0" }),
  ).toHaveAttribute("href", external.licence_url);
  const rawBody = fetch.mock.calls[1]?.[1]?.body;
  if (typeof rawBody !== "string")
    throw new Error("External cover request body was not JSON");
  const requestBody = JSON.parse(rawBody) as {
    privacy_acknowledged: boolean;
  };
  expect(requestBody.privacy_acknowledged).toBe(true);
  expect(fetch).toHaveBeenCalledTimes(2);

  fireEvent.error(image);
  expect(
    await screen.findByText(/external cover image is unavailable/i),
  ).toBeVisible();
  expect(screen.getByText("Ada Example")).toBeVisible();
  expect(screen.getByRole("button", { name: "Change cover" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Remove cover" })).toBeVisible();
});

test("renders local content lazily, reports breakage, uploads a replacement, and restores focus", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json(local))
    .mockResolvedValueOnce(json({ ...local, original_filename: "new.png" }));
  const user = userEvent.setup();
  renderCover();
  const image = await screen.findByRole("img", {
    name: "Representative image for Passiflora edulis",
  });
  expect(image).toHaveAttribute("src", local.content_url);
  expect(image).toHaveAttribute("loading", "lazy");
  fireEvent.error(image);
  expect(
    await screen.findByText(/uploaded cover image is unavailable/i),
  ).toBeVisible();

  const change = screen.getByRole("button", { name: "Change cover" });
  await user.click(change);
  screen.getByRole("dialog", { name: "Change identity cover" });
  await user.keyboard("{Escape}");
  expect(change).toHaveFocus();

  await user.click(change);
  const reopened = screen.getByRole("dialog", {
    name: "Change identity cover",
  });
  const file = new File(["png"], "new.png", { type: "image/png" });
  await user.upload(within(reopened).getByLabelText("Image file"), file);
  const form = reopened.querySelector("form");
  if (!form) throw new Error("Local cover form was not rendered");
  fireEvent.submit(form);
  expect(await screen.findByText("Cover image was saved.")).toBeVisible();
  const upload = fetch.mock.calls[1]?.[1];
  expect(upload?.method).toBe("POST");
  expect(upload?.body).toBeInstanceOf(FormData);
  expect(new Headers(upload?.headers).get("Content-Type")).toBeNull();
});

test("compacts URL-like attribution instead of exposing a raw URL", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
    json({
      ...external,
      attribution: "https://photos.example.test/archive/very-long-credit",
    }),
  );
  renderCover();
  await screen.findByRole("img", {
    name: "Representative image for Passiflora edulis",
  });
  expect(screen.getByText("photos.example.test")).toBeVisible();
  expect(
    screen.queryByText("https://photos.example.test/archive/very-long-credit"),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Source" })).toHaveAttribute(
    "href",
    external.source_url,
  );
});

test("keeps pending local cleanup truthful and provides deterministic removal retry", async () => {
  const pending: Cover = {
    ...local,
    deletion_pending: true,
    content_url: null,
  };
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json(pending))
    .mockResolvedValueOnce(new Response(null, { status: 204 }));
  const user = userEvent.setup();
  renderCover();
  expect(
    await screen.findByText(/local cover deletion is pending/i),
  ).toBeVisible();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Retry removal" }));
  const dialog = screen.getByRole("dialog", { name: "Remove identity cover?" });
  expect(dialog).toHaveTextContent(/protected binary will be deleted/i);
  await user.click(
    within(dialog).getByRole("button", { name: "Remove cover" }),
  );
  await waitFor(() => {
    expect(fetch).toHaveBeenLastCalledWith(
      `/api/v1/botanical-identities/${identityId}/cover-image`,
      expect.objectContaining({ method: "DELETE" }),
    );
  });
  expect(await screen.findByText("Cover image was removed.")).toBeVisible();
});
