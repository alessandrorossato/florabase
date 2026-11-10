import type { components } from "../../api/schema";
import { ApiError, requestJson } from "../../auth/api";
import { useEffect, useState } from "react";

type Schema = components["schemas"];
export type Lot = Schema["VegetativeLotResponse"];
export type LotDetail = Schema["VegetativeLotDetail"];
export type Attempt = Schema["PropagationAttemptResponse"];
export type AttemptDetail = Schema["PropagationAttemptDetail"];
export type AttemptSummary = Schema["CuttingPropagationSummary"];
export type ReceiptEligibility = Schema["PropagationReversalEligibility"];
export type CuttingQuantity = Schema["CuttingQuantity"];
export type LotWrite = Schema["VegetativeLotCreate"];
export type AttemptWrite = Schema["AttemptCreate"];
export type RootingObservation = Schema["RootingObservationResponse"];
export const lots = "/api/v1/vegetative-lots";
export const attempts = "/api/v1/propagation-attempts";

type Resource<T> =
  | { state: "loading" }
  | { state: "ready"; value: T }
  | { state: "error"; error: unknown };

export function useCuttingData<T>(path: string) {
  const [version, setVersion] = useState(0);
  const key = `${path}:${String(version)}`;
  const [result, setResult] = useState<{ key: string; data: Resource<T> }>();
  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    void requestJson<T>(path, { signal: controller.signal }).then(
      (value) => {
        if (!controller.signal.aborted)
          setResult({ key, data: { state: "ready", value } });
      },
      (error: unknown) => {
        if (!controller.signal.aborted)
          setResult({ key, data: { state: "error", error } });
      },
    );
    return () => {
      controller.abort();
    };
  }, [key, path]);
  const data: Resource<T> =
    result?.key === key ? result.data : { state: "loading" };
  return [
    data,
    () => {
      setVersion((current) => current + 1);
    },
  ] as const;
}

export function saveCutting<T>(
  path: string,
  body: object,
  token: string,
  method = "POST",
): Promise<T> {
  return requestJson(path, {
    method,
    headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
    body: JSON.stringify(body),
  });
}

export function cuttingError(error: unknown): string {
  if (error instanceof ApiError) {
    const body = error.body as
      { detail?: { message?: string } | { msg?: string }[] } | undefined;
    const detail = body?.detail;
    if (Array.isArray(detail)) {
      const messages = detail.map((item) => item.msg).filter(Boolean);
      if (messages.length) return messages.join(" ");
    } else if (detail?.message) return detail.message;
    if (error.status === 404)
      return "The requested cutting record could not be found.";
  }
  return "Florabase could not complete the request. Please try again.";
}

export const materialLabels = {
  stem_cutting: "Stem cutting",
  leaf_cutting: "Leaf cutting",
  root_cutting: "Root cutting",
} as const;

export const sourceLabels = {
  collection_produced: "From the collection",
  purchased: "Purchased",
  gift_exchange: "Gift or exchange",
  self_collected: "Self-collected",
  other: "Other",
  unknown: "Unknown",
} as const;

export function countLabel(count?: CuttingQuantity | null) {
  return count
    ? `${count.is_approximate ? "About " : ""}${String(count.value)}`
    : "Unknown";
}

export function rootingLabel(attempt: Attempt) {
  if (attempt.rooted_count == null)
    return attempt.lifecycle === "active"
      ? "Rooting pending"
      : "Rooted count unrecorded";
  const count = `${String(attempt.rooted_count)} rooted`;
  if (!attempt.quantity) return `${count} · starting count unknown`;
  return `${count} of ${countLabel(attempt.quantity).toLowerCase()}${
    attempt.rooting_rate_percent == null
      ? ""
      : ` (${new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(attempt.rooting_rate_percent)}%)`
  }`;
}
