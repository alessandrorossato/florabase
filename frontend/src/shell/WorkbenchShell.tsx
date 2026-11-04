import {
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
  type MouseEvent,
  type ReactNode,
} from "react";

import { Icon } from "../components/Icon";
import { OverflowMenu } from "../components/ReferenceUI";
import { TaskDialog } from "../components/TaskDialog";
import { ThemeControl } from "../components/ThemeControl";
import { CommandPalette } from "./CommandPalette";
import { RecordSheet } from "./RecordSheet";
import {
  createActions,
  currentLink,
  destinationOfHash,
  primaryWorkspaces,
  workspaceOf,
  workspaces,
  type Section,
  type Workspace,
  type WorkspaceId,
} from "./navigation";
import { useSavedViewLinks, type SavedViewLink } from "./useSavedViewLinks";

const panelPreferenceKey = "florabase.workbench.panel-collapsed.v1";

function readCollapsed() {
  try {
    return window.localStorage.getItem(panelPreferenceKey) === "true";
  } catch {
    return false;
  }
}

function plainClick(event: MouseEvent) {
  return !(
    event.button !== 0 ||
    event.metaKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.altKey
  );
}

function isEditable(target: EventTarget | null) {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable ||
      ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
  );
}

const shortcutLabel =
  typeof navigator !== "undefined" &&
  /Mac|iPhone|iPad/.test(navigator.userAgent)
    ? "⌘K"
    : "Ctrl K";

