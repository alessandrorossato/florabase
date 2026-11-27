import { useEffect, useState } from "react";

import {
  activeCsrfToken,
  ApiError,
  isExpectedAuthCancellation,
} from "../auth/api";
import { useAuth } from "../auth/context";
import { WfoNameInput } from "../botanical-identities/WfoNameInput";
import { listLocations, type LocationResponse } from "../locations/api";
import { listSuppliers, type SupplierListResponse } from "../suppliers/api";
import {
  applySheet,
  inspectSheet,
  previewSheet,
  rememberedMapping,
  rememberMapping,
  type SheetApplyResult,
  type SheetChoices,
  type SheetField,
  type SheetInspect,
  type SheetMappingColumns,
  type SheetOptions,
  type SheetPreview,
  type SheetRecordType,
  type SupplierKind,
} from "./sheetApi";

type Step = "upload" | "type" | "map" | "review" | "rows" | "done";
const steps: { id: Step; label: string }[] = [
  { id: "upload", label: "Upload" },
  { id: "type", label: "Row type" },
  { id: "map", label: "Columns" },
  { id: "review", label: "Names and places" },
  { id: "rows", label: "Rows" },
  { id: "done", label: "Import" },
];

const recordTypes: { id: SheetRecordType; label: string; hint: string }[] = [
  {
    id: "plants",
    label: "Plant",
    hint: "Each row is one individual specimen.",
  },
  {
    id: "plant-groups",
    label: "Plant group",
    hint: "Each row is a managed group of specimens with a count.",
  },
  { id: "seed-lots", label: "Seed lot", hint: "Each row is one lot of seeds." },
];

const pluralLabels: Record<SheetRecordType, string> = {
  plants: "Plants",
  "plant-groups": "Plant groups",
  "seed-lots": "Seed lots",
};

const recordRoutes: Record<SheetRecordType, string> = {
  plants: "#/plants/",
  "plant-groups": "#/plant-groups/",
  "seed-lots": "#/seeds/",
};

const fieldLabels: Record<SheetField, string> = {
  scientific_name: "Scientific name",
  cultivar_name: "Cultivar",
  common_name: "Common name",
  label: "Label",
  location: "Location",
  supplier: "Supplier",
  collection_entry_date: "Entry date",
  acquisition_date: "Acquisition date",
  harvest_date: "Harvest date",
  expected_viability_until: "Viable until",
  quantity_value: "Quantity",
  quantity_approximate: "Quantity is approximate",
  quantity_kind: "Quantity kind",
  quantity_unit: "Quantity unit",
  direct_origin_kind: "Origin kind",
  direct_origin_detail: "Origin detail",
  source_kind: "Source kind",
  source_detail: "Source detail",
  lifecycle: "Lifecycle",
  notes: "Notes",
};

const outcomeLabels: Record<SheetPreview["rows"][number]["outcome"], string> = {
  ready: "Ready to create",
  already_exists: "Already exists",
  needs_choice: "Choose an action",
  invalid: "Invalid",
  unresolved_reference: "Unresolved reference",
  ambiguous_reference: "Ambiguous reference",
  conflict: "Conflict",
};

const supplierKinds: Record<SupplierKind, string> = {
  seller: "Seller",
  nursery: "Nursery",
  supermarket: "Supermarket",
  person: "Person",
  exchange: "Exchange",
  other: "Other",
};

// Shared IMPORT-001 reference lines start with the record id; the wizard shows names only.
const uuidPrefix = /[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12} → /;

const emptyChoices = (): SheetChoices => ({
  identities: {},
  locations: {},
  suppliers: {},
});

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const body = error.body;
    if (body && typeof body === "object" && "detail" in body) {
      const detail = body.detail;
      if (typeof detail === "string") return detail;
    }
    if (error.status === 413) return "The spreadsheet is larger than 2 MiB.";
    return `Request failed (${String(error.status)}). Check the spreadsheet and try again.`;
  }
  return "Could not reach Florabase. Try again.";
}

