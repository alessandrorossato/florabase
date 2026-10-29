import { ScaffoldDirectoryExample } from "../ui-pages/ScaffoldDirectoryExample/ScaffoldDirectoryExample";
import { useEffect, useRef, useState } from "react";
import { PageHeader, BotanicalName } from "../components/ReferenceUI";
import {
  DirectoryTools,
  DirectorySearch,
  DirectoryFilterSelect,
} from "../components/DirectoryTools";
import {
  DirectoryPage,
  DirectoryViewSwitcher,
  DirectoryRecords,
  DirectoryRow,
  DirectoryCard,
  DirectoryInspector,
} from "../components/DirectoryPage";
import {
  useDirectoryPresentation,
  type PresentationSurface,
} from "../components/directoryPresentation";
import { ActionButton } from "../components/Action";
import { Icon } from "../components/Icon";
import { navigationIcons } from "../components/navigationIcons";
import { ThemeControl } from "../components/ThemeControl";
import {
  Metric,
  StatusBadge,
  EmptyState,
  LoadingState,
  ErrorState,
} from "../components/WorkspaceUI";
import { TaskDialog } from "../components/TaskDialog";
import { ActivityPage } from "../components/ActivityPage";
import { useDirectoryView } from "../saved-views/useDirectoryView";
import { savedViewHash, saveDirectoryState } from "../saved-views/state";
import { useAppearance, paletteLabels } from "../appearance/theme";
import { illustrations, records, type ExampleRecord } from "./fixtures";

const nav = [
  ["Overview", ["dashboard"]],
  ["Collection", ["seeds", "sowings", "plants", "harvests", "locations"]],
  ["Activity", ["events", "history", "schedule"]],
  ["Explore", ["identities", "taxonomy", "media", "geography"]],
  ["Sourcing", ["suppliers", "orders"]],
] as const;
const labels: Record<string, string> = {
  dashboard: "Dashboard",
  seeds: "Seeds",
  sowings: "Sowings",
  plants: "Plants",
  harvests: "Harvests",
  locations: "Locations",
  events: "Journal",
  history: "History",
  schedule: "Schedule",
  identities: "Botanical identities",
  taxonomy: "Taxonomy",
  media: "Media",
  geography: "Geography",
  suppliers: "Suppliers",
  orders: "Orders",
};
const navigable = new Set([
  "dashboard",
  "seeds",
  "sowings",
  "plants",
  "identities",
  "events",
  "components",
  "credits",
]);
function readPage() {
  return window.location.hash.split("?", 2)[0].slice(2) || "dashboard";
}
function usePage() {
  const [page, setPage] = useState(readPage);
  useEffect(() => {
    const sync = () => {
      setPage(readPage());
    };
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
    };
  }, []);
  return page;
}
function ReferenceImage({
  species,
  url,
  eager = false,
}: {
  species: string;
  url: string;
  eager?: boolean;
}) {
  const [broken, setBroken] = useState(false);
  return broken ? (
    <span className="ui-directory-no-image">
      Reference illustration unavailable
    </span>
  ) : (
    <img
      src={url}
      alt={`Reference illustration of ${species}; not an assigned specimen photo`}
      onError={() => {
        setBroken(true);
      }}
      loading={eager ? "eager" : "lazy"}
      decoding="async"
    />
  );
}
function name(record: ExampleRecord) {
  return (
    <BotanicalName
      label={
        record.scientificName + (record.cultivar ? ` ‘${record.cultivar}’` : "")
      }
      scientificName={record.scientificName}
    />
  );
}

