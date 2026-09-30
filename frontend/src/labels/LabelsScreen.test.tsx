/// <reference types="node" />
import { readFileSync } from "node:fs";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StrictMode } from "react";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "../App";
import { LabelSheet } from "./LabelSheet";
import { qrGeometry } from "./qrCode";
import { LabelsScreen } from "./LabelsScreen";
import {
  composePages,
  isLabelKind,
  labelKinds,
  listLabelRecords,
  recordUrl,
  type LabelKind,
  type LabelRecord,
} from "./labelData";

const id = "01900000-0000-7000-8000-000000000211";
const canonicalOrigin = "https://flora.example";
const sample: LabelRecord = {
  kind: "seed-lot",
  id,
  botanicalName: "Clitoria ternatea",
  context: "Packet A",
};
function response(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
function mockRecords() {
  return vi.spyOn(globalThis, "fetch").mockImplementation(() =>
    Promise.resolve(
      response([
        {
          id,
          label: "Packet A",
          botanical_identity: { display_label: "Clitoria ternatea" },
          primary_photo: {
            kind: "external",
            url: "https://unused.example/photo.jpg",
          },
        },
      ]),
    ),
  );
}
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.history.replaceState(null, "", "/");
});

test.each([
  ["seed-lot", "seeds"],
  ["plant", "plants"],
  ["plant-group", "plant-groups"],
] as const)(
  "%s QR contains only the configured-origin stable %s deep link",
  (kind, route) => {
    window.history.replaceState(
      null,
      "",
      "/?token=never-copy#/dashboard?csrf=never-copy",
    );
    const url = recordUrl(kind, id, canonicalOrigin);
    expect(url).toBe(`${canonicalOrigin}/#/${route}/${id}`);
    const parsed = new URL(url);
    expect(parsed.search).toBe("");
    expect(parsed.username).toBe("");
    expect(parsed.password).toBe("");
    expect(url).not.toMatch(/token|csrf|session|cookie|bearer/i);
  },
);

test("unsupported targets and injected references cannot become QR URLs", () => {
  for (const kind of [
    "sowing",
    "event",
    "identity",
    "supplier",
    "https://evil.example",
  ]) {
    expect(isLabelKind(kind)).toBe(false);
    expect(() => recordUrl(kind as LabelKind, id, canonicalOrigin)).toThrow();
  }
  for (const reference of [
    "",
    "invalid",
    `${id}?token=secret`,
    `${id}/other`,
    "https://evil.example",
  ]) {
    expect(() => recordUrl("plant", reference, canonicalOrigin)).toThrow();
  }
});

test("QR uses configured development and production origins, never the browser host", () => {
  expect(recordUrl("plant", id, "http://localhost:5173")).toBe(
    `http://localhost:5173/#/plants/${id}`,
  );
  expect(recordUrl("plant-group", id, canonicalOrigin)).toBe(
    `https://flora.example/#/plant-groups/${id}`,
  );
});

test.each([
  null,
  "",
  "https://user:secret@flora.example",
  "https://flora.example/other",
  "https://flora.example/?token=secret",
  "https://flora.example/#token=secret",
  "javascript:alert(1)",
])("invalid configured QR origin %s is rejected", (origin) => {
  expect(() => recordUrl("plant", id, origin)).toThrow();
});

test.each(labelKinds)(
  "label data for %s uses only the existing protected list and readable identity",
  async (kind) => {
    const fetch = mockRecords();
    const records = await listLabelRecords(kind, new AbortController().signal);
    expect(records).toEqual([{ ...sample, kind }]);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][1]?.credentials).toBe("same-origin");
    expect(fetch.mock.calls[0][0]).toBe(
      `/api/v1/${kind === "seed-lot" ? "seed-lots" : kind === "plant" ? "plants" : "plant-groups"}`,
    );
  },
);

test("partial identity and absent optional context remain explicit", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    response([
      { id, label: null, botanical_identity: { display_label: "Solanum sp." } },
      { id, label: "  ", botanical_identity: { display_label: " " } },
    ]),
  );
  const records = await listLabelRecords("plant", new AbortController().signal);
  expect(
    records.map(({ botanicalName, context }) => [botanicalName, context]),
  ).toEqual([
    ["Solanum sp.", null],
    ["Botanical identity unavailable", null],
  ]);
});

test("mixed records and duplicates fill one bounded A4 sheet", () => {
  const pages = composePages([
    { record: sample, copies: 2 },
    { record: { ...sample, kind: "plant" }, copies: 1 },
    { record: { ...sample, kind: "plant-group" }, copies: 33 },
  ]);
  expect(pages).toHaveLength(1);
  expect(pages[0]).toHaveLength(36);
  expect(pages[0].map(({ kind }) => kind).slice(0, 3)).toEqual([
    "seed-lot",
    "seed-lot",
    "plant",
  ]);
  expect(composePages([])).toEqual([]);
  for (const count of [0, -1, 1.5, 37, NaN])
    expect(() => composePages([{ record: sample, copies: count }])).toThrow();
  expect(() =>
    composePages([
      { record: sample, copies: 36 },
      { record: sample, copies: 1 },
    ]),
  ).toThrow();
});