function mappingProblem(columns: SheetMappingColumns): string | null {
  const used = Object.values(columns).filter(
    (field): field is SheetField => field !== null,
  );
  if (!used.includes("scientific_name"))
    return "Map one column to Scientific name.";
  const twice = used.find((field, index) => used.indexOf(field) !== index);
  return twice
    ? `${fieldLabels[twice]} is mapped to more than one column.`
    : null;
}

function initialMapping(
  inspect: SheetInspect,
  recordType: SheetRecordType,
): SheetMappingColumns {
  const suggested = Object.fromEntries(
    inspect.columns.map((column) => [column.key, column.suggested_field]),
  );
  const remembered = rememberedMapping(
    recordType,
    inspect.columns.map((column) => column.header),
  );
  if (!remembered) return suggested;
  // A remembered mapping is reused only where it still fits these columns and this type.
  for (const [key, field] of Object.entries(remembered)) {
    if (
      key in suggested &&
      (field === null || inspect.allowed_fields.includes(field))
    )
      suggested[key] = field;
  }
  return suggested;
}

export function SheetImportWizard({ onClose }: { onClose: () => void }) {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const [step, setStep] = useState<Step>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [inspect, setInspect] = useState<SheetInspect | null>(null);
  const [recordType, setRecordType] = useState<SheetRecordType>("plants");
  const [columns, setColumns] = useState<SheetMappingColumns>({});
  const [appendUnmapped, setAppendUnmapped] = useState(false);
  const [choices, setChoices] = useState<SheetChoices>(emptyChoices);
  const [preview, setPreview] = useState<{
    response: SheetPreview;
    options: SheetOptions;
  } | null>(null);
  const [onlyProblems, setOnlyProblems] = useState(false);
  const [result, setResult] = useState<SheetApplyResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [locations, setLocations] = useState<LocationResponse[]>([]);
  const [suppliers, setSuppliers] = useState<SupplierListResponse[]>([]);

  const needsLocations = Boolean(preview?.response.locations.length);
  const needsSuppliers = Boolean(preview?.response.suppliers.length);
  useEffect(() => {
    if (!needsLocations) return;
    const controller = new AbortController();
    listLocations(capability, controller.signal)
      .then((items) => {
        setLocations(items.filter((item) => item.retired_at === null));
      })
      .catch(() => {
        // Without the list only the suggested matches can be picked.
      });
    return () => {
      controller.abort();
    };
  }, [needsLocations, capability]);
  useEffect(() => {
    if (!needsSuppliers) return;
    const controller = new AbortController();
    listSuppliers(capability, controller.signal)
      .then((items) => {
        setSuppliers(items.filter((item) => item.retired_at === null));
      })
      .catch(() => {
        // Without the list only the suggested matches can be picked.
      });
    return () => {
      controller.abort();
    };
  }, [needsSuppliers, capability]);

  async function run<T>(
    request: () => Promise<T>,
    onSuccess: (value: T) => void,
  ) {
    setBusy(true);
    setError(null);
    try {
      onSuccess(await request());
    } catch (caught: unknown) {
      if (isExpectedAuthCancellation(caught)) return;
      if (caught instanceof ApiError && caught.status === 401) {
        sessionExpired();
        return;
      }
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  function reinspect(
    nextFile: File,
    params: {
      recordType: SheetRecordType;
      sheetName: string | null;
      headerRow: number | null;
    },
    then?: (value: SheetInspect) => void,
  ) {
    void run(
      () => inspectSheet(nextFile, params, capability),
      (value) => {
        setInspect(value);
        then?.(value);
      },
    );
  }

  function currentOptions(nextChoices = choices): SheetOptions {
    return {
      record_type: recordType,
      sheet_name: inspect?.selected_sheet ?? null,
      header_row: inspect?.header_row ?? null,
      mapping: { columns, append_unmapped_to_notes: appendUnmapped },
      choices: nextChoices,
    };
  }

  function runPreview(next: Step) {
    if (!file) return;
    const options = currentOptions();
    void run(
      () => previewSheet(file, options, capability),
      (response) => {
        setPreview({ response, options });
        setStep(next);
      },
    );
  }

  function runApply() {
    const csrfToken = activeCsrfToken(auth.state);
    if (!file || !preview || !csrfToken) return;
    setBusy(true);
    setError(null);
    applySheet(
      file,
      preview.options,
      preview.response.confirmation_token,
      csrfToken,
      capability,
    )
      .then((value) => {
        setResult(value);
        setStep("done");
      })
      .catch((caught: unknown) => {
        if (isExpectedAuthCancellation(caught)) return;
        if (caught instanceof ApiError && caught.status === 401) {
          sessionExpired();
          return;
        }
        setError(
          `${errorMessage(caught)} Nothing was imported. Check the names and places again.`,
        );
        setStep("review");
      })
      .finally(() => {
        setBusy(false);
      });
  }

  function choose<K extends keyof SheetChoices>(
    group: K,
    key: string,
    value: NonNullable<SheetChoices[K][string]>,
  ) {
    setChoices((current) => {
      return { ...current, [group]: { ...current[group], [key]: value } };
    });
  }

  const stepIndex = steps.findIndex((item) => item.id === step);
  const problem = mappingProblem(columns);
  const rows = preview?.response.rows.filter(
    (row) => !onlyProblems || row.outcome !== "ready",
  );

  return (
    <section
      className="card import-workspace__primary sheet-import"
      aria-labelledby="sheet-import-heading"
    >
      <h3 id="sheet-import-heading">Import a spreadsheet</h3>
      <ol
        className="import-progress import-progress--sheet"
        aria-label="Spreadsheet import steps"
      >
        {steps.map((item, index) => (
          <li
            key={item.id}
            aria-current={index === stepIndex ? "step" : undefined}
            className={index < stepIndex ? "is-complete" : undefined}
          >
            <span className="import-progress__number">{index + 1}</span>
            {item.label}
          </li>
        ))}
      </ol>

      {step === "upload" && (
        <>
          <div className="field">
            <label htmlFor="sheet-import-file">Spreadsheet</label>
            <input
              id="sheet-import-file"
              type="file"
              accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              aria-describedby="sheet-import-file-hint"
              disabled={busy}
              onChange={(event) => {
                const next = event.currentTarget.files?.[0] ?? null;
                setFile(next);
                setInspect(null);
                setChoices(emptyChoices());
                setPreview(null);
                if (next)
                  reinspect(next, {
                    recordType,
                    sheetName: null,
                    headerRow: null,
                  });
              }}
            />
            <small id="sheet-import-file-hint" className="import-field-hint">
              CSV (UTF-8) or Excel .xlsx · up to 2 MiB and 2,000 rows · one
              sheet, one row per record
            </small>
          </div>
          {file && inspect && (
            <>
              {inspect.sheets.length > 1 && (
                <div className="field">
                  <label htmlFor="sheet-import-sheet">Sheet</label>
                  <select
                    id="sheet-import-sheet"
                    value={inspect.selected_sheet ?? ""}
                    disabled={busy}
                    onChange={(event) => {
                      reinspect(file, {
                        recordType,
                        sheetName: event.currentTarget.value,
                        headerRow: null,
                      });
                    }}
                  >
                    {inspect.sheets.map((sheet) => (
                      <option key={sheet} value={sheet}>
                        {sheet}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div className="field">
                <label htmlFor="sheet-import-header">Header row</label>
                <select
                  id="sheet-import-header"
                  value={inspect.header_row}
                  disabled={busy}
                  onChange={(event) => {
                    reinspect(file, {
                      recordType,
                      sheetName: inspect.selected_sheet,
                      headerRow: Number(event.currentTarget.value),
                    });
                  }}
                >
                  {Array.from({ length: 10 }, (_, index) => index + 1).map(
                    (row) => (
                      <option key={row} value={row}>
                        Row {row}
                        {row === inspect.detected_header_row
                          ? " (detected)"
                          : ""}
                      </option>
                    ),
                  )}
                </select>
              </div>
              <p role="status">
                {inspect.row_count} data{" "}
                {inspect.row_count === 1 ? "row" : "rows"} ·{" "}
                {inspect.columns.length} columns:{" "}
                {inspect.columns.map((column) => column.header).join(", ")}
              </p>
            </>
          )}
        </>
      )}

      {step === "type" && (
        <fieldset className="import-preview__choices">
          <legend>What is each row?</legend>
          {recordTypes.map((type) => (
            <label key={type.id} className="import-preview__choice">
              <input
                type="radio"
                name="sheet-import-type"
                checked={recordType === type.id}
                onChange={() => {
                  setRecordType(type.id);
                }}
              />
              <span className="import-preview__choice-content">
                <strong>{type.label}</strong>
                <small>{type.hint}</small>
              </span>
            </label>
          ))}
        </fieldset>
      )}

      {step === "map" && inspect && (
        <>
          <p>
            Choose the Florabase field for each column. Columns left on Ignore
            are not imported.
          </p>
          <div className="sheet-import__table">
            <table className="import-field-guide__table">
              <caption className="sr-only">Column mapping</caption>
              <thead>
                <tr>
                  <th scope="col">Your column</th>
                  <th scope="col">Sample values</th>
                  <th scope="col">Florabase field</th>
                </tr>
              </thead>
              <tbody>
                {inspect.columns.map((column) => (
                  <tr key={column.key}>
                    <th scope="row">{column.header}</th>
                    <td>{column.samples.filter(Boolean).join(" · ") || "—"}</td>
                    <td>
                      <select
                        aria-label={`Field for column ${column.header}`}
                        value={columns[column.key] ?? ""}
                        onChange={(event) => {
                          const value = event.currentTarget.value;
                          setColumns((current) => ({
                            ...current,
                            [column.key]: value ? (value as SheetField) : null,
                          }));
                        }}
                      >
                        <option value="">Ignore</option>
                        {inspect.allowed_fields.map((field) => (
                          <option key={field} value={field}>
                            {fieldLabels[field]}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <label className="sheet-import__check">
            <input
              type="checkbox"
              checked={appendUnmapped}
              onChange={(event) => {
                setAppendUnmapped(event.currentTarget.checked);
              }}
            />
            Add ignored columns to notes as “Column: value”
          </label>
          {problem && (
            <p className="notice notice--error" role="alert">
              {problem}
            </p>
          )}
        </>
      )}

      {step === "review" && preview && (
        <ReviewGroups
          preview={preview.response}
          choices={choices}
          locations={locations}
          suppliers={suppliers}
          choose={choose}
        />
      )}

      {step === "rows" && preview && (
        <div className="import-preview">
          <div className="import-preview__heading">
            <p>
              {preview.response.ready} ready ·{" "}
              {preview.response.needs_attention} need attention (
              {preview.response.invalid} invalid)
            </p>
            <label className="sheet-import__check">
              <input
                type="checkbox"
                checked={onlyProblems}
                onChange={(event) => {
                  setOnlyProblems(event.currentTarget.checked);
                }}
              />
              Only problems
            </label>
          </div>
          <div className="import-preview__rows">
            {rows?.map((row) => (
              <article
                key={row.row_number}
                className="import-preview__row"
                aria-label={`Spreadsheet row ${String(row.row_number)}`}
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
                      <li key={item}>{item.replace(uuidPrefix, "")}</li>
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
              </article>
            ))}
            {rows?.length === 0 && <p>No rows with problems.</p>}
          </div>
          {preview.response.can_apply ? (
            <p>
              Import will create {preview.response.ready}{" "}
              {pluralLabels[recordType]},{" "}
              {preview.response.will_create_identities} identities,{" "}
              {preview.response.will_create_locations} locations and{" "}
              {preview.response.will_create_suppliers} suppliers, all in one
              step.
            </p>
          ) : (
            <p>
              Fix the spreadsheet or the names and places, then check again.
              Nothing has been imported.
            </p>
          )}
        </div>
      )}

      {step === "done" && result && (
        <div role="status">
          <p className="notice">
            Created {result.records_created} {pluralLabels[recordType]},{" "}
            {result.identities_created} identities, {result.locations_created}{" "}
            locations and {result.suppliers_created} suppliers.
          </p>
          <ul className="sheet-import__created">
            {result.created_records.map((record) => (
              <li key={record.id}>
                <a href={`${recordRoutes[recordType]}${record.id}`}>
                  {record.label}
                </a>{" "}
                · {record.identity_label}
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && (
        <p className="notice notice--error" role="alert">
          {error}
        </p>
      )}

      <div className="actions">
        {step === "upload" && (
          <button
            type="button"
            disabled={!inspect || busy}
            onClick={() => {
              setStep("type");
            }}
          >
            Next
          </button>
        )}
        {step === "type" && file && inspect && (
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              reinspect(
                file,
                {
                  recordType,
                  sheetName: inspect.selected_sheet,
                  headerRow: inspect.header_row,
                },
                (value) => {
                  setColumns(initialMapping(value, recordType));
                  setChoices(emptyChoices());
                  setStep("map");
                },
              );
            }}
          >
            Next
          </button>
        )}
        {step === "map" && inspect && (
          <button
            type="button"
            disabled={busy || problem !== null}
            onClick={() => {
              rememberMapping(
                recordType,
                inspect.columns.map((column) => column.header),
                columns,
              );
              runPreview("review");
            }}
          >
            {busy ? "Checking…" : "Check names and places"}
          </button>
        )}
        {step === "review" && (
          <>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                runPreview("rows");
              }}
            >
              {busy ? "Checking…" : "Check rows"}
            </button>
            <button
              type="button"
              className="button--secondary"
              disabled={busy}
              onClick={() => {
                runPreview("review");
              }}
            >
              Update review
            </button>
          </>
        )}
        {step === "rows" && preview && (
          <button
            type="button"
            disabled={busy || !preview.response.can_apply}
            onClick={runApply}
          >
            {busy ? "Importing…" : "Import"}
          </button>
        )}
        {(step === "type" ||
          step === "map" ||
          step === "review" ||
          step === "rows") && (
          <button
            type="button"
            className="button--secondary"
            disabled={busy}
            onClick={() => {
              setError(null);
              setStep(steps[stepIndex - 1].id);
            }}
          >
            Back
          </button>
        )}
        <button
          type="button"
          className="button--secondary"
          disabled={busy}
          onClick={onClose}
        >
          {step === "done" ? "Close" : "Cancel"}
        </button>
      </div>
    </section>
  );
}

function ReviewGroups({
  preview,
  choices,
  locations,
  suppliers,
  choose,
}: {
  preview: SheetPreview;
  choices: SheetChoices;
  locations: LocationResponse[];
  suppliers: SupplierListResponse[];
  choose: <K extends keyof SheetChoices>(
    group: K,
    key: string,
    value: NonNullable<SheetChoices[K][string]>,
  ) => void;
}) {
  const { capability } = useAuth();
  const count = (items: { status: string }[], status: string) =>
    items.filter((item) => item.status === status).length;
  return (
    <div className="sheet-import__review">
      <p>
        Nothing is created until the last step. Changes here take effect when
        you check again.
      </p>

      <fieldset className="import-preview__choices">
        <legend>
          Species: {count(preview.identities, "matched")} match existing
          identities · {count(preview.identities, "new")} new
        </legend>
        {preview.identities.map((group, index) => {
          const choice = choices.identities[group.key];
          const action = choice?.action ?? group.action;
          const id = `sheet-identity-${String(index)}`;
          return (
            <div key={group.key} className="sheet-import__group">
              <p>
                <i className="scientific-name">{group.scientific_name}</i>
                {group.cultivar_name ? ` ‘${group.cultivar_name}’` : ""} ·{" "}
                {group.row_count} {group.row_count === 1 ? "row" : "rows"} ·{" "}
                {group.status === "matched"
                  ? `uses ${group.matched_label ?? "existing identity"}`
                  : group.status === "new"
                    ? "will be created"
                    : "needs attention"}
              </p>
              {(group.messages ?? []).map((message) => (
                <p key={message} className="import-preview__messages">
                  {message}
                </p>
              ))}
              {(group.candidates ?? []).length > 0 && (
                <div className="field">
                  <label htmlFor={`${id}-existing`}>
                    Use existing identity
                  </label>
                  <select
                    id={`${id}-existing`}
                    value={
                      action === "use_existing"
                        ? (choice?.existing_id ?? group.matched_id ?? "")
                        : ""
                    }
                    onChange={(event) => {
                      const value = event.currentTarget.value;
                      choose(
                        "identities",
                        group.key,
                        value
                          ? { action: "use_existing", existing_id: value }
                          : { action: "create" },
                      );
                    }}
                  >
                    <option value="">No, create a new identity</option>
                    {(group.candidates ?? []).map((candidate) => (
                      <option key={candidate.id} value={candidate.id}>
                        {candidate.label}
                        {candidate.match_kind === "near" ? " (similar)" : ""}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              {action === "create" && (
                <div className="field">
                  <label htmlFor={`${id}-name`}>New scientific name</label>
                  <WfoNameInput
                    id={`${id}-name`}
                    capability={capability}
                    value={choice?.scientific_name ?? group.scientific_name}
                    onChange={(event) => {
                      choose("identities", group.key, {
                        ...choice,
                        action: "create",
                        scientific_name: event.currentTarget.value,
                      });
                    }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </fieldset>

      {preview.locations.length > 0 && (
        <fieldset className="import-preview__choices">
          <legend>
            Locations: {count(preview.locations, "matched")} existing ·{" "}
            {count(preview.locations, "new")} new
          </legend>
          {preview.locations.map((group, index) => {
            const choice = choices.locations[group.key];
            const action = choice?.action ?? group.action;
            const id = `sheet-location-${String(index)}`;
            return (
              <div key={group.key} className="sheet-import__group">
                <p>
                  <strong>{group.raw_value}</strong> · {group.row_count}{" "}
                  {group.row_count === 1 ? "row" : "rows"}
                  {group.matched_label ? ` · uses ${group.matched_label}` : ""}
                </p>
                {(group.messages ?? []).map((message) => (
                  <p key={message} className="import-preview__messages">
                    {message}
                  </p>
                ))}
                <ActionSelect
                  id={`${id}-action`}
                  value={action}
                  onChange={(next) => {
                    choose("locations", group.key, { action: next });
                  }}
                />
                {action === "use_existing" && (
                  <ExistingSelect
                    id={`${id}-existing`}
                    label="Existing location"
                    value={choice?.existing_id ?? group.matched_id ?? ""}
                    candidates={group.candidates ?? []}
                    all={locations.map((item) => ({
                      id: item.id,
                      label: item.display_path,
                    }))}
                    onChange={(value) => {
                      choose("locations", group.key, {
                        action: "use_existing",
                        existing_id: value || null,
                      });
                    }}
                  />
                )}
                {action === "create" && (
                  <>
                    <div className="field">
                      <label htmlFor={`${id}-name`}>New location name</label>
                      <input
                        id={`${id}-name`}
                        value={
                          choice?.name ?? group.create_name ?? group.raw_value
                        }
                        onChange={(event) => {
                          choose("locations", group.key, {
                            ...choice,
                            action: "create",
                            name: event.currentTarget.value,
                          });
                        }}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor={`${id}-parent`}>Create under</label>
                      <select
                        id={`${id}-parent`}
                        value={choice?.parent_id ?? group.parent_id ?? ""}
                        onChange={(event) => {
                          choose("locations", group.key, {
                            ...choice,
                            action: "create",
                            parent_id: event.currentTarget.value || null,
                          });
                        }}
                      >
                        <option value="">Top level</option>
                        {locations.map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.display_path}
                          </option>
                        ))}
                      </select>
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </fieldset>
      )}

      {preview.suppliers.length > 0 && (
        <fieldset className="import-preview__choices">
          <legend>
            Suppliers: {count(preview.suppliers, "matched")} existing ·{" "}
            {count(preview.suppliers, "new")} new
          </legend>
          {preview.suppliers.map((group, index) => {
            const choice = choices.suppliers[group.key];
            const action = choice?.action ?? group.action;
            const id = `sheet-supplier-${String(index)}`;
            return (
              <div key={group.key} className="sheet-import__group">
                <p>
                  <strong>{group.raw_value}</strong> · {group.row_count}{" "}
                  {group.row_count === 1 ? "row" : "rows"}
                  {group.matched_label ? ` · uses ${group.matched_label}` : ""}
                </p>
                {(group.messages ?? []).map((message) => (
                  <p key={message} className="import-preview__messages">
                    {message}
                  </p>
                ))}
                <ActionSelect
                  id={`${id}-action`}
                  value={action}
                  onChange={(next) => {
                    choose("suppliers", group.key, { action: next });
                  }}
                />
                {action === "use_existing" && (
                  <ExistingSelect
                    id={`${id}-existing`}
                    label="Existing supplier"
                    value={choice?.existing_id ?? group.matched_id ?? ""}
                    candidates={group.candidates ?? []}
                    all={suppliers.map((item) => ({
                      id: item.id,
                      label: item.name,
                    }))}
                    onChange={(value) => {
                      choose("suppliers", group.key, {
                        action: "use_existing",
                        existing_id: value || null,
                      });
                    }}
                  />
                )}
                {action === "create" && (
                  <>
                    <div className="field">
                      <label htmlFor={`${id}-name`}>New supplier name</label>
                      <input
                        id={`${id}-name`}
                        value={
                          choice?.name ?? group.create_name ?? group.raw_value
                        }
                        onChange={(event) => {
                          choose("suppliers", group.key, {
                            ...choice,
                            action: "create",
                            name: event.currentTarget.value,
                          });
                        }}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor={`${id}-kind`}>Kind</label>
                      <select
                        id={`${id}-kind`}
                        value={choice?.kind ?? group.kind}
                        onChange={(event) => {
                          choose("suppliers", group.key, {
                            ...choice,
                            action: "create",
                            kind: event.currentTarget.value as SupplierKind,
                          });
                        }}
                      >
                        {Object.entries(supplierKinds).map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </fieldset>
      )}
    </div>
  );
}

type GroupAction = "use_existing" | "create" | "skip";

function ActionSelect({
  id,
  value,
  onChange,
}: {
  id: string;
  value: GroupAction;
  onChange: (value: GroupAction) => void;
}) {
  return (
    <div className="field">
      <label htmlFor={id}>What to do</label>
      <select
        id={id}
        value={value}
        onChange={(event) => {
          onChange(event.currentTarget.value as GroupAction);
        }}
      >
        <option value="use_existing">Use an existing one</option>
        <option value="create">Create new</option>
        <option value="skip">Leave empty</option>
      </select>
    </div>
  );
}

function ExistingSelect({
  id,
  label,
  value,
  candidates,
  all,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  candidates: { id: string; label: string; match_kind: string }[];
  all: { id: string; label: string }[];
  onChange: (value: string) => void;
}) {
  const suggested = new Set(candidates.map((candidate) => candidate.id));
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select
        id={id}
        value={value}
        onChange={(event) => {
          onChange(event.currentTarget.value);
        }}
      >
        <option value="">Choose…</option>
        {candidates.length > 0 && (
          <optgroup label="Suggested">
            {candidates.map((candidate) => (
              <option key={candidate.id} value={candidate.id}>
                {candidate.label}
                {candidate.match_kind === "near" ? " (similar)" : ""}
              </option>
            ))}
          </optgroup>
        )}
        <optgroup label="All">
          {all
            .filter((item) => !suggested.has(item.id))
            .map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
        </optgroup>
      </select>
    </div>
  );
}
