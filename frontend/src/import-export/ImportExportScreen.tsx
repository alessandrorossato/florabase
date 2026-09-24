import { useState } from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import {
  applyImport,
  getFieldGuide,
  previewImport,
  recordTypes,
  type ImportPreview,
  type ImportResult,
  type FieldGuideItem,
  type PreviewOutcome,
  type RecordType,
} from "./api";

const outcomeLabels: Record<PreviewOutcome, string> = {
  ready: "Ready to create",
  already_exists: "Already exists",
  needs_choice: "Choose an action",
  invalid: "Invalid",
  unresolved_reference: "Unresolved reference",
  ambiguous_reference: "Ambiguous reference",
  conflict: "Conflict",
};

const actionLabels = {
  use_existing: "Use existing",
  update_existing: "Update existing",
  create_separate: "Create separate",
  choose_reference: "Choose this record",
} as const;

const controlledFields = new Set([
  "kind",
  "source_kind",
  "direct_origin_kind",
  "quantity_kind",
  "quantity_unit",
  "quantity_certainty",
  "lifecycle",
]);

function acceptedValue(field: FieldGuideItem): string {
  return controlledFields.has(field.field)
    ? field.accepted.split(", ").join(" · ")
    : field.accepted;
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const body = error.body;
    if (body && typeof body === "object" && "detail" in body) {
      const detail = body.detail;
      if (typeof detail === "string") return detail;
    }
    return `Request failed (${String(error.status)}). Check the CSV and try again.`;
  }
  return "Could not reach Florabase. Try again.";
}

