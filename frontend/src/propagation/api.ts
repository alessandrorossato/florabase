import type { components } from "../api/schema";
import {
  ApiError,
  requestJson,
  type ProtectedRequestCapability,
} from "../auth/api";

export type SowingPotOnCreate = components["schemas"]["SowingPotOnCreate"];
export type SowingPotOnResponse = components["schemas"]["SowingPotOnResponse"];
export type PlantGroupExtractBatchCreate =
  components["schemas"]["PlantGroupExtractBatchCreate"];
export type PlantGroupExtractBatchResponse =
  components["schemas"]["PlantGroupExtractBatchResponse"];

export const MAX_BATCH_COUNT = 200;
export const MAX_LABEL_LENGTH = 255;
export const COUNTER_PLACEHOLDER = "{n}";

const CONTROL_CHAR_PATTERN = /\p{Cc}/u;

export interface ExpandedLabelResult {
  labels: (string | null)[];
  error?: string;
  duplicateWarning: boolean;
}

export interface LabelPreviewSample {
  head: string[];
  tail: string | null;
  omitted: number;
  first: string | null;
  last: string | null;
}

export function defaultCounterPadding(count: number, counterStart = 1): number {
  const lastNumber = Math.max(0, counterStart) + Math.max(1, count) - 1;
  return String(lastNumber).length;
}

export function normalizeSingleLineLabel(value: string): {
  normalized: string | null;
  error?: string;
} {
  const normalized = value.trim().replace(/\s+/g, " ");
  if (!normalized) return { normalized: null };
  if (CONTROL_CHAR_PATTERN.test(normalized)) {
    return {
      normalized: null,
      error: "Label pattern must not contain control characters.",
    };
  }
  return { normalized };
}

export function expandLabelPattern(
  pattern: string,
  count: number,
  counterStart = 1,
  counterPadding: number | null = null,
): ExpandedLabelResult {
  if (!Number.isInteger(count) || count < 1 || count > MAX_BATCH_COUNT) {
    return {
      labels: [],
      error: `Count must be a whole number between 1 and ${String(MAX_BATCH_COUNT)}.`,
      duplicateWarning: false,
    };
  }
  if (!Number.isInteger(counterStart) || counterStart < 0) {
    return {
      labels: [],
      error: "Counter start must be zero or a positive whole number.",
      duplicateWarning: false,
    };
  }
  if (
    counterPadding !== null &&
    (!Number.isInteger(counterPadding) ||
      counterPadding < 0 ||
      counterPadding > MAX_LABEL_LENGTH)
  ) {
    return {
      labels: [],
      error: "Counter padding must be a whole number between 0 and 255.",
      duplicateWarning: false,
    };
  }
  const { normalized, error } = normalizeSingleLineLabel(pattern);
  if (error) {
    return { labels: [], error, duplicateWarning: false };
  }
  if (normalized === null) {
    return {
      labels: Array.from({ length: count }, () => null),
      duplicateWarning: false,
    };
  }
  const padding = counterPadding ?? defaultCounterPadding(count, counterStart);
  const labels: string[] = [];
  for (let offset = 0; offset < count; offset += 1) {
    const number = counterStart + offset;
    const formatted = String(number).padStart(padding, "0");
    const expanded = normalized.replaceAll(COUNTER_PLACEHOLDER, formatted);
    if (expanded.length > MAX_LABEL_LENGTH) {
      return {
        labels: [],
        error: `Expanded label "${expanded.slice(0, 32)}…" exceeds ${String(MAX_LABEL_LENGTH)} characters.`,
        duplicateWarning: false,
      };
    }
    labels.push(expanded);
  }
  return {
    labels,
    duplicateWarning: count > 1 && !normalized.includes(COUNTER_PLACEHOLDER),
  };
}

export function previewLabelSample(
  labels: (string | null)[],
): LabelPreviewSample {
  const nonEmpty = labels.filter((value): value is string => value !== null);
  if (nonEmpty.length === 0) {
    return { head: [], tail: null, omitted: 0, first: null, last: null };
  }
  const first = nonEmpty[0] ?? null;
  const last = nonEmpty[nonEmpty.length - 1] ?? null;
  if (nonEmpty.length <= 4) {
    return { head: nonEmpty, tail: null, omitted: 0, first, last };
  }
  return {
    head: nonEmpty.slice(0, 3),
    tail: last,
    omitted: nonEmpty.length - 4,
    first,
    last,
  };
}

export function potOnSowing(
  sowingId: string,
  payload: SowingPotOnCreate,
  csrfToken: string,
  capability: ProtectedRequestCapability,
): Promise<SowingPotOnResponse> {
  return requestJson(`/api/v1/sowings/${encodeURIComponent(sowingId)}/pot-on`, {
    capability,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
    },
    body: JSON.stringify(payload),
  });
}

export function extractPlantsFromGroup(
  groupId: string,
  payload: PlantGroupExtractBatchCreate,
  csrfToken: string,
  capability: ProtectedRequestCapability,
): Promise<PlantGroupExtractBatchResponse> {
  return requestJson(
    `/api/v1/plant-groups/${encodeURIComponent(groupId)}/extract-batch`,
    {
      capability,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify(payload),
    },
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function propagationErrorDetail(error: ApiError): {
  code?: string;
  message?: string;
} {
  if (!isRecord(error.body)) return {};
  const detail = error.body.detail;
  if (isRecord(detail)) {
    return {
      code: typeof detail.code === "string" ? detail.code : undefined,
      message: typeof detail.message === "string" ? detail.message : undefined,
    };
  }
  if (typeof detail === "string") {
    return { message: detail };
  }
  return {};
}
