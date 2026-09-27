import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { ReferencePicker } from "../seed-lots/ReferencePicker";
import { LabelSheet } from "./LabelSheet";
import {
  composePages,
  isLabelKind,
  labelKey,
  labelKinds,
  labelsPerPage,
  labelTypeNames,
  listLabelRecords,
  recordUrl,
  type LabelEntry,
  type LabelKind,
  type LabelRecord,
} from "./labelData";
import "./labels.css";

type RecordsState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; records: LabelRecord[] };

export function LabelsScreen({
  initialKind,
  initialId,
  canonicalOrigin,
}: {
  initialKind?: string;
  initialId?: string;
  canonicalOrigin: string | null;
}) {
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
  const pages = composePages(entries);

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
            if (!isLabelKind(initialKind) || !target) {
              setError(
                "The requested label target is unavailable. Choose a Seed lot, Plant, or Plant group.",
              );
            } else {
              try {
                recordUrl(target.kind, target.id, canonicalOrigin);
                setEntries([{ record: target, copies: 1 }]);
                setMessage("Label added to the sheet.");
              } catch {
                setError(
                  canonicalOrigin
                    ? "The requested record reference is invalid."
                    : "Florabase has no canonical public address configured; labels cannot be created.",
                );
              }
            }
          }
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setRecords({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [kind, retry, initialKind, initialId, canonicalOrigin]);

  function addLabel() {
    if (records.status !== "ready") return;
    const record = records.records.find(({ id }) => id === selectedId);
    if (!record) {
      setError("Choose a record first.");
      return;
    }
    if (total >= labelsPerPage) {
      setError(
        "The sheet is full. Remove a label or reduce copies before adding another.",
      );
      return;
    }
    try {
      recordUrl(record.kind, record.id, canonicalOrigin);
    } catch {
      setError(
        canonicalOrigin
          ? "The selected record reference is invalid."
          : "Florabase has no canonical public address configured; labels cannot be created.",
      );
      return;
    }
    setEntries((current) => {
      const exists = current.some(
        (entry) => labelKey(entry.record) === labelKey(record),
      );
      return exists
        ? current.map((entry) =>
            labelKey(entry.record) === labelKey(record)
              ? { ...entry, copies: entry.copies + 1 }
              : entry,
          )
        : [...current, { record, copies: 1 }];
    });
    setError(null);
    setMessage(
      `${labelTypeNames[kind]} label added. ${String(total + 1)} of 36 spaces used.`,
    );
  }

  return (
    <section className="labels-workspace" aria-labelledby="labels-heading">
      <header className="page-header">
        <div>
          <p className="eyebrow">Collection tools</p>
          <h2 id="labels-heading">Labels</h2>
          <p>Prepare an A4 sheet of 50 × 30 mm lookup labels.</p>
        </div>
        <button
          type="button"
          disabled={!total}
          onClick={() => {
            try {
              window.print();
            } catch {
              setError(
                "Could not open browser printing. Use your browser’s Print command.",
              );
            }
          }}
        >
          Print sheet
        </button>
      </header>
      <p className="notice">
        Print at 100% / Actual size. Turn off Fit to page and browser headers
        and footers. Use A4 portrait with the stylesheet’s margins. Measure one
        label: 50 mm wide × 30 mm high.
      </p>
      <p className="field-help">
        Sheet edits are discarded when you leave or refresh. QR links use the
        configured Florabase address; the scanning device must be able to reach
        it and sign in normally.
      </p>
      {!canonicalOrigin && (
        <p className="notice" role="alert">
          Florabase has no canonical public address configured; labels cannot be
          created.
        </p>
      )}
      <div className="label-composer">
        <section
          className="label-controls"
          aria-labelledby="label-selection-heading"
        >
          <h3 id="label-selection-heading">Add records</h3>
          <label>
            Record type
            <select
              ref={recordType}
              value={kind}
              onChange={(event) => {
                const next = event.target.value;
                if (!isLabelKind(next)) return;
                setKind(next);
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
            <p role="status">Loading records…</p>
          ) : records.status === "error" ? (
            <div className="notice notice--error" role="alert">
              <p>Could not load records.</p>
              <button
                type="button"
                onClick={() => {
                  setRecords({ status: "loading" });
                  setRetry((value) => value + 1);
                }}
              >
                Retry
              </button>
            </div>
          ) : records.records.length === 0 ? (
            <p>No {labelTypeNames[kind].toLowerCase()} records available.</p>
          ) : (
            <ReferencePicker
              label="Record"
              choices={records.records.map((record) => ({
                id: record.id,
                label: `${record.botanicalName} · ${record.context ?? "Unlabelled"} · ${record.id}`,
              }))}
              value={selectedId}
              onChange={setSelectedId}
            />
          )}
          <button
            type="button"
            className="button--secondary"
            disabled={records.status !== "ready" || !selectedId}
            onClick={addLabel}
          >
            Add label
          </button>
          {error && (
            <p className="notice notice--error" role="alert">
              {error}
            </p>
          )}
          <p className="sr-only" role="status">
            {message}
          </p>
          <h3>Sheet entries · {String(total)} / 36</h3>
          {entries.length === 0 ? (
            <p>Choose records to start your sheet.</p>
          ) : (
            <ul className="label-entries">
              {entries.map((entry) => {
                const key = labelKey(entry.record);
                const description = `${labelTypeNames[entry.record.kind]}: ${entry.record.botanicalName}${entry.record.context ? ` · ${entry.record.context}` : ""}`;
                return (
                  <li key={key}>
                    <a
                      href={recordUrl(
                        entry.record.kind,
                        entry.record.id,
                        canonicalOrigin,
                      )}
                    >
                      {entry.record.botanicalName}
                    </a>
                    <small>
                      {labelTypeNames[entry.record.kind]}
                      {entry.record.context && ` · ${entry.record.context}`}
                    </small>
                    <div className="label-entry-actions">
                      <label>
                        Copies
                        <input
                          aria-label={`Copies for ${description}`}
                          type="number"
                          min="1"
                          max={labelsPerPage - total + entry.copies}
                          step="1"
                          value={entry.copies}
                          onChange={(event) => {
                            const count = Number(event.target.value);
                            if (
                              !Number.isInteger(count) ||
                              count < 1 ||
                              total - entry.copies + count > labelsPerPage
                            ) {
                              setError(
                                "Copies must be a whole number of at least 1; the sheet holds 36 labels.",
                              );
                              return;
                            }
                            setEntries((current) =>
                              current.map((item) =>
                                labelKey(item.record) === key
                                  ? { ...item, copies: count }
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
                          setMessage("Label removed.");
                          recordType.current?.focus();
                        }}
                      >
                        Remove
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
        <section
          className="label-preview"
          aria-labelledby="label-preview-heading"
        >
          <h3 id="label-preview-heading">Sheet preview</h3>
          <p className="field-help">
            4 columns × 9 rows when printed. Labels fill left to right from the
            top; use a fresh sheet.
          </p>
          {total ? (
            <LabelSheet pages={pages} canonicalOrigin={canonicalOrigin} />
          ) : (
            <div className="label-empty">
              <p>Your label sheet is empty.</p>
              <p>
                Botanical name, record type, optional record label, and QR will
                appear here.
              </p>
            </div>
          )}
        </section>
      </div>
      {createPortal(
        <div className="label-print-root">
          <LabelSheet pages={pages} canonicalOrigin={canonicalOrigin} />
        </div>,
        document.body,
      )}
    </section>
  );
}
