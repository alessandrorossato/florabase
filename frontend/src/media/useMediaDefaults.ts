import { useEffect, useState } from "react";
import { useAuth } from "../auth/context";
import {
  getApplicationSettings,
  type ApplicationSettings,
} from "../settings/api";

/**
 * Installation-wide media defaults from Settings → Media. Null until loaded, or when loading
 * fails: forms then fall back to the built-in defaults (local copy pre-checked, no prefill).
 */
export function useMediaDefaults(enabled = true): ApplicationSettings | null {
  const { capability } = useAuth();
  const [settings, setSettings] = useState<ApplicationSettings | null>(null);
  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    getApplicationSettings(capability, controller.signal)
      .then(setSettings)
      .catch(() => {
        // Defaults are a convenience; a failed read must never block saving media.
      });
    return () => {
      controller.abort();
    };
  }, [capability, enabled]);
  return settings;
}