export function ImportExportScreen() {
  const auth = useAuth();
  const [kind, setKind] = useState<RecordType>("botanical-identities");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState<"preview" | "apply" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "ready" | "attention">("all");
  const [choices, setChoices] = useState<
    Record<string, Record<string, string> | undefined>
  >({});
  const [guideOpen, setGuideOpen] = useState(false);
  const [guide, setGuide] = useState<FieldGuideItem[] | null>(null);
  const [guideBusy, setGuideBusy] = useState(false);
  const [guideError, setGuideError] = useState<string | null>(null);
  const owner =
    auth.state.status === "authenticated" && auth.state.session.owner;
  const selectedType =
    recordTypes.find((type) => type.id === kind)?.label ?? "records";
  const activeStep = result ? 4 : preview ? 3 : file ? 2 : 1;

  function reset() {
    setPreview(null);
    setResult(null);
    setError(null);
    setFilter("all");
    setChoices({});
  }

  async function toggleGuide() {
    if (guideOpen) {
      setGuideOpen(false);
      return;
    }
    setGuideOpen(true);
    if (guide) return;
    setGuideBusy(true);
    setGuideError(null);
    try {
      setGuide((await getFieldGuide(kind)).fields);
    } catch (caught: unknown) {
      setGuideError(errorMessage(caught));
    } finally {
      setGuideBusy(false);
    }
  }

  async function validate() {
    if (!file) return;
    setBusy("preview");
    setError(null);
    setResult(null);
    setFilter("all");
    setChoices({});
    try {
      const response = await previewImport(kind, file);
      setPreview(response);
    } catch (caught: unknown) {
      setPreview(null);
      setError(errorMessage(caught));
    } finally {
      setBusy(null);
    }
  }

  async function confirm() {
    if (!file || !preview || auth.state.status !== "authenticated") return;
    setBusy("apply");
    setError(null);
    try {
      const response = await applyImport(
        kind,
        file,
        preview.confirmation_token,
        auth.state.csrfToken,
        choices,
      );
      setResult(response);
      setPreview(null);
    } catch (caught: unknown) {
      setPreview(null);
      setError(
        `${errorMessage(caught)} Validate the file again before importing.`,
      );
    } finally {
      setBusy(null);
    }
  }

  const visibleRows = preview?.rows.filter((row) => {
    if (filter === "ready")
      return row.outcome === "ready" || row.outcome === "already_exists";
    if (filter === "attention")
      return row.outcome !== "ready" && row.outcome !== "already_exists";
    return true;
  });
  const canApply =
    preview?.rows.every(
      (row) =>
        !row.hard_blocker &&
        [...new Set(row.options.map((option) => option.key))].every((key) =>
          Boolean(choices[String(row.row_number)]?.[key]),
        ),
    ) ?? false;

  return (
    <div className="import-workspace" aria-labelledby="import-title">
      <header className="page-header">
        <div>
          <p className="eyebrow">Collection tools</p>
          <h2 id="import-title">Import & export</h2>
          <p>Bring collection records in with a reviewed CSV.</p>
        </div>
      </header>
      <div className="import-workspace__grid">
        <section
          className="card import-workspace__primary"
          aria-labelledby="import-heading"
        >
          <h3 id="import-heading">Import CSV</h3>
          <ol className="import-progress" aria-label="Import steps">
            {(["Template", "Upload", "Preview", "Import"] as const).map(
              (step, index) => (
                <li
                  key={step}
                  aria-current={activeStep === index + 1 ? "step" : undefined}
                  className={activeStep > index + 1 ? "is-complete" : undefined}
                >
                  <span className="import-progress__number">{index + 1}</span>
                  {step}
                </li>
              ),
            )}
          </ol>
          <div className="field">
            <label htmlFor="import-record-type">Record type</label>
            <select
              id="import-record-type"
              value={kind}
              disabled={busy !== null}
              onChange={(event) => {
                setKind(event.currentTarget.value as RecordType);
                setFile(null);
                setGuide(null);
                setGuideOpen(false);
                setGuideError(null);
                reset();
              }}
            >
              {recordTypes.map((type) => (
                <option key={type.id} value={type.id}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>
          <div
            className="import-format-actions"
            role="group"
            aria-label="CSV preparation"
          >
            <a
              className="import-resource"
              href={`/api/v1/imports/templates/${kind}.csv`}
              download
            >
              Blank template
            </a>
            <a
              className="import-resource"
              href={`/api/v1/imports/examples/${kind}.csv`}
              download
            >
              Example CSV
            </a>
            <button
              type="button"
              className="import-resource"
              aria-expanded={guideOpen}
              aria-controls="import-field-guide"
              onClick={() => void toggleGuide()}
            >
              {guideOpen ? "Hide guide" : "Field guide"}
            </button>
          </div>
          <div className="field">
            <label htmlFor="import-file">CSV file</label>
            <input
              id="import-file"
              key={kind}
              type="file"
              accept=".csv,text/csv"
              aria-describedby="import-file-hint"
              disabled={busy !== null || !owner}
              onChange={(event) => {
                setFile(event.currentTarget.files?.[0] ?? null);
                reset();
              }}
            />
            <small id="import-file-hint" className="import-field-hint">
              UTF-8 · up to 2 MiB and 2,000 rows
            </small>
          </div>
          {!owner && <p>Only the collection owner can import records.</p>}
          <div className="actions">
            <button
              type="button"
              disabled={!file || busy !== null || !owner}
              onClick={() => void validate()}
            >
              {busy === "preview" ? "Validating…" : "Validate and preview"}
            </button>
          </div>
          {error && (
            <p className="notice notice--error" role="alert">
              {error}
            </p>
          )}
          {result && (
            <div className="notice" role="status">
              Created {result.created}{" "}
              {result.created === 1 ? "record" : "records"}. Updated{" "}
              {result.updated}. Used existing {result.already_exists}.
            </div>
          )}
        </section>
        <aside
          className="import-workspace__secondary"
          aria-labelledby="export-heading"
        >
          <h3 id="export-heading">Export CSV</h3>
          <p className="import-workspace__selected">{selectedType}</p>
          <a
            className="button-link button--secondary"
            href={`/api/v1/exports/${kind}.csv`}
            aria-label={`Download ${selectedType} CSV`}
            download
          >
            Download CSV
          </a>
          <p>For spreadsheets, not backup or full collection transfer.</p>
          <div className="import-order">
            <strong>Recommended import order</strong>
            <p>
              Identities → Suppliers → Locations → Seed lots → Plants → Plant
              groups
            </p>
          </div>
        </aside>
      </div>
      <section
        id="import-field-guide"
        className="import-field-guide"
        aria-labelledby="import-guide-heading"
        hidden={!guideOpen}
      >
        <div className="import-field-guide__heading">
          <div>
            <p className="eyebrow">CSV reference</p>
            <h3 id="import-guide-heading">Field guide · {selectedType}</h3>
          </div>
          <p>
            Exact names and paths resolve in Preview. The example CSV shows a
            valid sequence; referenced collection records must already exist.
          </p>
        </div>
        {kind === "plants" && (
          <p>A Plant is one individual specimen in the collection.</p>
        )}
        {kind === "plant-groups" && (
          <p>
            A Plant group is a managed group of specimens. Its count can be
            exact, approximate, or unknown.
          </p>
        )}
        {guideBusy && <p role="status">Loading field guide…</p>}
        {guideError && (
          <p className="notice notice--error" role="alert">
            {guideError}
          </p>
        )}
        {guide && (
          <>
            <div className="import-field-guide__table-wrap">
              <table className="import-field-guide__table">
                <caption className="sr-only">
                  CSV fields for {selectedType}
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Field</th>
                    <th scope="col">Required</th>
                    <th scope="col">Accepted / format</th>
                    <th scope="col">Example</th>
                  </tr>
                </thead>
                <tbody>
                  {guide.map((field) => (
                    <tr key={field.field}>
                      <th scope="row">
                        <code>{field.field}</code>
                        <span>{field.meaning}</span>
                        {field.notes && <small>{field.notes}</small>}
                      </th>
                      <td>{field.required ? "Yes" : "No"}</td>
                      <td>{acceptedValue(field)}</td>
                      <td>
                        <code>{field.example}</code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="import-field-guide__mobile">
              {guide.map((field) => (
                <article key={field.field}>
                  <div className="import-field-guide__mobile-heading">
                    <h4>
                      <code>{field.field}</code>
                    </h4>
                    <span>{field.required ? "Required" : "Optional"}</span>
                  </div>
                  <p>{field.meaning}</p>
                  <p className="import-field-guide__accepted">
                    {acceptedValue(field)}
                  </p>
                  <p>
                    Example: <code>{field.example}</code>
                  </p>
                  {field.notes && <small>{field.notes}</small>}
                </article>
              ))}
            </div>
          </>
        )}
      </section>
      {preview && (
        <section
          className="card import-preview"
          aria-labelledby="preview-heading"
        >
          <div className="import-preview__heading">
            <div>
              <h3 id="preview-heading">Preview: {file?.name}</h3>
              <p>
                {preview.ready} ready · {preview.already_exists} already exist ·{" "}
                {preview.needs_attention} need attention
              </p>
            </div>
            <div
              className="import-preview__filters"
              role="group"
              aria-label="Filter preview rows"
            >
              {(["all", "ready", "attention"] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  className="filter-chip"
                  aria-pressed={filter === value}
                  onClick={() => {
                    setFilter(value);
                  }}
                >
                  {value === "all"
                    ? "All"
                    : value === "ready"
                      ? "Ready"
                      : "Needs attention"}
                </button>
              ))}
            </div>
          </div>
          <div className="import-preview__rows">
            {visibleRows?.map((row) => (
              <article
                key={row.row_number}
                className="import-preview__row"
                aria-label={`CSV record ${String(row.row_number)}`}
              >
                <div className="import-preview__row-heading">
                  <h4>
                    Row {row.row_number}: {row.record}
                  </h4>
                  <span
                    className={`import-preview__outcome import-preview__outcome--${row.outcome}`}
                  >
                    {outcomeLabels[row.outcome]}
                  </span>
                </div>
                {row.references.length > 0 && (
                  <ul>
                    {row.references.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
                {row.normalized.length > 0 && (
                  <div className="import-preview__normalized">
                    <strong>Florabase will use</strong>
                    <ul>
                      {row.normalized.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {row.messages.length > 0 && (
                  <ul className="import-preview__messages">
                    {row.messages.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
                {[...new Set(row.options.map((option) => option.key))].map(
                  (key) => (
                    <fieldset key={key} className="import-preview__choices">
                      <legend>
                        {key === "record"
                          ? "Choose what happens to this record"
                          : `Choose ${key.replaceAll("_", " ")}`}
                      </legend>
                      {row.options
                        .filter((option) => option.key === key)
                        .map((option) => (
                          <label
                            key={option.token}
                            className="import-preview__choice"
                          >
                            <input
                              type="radio"
                              name={`import-${String(row.row_number)}-${key}`}
                              checked={
                                choices[String(row.row_number)]?.[key] ===
                                option.token
                              }
                              onChange={() => {
                                setChoices((current) => ({
                                  ...current,
                                  [row.row_number]: {
                                    ...current[String(row.row_number)],
                                    [key]: option.token,
                                  },
                                }));
                              }}
                            />
                            <div className="import-preview__choice-content">
                              <strong>
                                {actionLabels[option.action]}: {option.label}
                              </strong>
                              <small>{option.details}</small>
                              {option.changes.length > 0 && (
                                <table className="import-preview__diff-table">
                                  <caption>
                                    {option.action === "update_existing"
                                      ? "Changes if updated"
                                      : "CSV differences left unchanged"}
                                  </caption>
                                  <thead>
                                    <tr>
                                      <th scope="col">Field</th>
                                      <th scope="col">Existing</th>
                                      <th scope="col">CSV</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {option.changes.map((change) => (
                                      <tr key={change.field}>
                                        <th scope="row">
                                          {change.field.replaceAll("_", " ")}
                                        </th>
                                        <td>{change.before || "(blank)"}</td>
                                        <td>{change.after || "(blank)"}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              )}
                            </div>
                          </label>
                        ))}
                    </fieldset>
                  ),
                )}
              </article>
            ))}
          </div>
          {!canApply ? (
            <p>
              Resolve each choice or correct the CSV and validate again. No
              records have been changed.
            </p>
          ) : (
            <div className="actions">
              <button
                type="button"
                disabled={busy !== null || !owner}
                onClick={() => void confirm()}
              >
                {busy === "apply" ? "Importing…" : "Confirm import"}
              </button>
              <button
                type="button"
                className="button--secondary"
                disabled={busy !== null}
                onClick={reset}
              >
                Cancel preview
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
