import { cleanup, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/context";
import { ExternalCopyChoice } from "../media/ExternalCopyChoice";
import { acquireTestAuth } from "../test/auth";
import type { ApplicationSettings } from "./api";
import { MediaSettingsScreen } from "./MediaSettingsScreen";

let auth: AuthContextValue;
beforeEach(async () => {
  auth = (await acquireTestAuth({ csrfToken: "csrf-test" })).auth;
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const stored: ApplicationSettings = {
  public_qr_base_url: "https://flora.example",
  default_label_preset: "large",
  media_save_local_copy_default: true,
  media_default_attribution: null,
  media_default_licence_label: null,
  media_default_licence_url: null,
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function withAuth(node: ReactNode) {
  return render(
    <AuthContext.Provider value={auth}>{node}</AuthContext.Provider>,
  );
}

test("saves media defaults while preserving QR and label preferences", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((_input, init) =>
      Promise.resolve(
        init?.method === "PUT"
          ? json(JSON.parse(init.body as string))
          : json(stored),
      ),
    );
  const user = userEvent.setup();
  withAuth(<MediaSettingsScreen />);
  const toggle = await screen.findByRole("checkbox", {
    name: /Pre-select “Save a local copy”/,
  });
  expect(toggle).toBeChecked();
  expect(
    screen.getByText(/never fetches remote images on its own/),
  ).toBeVisible();
  await user.click(toggle);
  await user.type(screen.getByLabelText("Default attribution"), "Photo: Owner");
  await user.type(screen.getByLabelText("Default licence label"), "CC BY 4.0");
  await user.type(
    screen.getByLabelText("Default licence URL"),
    "https://creativecommons.org/licenses/by/4.0/",
  );
  await user.click(screen.getByRole("button", { name: "Save media settings" }));
  expect(await screen.findByText("Media settings saved.")).toBeVisible();
  const put = fetch.mock.calls.find(([, init]) => init?.method === "PUT");
  expect(JSON.parse(put?.[1]?.body as string)).toEqual({
    ...stored,
    media_save_local_copy_default: false,
    media_default_attribution: "Photo: Owner",
    media_default_licence_label: "CC BY 4.0",
    media_default_licence_url: "https://creativecommons.org/licenses/by/4.0/",
  });
  expect(
    screen.getByRole("checkbox", { name: /Pre-select/ }),
  ).not.toBeChecked();
});

test("shows load failure with retry and keeps edits after a rejected save", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(json({ detail: "down" }, 503))
    .mockResolvedValueOnce(json(stored))
    .mockResolvedValueOnce(json(stored))
    .mockResolvedValueOnce(json({ detail: [] }, 422));
  const user = userEvent.setup();
  withAuth(<MediaSettingsScreen />);
  expect(
    await screen.findByText("Could not load media settings."),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Retry" }));
  const url = await screen.findByLabelText("Default licence URL");
  await user.type(url, "https://licence.example/terms");
  await user.click(screen.getByRole("button", { name: "Save media settings" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "licence URL must be an absolute HTTPS URL",
  );
  expect(url).toHaveValue("https://licence.example/terms");
  expect(fetch).toHaveBeenCalledTimes(4);
});

test("the external-image local copy choice follows the saved default", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    json({ ...stored, media_save_local_copy_default: false }),
  );
  withAuth(<ExternalCopyChoice disabled={false} />);
  const choice = screen.getByRole("checkbox", {
    name: "Save a local copy in Florabase",
  });
  // Built-in default while loading, then the configured one.
  expect(choice).toBeChecked();
  await waitFor(() => {
    expect(
      screen.getByRole("checkbox", { name: "Save a local copy in Florabase" }),
    ).not.toBeChecked();
  });
});
