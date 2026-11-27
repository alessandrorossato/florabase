import { Fragment } from "react";
import { ActionButton } from "./Action";
import type {
  CSSProperties,
  HTMLAttributes,
  MouseEventHandler,
  ReactNode,
  RefObject,
} from "react";
import { Breadcrumbs } from "./Breadcrumbs";
import { PageHeader } from "./ReferenceUI";
import { LifecycleStatus } from "./WorkspaceUI";
import "./detail-page.css";
import "./specimen.css";

/** One fact on a record's specimen label. Unknown facts say so in words, never "—" or 0. */
export interface SpecimenRow {
  label: string;
  value: ReactNode;
  unknown?: boolean;
  /** Use the monospace data face (dates, quantities, codes). Inferred for dates/numbers. */
  mono?: boolean;
  /** Accepted so DetailSummary metrics move into the label unchanged; not used here. */
  wide?: boolean;
  emphasis?: boolean;
}

// Values the domains already use for missing facts; the label sets them as "unknown".
const unknownWords = new Set([
  "Not recorded",
  "Unknown",
  "Quantity unknown",
  "Unknown quantity",
  "Not applicable",
  "None recorded",
  "Germination not recorded",
  "Not linked",
  "No observations",
  "Location not recorded",
]);

const DATA_VALUE_PATTERN =
  /^(?:~|About\s+)?\d+(?:[.,–-]\d+)*(?:\s|$)|^\d{4}(?:-\d{2}(?:-\d{2})?)?$/;

function isDataValue(value: ReactNode): boolean {
  if (typeof value === "number") return true;
  if (typeof value !== "string") return false;
  const trimmed = value.trim();
  return trimmed.length > 0 && DATA_VALUE_PATTERN.test(trimmed);
}

/**
 * The record's ruled fact block (the herbarium label of the Specimen Sheet). It replaces the
 * header facts and the At a glance band, so each fact is stated once.
 */
export function SpecimenLabel({
  kind,
  rows,
  note,
  name,
}: {
  kind: string;
  rows: SpecimenRow[];
  /** The fact list's accessible name (as DetailSummary's label was), e.g. "Current inventory". */
  name?: string;
  /** A sentence the facts need to be read correctly (for example how a price applies). */
  note?: ReactNode;
}) {
  const shown = rows.filter(
    ({ value }) => value !== null && value !== undefined && value !== false,
  );
  if (!shown.length) return null;
  return (
    <section className="specimen-label" aria-label={`${kind} facts`}>
      <p className="specimen-label__title" aria-hidden="true">
        Florabase · {kind}
      </p>
      <dl aria-label={name}>
        {shown.map((row) => {
          const isUnknown =
            row.unknown ??
            (typeof row.value === "string" &&
              unknownWords.has(row.value.trim()));
          const isData = !isUnknown && (row.mono ?? isDataValue(row.value));
          return (
            <div key={row.label}>
              <dt>{row.label}</dt>
              <dd
                className={
                  isUnknown
                    ? "specimen-label__unknown"
                    : isData
                      ? "specimen-label__data"
                      : undefined
                }
              >
                {row.value}
              </dd>
            </div>
          );
        })}
      </dl>
      {note && <div className="specimen-label__note">{note}</div>}
    </section>
  );
}

/** The record's plate: its own photo, else its identity reference, else a quiet fallback. */
/**
 * The record's image plate. With no image (the RecordVisual inside is `data-empty`), the
 * plate shrinks to a short placeholder and offers `addPhoto`, which opens the Photos tab.
 */
export function SpecimenPlate({
  children,
  addPhoto,
}: {
  children: ReactNode;
  addPhoto?: { href: string; onClick?: MouseEventHandler<HTMLAnchorElement> };
}) {
  return (
    <figure className="specimen-plate">
      {children}
      {addPhoto && (
        <a
          className="button-link button--secondary specimen-plate__add"
          href={addPhoto.href}
          onClick={addPhoto.onClick}
        >
          Add photo
        </a>
      )}
    </figure>
  );
}

export interface KeyFact {
  label: string;
  value: ReactNode;
}

/**
 * The record's key facts under the action bar: three or four big numbers or dates, the
 * same component for every Collection record type.
 */
