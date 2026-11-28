export interface DemoReadOnlyDetail {
  code: "demo_read_only";
  message: string;
}

type Listener = (message: string) => void;

const listeners = new Set<Listener>();

export function extractDemoReadOnlyMessage(body: unknown): string | null {
  if (typeof body !== "object" || body === null) return null;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail !== "object" || detail === null) return null;
  const candidate = detail as { code?: unknown; message?: unknown };
  if (
    candidate.code === "demo_read_only" &&
    typeof candidate.message === "string" &&
    candidate.message.trim().length > 0
  ) {
    return candidate.message;
  }
  return null;
}

export function notifyDemoReadOnlyBlocked(message: string): void {
  for (const listener of listeners) {
    listener(message);
  }
}

export function subscribeDemoReadOnlyBlocked(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
