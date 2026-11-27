/**
 * Lightweight event bus notifying native-only subscribers when a Schedule
 * activity is created, updated, completed, or cancelled. Inert on web/PWA.
 */

const listeners = new Set<() => void>();

export function onScheduleChanged(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function notifyScheduleChanged(): void {
  for (const listener of [...listeners]) {
    try {
      listener();
    } catch {
      // Ignore subscriber errors so Schedule mutations never fail.
    }
  }
}
