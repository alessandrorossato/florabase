import { requestJson } from "../auth/api";

export const recordTypes = [
  { id: "botanical-identities", label: "Botanical identities" },
  { id: "suppliers", label: "Suppliers" },
  { id: "locations", label: "Locations" },
  { id: "seed-lots", label: "Seed lots" },
  { id: "plants", label: "Plants" },
  { id: "plant-groups", label: "Plant groups" },
] as const;

export type RecordType = (typeof recordTypes)[number]["id"];
export type PreviewOutcome =
  | "ready"
  | "already_exists"
  | "needs_choice"
  | "invalid"
  | "unresolved_reference"
  | "ambiguous_reference"
  | "conflict";

export interface PreviewRow {
  row_number: number;
  record: string;
  outcome: PreviewOutcome;
  messages: string[];
  references: string[];
  normalized: string[];
  hard_blocker: boolean;
  options: DecisionOption[];
}

export interface DecisionOption {
  key: string;
  action:
    "use_existing" | "update_existing" | "create_separate" | "choose_reference";
  candidate_id: string;
  label: string;
  details: string;
  changes: { field: string; before: string; after: string }[];
  token: string;
}

export interface FieldGuideItem {
  field: string;
  meaning: string;
  required: boolean;
  accepted: string;
  example: string;
  notes: string;
}

export interface ImportPreview {
  rows: PreviewRow[];
  ready: number;
  already_exists: number;
  needs_attention: number;
  confirmation_token: string;
}

export interface ImportResult {
  created: number;
  already_exists: number;
  updated: number;
}

export function getFieldGuide(
  kind: RecordType,
): Promise<{ fields: FieldGuideItem[] }> {
  return requestJson(`/api/v1/imports/formats/${kind}`);
}

export function previewImport(
  kind: RecordType,
  file: File,
): Promise<ImportPreview> {
  return requestJson(`/api/v1/imports/${kind}/preview`, {
    method: "POST",
    headers: { "Content-Type": "text/csv" },
    body: file,
  });
}

function encodeFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result !== "string") {
        reject(new Error("Could not read CSV"));
        return;
      }
      resolve(reader.result.slice(reader.result.indexOf(",") + 1));
    };
    reader.onerror = () => {
      reject(new Error("Could not read CSV"));
    };
    reader.readAsDataURL(file);
  });
}

export async function applyImport(
  kind: RecordType,
  file: File,
  confirmationToken: string,
  csrfToken: string,
  decisions: Record<string, Record<string, string> | undefined>,
): Promise<ImportResult> {
  const csv_base64 = await encodeFile(file);
  return requestJson(`/api/v1/imports/${kind}/apply`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
      "X-Import-Confirmation": confirmationToken,
    },
    body: JSON.stringify({ csv_base64, decisions }),
  });
}
