import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { App } from "../App";
import { openSection } from "../test/navigation";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

type ExportReply = () => Promise<Response>;

function mockServer({
  exportReply,
  demo = false,
}: {
  exportReply: ExportReply;
  demo?: boolean;
}) {
  const paths: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const path =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    paths.push(path);
    if (path.endsWith("/auth/session"))
      return Promise.resolve(
        jsonResponse({
          user_id: "01900000-0000-7000-8000-000000000001",
          login_name: "owner",
          display_name: "Owner",
          owner: true,
          demo_readonly: demo,
        }),
      );
    if (path.endsWith("/auth/csrf"))
      return Promise.resolve(jsonResponse({ csrf_token: "csrf-value" }));
    if (path.endsWith("/health"))
      return Promise.resolve(jsonResponse({ status: "ok" }));
    if (path.endsWith("/exports/full/summary"))
      return Promise.resolve(
        jsonResponse({
          records: 120,
          attachments: 3,
          attachment_bytes: 5 * 1024 * 1024,
          files_allowed: !demo,
        }),
      );
    if (path.includes("/exports/full.zip")) return exportReply();
    return Promise.resolve(jsonResponse([]));
  });
  return paths;
}

function zipResponse() {
  return new Response(new Uint8Array([0x50, 0x4b, 0x03, 0x04]), {
    status: 200,
    headers: {
      "Content-Type": "application/zip",
      "Content-Disposition":
        'attachment; filename="florabase-export-20261128T120000Z.zip"',
    },
  });
}

beforeEach(() => {
  window.location.hash = "#/dashboard";
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("downloads the full export, shows progress and the photo size estimate", async () => {
  const user = userEvent.setup();
  let release: ((response: Response) => void) | undefined;
  const paths = mockServer({
    exportReply: () =>
      new Promise<Response>((resolve) => {
        release = resolve;
      }),
  });
  vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:zip");
  const names: string[] = [];
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    names.push(this.download);
  });

  render(<App />);
  await openSection(user, "Import / Export");
  expect(
    await screen.findByRole("heading", { name: "Export all data" }),
  ).toBeInTheDocument();
  expect(screen.getByText("This is not a backup.")).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "backup and restore" }),
  ).toHaveAttribute("href", expect.stringContaining("backup-restore.md"));
  expect(paths.some((path) => path.endsWith("/exports/full/summary"))).toBe(
    false,
  );

  await user.click(
    screen.getByRole("checkbox", { name: "Include photos and files" }),
  );
  expect(
    await screen.findByText("3 files, about 5.0 MB in total."),
  ).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Export all data" }));
  const busy = await screen.findByRole("button", {
    name: "Preparing export…",
  });
  expect(busy).toBeDisabled();
  expect(
    paths.some((path) => path.endsWith("/exports/full.zip?include_files=true")),
  ).toBe(true);
  release?.(zipResponse());
  await waitFor(() => {
    expect(names).toEqual(["florabase-export-20261128T120000Z.zip"]);
  });
  expect(
    await screen.findByRole("button", { name: "Export all data" }),
  ).toBeEnabled();
});

test("shows an error when the export fails and lets the user retry", async () => {
  const user = userEvent.setup();
  let fail = true;
  const paths = mockServer({
    exportReply: () =>
      Promise.resolve(
        fail ? jsonResponse({ detail: "boom" }, 500) : zipResponse(),
      ),
  });
  vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:zip");
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(
    () => undefined,
  );

  render(<App />);
  await openSection(user, "Import / Export");
  await user.click(
    await screen.findByRole("button", { name: "Export all data" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Could not download the export. Try again.",
  );
  expect(
    paths.some((path) =>
      path.endsWith("/exports/full.zip?include_files=false"),
    ),
  ).toBe(true);
  fail = false;
  await user.click(screen.getByRole("button", { name: "Export all data" }));
  await waitFor(() => {
    expect(
      screen.queryByText("Could not download the export. Try again."),
    ).not.toBeInTheDocument();
  });
});

test("the public demo exports without the photo option", async () => {
  mockServer({ exportReply: () => Promise.resolve(zipResponse()), demo: true });

  // The demo tour dialog covers the navigation, so open the screen by its route.
  window.location.hash = "#/import-export";
  render(<App />);
  expect(
    await screen.findByText("Photos are not included in the public demo."),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("checkbox", { name: "Include photos and files" }),
  ).not.toBeInTheDocument();
});