test("print content is compact, safe text with cultivar and bounded long-name containers", () => {
  const long =
    "Pelargonium extremelylonginfraspecificname subsp. extraordinarilylongname ‘Cultivar’";
  const { container } = render(
    <LabelSheet
      pages={[
        [
          sample,
          {
            ...sample,
            kind: "plant",
            botanicalName: long,
            context: "<img src='https://unused.example'>",
          },
          {
            ...sample,
            kind: "plant-group",
            botanicalName: "Solanum sp.",
            context: null,
          },
        ],
      ]}
      canonicalOrigin={canonicalOrigin}
    />,
  );
  expect(container.querySelectorAll(".physical-label")).toHaveLength(3);
  expect(screen.getByText(sample.botanicalName)).toBeVisible();
  for (const name of [
    "Seed lot",
    "Plant",
    "Plant group",
    "Packet A",
    "Solanum sp.",
  ])
    expect(screen.getByText(name)).toBeVisible();
  expect(screen.getByText(long)).toHaveClass("physical-label__name");
  expect(container.querySelector("img")).toBeNull();
  expect(container.querySelectorAll("svg title")[0].textContent).toBe(
    recordUrl("seed-lot", id, canonicalOrigin),
  );
});

test("SVG QR retains a four-module white quiet zone and standard finder geometry", () => {
  const { size, path } = qrGeometry(recordUrl("plant", id, canonicalOrigin));
  const modules = [...path.matchAll(/M(\d+),(\d+)h1v1h-1z/g)].map((m) => [
    Number(m[1]),
    Number(m[2]),
  ]);
  expect(size).toBeGreaterThanOrEqual(29);
  expect(modules.length).toBeGreaterThan(100);
  expect(
    modules.every(([x, y]) => x >= 4 && y >= 4 && x < size - 4 && y < size - 4),
  ).toBe(true);
  const dark = new Set(modules.map(([x, y]) => `${String(x)},${String(y)}`));
  for (let y = 0; y < 7; y++)
    for (let x = 0; x < 7; x++) {
      const expected =
        x === 0 ||
        x === 6 ||
        y === 0 ||
        y === 6 ||
        (x >= 2 && x <= 4 && y >= 2 && y <= 4);
      expect(dark.has(`${String(x + 4)},${String(y + 4)}`)).toBe(expected);
    }
});