export function KeyFacts({ facts }: { facts: KeyFact[] }) {
  if (!facts.length) return null;
  return (
    <dl className="detail-key-facts" aria-label="Key facts">
      {facts.map((fact) => {
        const unknown =
          typeof fact.value === "string" &&
          (unknownWords.has(fact.value) || /not recorded$/i.test(fact.value));
        return (
          <div key={fact.label}>
            <dd className={unknown ? "detail-key-facts__unknown" : undefined}>
              {fact.value}
            </dd>
            <dt>{fact.label}</dt>
          </div>
        );
      })}
    </dl>
  );
}

/** Shared record presentation; routes, tabs, permissions and content remain domain-owned. */
export function DetailPage({
  as: Element = "article",
  className = "",
  ...props
}: HTMLAttributes<HTMLElement> & { as?: "article" | "section" | "div" }) {
  return (
    <Element
      {...props}
      className={`collection-detail ui-detail-page ${className}`}
    />
  );
}

export interface TabItem<TabId extends string = string> {
  id: TabId;
  label: string;
  /** Shown as a badge so the count is visible before opening the tab; null while loading. */
  count?: number | null;
}

export function WorkspaceIntro({
  eyebrow,
  title,
  titleId,
  description,
  actions,
  tools,
  contextOnly = false,
  directory = false,
}: {
  eyebrow: string;
  title: string;
  titleId: string;
  description: string;
  actions?: ReactNode;
  tools?: ReactNode;
  contextOnly?: boolean;
  directory?: boolean;
}) {
  if (contextOnly)
    return (
      <>
        <h2 className="sr-only" id={titleId}>
          {title}
        </h2>
        {Boolean(actions) && (
          <div className="workspace-context-actions">{actions}</div>
        )}
      </>
    );
  return (
    <PageHeader
      eyebrow={eyebrow}
      title={title}
      titleId={titleId}
      description={description}
      tools={tools}
      actions={actions}
      directory={directory}
    />
  );
}

export { Breadcrumbs };

/**
 * Shared record header. Action bar contract (UI-POLISH-006):
 *   - `primaryActions`: at most one primary action (rendered first)
 *   - `secondaryActions`: at most two secondary actions
 *   - `onEdit`: Edit button
 *   - `overflow`: `⋯` OverflowMenu holding any additional actions
 */
export function DetailHeader({
  eyebrow,
  title,
  secondary,
  status,
  primaryActions,
  secondaryActions,
  onEdit,
  editLabel = "Edit",
  overflow,
  keyFacts,
  headingRef,
  visual,
  headingLevel = 3,
  titleId,
  lineage,
  plate,
  label,
}: {
  eyebrow: string;
  title: ReactNode;
  secondary?: ReactNode;
  status?: ReactNode;
  primaryActions?: ReactNode;
  secondaryActions?: ReactNode;
  onEdit?: MouseEventHandler<HTMLButtonElement>;
  editLabel?: string;
  overflow?: ReactNode;
  /** Key facts strip under the action bar (UI-POLISH-006 B2). */
  keyFacts?: KeyFact[];
  headingRef?: RefObject<HTMLHeadingElement | null>;
  visual?: ReactNode;
  headingLevel?: 2 | 3;
  titleId?: string;
  /** A recorded-lineage strip spanning the header (records with recorded sources). */
  lineage?: ReactNode;
  /** Specimen Sheet: a large plate (SpecimenPlate) beside the record. */
  plate?: ReactNode;
  /** Specimen Sheet: the ruled fact block under the plate (SpecimenLabel). */
  label?: ReactNode;
}) {
  const Heading = headingLevel === 2 ? "h2" : "h3";
  const specimen = Boolean(plate) || Boolean(label);
  const main = (
    <>
      <div className="detail-identity">
        {!specimen && visual && <div className="detail-visual">{visual}</div>}
        <div className="detail-identity__text">
          <p className="eyebrow">{eyebrow}</p>
          <Heading
            id={titleId}
            ref={headingRef}
            tabIndex={headingRef ? -1 : undefined}
          >
            {title}
          </Heading>
          {secondary && <div className="detail-secondary">{secondary}</div>}
          {status && <div className="detail-status">{status}</div>}
        </div>
      </div>
      {(primaryActions ?? secondaryActions ?? onEdit ?? overflow) && (
        <div
          className="actions detail-actions"
          role="group"
          aria-label="Record actions"
        >
          {primaryActions}
          {secondaryActions}
          {onEdit && (
            <ActionButton
              icon="edit"
              className="button--secondary"
              type="button"
              onClick={onEdit}
            >
              {editLabel}
            </ActionButton>
          )}
          {overflow}
        </div>
      )}
      {keyFacts && <KeyFacts facts={keyFacts} />}
      {lineage && <div className="detail-lineage">{lineage}</div>}
    </>
  );
  if (!specimen) return <header className="detail-header">{main}</header>;
  return (
    <header className="detail-header detail-header--specimen">
      <div className="specimen-aside">
        {plate}
        {label}
      </div>
      <div className="specimen-main">{main}</div>
    </header>
  );
}

