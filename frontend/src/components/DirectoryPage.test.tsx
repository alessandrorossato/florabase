import { useDirectoryPagination } from "./useDirectoryPagination";
import { DirectoryResults } from "./DirectoryResults";
import { StatusBadge } from "./WorkspaceUI";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRef, useState } from "react";
import { afterEach, expect, test, vi } from "vitest";
import {
  DirectoryRecordActions,
  DirectoryTrigger,
  DirectoryCard,
  DirectoryInspector,
  DirectoryPage,
  DirectoryRecords,
  DirectoryRow,
  DirectoryViewSwitcher,
} from "./DirectoryPage";
import {
  useDirectoryPresentation,
  directoryPresentationHash,
  directoryPreferenceKey,
  readDirectoryPresentation,
} from "./directoryPresentation";
import { useDirectoryView } from "../saved-views/useDirectoryView";
import { readDirectoryState, savedViewHash } from "../saved-views/state";
import { BotanicalName, PageHeader } from "./ReferenceUI";
import { PrimaryPhotoVisual } from "../photos/PrimaryPhotoVisual";
import { navigationIcons } from "./navigationIcons";
import { Icon } from "./Icon";

afterEach(() => {
  cleanup();
  window.localStorage.removeItem(directoryPreferenceKey("plants"));
  vi.restoreAllMocks();
});
function Example() {
  const presentation = useDirectoryPresentation("plants");
  const filters = useDirectoryView("plants");
  const [selected, setSelected] = useState(false);
  const [checked, setChecked] = useState(false);
  const ref = useRef<HTMLButtonElement | null>(null);
  const fallback = useRef<HTMLButtonElement | null>(null);
  const Row = presentation.view === "list" ? DirectoryRow : DirectoryCard;
  return (
    <DirectoryPage
      titleId="title"
      header={<PageHeader title="Plants" titleId="title" />}
      toolbar={
        <>
          <DirectoryViewSwitcher
            value={presentation.view}
            onChange={presentation.select}
          />
          <button
            ref={fallback}
            onClick={() => {
              filters.update("q", "Ficus");
            }}
          >
            Filter Ficus
          </button>
          <output aria-label="Current filters">
            {JSON.stringify(filters.savedState)}
          </output>
        </>
      }
      content={
        <DirectoryRecords label="Plants" view={presentation.view}>
          <Row
            label="Aloe"
            name={
              <BotanicalName
                label="Aloe vera ‘Tricolor’"
                scientificName="Aloe vera"
              />
            }
            href="#/plants/example"
            metadata={<span>Quantity unknown</span>}
            onPreview={(trigger) => {
              ref.current = trigger;
              setSelected(true);
            }}
            previewRef={selected ? ref : undefined}
            selected={selected}
            checked={checked}
            onCheck={setChecked}
          />
        </DirectoryRecords>
      }
      inspector={
        selected ? (
          <DirectoryInspector
            mode="modal"
            title="Aloe preview"
            returnFocusTo={ref}
            fallbackFocusTo={fallback}
            onClose={() => {
              setSelected(false);
            }}
          >
            Useful context
          </DirectoryInspector>
        ) : null
      }
    />
  );
}

test("view-only URLs preserve filters, scope, selection and pagination; canonical Saved Views exclude presentation", () => {
  const original =
    "#/plants?q=Ficus&type=group&lifecycle=history&identity_id=01900000-0000-7000-8000-000000000001&offset=20&selected=one";
  const next = directoryPresentationHash(original, "list");
  const params = new URLSearchParams(next.split("?")[1]);
  expect(params.get("q")).toBe("Ficus");
  expect(params.get("type")).toBe("group");
  expect(params.get("offset")).toBe("20");
  expect(params.get("selected")).toBe("one");
  expect(readDirectoryState("plants", next)).toEqual(
    readDirectoryState("plants", original),
  );
  expect(savedViewHash("plants", 1, { q: "Ficus", type: "group" })).toBe(
    "#/plants?q=Ficus&type=group",
  );
  expect(readDirectoryPresentation("seed_lots", "#/seeds?view=garbage")).toBe(
    "list",
  );
  expect(readDirectoryPresentation("sowings", "#/sowings")).toBe("list");
  expect(
    readDirectoryPresentation("botanical_identities", "#/identities"),
  ).toBe("gallery");
});