function Dashboard() {
  return (
    <section className="lab-dashboard" aria-labelledby="dashboard-title">
      <div className="lab-dashboard-header">
        <PageHeader
          title="Your botanical collection"
          titleId="dashboard-title"
          description="Current holdings, botanical imagery and planned work."
          eyebrow="Overview"
        />
        <a href="#/components" className="button-link button--secondary">
          Quick actions
        </a>
      </div>
      <div className="lab-kpis" aria-label="Current collection snapshot">
        <Metric
          label="Individual Plants"
          value={17}
          context="Active individual records"
          href="#/plants?type=plant"
        />
        <Metric
          label="Plant groups"
          value={7}
          context="Groups, not individual Plants"
          href="#/plants?type=group"
        />
        <Metric
          label="Seed lots"
          value={40}
          context="Lots, not seed quantities"
          href="#/seeds"
        />
        <Metric
          label="Sowings"
          value={12}
          context="Active propagation records"
          href="#/sowings"
        />
      </div>
      <div className="lab-dashboard-grid">
        <section aria-labelledby="overview-title">
          <div className="lab-section-heading">
            <h3 id="overview-title">Botanical overview</h3>
            <a href="#/identities">Browse identities</a>
          </div>
          <ul className="lab-photo-overview">
            {illustrations.map((photo) => (
              <li key={photo.key}>
                <a href={`#/identities?q=${encodeURIComponent(photo.species)}`}>
                  <div className="lab-overview-image">
                    <ReferenceImage
                      species={photo.species}
                      url={photo.url}
                      eager
                    />
                  </div>
                  <BotanicalName
                    label={photo.species}
                    scientificName={photo.species}
                  />
                </a>
              </li>
            ))}
          </ul>
          <p className="lab-illustration-note">
            Eight distinct licensed v5 reference illustrations · no
            specimen/cover assignments. <a href="#/credits">Attribution</a>
          </p>
        </section>
        <section aria-labelledby="next-title">
          <div className="lab-section-heading">
            <h3 id="next-title">Next work</h3>
            <a href="http://localhost:15283/prototype.html?page=schedule">
              Schedule
            </a>
          </div>
          <p className="lab-work-summary">
            <StatusBadge attention>9 overdue</StatusBadge>{" "}
            <StatusBadge>7 due today</StatusBadge>
          </p>
          {[
            [
              "2026-10-26",
              "Water basil mother plant",
              "Preview — Basil mother plant",
            ],
            ["2026-10-28", "Repot nursery aloe", "Preview — Nursery aloe"],
            [
              "2026-10-29",
              "Check seed packet storage",
              "Preview — Basil counted packet",
            ],
            [
              "2026-10-31",
              "Check basil germination",
              "Preview — Spring basil tray",
            ],
          ].map(([date, title, target]) => (
            <article className="lab-work-row" key={title}>
              <time dateTime={date}>{date}</time>
              <h4>{title}</h4>
              <p>{target}</p>
            </article>
          ))}
          <div className="lab-history-links">
            <a href="http://localhost:15283/prototype.html?page=history">
              Authoritative History
            </a>
            <a href="#/events">Journal</a>
          </div>
        </section>
      </div>
    </section>
  );
}