test("print stylesheet fixes A4, exact label/grid dimensions and isolated unsplit output", () => {
  const css = readFileSync("src/labels/labels.css", "utf8");
  expect(css).toMatch(/@page florabase-labels\s*\{\s*size: A4 portrait;/);
  expect(css).toContain("margin: 13.5mm 5mm");
  expect(css).toContain("width: 50mm");
  expect(css).toContain("height: 30mm");
  expect(css).toContain("box-sizing: border-box");
  expect(css).toContain("break-inside: avoid");
  expect(css).toContain("repeat(4, 50mm)");
  expect(css).toContain("repeat(9, 30mm)");
  expect(css).toContain("display: none !important");
  expect(css).not.toMatch(/scale\(|zoom:/);
  expect(css).toContain("overflow: hidden");
  expect(css).toContain("-webkit-line-clamp: 4");
});

test("empty workspace, keyboard add, copy validation, printing and removal", async () => {
  mockRecords();
  const print = vi.spyOn(window, "print").mockImplementation(() => undefined);
  const user = userEvent.setup();
  render(<LabelsScreen canonicalOrigin={canonicalOrigin} />);
  expect(screen.getByRole("button", { name: "Print sheet" })).toBeDisabled();
  expect(screen.getByText("Your label sheet is empty.")).toBeVisible();
  const printSetup = screen.getByText("Print setup and QR guidance");
  expect(printSetup.closest("details")).not.toHaveAttribute("open");
  await user.click(printSetup);
  expect(printSetup.closest("details")).toHaveAttribute("open");
  expect(screen.getByText(/Print at 100%/)).toBeVisible();
  await user.click(printSetup);
  expect(printSetup.closest("details")).not.toHaveAttribute("open");
  const picker = await screen.findByRole("combobox", { name: "Record" });
  await user.click(picker);
  await user.keyboard("{ArrowDown}{Enter}");
  await user.click(screen.getByRole("button", { name: "Add label" }));
  const preview = screen.getByRole("region", { name: "Sheet preview" });
  expect(within(preview).getAllByRole("article")).toHaveLength(1);
  const copies = screen.getByRole("spinbutton");
  fireEvent.change(copies, { target: { value: "3" } });
  expect(within(preview).getAllByRole("article")).toHaveLength(3);
  expect(screen.getByText("33 spaces remaining")).toBeInTheDocument();
  fireEvent.change(copies, { target: { value: "37" } });
  expect(screen.getByRole("alert")).toHaveTextContent("sheet holds 36");
  expect(within(preview).getAllByRole("article")).toHaveLength(3);
  fireEvent.change(copies, { target: { value: "36" } });
  expect(screen.getByText("0 spaces remaining")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Add label" }));
  expect(screen.getByRole("alert")).toHaveTextContent("sheet is full");
  await user.click(screen.getByRole("button", { name: "Print sheet" }));
  expect(print).toHaveBeenCalledOnce();
  await user.click(screen.getByRole("button", { name: /^Remove / }));
  expect(screen.getByRole("combobox", { name: "Record type" })).toHaveFocus();
  expect(screen.getByText("Your label sheet is empty.")).toBeVisible();
  expect(screen.getByText("36 spaces remaining")).toBeInTheDocument();
});

test("detail entry adds once under StrictMode, supports mixing record types and duplicate copies", async () => {
  mockRecords();
  const user = userEvent.setup();
  render(
    <StrictMode>
      <LabelsScreen
        initialKind="plant"
        initialId={id}
        canonicalOrigin={canonicalOrigin}
      />
    </StrictMode>,
  );
  await screen.findByRole("spinbutton");
  expect(
    screen.getByRole("heading", { name: "Sheet entries · 1 / 36" }),
  ).toBeVisible();
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Record type" }),
    "plant-group",
  );
  await user.click(await screen.findByRole("combobox", { name: "Record" }));
  await user.keyboard("{ArrowDown}{Enter}");
  await user.click(screen.getByRole("button", { name: "Add label" }));
  await user.click(screen.getByRole("button", { name: "Add label" }));
  expect(
    screen
      .getAllByRole("spinbutton")
      .map((input) => (input as HTMLInputElement).value),
  ).toEqual(["1", "2"]);
  expect(
    screen.getByRole("heading", { name: "Sheet entries · 3 / 36" }),
  ).toBeVisible();
});

test("load errors retry, empty lists explain themselves, unsupported deep links stay empty", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValue(response([]));
  const user = userEvent.setup();
  render(
    <LabelsScreen
      initialKind="sowing"
      initialId={id}
      canonicalOrigin={canonicalOrigin}
    />,
  );
  await screen.findByText("Could not load records.");
  await user.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByText("No seed lot records available.");
  expect(screen.getByRole("alert")).toHaveTextContent(
    "requested label target is unavailable",
  );
  expect(screen.getByRole("button", { name: "Print sheet" })).toBeDisabled();
  expect(fetch).toHaveBeenCalledTimes(2);
});

test.each([
  `#/seeds/${id}`,
  `#/plants/${id}`,
  `#/plant-groups/${id}`,
  "#/labels",
])("unauthenticated %s retains normal login protection", async (hash) => {
  window.location.hash = hash;
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(response({ detail: "Authentication required" }, 401));
  render(<App />);
  await screen.findByRole("button", { name: "Sign in" });
  expect(
    screen.queryByRole("button", { name: "Print sheet" }),
  ).not.toBeInTheDocument();
  expect(fetch.mock.calls.map(([path]) => path)).toEqual([
    "/api/v1/auth/session",
  ]);
});

test("authenticated labels route composes the exact requested record", async () => {
  window.location.hash = `#/labels?kind=seed-lot&record=${id}`;
  vi.spyOn(globalThis, "fetch").mockImplementation((path) => {
    if (path === "/api/v1/auth/session")
      return Promise.resolve(
        response({
          user_id: id,
          login_name: "owner",
          display_name: null,
          owner: true,
          canonical_origin: canonicalOrigin,
        }),
      );
    if (path === "/api/v1/auth/csrf")
      return Promise.resolve(response({ csrf_token: "never-encode" }));
    if (path === "/api/v1/health")
      return Promise.resolve(response({ status: "ok" }));
    return Promise.resolve(
      response([
        {
          id,
          label: "Packet A",
          botanical_identity: { display_label: "Clitoria ternatea" },
        },
      ]),
    );
  });
  render(<App />);
  await waitFor(() => {
    expect(screen.getByRole("button", { name: "Print sheet" })).toBeEnabled();
  });
  expect(
    document.querySelector(".label-print-root svg title")?.textContent,
  ).toBe(recordUrl("seed-lot", id, canonicalOrigin));
});
