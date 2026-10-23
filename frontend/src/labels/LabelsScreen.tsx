import { ActionButton } from "../components/Action";
import { FieldLabel } from "../components/FieldLabel";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { PageHeader } from "../components/ReferenceUI";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  Page,
} from "../components/WorkspaceUI";
import { ReferencePicker } from "../seed-lots/ReferencePicker";
import {
  getApplicationSettings,
  saveApplicationSettings,
} from "../settings/api";
import { QrDestinationDialog } from "../settings/QrDestinationDialog";
import { CategoryGlyph } from "./CategoryGlyph";
import { qrGeometry } from "./qrCode";
import { LabelIdentity, LabelSheet } from "./LabelSheet";
import {
  composePages,
  isLabelKind,
  labelKey,
  labelKinds,
  labelPresets,
  isLabelPreset,
  pickerLabel,
  pickerDescription,
  recordUrl,
  maxLabels,
  labelTypeNames,
  listLabelRecords,
  sourceHref,
  type LabelEntry,
  type LabelKind,
  type LabelRecord,
  type LabelPresetId,
} from "./labelData";
import "./labels.css";

type RecordsState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; records: LabelRecord[] };
export function LabelsScreen({
  initialKind,
  initialId,
}: {
  initialKind?: string;
  initialId?: string;
}) {
  const auth = useAuth();
  const [presetId, setPresetId] = useState<LabelPresetId>("medium");
  const [configuration, setConfiguration] = useState<{
    status: "loading" | "error" | "ready";
    baseUrl: string | null;
  }>({ status: "loading", baseUrl: null });
  const [editingQr, setEditingQr] = useState(false);
  const [settingsRetry, setSettingsRetry] = useState(0);
  const [defaultPreset, setDefaultPreset] = useState<LabelPresetId | null>(
    null,
  );
  const [savingDefault, setSavingDefault] = useState(false);
  const [defaultError, setDefaultError] = useState("");
  const [defaultMessage, setDefaultMessage] = useState("");
  const preset = labelPresets[presetId];
  const labelsPerPage = preset.columns * preset.rows;
  const [kind, setKind] = useState<LabelKind>(
    isLabelKind(initialKind) ? initialKind : "seed-lot",
  );
  const [records, setRecords] = useState<RecordsState>({ status: "loading" });
  const [selectedId, setSelectedId] = useState("");
  const [entries, setEntries] = useState<LabelEntry[]>([]);
  const [retry, setRetry] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const initialHandled = useRef(false);
  const recordType = useRef<HTMLSelectElement>(null);
  const total = entries.reduce((sum, entry) => sum + entry.copies, 0);
  const pages = composePages(entries, preset);
  const denseQr =
    configuration.baseUrl !== null &&
    entries.some(
      ({ record }) =>
        preset.qrMm /
          qrGeometry(
            recordUrl(
              record.kind,
              record.id,
              configuration.baseUrl,
              record.harvestId,
            ),
          ).size <
        0.22,
    );
  const canPrint =
    total > 0 &&
    configuration.status === "ready" &&
    configuration.baseUrl !== null &&
    !denseQr;
  useEffect(() => {
    const controller = new AbortController();
    void getApplicationSettings(controller.signal)
      .then((settings) => {
        if (controller.signal.aborted) return;
        setPresetId(settings.default_label_preset);
        setDefaultPreset(settings.default_label_preset);
        setConfiguration({
          status: "ready",
          baseUrl: settings.public_qr_base_url,
        });
      })
      .catch((failure: unknown) => {
        if (controller.signal.aborted) return;
        if (failure instanceof ApiError && failure.status === 401)
          auth.sessionExpired();
        else setConfiguration({ status: "error", baseUrl: null });
      });
    return () => {
      controller.abort();
    };
  }, [auth, settingsRetry]);
  useEffect(() => {
    const controller = new AbortController();
    void listLabelRecords(kind, controller.signal)
      .then((loaded) => {
        if (controller.signal.aborted) return;
        setRecords({ status: "ready", records: loaded });
        if (!initialHandled.current) {
          initialHandled.current = true;
          if (initialKind || initialId) {
            const target = loaded.find((record) => record.id === initialId);
            if (!isLabelKind(initialKind) || !target)
              setError(
                "The requested label source is unavailable. Choose a supported collection record.",
              );
            else {
              setEntries([{ record: target, copies: 1 }]);
              setMessage("Record added to the batch.");
            }
          }
        }
      })
      .catch((failure: unknown) => {
        if (controller.signal.aborted) return;
        if (failure instanceof ApiError && failure.status === 401)
          auth.sessionExpired();
        else setRecords({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [kind, retry, initialKind, initialId, auth]);
  function addRecord() {
    if (records.status !== "ready") return;
    const record = records.records.find(({ id }) => id === selectedId);
    if (!record) return;
    if (total >= maxLabels) {
      setError("A batch holds 360 labels. Reduce copies or remove records.");
      return;
    }
    setEntries((current) =>
      current.some((entry) => labelKey(entry.record) === labelKey(record))
        ? current.map((entry) =>
            labelKey(entry.record) === labelKey(record)
              ? { ...entry, copies: entry.copies + 1 }
              : entry,
          )
        : [...current, { record, copies: 1 }],
    );
    setError(null);
    setMessage(
      `${labelTypeNames[kind]} added. ${String(total + 1)} ${total + 1 === 1 ? "label" : "labels"} in the batch.`,
    );
  }
  async function setAsDefault() {
    if (!("csrfToken" in auth.state)) return;
    setSavingDefault(true);
    setDefaultError("");
    setDefaultMessage("");
    try {
      // Preserve the latest configured origin when saving this preference.
      const latest = await getApplicationSettings();
      const saved = await saveApplicationSettings(
        { ...latest, default_label_preset: presetId },
        auth.state.csrfToken,
      );
      setDefaultPreset(saved.default_label_preset);
      setConfiguration({ status: "ready", baseUrl: saved.public_qr_base_url });
      setDefaultMessage("Default label size saved.");
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401)
        auth.sessionExpired();
      else
        setDefaultError(
          "Could not save the default label size. Your batch is unchanged. Try again.",
        );
    } finally {
      setSavingDefault(false);
    }
  }
  return (
    <Page className="labels-workspace" titleId="labels-heading">
      <PageHeader
        title="Labels"
        titleId="labels-heading"
        eyebrow="Tools"
        description="Prepare collection material for print."
        tools={
          <ActionButton
            icon="print"
            type="button"
            disabled={!canPrint}
            onClick={() => {
              if (!canPrint) return;
              try {
                window.print();
              } catch {
                setError(
                  "Could not open browser printing. Use your browser’s Print command.",
                );
              }
            }}
          >
            Print
          </ActionButton>
        }
      />
      {configuration.status === "loading" ? (
        <LoadingState>Loading print settings…</LoadingState>
      ) : configuration.status === "error" ? (
        <ErrorState
          onRetry={() => {
            setConfiguration({ status: "loading", baseUrl: null });
            setSettingsRetry((n) => n + 1);
          }}
        >
          Could not load print settings. Printing is unavailable.
        </ErrorState>
      ) : (
        <div
          className={`label-qr-destination${configuration.baseUrl ? "" : " notice notice--warning"}`}
        >
          <span>
            {configuration.baseUrl
              ? `QR destination: ${configuration.baseUrl}`
              : "QR destination is not configured. Set a public URL before printing."}
          </span>
          <ActionButton
            icon="edit"
            type="button"
            className="button--secondary"
            aria-label="Edit QR destination"
            onClick={() => {
              setEditingQr(true);
            }}
          >
            Edit
          </ActionButton>
        </div>
      )}
      {editingQr && (
        <QrDestinationDialog
          value={configuration.baseUrl}
          onClose={() => {
            setEditingQr(false);
          }}
          onSaved={(settings) => {
            setConfiguration({
              status: "ready",
              baseUrl: settings.public_qr_base_url,
            });
            setDefaultPreset(settings.default_label_preset);
            setMessage("QR destination saved. Labels updated.");
          }}
        />
      )}
      {denseQr && (
        <p className="notice notice--warning" role="alert">
          The QR destination is too dense for this label size. Choose a larger
          preset or configure a shorter public URL before printing.
        </p>
      )}
      <div className="label-composer">
        <section
          className="label-controls"
          aria-labelledby="label-selection-heading"
        >
          <div className="label-preset">
            <h3>Print format</h3>
            <div className="label-format-choice">
              <label>
                Label size
                <select
                  value={presetId}
                  disabled={configuration.status === "loading" || savingDefault}
                  onChange={(event) => {
                    if (isLabelPreset(event.target.value))
                      setPresetId(event.target.value);
                    setDefaultMessage("");
                    setDefaultError("");
                  }}
                >
                  {Object.values(labelPresets).map((size) => (
                    <option key={size.id} value={size.id}>
                      {size.title}
                    </option>
                  ))}
                </select>
              </label>
              {defaultPreset === presetId ? (
                <span className="label-default-indicator">Default</span>
              ) : (
                <button
                  type="button"
                  className="button--secondary"
                  disabled={configuration.status !== "ready" || savingDefault}
                  onClick={() => {
                    void setAsDefault();
                  }}
                >
                  {savingDefault ? "Saving…" : "Set as default"}
                </button>
              )}
            </div>
            {defaultError && <p role="alert">{defaultError}</p>}
            {defaultMessage && <p role="status">{defaultMessage}</p>}
            <small>
              A4 · {preset.columns} columns × {preset.rows} rows ·{" "}
              {labelsPerPage} labels / sheet · fresh sheets
            </small>
          </div>
          <h3 id="label-selection-heading">Add material</h3>
          <label>
            Record type
            <select
              ref={recordType}
              value={kind}
              onChange={(event) => {
                if (
                  !isLabelKind(event.target.value) ||
                  event.target.value === kind
                )
                  return;
                setKind(event.target.value);
                setSelectedId("");
                setRecords({ status: "loading" });
                setError(null);
              }}
            >
              {labelKinds.map((target) => (
                <option key={target} value={target}>
                  {labelTypeNames[target]}
                </option>
              ))}
            </select>
          </label>
          {records.status === "loading" ? (
            <LoadingState>Loading records…</LoadingState>
          ) : records.status === "error" ? (
            <ErrorState
              onRetry={() => {
                setRecords({ status: "loading" });
                setRetry((value) => value + 1);
              }}
            >
              Could not load records.
            </ErrorState>
          ) : !records.records.length ? (
            <EmptyState>
              No {labelTypeNames[kind].toLowerCase()} records available.
            </EmptyState>
          ) : (
            <ReferencePicker
              key={kind}
              label="Record"
              choices={records.records.map((record) => ({
                id: record.id,
                label: pickerLabel(record),
                description: pickerDescription(record),
              }))}
              value={selectedId}
              onChange={setSelectedId}
            />
          )}
          <button
            type="button"
            className="button--secondary"
            disabled={
              records.status !== "ready" || !selectedId || total >= maxLabels
            }
            onClick={addRecord}
          >
            Add record
          </button>
          {error && (
            <p className="notice notice--error" role="alert">
              {error}
            </p>
          )}
          <p className="sr-only" role="status">
            {message}
          </p>
          <div className="label-batch-heading">
            <h3>Selected material</h3>
            <span>
              {entries.length} {entries.length === 1 ? "record" : "records"}
            </span>
          </div>
          {!entries.length ? (
            <EmptyState>
              No material selected. Add collection records to prepare labels.
            </EmptyState>
          ) : (
            <ul className="label-entries" aria-label="Selected material">
              {entries.map((entry) => {
                const key = labelKey(entry.record);
                const description = `${labelTypeNames[entry.record.kind]}: ${entry.record.context ?? entry.record.botanicalName}`;
                return (
                  <li key={key}>
                    <div className="label-source-meta">
                      <small>
                        <CategoryGlyph kind={entry.record.kind} />
                        {labelTypeNames[entry.record.kind]}
                      </small>
                    </div>
                    <a href={sourceHref(entry.record)}>
                      <LabelIdentity record={entry.record} />
                    </a>
                    {entry.record.context && (
                      <span>{entry.record.context}</span>
                    )}
                    <div className="label-entry-actions">
                      <label>
                        <FieldLabel as="span" required>
                          Copies
                        </FieldLabel>
                        <input
                          aria-required="true"
                          aria-label={`Copies for ${description}`}
                          type="number"
                          min="1"
                          max={maxLabels - total + entry.copies}
                          step="1"
                          value={entry.copies}
                          onChange={(event) => {
                            const copies = Number(event.target.value);
                            if (
                              !Number.isInteger(copies) ||
                              copies < 1 ||
                              total - entry.copies + copies > maxLabels
                            ) {
                              setError(
                                "Copies must be a whole number of at least 1; a batch holds 360 labels.",
                              );
                              return;
                            }
                            setEntries((current) =>
                              current.map((item) =>
                                labelKey(item.record) === key
                                  ? { ...item, copies }
                                  : item,
                              ),
                            );
                            setError(null);
                            setMessage("Copies updated.");
                          }}
                        />
                      </label>
                      <button
                        className="button--secondary"
                        type="button"
                        aria-label={`Remove ${description}`}
                        onClick={() => {
                          setEntries((current) =>
                            current.filter(
                              (item) => labelKey(item.record) !== key,
                            ),
                          );
                          setError(null);
                          setMessage("Record removed.");
                          recordType.current?.focus();
                        }}
                      >
                        Remove
                      </button>
                    </div>
                    <details className="label-content-details">
                      <summary>Label content</summary>
                      <div>
                        <strong>Printed names</strong>
                        <LabelIdentity record={entry.record} />
                        {entry.record.commonName && (
                          <span>{entry.record.commonName}</span>
                        )}
                        <strong>Record details (not printed)</strong>
                        <span>{labelTypeNames[entry.record.kind]}</span>
                        {entry.record.context && (
                          <span>{entry.record.context}</span>
                        )}
                        <span>Record ID: {entry.record.id}</span>
                        {entry.record.metadata.map((line, index) => (
                          <span key={index}>{line}</span>
                        ))}
                      </div>
                    </details>
                  </li>
                );
              })}
            </ul>
          )}

          <p className="label-totals" aria-live="polite">
            {entries.length} {entries.length === 1 ? "record" : "records"} ·{" "}
            {total} {total === 1 ? "label" : "labels"} · {pages.length} A4{" "}
            {pages.length === 1 ? "sheet" : "sheets"}
          </p>
          {total > 0 && (
            <p className="field-help">
              {labelsPerPage - (total % labelsPerPage || labelsPerPage)} empty
              cells on the final sheet · maximum 360 labels per batch
            </p>
          )}
          <details className="label-print-guidance">
            <summary>Print setup</summary>
            <p>
              A4 portrait · 100% / Actual size. Disable Fit to page and browser
              headers and footers. Keep the stylesheet’s margins. Measure a
              trial label: {preset.widthMm} × {preset.heightMm} mm. Scan a trial
              QR before printing the batch.
            </p>
            <p>
              Screen zoom changes the preview, while print dimensions remain in
              millimetres. Leaving or refreshing discards this temporary batch.
              Reopen after editing source records.
            </p>
          </details>
        </section>
        <section
          className="label-preview"
          aria-labelledby="label-preview-heading"
        >
          <h3 id="label-preview-heading">Print preview</h3>
          {total ? (
            <LabelSheet
              pages={pages}
              preview
              preset={preset}
              baseUrl={configuration.baseUrl}
            />
          ) : (
            <EmptyState>
              Your sheets will appear here after adding material.
            </EmptyState>
          )}
        </section>
      </div>
      {createPortal(
        <div className="label-print-root" aria-hidden="true">
          {canPrint ? (
            <LabelSheet
              pages={pages}
              preset={preset}
              baseUrl={configuration.baseUrl}
            />
          ) : (
            <p className="label-print-blocked">
              Labels cannot be printed until a valid QR destination and
              scannable size are configured.
            </p>
          )}
        </div>,
        document.body,
      )}
    </Page>
  );
}