function DirectoryExample({ surface }: { surface: PresentationSurface }) {
  const { view, select } = useDirectoryPresentation(surface);
  // Current filters and canonical Saved View adapters are the delivered ones.
  const filters = useDirectoryView(surface);
  const [selected, setSelected] = useState<string | null>(null);
  const [checked, setChecked] = useState<string[]>([]);
  const [savedOpen, setSavedOpen] = useState(false);
  const [state, setState] = useState("ready");
  const trigger = useRef<HTMLButtonElement | null>(null);
  const fallback = useRef<HTMLDivElement | null>(null);
  const title =
    surface === "seed_lots"
      ? "Seeds"
      : surface === "sowings"
        ? "Sowings"
        : surface === "plants"
          ? "Plants"
          : "Botanical identities";
  const params = new URLSearchParams(window.location.hash.split("?", 2)[1]);
  function selectType(value: "all" | "plant" | "group") {
    const params = new URLSearchParams(window.location.hash.split("?", 2)[1]);
    params.set("type", value);
    window.location.hash = `#/plants?${params}`;
  }
  const plantType = "type" in filters.state ? filters.state.type : "all";
  const groups = surface === "plants" && plantType === "group";
  const source = records
    .filter((r) => r.state === "active")
    .filter((r) =>
      surface === "seed_lots"
        ? r.kind === "seed"
        : surface === "sowings"
          ? r.kind === "sowing"
          : surface === "plants"
            ? (r.kind === "plant" || r.kind === "group") &&
              (plantType === "all" || r.kind === plantType)
            : r.kind === "identity",
    );
  const visible = source
    .filter((r) =>
      (r.scientificName + " " + r.label + " " + (r.cultivar ?? ""))
        .toLowerCase()
        .includes(filters.state.q.toLowerCase()),
    )
    .slice(0, 10);
  const selectedRecord = visible.find((r) => r.key === selected);
  const counts =
    surface === "seed_lots"
      ? 40
      : surface === "sowings"
        ? 12
        : surface === "plants"
          ? groups
            ? 7
            : plantType === "plant"
              ? 17
              : 24
          : 37;
  const snapshot = saveDirectoryState(surface, filters.state);
  function renderRecord(r: ExampleRecord) {
    const photo = illustrations.find((p) => p.species === r.scientificName);
    const props = {
      label: `${r.scientificName} · ${r.label}`,
      name: name(r),
      href: `#/components?record=${encodeURIComponent(r.key)}`,
      selected: selected === r.key,
      checked: checked.includes(r.key),
      onCheck: (value: boolean) => {
        setChecked((c) =>
          value ? [...c, r.key] : c.filter((k) => k !== r.key),
        );
      },
      onPreview: (button: HTMLButtonElement) => {
        trigger.current = button;
        setSelected(r.key);
      },
      previewRef: selected === r.key ? trigger : undefined,
      visual: photo ? (
        <ReferenceImage species={photo.species} url={photo.url} />
      ) : undefined,
      status:
        surface === "botanical_identities" ? undefined : (
          <StatusBadge>
            {r.state[0].toUpperCase() + r.state.slice(1)}
          </StatusBadge>
        ),
      metadata:
        surface === "botanical_identities" ? (
          <p>{r.coverage ?? "Coverage in hub"}</p>
        ) : (
          <dl>
            {surface === "seed_lots" || r.kind === "group" ? (
              <div>
                <dt>
                  {r.kind === "group" ? "Group size (plants)" : "Remaining"}
                </dt>
                <dd>{r.quantity}</dd>
              </div>
            ) : null}
            <div>
              <dt>Location</dt>
              <dd>{r.location}</dd>
            </div>
            {surface === "seed_lots" ? (
              <div>
                <dt>Acquired</dt>
                <dd>{r.date}</dd>
              </div>
            ) : null}
          </dl>
        ),
    };
    return view === "list" ? (
      <DirectoryRow key={r.key} {...props} />
    ) : (
      <DirectoryCard key={r.key} {...props} />
    );
  }
  return (
    <>
      <DirectoryPage
        titleId="directory-title"
        header={
          <PageHeader
            title={title}
            titleId="directory-title"
            description={
              surface === "seed_lots"
                ? "Physical lots, remaining stock and recorded acquisition."
                : "Botanical identity, current context and collection records."
            }
            eyebrow={
              surface === "botanical_identities" ? "Explore" : "Collection"
            }
            tools={
              <DirectoryTools
                name={title}
                search={
                  <DirectorySearch
                    id="lab-search"
                    label={`Search ${title}`}
                    hideLabel
                    value={filters.state.q}
                    onChange={(q) => {
                      filters.update("q", q);
                    }}
                    placeholder="Search identity or record…"
                  />
                }
                savedViews={
                  <ActionButton
                    variant="secondary"
                    icon="saved-views"
                    onClick={() => {
                      setSavedOpen(true);
                    }}
                  >
                    Saved views
                  </ActionButton>
                }
                filters={
                  surface === "plants" ? (
                    <DirectoryFilterSelect
                      label="Record type"
                      value={
                        groups
                          ? "group"
                          : params.get("type") === "plant"
                            ? "plant"
                            : "all"
                      }
                      options={[
                        { value: "all", label: "All" },
                        { value: "plant", label: "Plants" },
                        { value: "group", label: "Plant groups" },
                      ]}
                      onChange={selectType}
                    />
                  ) : (
                    <p>
                      Existing domain filters remain page-owned. This specimen
                      preserves the current query and URL dimensions.
                    </p>
                  )
                }
                actions={
                  <ActionButton
                    icon="add"
                    onClick={() => {
                      window.location.href =
                        "http://localhost:15283/prototype.html?page=form&variant=b";
                    }}
                  >
                    New record example
                  </ActionButton>
                }
              />
            }
          />
        }
        toolbar={
          <div className="lab-directory-toolbar" ref={fallback} tabIndex={-1}>
            <p>
              <strong>{counts}</strong>{" "}
              {surface === "botanical_identities"
                ? "identities"
                : "active records"}{" "}
              · {visible.length} fixture examples
            </p>
            <DirectoryViewSwitcher value={view} onChange={select} />
            {surface === "plants" ? (
              <div className="actions">
                <ActionButton
                  variant="secondary"
                  aria-pressed={plantType === "plant"}
                  onClick={() => {
                    selectType("plant");
                  }}
                >
                  Plants
                </ActionButton>
                <ActionButton
                  variant="secondary"
                  aria-pressed={groups}
                  onClick={() => {
                    selectType("group");
                  }}
                >
                  Plant groups
                </ActionButton>
              </div>
            ) : null}
          </div>
        }
        selection={
          checked.length ? (
            <p role="status">
              {checked.length} selected · selection remains stable across
              List/Gallery
            </p>
          ) : null
        }
        feedback={
          state === "loading" ? (
            <LoadingState>Loading records…</LoadingState>
          ) : state === "error" ? (
            <ErrorState
              onRetry={() => {
                setState("ready");
              }}
            >
              Could not load records; current query is retained.
            </ErrorState>
          ) : null
        }
        content={
          state === "empty" || visible.length === 0 ? (
            <EmptyState>
              No matching records. Review search and filters.
            </EmptyState>
          ) : state === "ready" ? (
            <DirectoryRecords view={view} label={`${title} ${view}`}>
              {visible.map(renderRecord)}
            </DirectoryRecords>
          ) : null
        }
        pagination={
          <p className="lab-illustration-note">
            Fixture excerpt, not a new server page contract. Photographs are
            labelled reference illustrations, not saved primary photos or
            Identity covers.
          </p>
        }
        inspector={
          selectedRecord ? (
            <DirectoryInspector
              title={`Preview ${selectedRecord.label}`}
              onClose={() => {
                setSelected(null);
              }}
              returnFocusTo={trigger}
              fallbackFocusTo={fallback}
            >
              <h4>{name(selectedRecord)}</h4>
              <p>
                {selectedRecord.quantity} · {selectedRecord.date}
              </p>
              <p>{selectedRecord.location}</p>
              <p>
                Domain detail, edit and eligibility stay with the existing
                record page.
              </p>
            </DirectoryInspector>
          ) : null
        }
      />
      <div
        className="lab-state-controls"
        role="group"
        aria-label="Development state examples"
      >
        {["ready", "loading", "error", "empty"].map((value) => (
          <ActionButton
            key={value}
            variant="quiet"
            onClick={() => {
              setState(value);
            }}
          >
            {value}
          </ActionButton>
        ))}
      </div>
      {savedOpen && (
        <TaskDialog
          title="Saved Views compatibility exercise"
          onClose={() => {
            setSavedOpen(false);
          }}
          dismissOnBackdrop
        >
          <h3>Existing Saved Views v1</h3>
          <p>
            This local exercise uses the real canonical adapter. Presentation,
            selection and page offsets are not saved as filters. No owner data
            is persisted.
          </p>
          <pre>{JSON.stringify(snapshot, null, 2)}</pre>
          <ActionButton
            variant="secondary"
            onClick={() => {
              const hash = savedViewHash(surface, 1, { q: "Ficus" });
              if (hash) window.location.hash = hash;
              setSavedOpen(false);
            }}
          >
            Apply Ficus filter example
          </ActionButton>
          <ActionButton
            variant="secondary"
            onClick={() => {
              setSavedOpen(false);
            }}
          >
            Close
          </ActionButton>
        </TaskDialog>
      )}
    </>
  );
}

