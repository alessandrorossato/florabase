import { useState } from "react";

import { ActionButton } from "../components/Action";
import {
  ApiError,
  downloadProtectedFile,
  isExpectedAuthCancellation,
  NativeFileActionUnavailableError,
  requestJson,
} from "../auth/api";
import { useAuth } from "../auth/context";
import type { components } from "../api/schema";

type FullExportSummary = components["schemas"]["FullExportSummary"];

const BACKUP_GUIDE_URL =
  "https://github.com/alessandrorossato/florabase/blob/main/docs/operate/backup-restore.md";

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024)
    return `${String(Math.max(1, Math.ceil(bytes / 1024)))} KB`;
  if (bytes < 1024 * 1024 * 1024)
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

/** DATA-EXPORT-001: one ZIP with every collection record as CSV, photos optional. */
export function FullExportCard() {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const demo =
    auth.state.status === "authenticated" && auth.state.session.demo_readonly;
  const [includeFiles, setIncludeFiles] = useState(false);
  const [summary, setSummary] = useState<FullExportSummary | null>(null);
  const [summaryError, setSummaryError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const filesAllowed = !demo && summary?.files_allowed !== false;

  async function loadSummary() {
    if (summary || !authorized) return;
    setSummaryError(false);
    try {
      setSummary(
        await requestJson<FullExportSummary>("/api/v1/exports/full/summary", {
          capability,
        }),
      );
    } catch (caught: unknown) {
      if (isExpectedAuthCancellation(caught)) return;
      setSummaryError(true);
    }
  }

  async function download() {
    if (busy || !authorized) return;
    setBusy(true);
    setError(null);
    try {
      const files = includeFiles && filesAllowed;
      await downloadProtectedFile({
        path: `/api/v1/exports/full.zip?include_files=${String(files)}`,
        capability,
        fallbackFilename: "florabase-export.zip",
        accept: "application/zip",
      });
    } catch (caught: unknown) {
      if (isExpectedAuthCancellation(caught)) return;
      if (caught instanceof ApiError && caught.status === 401) {
        sessionExpired();
        return;
      }
      if (caught instanceof NativeFileActionUnavailableError) {
        setError(caught.message);
        return;
      }
      setError("Could not download the export. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="card import-workspace__primary"
      aria-labelledby="full-export-heading"
    >
      <h3 id="full-export-heading">Export all data</h3>
      <p>
        Download every collection record as a ZIP of CSV files, one per record
        type, with a manifest and a README. It opens in any spreadsheet and
        stays readable without Florabase.
      </p>
      {filesAllowed ? (
        <div className="field">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={includeFiles}
              disabled={busy}
              onChange={(event) => {
                const checked = event.currentTarget.checked;
                setIncludeFiles(checked);
                if (checked) void loadSummary();
              }}
            />
            Include photos and files
          </label>
          {includeFiles && summary && (
            <p className="field-help" role="status">
              {summary.attachments === 0
                ? "No photos stored yet."
                : `${String(summary.attachments)} ${summary.attachments === 1 ? "file" : "files"}, about ${formatBytes(summary.attachment_bytes)} in total.`}
            </p>
          )}
          {includeFiles && summaryError && (
            <p className="field-help">Size estimate unavailable.</p>
          )}
        </div>
      ) : (
        <p className="field-help">
          Photos are not included in the public demo.
        </p>
      )}
      <div className="actions">
        <ActionButton
          icon="download"
          disabled={busy || !authorized}
          onClick={() => void download()}
        >
          {busy ? "Preparing export…" : "Export all data"}
        </ActionButton>
      </div>
      {error && (
        <p className="notice notice--error" role="alert">
          {error}
        </p>
      )}
      <p>
        <strong>This is not a backup.</strong> It cannot be imported back. To
        protect or move your installation, use{" "}
        <a href={BACKUP_GUIDE_URL} target="_blank" rel="noreferrer">
          backup and restore
        </a>
        .
      </p>
    </section>
  );
}
