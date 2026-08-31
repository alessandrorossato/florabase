import type { components } from "../api/schema";
import { requestJson } from "../auth/api";

export type BotanicalProfilePut = components["schemas"]["BotanicalProfilePut"];
export type BotanicalProfileResponse =
  components["schemas"]["BotanicalProfileResponse"];

function profilePath(botanicalIdentityId: string): string {
  return `/api/v1/botanical-identities/${encodeURIComponent(botanicalIdentityId)}/profile`;
}

export function getBotanicalProfile(
  botanicalIdentityId: string,
  signal?: AbortSignal,
): Promise<BotanicalProfileResponse> {
  return requestJson(profilePath(botanicalIdentityId), { signal });
}

export function putBotanicalProfile(
  botanicalIdentityId: string,
  payload: BotanicalProfilePut,
  csrfToken: string,
): Promise<BotanicalProfileResponse | undefined> {
  return requestJson(profilePath(botanicalIdentityId), {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
    },
    body: JSON.stringify(payload),
  });
}
