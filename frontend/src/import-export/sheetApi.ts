import type { components } from "../api/schema";
import { requestJson, type ProtectedRequestCapability } from "../auth/api";

type Schemas = components["schemas"];
export type SheetRecordType = Schemas["Body_inspectSheetImport"]["record_type"];
export type SheetField = Schemas["SheetImportField"];
export type SheetInspect = Schemas["SheetImportInspectResponse"];
export type SheetPreview = Schemas["SheetImportPreviewResponse"];
export type SheetApplyResult = Schemas["SheetImportApplyResponse"];
export type SupplierKind = Schemas["SupplierKind"];
export type SheetMappingColumns = Record<string, SheetField | null>;

// `options` travels as a JSON form field, so OpenAPI does not describe it; this mirrors
// backend `import_wizard/schemas.py` (SheetImportOptions and its choice models).
export interface SheetIdentityChoice {
  action: "use_existing" | "create";
  existing_id?: string | null;
  scientific_name?: string | null;
  cultivar_name?: string | null;
  common_name?: string | null;
}
export interface SheetLocationChoice {
  action: "use_existing" | "create" | "skip";
  existing_id?: string | null;
  name?: string | null;
  parent_id?: string | null;
}
export interface SheetSupplierChoice {
  action: "use_existing" | "create" | "skip";
  existing_id?: string | null;
  name?: string | null;
  kind?: SupplierKind;
}
export interface SheetChoices {
  identities: Partial<Record<string, SheetIdentityChoice>>;
  locations: Partial<Record<string, SheetLocationChoice>>;
  suppliers: Partial<Record<string, SheetSupplierChoice>>;
}
export interface SheetOptions {
  record_type: SheetRecordType;
  sheet_name: string | null;
  header_row: number | null;
  mapping: { columns: SheetMappingColumns; append_unmapped_to_notes: boolean };
  choices: SheetChoices;
}

export function inspectSheet(
  file: File,
  params: {
    recordType: SheetRecordType;
    sheetName: string | null;
    headerRow: number | null;
  },
  capability: ProtectedRequestCapability,
): Promise<SheetInspect> {
  const body = new FormData();
  body.set("file", file);
  body.set("record_type", params.recordType);
  if (params.sheetName) body.set("sheet_name", params.sheetName);
  if (params.headerRow) body.set("header_row", String(params.headerRow));
  return requestJson("/api/v1/sheet-imports/inspect", {
    capability,
    method: "POST",
    body,
  });
}

function optionsBody(file: File, options: SheetOptions): FormData {
  const body = new FormData();
  body.set("file", file);
  body.set("options", JSON.stringify(options));
  return body;
}

export function previewSheet(
  file: File,
  options: SheetOptions,
  capability: ProtectedRequestCapability,
): Promise<SheetPreview> {
  return requestJson("/api/v1/sheet-imports/preview", {
    capability,
    method: "POST",
    body: optionsBody(file, options),
  });
}

export function applySheet(
  file: File,
  options: SheetOptions,
  confirmationToken: string,
  csrfToken: string,
  capability: ProtectedRequestCapability,
): Promise<SheetApplyResult> {
  return requestJson("/api/v1/sheet-imports/apply", {
    capability,
    method: "POST",
    headers: {
      "X-CSRF-Token": csrfToken,
      "X-Import-Confirmation": confirmationToken,
    },
    body: optionsBody(file, options),
  });
}

// The last mapping for the same header set stays in this browser only (owner decision 4).
function mappingKey(recordType: SheetRecordType, headers: string[]): string {
  const normalized = headers.map((header) => header.trim().toLowerCase());
  return `florabase.sheet-import.mapping.${recordType}.${JSON.stringify(normalized)}`;
}

export function rememberedMapping(
  recordType: SheetRecordType,
  headers: string[],
): SheetMappingColumns | null {
  try {
    const raw = window.localStorage.getItem(mappingKey(recordType, headers));
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    return parsed && typeof parsed === "object"
      ? (parsed as SheetMappingColumns)
      : null;
  } catch {
    return null;
  }
}

export function rememberMapping(
  recordType: SheetRecordType,
  headers: string[],
  columns: SheetMappingColumns,
): void {
  try {
    window.localStorage.setItem(
      mappingKey(recordType, headers),
      JSON.stringify(columns),
    );
  } catch {
    // Storage may be unavailable (private mode); the wizard still works.
  }
}