test("List/Gallery retains selection, checked state, filters and a correct focus-return target after remount", async () => {
  window.history.replaceState(
    { review: true },
    "",
    "#/plants?q=Aloe&type=plant&selected=one&offset=20",
  );
  const user = userEvent.setup();
  render(<Example />);
  expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  await user.click(screen.getByRole("checkbox", { name: "Select Aloe" }));
  await user.click(screen.getByRole("button", { name: "Quick preview Aloe" }));
  expect(screen.getByRole("button", { name: "Close preview" })).toHaveFocus();
  await user.click(screen.getByRole("button", { name: "List" }));
  expect(screen.getByRole("checkbox", { name: "Select Aloe" })).toBeChecked();
  expect(
    screen.getByRole("dialog", { name: "Aloe preview" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Quick preview Aloe" }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(window.history.state).toEqual({ review: true });
  await user.click(screen.getByRole("button", { name: "Close preview" }));
  expect(
    screen.getByRole("button", { name: "Quick preview Aloe" }),
  ).toHaveFocus();
  await user.click(screen.getByRole("button", { name: "Filter Ficus" }));
  expect(
    new URLSearchParams(window.location.hash.split("?")[1]).get("view"),
  ).toBe("list");
  expect(screen.getByLabelText("Current filters")).not.toHaveTextContent(
    "view",
  );
  expect(window.localStorage.getItem(directoryPreferenceKey("plants"))).toBe(
    "list",
  );
});

test("Back/forward view restoration follows URL over the preference, while Saved View URLs retain the preference", async () => {
  window.history.replaceState(null, "", "#/plants?view=list&q=Aloe");
  render(<Example />);
  await userEvent.click(screen.getByRole("button", { name: "Gallery" }));
  window.history.replaceState(null, "", "#/plants?view=list&q=Aloe");
  fireEvent.popState(window);
  expect(
    await screen.findByRole("button", { name: "List", pressed: true }),
  ).toBeInTheDocument();
  window.history.replaceState(null, "", "#/plants?q=Ficus");
  fireEvent(window, new HashChangeEvent("hashchange"));
  expect(
    await screen.findByRole("button", { name: "Gallery", pressed: true }),
  ).toBeInTheDocument();
});

test("browser storage denial does not prevent keyboard view switching", async () => {
  window.history.replaceState(null, "", "#/plants");
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw new Error("denied");
  });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("denied");
  });
  render(<Example />);
  screen.getByRole("button", { name: "List" }).focus();
  await userEvent.keyboard(" ");
  expect(
    screen.getByRole("button", { name: "List", pressed: true }),
  ).toHaveFocus();
  expect(window.location.hash).toContain("view=list");
});

test("compact preview uses the house dialog, contains focus and returns on Escape", async () => {
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query) =>
      ({
        matches: query.includes("75rem"),
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }) as unknown as MediaQueryList,
  );
  window.history.replaceState(null, "", "#/plants");
  render(<Example />);
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Quick preview Aloe" }));
  const dialog = screen.getByRole("dialog", { name: "Aloe preview" });
  expect(
    within(dialog).getByRole("button", { name: "Close preview" }),
  ).toHaveFocus();
  await user.keyboard("{Tab}");
  expect(
    within(dialog).getByRole("button", { name: "Close preview" }),
  ).toHaveFocus();
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Quick preview Aloe" }),
  ).toHaveFocus();
});

test("gallery has an honest missing image and preserves scientific/cultivar formatting", () => {
  window.history.replaceState(null, "", "#/plants?view=gallery");
  render(<Example />);
  expect(screen.getByText("No image for Aloe")).toBeInTheDocument();
  const link = screen.getByRole("button", { name: "Quick preview Aloe" });
  expect(link.querySelector("i")?.textContent).toBe("Aloe vera");
  expect(link.querySelector("i")?.textContent).not.toContain("Tricolor");
});

test("domain photo fallback is retained inside the shared card", () => {
  render(
    <DirectoryRecords label="Photos" view="gallery">
      <DirectoryCard
        label="Aloe"
        name="Aloe"
        href="#/plants/one"
        metadata="Location unknown"
        onPreview={() => undefined}
        visual={
          <PrimaryPhotoVisual
            label="Aloe"
            photo={{
              photo_id: "one",
              kind: "local",
              thumbnail_url: "/api/v1/collection-photos/one/thumbnail",
            }}
          />
        }
      />
    </DirectoryRecords>,
  );
  fireEvent.error(screen.getByRole("img", { name: "Primary photo for Aloe" }));
  expect(screen.getByText("Primary photo unavailable")).toBeInTheDocument();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});