function ActivityExample() {
  return (
    <ActivityPage
      titleId="journal-title"
      header={
        <PageHeader
          title="Journal"
          titleId="journal-title"
          eyebrow="Activity"
          description="Operator-recorded occurrences; recorded timestamps remain distinct."
        />
      }
      chronology={
        <div className="lab-chronology">
          {[
            ["26 Oct 2026", "Repotting", "Preview — Basil mother plant"],
            ["13 Oct 2026", "Repotting", "Review v5 — direct plant 04"],
            ["12 Oct 2026", "Fruiting", "Review v5 — direct plant 03"],
          ].map(([date, kind, target]) => (
            <article key={target}>
              <time>{date}</time>
              <div>
                <StatusBadge>Journal</StatusBadge>
                <h3>{kind}</h3>
                <p>{target}</p>
              </div>
            </article>
          ))}
        </div>
      }
    />
  );
}
function Components() {
  return (
    <section aria-labelledby="components-title">
      <PageHeader
        title="Working component specimens"
        titleId="components-title"
        eyebrow="UI System v1"
        description="Real house components; domain integration remains bounded."
      />
      <details>
        <summary>Generated directory · keyboard/search/state example</summary>
        <ScaffoldDirectoryExample />
      </details>
      <div className="lab-specimens">
        <section>
          <h3>Page and directory compositions</h3>
          <p>
            DirectoryPage, optional inspector, List/Gallery, loading/error/empty
            states, Saved Views compatibility.
          </p>
          <a href="#/seeds">SeedLot example</a> ·{" "}
          <a href="#/plants">Plant example</a> ·{" "}
          <a href="#/events">ActivityPage example</a>
        </section>
        <section>
          <h3>Semantic destination icons</h3>
          <div className="lab-icon-specimens">
            {Object.entries(navigationIcons).map(([destination, icon]) => (
              <div key={destination}>
                <Icon name={icon} />
                <span>{labels[destination] ?? destination}</span>
              </div>
            ))}
          </div>
        </section>
        <section>
          <h3>Shared tokens and states</h3>
          <StatusBadge>Active</StatusBadge>{" "}
          <StatusBadge attention>Overdue</StatusBadge>
          <EmptyState>No matching records</EmptyState>
          <LoadingState>Loading records…</LoadingState>
          <ErrorState
            onRetry={() => {
              window.location.hash = "#/seeds";
            }}
          >
            Retain query and provide a recovery action.
          </ErrorState>
        </section>
      </div>
    </section>
  );
}
function Credits() {
  return (
    <section>
      <h2>Reference illustration attribution</h2>
      <p>
        Existing v5 synthetic Review illustrations, cropped for layout. These
        are not assigned owned-specimen photographs or identity covers.
      </p>
      {illustrations.map((p) => (
        <p key={p.key}>
          <strong>{p.species}</strong> · {p.creator} ·{" "}
          <a href={p.licenceUrl}>{p.licence}</a> ·{" "}
          <a href={p.source}>Original source</a>
        </p>
      ))}
    </section>
  );
}
export function Lab() {
  const page = usePage();
  const [more, setMore] = useState(false);
  const appearance = useAppearance();
  const navigation = (
    <>
      {nav.map(([group, items]) => (
        <div className="lab-nav-group" key={group}>
          <p>{group}</p>
          {items.map((id) => (
            <a
              key={id}
              href={
                navigable.has(id)
                  ? `#/${id}`
                  : `http://localhost:15283/prototype.html?page=${id === "sowings" ? "specialized" : id === "history" ? "history" : id === "schedule" ? "schedule" : "specialized"}`
              }
              aria-current={page === id ? "page" : undefined}
              onClick={() => {
                setMore(false);
              }}
            >
              <Icon name={navigationIcons[id]} />
              <span>{labels[id]}</span>
            </a>
          ))}
        </div>
      ))}
    </>
  );
  return (
    <div className="ui-lab-root">
      <div className="lab-review-bar">
        <a href="http://localhost:15283/">Preserved Gate A research</a>
        <a href="#/dashboard">Proposal B refined</a>
        <a href="#/components">UI laboratory</a>
        <label>
          Palette{" "}
          <select
            aria-label="Palette"
            value={appearance.palette}
            onChange={(e) => {
              appearance.setPalette(
                e.currentTarget.value as typeof appearance.palette,
              );
            }}
          >
            {Object.entries(paletteLabels).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Appearance{" "}
          <select
            aria-label="Appearance"
            value={appearance.appearance}
            onChange={(e) => {
              appearance.setAppearance(
                e.currentTarget.value as typeof appearance.appearance,
              );
            }}
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="system">System</option>
          </select>
        </label>
        <span>Development only · synthetic Review data</span>
      </div>
      <div className="lab-shell">
        <aside className="lab-sidebar" aria-label="Application sidebar">
          <a href="#/dashboard" className="lab-brand">
            <Icon name="plant" />
            Florabase
          </a>
          <nav aria-label="Primary navigation">{navigation}</nav>
          <div className="lab-utilities">
            <a href="#/components">
              <Icon name="gear" />
              Settings specimen
            </a>
            <ThemeControl />
            <button
              onClick={() => {
                setMore(true);
              }}
            >
              Account controls specimen
            </button>
          </div>
        </aside>
        <div className="lab-mobile-header">
          <a href="#/dashboard">Florabase</a>
          <ActionButton
            variant="quiet"
            icon="menu"
            onClick={() => {
              setMore(true);
            }}
          >
            Menu
          </ActionButton>
        </div>
        <main className="app-content ui-lab-content">
          {page === "dashboard" ? (
            <Dashboard />
          ) : page === "plants" ||
            page === "seeds" ||
            page === "sowings" ||
            page === "identities" ? (
            <DirectoryExample
              key={page}
              surface={
                page === "plants"
                  ? "plants"
                  : page === "seeds"
                    ? "seed_lots"
                    : page === "sowings"
                      ? "sowings"
                      : "botanical_identities"
              }
            />
          ) : page === "events" ? (
            <ActivityExample />
          ) : page === "credits" ? (
            <Credits />
          ) : (
            <Components />
          )}
        </main>
      </div>
      <nav
        className="lab-mobile-navigation"
        aria-label="Mobile primary navigation"
      >
        {(
          [
            ["dashboard", "Home"],
            ["seeds", "Seeds"],
            ["sowings", "Sowings"],
            ["plants", "Plants"],
          ] as const
        ).map(([id, label]) => (
          <a key={id} href={`#/${id}`}>
            <Icon name={navigationIcons[id]} />
            {label}
          </a>
        ))}
        <ActionButton
          icon="more"
          variant="quiet"
          onClick={() => {
            setMore(true);
          }}
        >
          More
        </ActionButton>
      </nav>
      {more && (
        <TaskDialog
          title="Navigation"
          onClose={() => {
            setMore(false);
          }}
          dismissOnBackdrop
        >
          <ActionButton
            icon="close"
            variant="secondary"
            onClick={() => {
              setMore(false);
            }}
          >
            Close navigation
          </ActionButton>
          <nav aria-label="More navigation">{navigation}</nav>
          <div className="lab-utilities">
            <a
              href="#/components"
              onClick={() => {
                setMore(false);
              }}
            >
              Settings specimen
            </a>
            <ThemeControl />
            <p>
              Sign out remains owned by the authenticated application. This
              development preview has no session.
            </p>
          </div>
        </TaskDialog>
      )}
    </div>
  );
}