/** Holds a record page's structure while it loads; it never shows record data. */
export function DetailLoading({
  eyebrow,
  label,
  parents,
  className = "",
  visual = true,
}: {
  eyebrow: string;
  label: string;
  parents: { label: string; href: string }[];
  className?: string;
  visual?: boolean;
}) {
  return (
    <DetailPage as="div" className={`detail-loading ${className}`}>
      <Breadcrumbs items={[...parents, { label: "Loading" }]} />
      <div aria-hidden="true" className="detail-header">
        <div className="detail-identity">
          {visual && (
            <div className="detail-visual">
              <span className="detail-loading__visual" />
            </div>
          )}
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <span className="detail-loading__title" />
          </div>
        </div>
      </div>
      <p role="status">{label}</p>
    </DetailPage>
  );
}

export interface DetailMetric {
  label: string;
  value: ReactNode;
  /** Takes two columns, for paths and other long values. */
  wide?: boolean;
  /** The record's primary figure. */
  emphasis?: boolean;
}

/** One summary band for every record; each domain supplies its own metrics. */
export function DetailSummary({
  id,
  label,
  metrics,
  title = "At a glance",
  titleRef,
  note,
}: {
  id: string;
  label: string;
  metrics: DetailMetric[];
  title?: string;
  titleRef?: RefObject<HTMLHeadingElement | null>;
  note?: ReactNode;
}) {
  const shown = metrics.filter(
    ({ value }) =>
      value !== null && value !== undefined && value !== false && value !== "",
  );
  if (shown.length === 0) return null;
  const columns = shown.reduce((sum, { wide }) => sum + (wide ? 2 : 1), 0);
  return (
    <section className="detail-summary" aria-labelledby={id}>
      <h4 id={id} ref={titleRef} tabIndex={titleRef ? -1 : undefined}>
        {title}
      </h4>
      <dl
        aria-label={label}
        style={{ "--detail-summary-columns": columns } as CSSProperties}
      >
        {shown.map((metric) => (
          <div
            key={metric.label}
            className={[
              metric.wide && "detail-summary__metric--wide",
              metric.emphasis && "detail-summary__metric--emphasis",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            <dt>{metric.label}</dt>
            <dd>{metric.value}</dd>
          </div>
        ))}
      </dl>
      {note}
    </section>
  );
}

export function DetailContext({
  items,
}: {
  items: { label: string; value: ReactNode }[];
}) {
  return (
    <dl className="detail-context">
      {items.map(({ label, value }) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function DetailTabs<TabId extends string>({
  tabs,
  selected,
  onSelect,
  label = "Record sections",
}: {
  label?: string;
  tabs: TabItem<TabId>[];
  selected: TabId;
  onSelect: (id: TabId) => void;
}) {
  return (
    <div aria-label={label} className="detail-tabs" role="tablist">
      {tabs.map((tab) => (
        <button
          aria-selected={selected === tab.id}
          aria-controls={`panel-${tab.id}`}
          className="detail-tab"
          id={`tab-${tab.id}`}
          key={tab.id}
          role="tab"
          tabIndex={selected === tab.id ? 0 : -1}
          type="button"
          onClick={() => {
            onSelect(tab.id);
          }}
          onKeyDown={(event) => {
            if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key))
              return;
            event.preventDefault();
            const index = tabs.findIndex(({ id }) => id === selected);
            const next =
              event.key === "Home"
                ? 0
                : event.key === "End"
                  ? tabs.length - 1
                  : (index +
                      (event.key === "ArrowRight" ? 1 : -1) +
                      tabs.length) %
                    tabs.length;
            onSelect(tabs[next].id);
            const target = event.currentTarget.parentElement?.children[next];
            if (target instanceof HTMLElement)
              window.setTimeout(() => {
                target.focus();
              });
          }}
        >
          {tab.label}
          {typeof tab.count === "number" && (
            // The tab keeps its plain name for assistive technology; the panel states the count.
            <span className="detail-tab__count" aria-hidden="true">
              {tab.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

export function CollectionCard({
  title,
  eyebrow,
  href,
  children,
}: {
  title: string;
  eyebrow?: string;
  href?: string;
  children?: ReactNode;
}) {
  return (
    <article className="collection-card">
      {eyebrow && <p className="card-type">{eyebrow}</p>}
      <h3>{href ? <a href={href}>{title}</a> : title}</h3>
      {children}
    </article>
  );
}

/**
 * Shared two-column Overview layout for every Collection record: left column holds the
 * record type's facts sections, right column holds RecordAlmanac, collapsing to one column
 * below the container breakpoint.
 */
export function RecordOverview({
  facts,
  almanac,
  className = "",
}: {
  facts: ReactNode;
  almanac: ReactNode;
  className?: string;
}) {
  return (
    <div className={`record-overview ${className}`.trim()}>
      <div className="record-overview__facts">{facts}</div>
      <div className="record-overview__almanac">{almanac}</div>
    </div>
  );
}

export interface DescendantLinkItem {
  label: string;
  href?: string;
  onClick?: MouseEventHandler<HTMLAnchorElement>;
}

/**
 * One-line Descendants summary for record Overview tabs: compact counts with links to the
 * type's work tab and to the Lineage tab. Full descendant trees live in the work tab and
 * in LineagePanel.
 */
export function RecordDescendants({
  title = "Descendants",
  headingId,
  items,
  lineageHref,
  onOpenLineage,
  loading = false,
  error = false,
}: {
  title?: string;
  headingId?: string;
  items: DescendantLinkItem[];
  lineageHref?: string;
  onOpenLineage?: MouseEventHandler<HTMLAnchorElement>;
  loading?: boolean;
  error?: boolean;
}) {
  return (
    <section
      className="record-descendants"
      aria-labelledby={headingId}
      aria-label={headingId ? undefined : title}
    >
      <h4 id={headingId}>{title}</h4>
      {loading ? (
        <p className="record-descendants__line" role="status">
          Loading descendants…
        </p>
      ) : error ? (
        <p className="record-descendants__line">
          Could not load descendants summary.
        </p>
      ) : (
        <p className="record-descendants__line">
          {items.map((item, index) => (
            <Fragment key={`${item.label}:${String(index)}`}>
              {index > 0 && (
                <span className="record-descendants__sep" aria-hidden="true">
                  {" · "}
                </span>
              )}
              {item.href ? (
                <a href={item.href} onClick={item.onClick}>
                  {item.label}
                </a>
              ) : (
                <span>{item.label}</span>
              )}
            </Fragment>
          ))}
          {lineageHref && (
            <>
              {items.length > 0 && (
                <span className="record-descendants__sep" aria-hidden="true">
                  {" · "}
                </span>
              )}
              <a href={lineageHref} onClick={onOpenLineage}>
                View lineage
              </a>
            </>
          )}
        </p>
      )}
    </section>
  );
}

/**
 * Shared child-record card matching LineagePanel's card grammar: compact kind eyebrow,
 * strong title link, LifecycleStatus chip and concise metadata lines.
 */
export function RecordChildCard({
  kind,
  title,
  href,
  status,
  statusLabel,
  meta,
  actions,
}: {
  kind: string;
  title: string;
  href: string;
  status: string;
  statusLabel?: string;
  meta?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <article className="record-child-card">
      <div className="record-child-card__header">
        <span className="record-child-card__kind">{kind}</span>
        <LifecycleStatus state={status}>{statusLabel}</LifecycleStatus>
      </div>
      <a className="record-child-card__title" href={href}>
        {title}
      </a>
      {meta && <div className="record-child-card__meta">{meta}</div>}
      {actions && <div className="record-child-card__actions">{actions}</div>}
    </article>
  );
}