test("every destination has a distinct decorative pictogram and a visible accessible label", () => {
  render(
    <nav>
      {Object.entries(navigationIcons).map(([name, icon]) => (
        <a key={name} href={`#/${name}`}>
          <Icon name={icon} />
          {name}
        </a>
      ))}
    </nav>,
  );
  expect(new Set(Object.values(navigationIcons)).size).toBe(
    Object.keys(navigationIcons).length,
  );
  for (const [name, icon] of Object.entries(navigationIcons)) {
    const link = screen.getByRole("link", { name });
    expect(link.querySelector("svg")).toHaveAttribute("data-icon", icon);
    expect(link.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  }
});

test.each([false, true])(
  "removed preview trigger uses a connected fallback (compact=%s)",
  async (compact) => {
    vi.spyOn(window, "matchMedia").mockImplementation(
      (query) =>
        ({
          matches: compact,
          media: query,
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
        }) as unknown as MediaQueryList,
    );
    function RemovalExample() {
      const [visible, setVisible] = useState(true);
      const [open, setOpen] = useState(false);
      const trigger = useRef<HTMLButtonElement | null>(null);
      const fallback = useRef<HTMLButtonElement | null>(null);
      return (
        <>
          <button ref={fallback}>Results</button>
          {visible && (
            <button
              ref={trigger}
              onClick={() => {
                setOpen(true);
              }}
            >
              Preview record
            </button>
          )}
          {open && (
            <DirectoryInspector
              mode="modal"
              title="Preview"
              returnFocusTo={trigger}
              fallbackFocusTo={fallback}
              onClose={() => {
                setVisible(false);
                setOpen(false);
              }}
            >
              Selected record
            </DirectoryInspector>
          )}
        </>
      );
    }
    render(<RemovalExample />);
    await userEvent.click(
      screen.getByRole("button", { name: "Preview record" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Close preview" }),
    );
    expect(screen.getByRole("button", { name: "Results" })).toHaveFocus();
  },
);

test("filtering away the selected row never steals focus from the search field", async () => {
  function FilteringExample() {
    const [query, setQuery] = useState("");
    const [open, setOpen] = useState(false);
    const trigger = useRef<HTMLButtonElement | null>(null);
    const fallback = useRef<HTMLInputElement | null>(null);
    return (
      <>
        <label>
          Find record
          <input
            ref={fallback}
            value={query}
            onChange={(e) => {
              setQuery(e.currentTarget.value);
            }}
          />
        </label>
        {!query && (
          <button
            ref={trigger}
            onClick={() => {
              setOpen(true);
            }}
          >
            Preview record
          </button>
        )}
        {open && !query && (
          <DirectoryInspector
            mode="modal"
            title="Preview"
            returnFocusTo={trigger}
            fallbackFocusTo={fallback}
            onClose={() => {
              setOpen(false);
            }}
          >
            Selected context
          </DirectoryInspector>
        )}
      </>
    );
  }
  render(<FilteringExample />);
  await userEvent.click(screen.getByRole("button", { name: "Preview record" }));
  await userEvent.type(
    screen.getByRole("textbox", { name: "Find record" }),
    "absent",
  );
  expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  expect(screen.getByRole("textbox", { name: "Find record" })).toHaveFocus();
});

test("Back restores the displayed default even after persisting the opposite mode", async () => {
  window.history.replaceState({ review: true }, "", "#/plants?q=Aloe");
  render(<Example />);
  await userEvent.click(screen.getByRole("button", { name: "List" }));
  await import("../test/history").then(({ browserBack }) => browserBack());
  expect(
    await screen.findByRole("button", { name: "Gallery", pressed: true }),
  ).toBeVisible();
  expect(window.location.hash).toBe("#/plants?q=Aloe&view=gallery");
  expect(window.history.state).toEqual({ review: true });
});

test("default side inspection permits directory interaction and does not trap Tab", async () => {
  function SideExample() {
    const [open, setOpen] = useState(false);
    const [count, setCount] = useState(0);
    const trigger = useRef<HTMLButtonElement>(null);
    return (
      <>
        <button
          ref={trigger}
          onClick={() => {
            setOpen(true);
          }}
        >
          Inspect
        </button>
        <button
          onClick={() => {
            setCount(count + 1);
          }}
        >
          Other record {count}
        </button>
        {open && (
          <DirectoryInspector
            title="Side inspection"
            onClose={() => {
              setOpen(false);
            }}
            returnFocusTo={trigger}
            fallbackFocusTo={trigger}
          >
            <a href="#/details">Details</a>
          </DirectoryInspector>
        )}
      </>
    );
  }
  render(<SideExample />);
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Inspect" }));
  const panel = screen.getByRole("complementary", { name: "Side inspection" });
  await user.tab();
  expect(within(panel).getByRole("link", { name: "Details" })).toHaveFocus();
  await user.tab();
  expect(
    screen.getByRole("button", { name: "Close preview" }),
  ).not.toHaveFocus();
  expect(panel).not.toHaveAttribute("aria-modal");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Other record 0" }));
  expect(screen.getByRole("button", { name: "Other record 1" })).toHaveFocus();
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Inspect" })).toHaveFocus();
});

test("record surfaces support keyboard Preview while Details and Edit bypass it", async () => {
  const preview = vi.fn();
  const details = vi.fn();
  const edit = vi.fn();
  render(
    <DirectoryRecords label="Records" view="list">
      <DirectoryRow>
        <DirectoryTrigger
          onClick={preview}
          description="Active · Open Quick Preview"
        >
          <strong>Record one</strong>
          <StatusBadge compactState="active">Active</StatusBadge>
        </DirectoryTrigger>
        <DirectoryRecordActions
          label="Record one"
          onDetails={details}
          onEdit={edit}
        />
      </DirectoryRow>
    </DirectoryRecords>,
  );
  const user = userEvent.setup();
  expect(
    document.querySelector('.ui-directory-record-actions [data-icon="eye"]'),
  ).toBeNull();
  const surface = screen.getByRole("button", { name: /Record one.*Active/ });
  surface.focus();
  await user.keyboard("{Enter}");
  await user.keyboard(" ");
  expect(preview).toHaveBeenCalledTimes(2);
  await user.click(screen.getByRole("button", { name: "Details Record one" }));
  await user.click(screen.getByRole("button", { name: "Edit Record one" }));
  expect(preview).toHaveBeenCalledTimes(2);
  expect(details).toHaveBeenCalledOnce();
  expect(edit).toHaveBeenCalledOnce();
  expect(
    screen.getByRole("img", { name: "Active" }).querySelector("svg"),
  ).toHaveAttribute("data-icon", "check");
});
test("binary inactive icons retain the exact accessible status and richer labels stay textual", () => {
  render(
    <>
      <StatusBadge compactState="inactive">Inactive</StatusBadge>
      <StatusBadge>Exhausted</StatusBadge>
    </>,
  );
  expect(
    screen.getByRole("img", { name: "Inactive" }).querySelector("svg"),
  ).toHaveAttribute("data-icon", "close");
  expect(screen.getByText("Exhausted")).toHaveClass("ui-badge");
});

test("directory pagination defaults to twenty and resets on filtering while All stays explicit", async () => {
  function Paginated() {
    const [narrow, setNarrow] = useState(false);
    const records = Array.from(
      { length: narrow ? 3 : 45 },
      (_, index) => `Packet ${String(index + 1)}`,
    );
    const pagination = useDirectoryPagination(records, String(narrow));
    return (
      <>
        <button
          onClick={() => {
            setNarrow(true);
          }}
        >
          Narrow records
        </button>
        <DirectoryResults
          count={records.length}
          total={50}
          pagination={pagination}
          actions={<button>Select records</button>}
        />
        <ul aria-label="Paged records">
          {pagination.visible.map((record) => (
            <li key={record}>{record}</li>
          ))}
        </ul>
      </>
    );
  }
  const user = userEvent.setup();
  render(<Paginated />);
  const list = screen.getByRole("list", { name: "Paged records" });
  expect(within(list).getAllByRole("listitem")).toHaveLength(20);
  expect(screen.getByLabelText("Directory results")).toHaveTextContent(
    "1–20 of 45 records · 50 total",
  );
  await user.click(screen.getByRole("button", { name: "Next page" }));
  expect(within(list).getByText("Packet 21")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Next page" }));
  expect(within(list).getAllByRole("listitem")).toHaveLength(5);
  expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
  await user.selectOptions(screen.getByLabelText("Records per page"), "all");
  expect(within(list).getAllByRole("listitem")).toHaveLength(45);
  await user.selectOptions(screen.getByLabelText("Records per page"), "20");
  await user.click(screen.getByRole("button", { name: "Next page" }));
  await user.click(screen.getByRole("button", { name: "Narrow records" }));
  expect(within(list).getAllByRole("listitem")).toHaveLength(3);
  expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();
  expect(screen.getByLabelText("Directory results")).toHaveTextContent(
    "1–3 of 3 records · 50 total",
  );
});
