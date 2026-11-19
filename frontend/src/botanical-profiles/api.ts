import type { components } from "../api/schema";
import { requestJson, type ProtectedRequestCapability } from "../auth/api";

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
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<BotanicalProfileResponse> {
  return requestJson(profilePath(botanicalIdentityId), { capability, signal });
}

export function putBotanicalProfile(
  botanicalIdentityId: string,
  payload: BotanicalProfilePut,
  csrfToken: string,
  capability: ProtectedRequestCapability,
): Promise<BotanicalProfileResponse | undefined> {
  return requestJson(profilePath(botanicalIdentityId), {
    capability,
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
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<BotanicalNativeRangeResponse[]> {
  return requestJson(nativeRangesPath(botanicalIdentityId), {
    capability,
    signal,
  });
}

export function addBotanicalNativeRange(
  botanicalIdentityId: string,
  geographicPlaceId: string,
  csrfToken: string,
  capability: ProtectedRequestCapability,
): Promise<BotanicalNativeRangeResponse> {
  return requestJson(nativeRangesPath(botanicalIdentityId), {
    capability,
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
  capability: ProtectedRequestCapability,
): Promise<void> {
  return requestJson(
    `${nativeRangesPath(botanicalIdentityId)}/${encodeURIComponent(geographicPlaceId)}`,
    {
      capability,
      method: "DELETE",
      headers: { "X-CSRF-Token": csrfToken },
    },
  );
}
