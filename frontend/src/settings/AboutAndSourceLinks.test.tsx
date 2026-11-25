import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { AboutScreen, PROJECT_URL } from "./AboutScreen";
import { DataSourcesScreen } from "./DataSourcesScreen";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function stubRelease(response: Response | Error) {
  const fetchMock = vi.fn(() =>
    response instanceof Error
      ? Promise.reject(response)
      : Promise.resolve(response),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

test("About shows the image release, changelog, licence and project links", async () => {
  const fetchMock = stubRelease(
    Response.json({
      version: "0.1.0-beta.9",
      revision: "98003B5c0ffee0000000000000000000000000ab",
      source: "https://github.com/alessandrorossato/florabase",
    }),
  );
  render(<AboutScreen />);

  expect(
    screen.getByRole("heading", { name: "About", level: 2 }),
  ).toBeVisible();
  expect(await screen.findByText("98003b5")).toBeVisible();
  expect(fetchMock).toHaveBeenCalledWith("/release.json", expect.anything());
  expect(screen.getByText("Florabase 0.1.0-beta.9")).toBeVisible();
  expect(
    screen.getByRole("link", { name: "Changelog for v0.1.0-beta.9" }),
  ).toHaveAttribute("href", `${PROJECT_URL}/blob/v0.1.0-beta.9/CHANGELOG.md`);
  expect(
    screen.getByRole("link", { name: "Release notes for v0.1.0-beta.9" }),
  ).toHaveAttribute("href", `${PROJECT_URL}/releases/tag/v0.1.0-beta.9`);
  expect(screen.getByRole("link", { name: "Licence text" })).toHaveAttribute(
    "href",
    "/LICENSE",
  );
  expect(
    screen.getByRole("link", { name: "Third-party notices" }),
  ).toHaveAttribute("href", "/THIRD_PARTY_NOTICES.txt");
  expect(screen.getByRole("link", { name: PROJECT_URL })).toHaveAttribute(
    "rel",
    "noopener noreferrer",
  );
});

test("About falls back to the build version and project URL without release metadata", async () => {
  stubRelease(new Response("<!doctype html>", { status: 404 }));
  render(<AboutScreen />);

  expect(
    await screen.findByText("Development build (no release metadata)"),
  ).toBeVisible();
  expect(
    screen.getByText(`Florabase ${__FLORABASE_APP_VERSION__}`),
  ).toBeVisible();
  expect(screen.getByRole("link", { name: PROJECT_URL })).toBeVisible();
});

test("About ignores a non-https source from release metadata", async () => {
  stubRelease(
    Response.json({
      version: "1.2.3",
      revision: "manual",
      source: "javascript:alert(1)",
    }),
  );
  render(<AboutScreen />);

  expect(await screen.findByText("manual")).toBeVisible();
  expect(
    screen.getByRole("link", { name: "Changelog for v1.2.3" }),
  ).toHaveAttribute("href", `${PROJECT_URL}/blob/v1.2.3/CHANGELOG.md`);
});

test("Data sources link each external source to its official site in a new tab", () => {
  render(<DataSourcesScreen />);
  const table = screen.getByRole("table");
  const expected: [string, string][] = [
    ["World Flora Online (WFO) website", "https://www.worldfloraonline.org/"],
    [
      "World Flora Online (WFO) dataset release",
      "https://doi.org/10.5281/zenodo.20782718",
    ],
    ["Kew WCVP website", "https://powo.science.kew.org/about-wcvp"],
    [
      "Kew WCVP dataset release",
      "https://sftp.kew.org/pub/data-repositories/WCVP/",
    ],
    ["GBIF website", "https://www.gbif.org/"],
    ["Natural Earth website", "https://www.naturalearthdata.com/"],
    ["OpenStreetMap tiles website", "https://www.openstreetmap.org/copyright"],
  ];
  for (const [name, href] of expected) {
    const link = within(table).getByRole("link", { name });
    expect(link).toHaveAttribute("href", href);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  }
  const csvRow = within(table)
    .getByRole("rowheader", { name: "Your own data (CSV)" })
    .closest("tr");
  if (!csvRow) throw new Error("CSV row missing");
  expect(within(csvRow).getAllByRole("link")).toHaveLength(1);
});
