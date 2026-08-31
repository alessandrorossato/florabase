import type { components } from "../api/schema";
import { ApiError, requestJson } from "../auth/api";

export type BotanicalIdentityCreate =
  components["schemas"]["BotanicalIdentityCreate"];
export type BotanicalIdentityResponse =
  components["schemas"]["BotanicalIdentityResponse"];
type HTTPValidationError = components["schemas"]["HTTPValidationError"];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function conflictExistingId(error: ApiError): string | null {
  if (!isRecord(error.body) || !isRecord(error.body.detail)) return null;
  const existingId = error.body.detail.existing_id;
  return typeof existingId === "string" ? existingId : null;
}

function fieldLabel(location: (string | number)[]): string | null {
  const field = location.at(-1);
  if (field === "scientific_name") return "Scientific name";
  if (field === "cultivar_name") return "Cultivar";
  if (field === "common_name") return "Common name";
  return null;
}

export function validationMessages(error: ApiError): string[] {
  if (!isRecord(error.body) || !Array.isArray(error.body.detail)) {
    return ["Check the botanical identity details and try again."];
  }
  const detail = error.body as HTTPValidationError;
  const messages = (detail.detail ?? []).map((item) => {
    const label = fieldLabel(item.loc);
    if (item.type === "extra_forbidden") {
      return "The form included a field Florabase does not accept.";
    }
    if (item.msg.toLowerCase().includes("not be blank")) {
      return `${label ?? "This field"} cannot be blank.`;
    }
    if (item.msg.toLowerCase().includes("control character")) {
      return `${label ?? "This field"} contains an unsupported character.`;
    }
    if (item.type === "string_too_long") {
      return `${label ?? "This field"} is too long.`;
    }
    return label
      ? `Check ${label.toLowerCase()} and try again.`
      : "Check the botanical identity details and try again.";
  });
  return messages.length > 0
    ? Array.from(new Set(messages))
    : ["Check the botanical identity details and try again."];
}

export function createBotanicalIdentity(
  payload: BotanicalIdentityCreate,
  csrfToken: string,
): Promise<BotanicalIdentityResponse> {
  return requestJson("/api/v1/botanical-identities", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
    },
    body: JSON.stringify(payload),
  });
}

export function listBotanicalIdentities(
  signal?: AbortSignal,
): Promise<BotanicalIdentityResponse[]> {
  return requestJson("/api/v1/botanical-identities", { signal });
}

export function getBotanicalIdentity(
  botanicalIdentityId: string,
): Promise<BotanicalIdentityResponse> {
  return requestJson(
    `/api/v1/botanical-identities/${encodeURIComponent(botanicalIdentityId)}`,
  );
}