/** The sections of one workspace, with sub-destinations, as a list of links. */
function WorkspaceLinks({
  workspace,
  section,
  hash,
  follow,
}: {
  workspace: Workspace;
  section: Section;
  hash: string;
  follow: (event: MouseEvent<HTMLAnchorElement>, href: string) => void;
}) {
  return (
    <ul className="wb-links">
      {workspace.destinations.map((item) => {
        const current = currentLink(item, section, hash);
        const href = `#/${item.section}`;
        return (
          <li key={item.section}>
            <a
              href={href}
              className="wb-link navigation-link"
              aria-current={current.section ? "page" : undefined}
              onClick={(event) => {
                follow(event, href);
              }}
            >
              <Icon name={item.icon} shell />
              <span>{item.label}</span>
            </a>
            {item.children && (
              <ul className="wb-sublinks">
                {item.children.map((child) => (
                  <li key={child.href}>
                    <a
                      href={child.href}
                      className="wb-sublink"
                      aria-current={
                        current.child === child ? "page" : undefined
                      }
                      onClick={(event) => {
                        follow(event, child.href);
                      }}
                    >
                      {child.label}
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </li>
        );
      })}
    </ul>
  );
}

/** A labelled list of plain links (Saved views, Recent) inside the panel or a sheet. */
function LinkGroup({
  label,
  items,
  follow,
  limit,
  moreLabel,
}: {
  label: string;
  items: { key: string; href: string; name: string; detail?: string }[];
  follow: (event: MouseEvent<HTMLAnchorElement>, href: string) => void;
  /** Show this many, then a disclosure for the rest (accounts with many items). */
  limit?: number;
  moreLabel?: (count: number) => string;
}) {
  const [expanded, setExpanded] = useState(false);
  const listId = useId();
  if (!items.length) return null;
  const capped = limit !== undefined && items.length > limit;
  const shown = capped && !expanded ? items.slice(0, limit) : items;
  return (
    <nav className="wb-group" aria-label={label}>
      <p className="wb-group__title" aria-hidden="true">
        {label}
      </p>
      <ul id={listId}>
        {shown.map((item) => (
          <li key={item.key}>
            <a
              href={item.href}
              onClick={(event) => {
                follow(event, item.href);
              }}
            >
              <span className="wb-group__name">{item.name}</span>
              {item.detail && (
                <span className="wb-group__detail">{item.detail}</span>
              )}
            </a>
          </li>
        ))}
      </ul>
      {capped && (
        <button
          type="button"
          className="button--quiet wb-group__more"
          aria-expanded={expanded}
          aria-controls={listId}
          onClick={() => {
            setExpanded((value) => !value);
          }}
        >
          {expanded
            ? "Show fewer"
            : (moreLabel?.(items.length) ?? `Show all ${String(items.length)}`)}
        </button>
      )}
    </nav>
  );
}

function savedItems(views: SavedViewLink[], workspace: WorkspaceId) {
  return views
    .filter((view) => workspace === "today" || view.workspace === workspace)
    .map((view) => ({
      key: view.id,
      href: view.href,
      name: view.name,
      detail: view.surface,
    }));
}

/**
 * Florabase Next Workbench shell. A rail of workspaces (a vertical tablist)
 * switches the context panel without navigating, like an activity bar; the
 * panel holds global tools, the workspace's sections and the account. Below
 * 48rem the rail becomes a header with a section strip plus a bottom bar of
 * workspaces. Routes, history and the page content are owned by App.
 */
export function WorkbenchShell({
  section,
  hash,
  signedInAs,
  signingOut,
  onSignOut,
  onNavigate,
  children,
}: {
  section: Section;
  hash: string;
  signedInAs: string;
  signingOut: boolean;
  onSignOut: () => void;
  onNavigate: (href: string) => void;
  children: ReactNode;
}) {
  const routeWorkspace = workspaceOf(section);
  // A panel choice lasts until the next navigation; then the panel shows the
  // workspace of the page that was opened.
  const [panelChoice, setPanelChoice] = useState<{
    from: string;
    id: WorkspaceId;
  } | null>(null);
  const panelId =
    panelChoice?.from === hash ? panelChoice.id : routeWorkspace.id;
  const setPanelId = (id: WorkspaceId) => {
    setPanelChoice({ from: hash, id });
  };
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const savedViews = useSavedViewLinks();
  // Recently opened section-level destinations in this session (never records,
  // never stored). Updated while rendering when the route changes.
  const [recentState, setRecentState] = useState<{
    hash: string;
    items: { label: string; href: string }[];
  }>({ hash: "", items: [] });
  if (recentState.hash !== hash) {
    const entry = destinationOfHash(hash);
    setRecentState({
      hash,
      items: entry
        ? [
            { label: entry.label, href: entry.href },
            ...recentState.items.filter((item) => item.href !== entry.href),
          ].slice(0, 6)
        : recentState.items,
    });
  }
  const currentHref = destinationOfHash(hash)?.href;
  const recent = recentState.items
    .filter((item) => item.href !== currentHref)
    .slice(0, 4)
    .map((item) => ({ key: item.href, href: item.href, name: item.label }));
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [recordOpen, setRecordOpen] = useState(false);
  const recordReturn = useRef<HTMLElement | null>(null);
  const [sheet, setSheet] = useState<WorkspaceId | "account" | null>(null);
  const searchTrigger = useRef<HTMLButtonElement>(null);
  const railSearch = useRef<HTMLButtonElement>(null);
  const mobileSearch = useRef<HTMLButtonElement>(null);
  const paletteReturn = useRef<HTMLElement | null>(null);
  const tabs = useRef<Record<string, HTMLButtonElement | null>>({});
  const panel =
    workspaces.find((item) => item.id === panelId) ?? routeWorkspace;

  useEffect(() => {
    try {
      window.localStorage.setItem(panelPreferenceKey, String(collapsed));
    } catch {
      // The panel still works when browser preference storage is unavailable.
    }
  }, [collapsed]);

  useEffect(() => {
    const open = (event: globalThis.KeyboardEvent) => {
      if (event.defaultPrevented || document.querySelector("dialog[open]"))
        return;
      const command =
        (event.metaKey || event.ctrlKey) &&
        !event.altKey &&
        event.key.toLowerCase() === "k";
      const slash =
        event.key === "/" &&
        !event.metaKey &&
        !event.ctrlKey &&
        !event.altKey &&
        !isEditable(event.target);
      if (!command && !slash) return;
      event.preventDefault();
      paletteReturn.current =
        document.activeElement instanceof HTMLElement
          ? document.activeElement
          : null;
      setPaletteOpen(true);
    };
    document.addEventListener("keydown", open);
    return () => {
      document.removeEventListener("keydown", open);
    };
  }, []);

  function openPalette(trigger: HTMLElement | null) {
    paletteReturn.current = trigger;
    setPaletteOpen(true);
  }

  function openRecord(trigger: HTMLElement) {
    recordReturn.current = trigger;
    setSheet(null);
    setRecordOpen(true);
  }

  function follow(event: MouseEvent<HTMLAnchorElement>, href: string) {
    if (!plainClick(event)) return;
    event.preventDefault();
    setSheet(null);
    onNavigate(href);
  }

  function selectTab(id: WorkspaceId) {
    if (id === panelId && !collapsed) {
      setCollapsed(true);
      return;
    }
    setPanelId(id);
    setCollapsed(false);
  }

  function tabKeys(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const keys: Record<string, number> = {
      ArrowDown: index + 1,
      ArrowUp: index - 1,
      Home: 0,
      End: workspaces.length - 1,
    };
    if (!(event.key in keys)) return;
    event.preventDefault();
    const next =
      workspaces[(keys[event.key] + workspaces.length) % workspaces.length];
    setPanelId(next.id);
    setCollapsed(false);
    tabs.current[next.id]?.focus();
  }

  const sheetWorkspace =
    sheet && sheet !== "account"
      ? workspaces.find((item) => item.id === sheet)
      : undefined;
  const settingsWorkspace = workspaces.find((item) => item.id === "settings");

  return (
    <div
      className={`application-shell wb-shell${collapsed ? " wb-shell--collapsed" : ""}`}
    >
      <aside className="wb-sidebar" aria-label="Application sidebar">
        <div className="wb-rail">
          <h1 className="wb-brand" id="page-title">
            <a
              href="#/dashboard"
              onClick={(event) => {
                follow(event, "#/dashboard");
              }}
            >
              <span className="wb-brand__mark" aria-hidden="true">
                F
              </span>
              <span className="wb-brand__name">Florabase</span>
            </a>
          </h1>
          <button
            type="button"
            ref={railSearch}
            className="wb-rail__search"
            aria-label="Search and commands"
            onClick={() => {
              openPalette(railSearch.current);
            }}
          >
            <Icon name="search" shell />
          </button>
          <button
            type="button"
            className="wb-rail__record"
            aria-haspopup="dialog"
            onClick={(event) => {
              openRecord(event.currentTarget);
            }}
          >
            <Icon name="journal" shell />
            Record
          </button>
          <div
            className="wb-rail__tabs"
            role="tablist"
            aria-label="Workspaces"
            aria-orientation="vertical"
          >
            {workspaces.map((workspace, index) => {
              const selected = workspace.id === panel.id && !collapsed;
              const here = workspace.id === routeWorkspace.id;
              return (
                <button
                  key={workspace.id}
                  ref={(element) => {
                    tabs.current[workspace.id] = element;
                  }}
                  type="button"
                  role="tab"
                  id={`wb-tab-${workspace.id}`}
                  aria-selected={selected}
                  aria-controls="wb-panel"
                  tabIndex={workspace.id === panel.id ? 0 : -1}
                  className={`wb-tab${here ? " wb-tab--here" : ""}${workspace.id === "settings" ? " wb-tab--utility" : ""}`}
                  onClick={() => {
                    selectTab(workspace.id);
                  }}
                  onKeyDown={(event) => {
                    tabKeys(event, index);
                  }}
                >
                  <Icon name={workspace.icon} shell />
                  <span className="wb-tab__label">{workspace.label}</span>
                  {here && (
                    <span className="wb-visually-hidden">
                      , current location
                    </span>
                  )}
                </button>
              );
            })}
          </div>
          <div className="wb-mobilebar">
            <button
              type="button"
              ref={mobileSearch}
              className="wb-icon-button"
              aria-label="Search and commands"
              onClick={() => {
                openPalette(mobileSearch.current);
              }}
            >
              <Icon name="search" shell />
            </button>
            <button
              type="button"
              className="wb-icon-button"
              aria-label="Account and settings"
              aria-haspopup="dialog"
              onClick={() => {
                setSheet("account");
              }}
            >
              <Icon name="settings" shell />
            </button>
          </div>
        </div>

        <div
          className="wb-panel"
          id="wb-panel"
          role="tabpanel"
          aria-labelledby={`wb-tab-${panel.id}`}
        >
          <div className="wb-panel__tools">
            <button
              type="button"
              ref={searchTrigger}
              className="wb-search-trigger"
              aria-keyshortcuts="Control+K Meta+K /"
              onClick={() => {
                openPalette(searchTrigger.current);
              }}
            >
              <Icon name="search" />
              <span>Search</span>
              <kbd aria-hidden="true">{shortcutLabel}</kbd>
            </button>
            <OverflowMenu
              label="+ New"
              ariaLabel="New record"
              popoverClassName="wb-create-popover"
              triggerContent={<Icon name="add" />}
            >
              <nav className="wb-create" aria-label="Create">
                {createActions.map(([label, href, icon]) => (
                  <a
                    key={href}
                    href={href}
                    onClick={(event) => {
                      follow(event, href);
                    }}
                  >
                    <Icon name={icon} />
                    {label}
                  </a>
                ))}
              </nav>
            </OverflowMenu>
          </div>
          <header className="wb-panel__header">
            <p className="wb-panel__eyebrow">
              {panel.id === routeWorkspace.id ? "You are in" : "Workspace"}
            </p>
            <p className="wb-panel__title">{panel.label}</p>
            <p className="wb-panel__summary">{panel.summary}</p>
          </header>
          <nav className="wb-sections" aria-label="Primary navigation">
            <WorkspaceLinks
              workspace={panel}
              section={section}
              hash={hash}
              follow={follow}
            />
          </nav>
          <LinkGroup
            label="Saved views"
            items={savedItems(savedViews, panel.id)}
            follow={follow}
            limit={5}
            moreLabel={(count) => `Show all ${String(count)} saved views`}
          />
          <LinkGroup label="Recent" items={recent} follow={follow} />
          <footer className="wb-panel__footer">
            <p className="wb-account">{`Signed in as ${signedInAs}`}</p>
            <div className="wb-panel__footer-actions">
              <ThemeControl />
              <button
                type="button"
                className="button--quiet wb-collapse"
                onClick={() => {
                  setCollapsed(true);
                  window.setTimeout(() => tabs.current[panel.id]?.focus(), 0);
                }}
              >
                Hide panel
              </button>
            </div>
            <button
              type="button"
              className="button--secondary wb-sign-out"
              disabled={signingOut}
              onClick={onSignOut}
            >
              {signingOut ? "Signing out…" : "Sign out"}
            </button>
          </footer>
        </div>
      </aside>

      {children}

      <nav aria-label="Mobile primary navigation" className="wb-bottombar">
        <button
          type="button"
          className="wb-bottombar__record"
          aria-haspopup="dialog"
          onClick={(event) => {
            openRecord(event.currentTarget);
          }}
        >
          <Icon name="journal" shell />
          Record
        </button>
        {primaryWorkspaces.map((workspace) => (
          <button
            key={workspace.id}
            type="button"
            aria-haspopup="dialog"
            aria-current={
              workspace.id === routeWorkspace.id ? "true" : undefined
            }
            onClick={() => {
              setSheet(workspace.id);
            }}
          >
            <Icon name={workspace.icon} shell />
            {workspace.label}
          </button>
        ))}
      </nav>

      {sheetWorkspace && (
        <TaskDialog
          title={sheetWorkspace.label}
          className="wb-sheet"
          onClose={() => {
            setSheet(null);
          }}
          dismissOnBackdrop
        >
          <div className="wb-sheet__header">
            <h2>{sheetWorkspace.label}</h2>
            <button
              type="button"
              className="button--secondary"
              onClick={() => {
                setSheet(null);
              }}
            >
              Close
            </button>
          </div>
          <p className="wb-panel__summary">{sheetWorkspace.summary}</p>
          <nav aria-label={`${sheetWorkspace.label} sections`}>
            <WorkspaceLinks
              workspace={sheetWorkspace}
              section={section}
              hash={hash}
              follow={follow}
            />
          </nav>
          <LinkGroup
            label="Saved views"
            items={savedItems(savedViews, sheetWorkspace.id)}
            follow={follow}
            limit={5}
            moreLabel={(count) => `Show all ${String(count)} saved views`}
          />
        </TaskDialog>
      )}

      {sheet === "account" && settingsWorkspace && (
        <TaskDialog
          title="Account and settings"
          className="wb-sheet"
          onClose={() => {
            setSheet(null);
          }}
          dismissOnBackdrop
        >
          <div className="wb-sheet__header">
            <h2>Account and settings</h2>
            <button
              type="button"
              className="button--secondary"
              onClick={() => {
                setSheet(null);
              }}
            >
              Close
            </button>
          </div>
          <p className="wb-account">{`Signed in as ${signedInAs}`}</p>
          <nav aria-label="Settings sections">
            <WorkspaceLinks
              workspace={settingsWorkspace}
              section={section}
              hash={hash}
              follow={follow}
            />
          </nav>
          <div className="wb-panel__footer-actions">
            <ThemeControl />
            <button
              type="button"
              className="button--secondary wb-sign-out"
              disabled={signingOut}
              onClick={onSignOut}
            >
              {signingOut ? "Signing out…" : "Sign out"}
            </button>
          </div>
        </TaskDialog>
      )}

      {recordOpen && (
        <RecordSheet
          hash={hash}
          follow={follow}
          onNavigate={onNavigate}
          returnFocusTo={recordReturn}
          onClose={() => {
            setRecordOpen(false);
          }}
        />
      )}

      {paletteOpen && (
        <CommandPalette
          hash={hash}
          onClose={() => {
            setPaletteOpen(false);
          }}
          onNavigate={onNavigate}
          returnFocusTo={paletteReturn}
          savedViews={savedViews}
        />
      )}
    </div>
  );
}
