import type { components } from "../api/schema";
import { requestJson } from "../auth/api";

export type BotanicalProfilePut = components["schemas"]["BotanicalProfilePut"];
export type BotanicalProfileResponse =
  components["schemas"]["BotanicalProfileResponse"];
export type BotanicalNativeRangeResponse =
  components["schemas"]["BotanicalNativeRangeResponse"];

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

function nativeRangesPath(botanicalIdentityId: string): string {
  return `${profilePath(botanicalIdentityId)}/native-ranges`;
}

export function listBotanicalNativeRanges(
  botanicalIdentityId: string,
  signal?: AbortSignal,
): Promise<BotanicalNativeRangeResponse[]> {
  return requestJson(nativeRangesPath(botanicalIdentityId), { signal });
}

export function addBotanicalNativeRange(
  botanicalIdentityId: string,
  geographicPlaceId: string,
  csrfToken: string,
): Promise<BotanicalNativeRangeResponse> {
  return requestJson(nativeRangesPath(botanicalIdentityId), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
    },
    body: JSON.stringify({ geographic_place_id: geographicPlaceId }),
  });
}

export function removeBotanicalNativeRange(
  botanicalIdentityId: string,
  geographicPlaceId: string,
  csrfToken: string,
): Promise<void> {
  return requestJson(
    `${nativeRangesPath(botanicalIdentityId)}/${encodeURIComponent(geographicPlaceId)}`,
    {
      method: "DELETE",
      headers: { "X-CSRF-Token": csrfToken },
    },
  );
}
