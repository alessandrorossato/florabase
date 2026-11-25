import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { App } from "../App";
import {
  clearNativeBearerToken,
  configureNativeBearerTransport,
  resetAuthTransport,
} from "../auth/transport";
import type { HttpGetFn } from "./healthProbe";
import { NativeServerOnboarding } from "./NativeServerOnboarding";
import { createServerUrlStore, type ServerUrlStore } from "./preferences";
import { isNativeDebugBuild } from "./runtime";
import { createSecureTokenStore, type SecureTokenStore } from "./secureToken";
import { validateServerUrl } from "./serverUrl";
import {
  checkServerCompatibility,
  onboardingErrorHeading,
  type OnboardingError,
  type SystemInfo,
} from "./systemInfo";

type NativeShellState =
  | { status: "booting" }
  | {
      status: "onboarding";
      initialServerUrl: string | null;
      initialError: OnboardingError | null;
    }
  | {
      status: "ready";
      serverUrl: string;
      info: SystemInfo;
      sessionKey: number;
    };

export interface NativeAppProps {
  allowDebugHttp?: boolean;
  urlStore?: ServerUrlStore;
  tokenStore?: SecureTokenStore;
  httpGet?: HttpGetFn;
  appVersion?: string;
}

export function NativeApp({
  allowDebugHttp = isNativeDebugBuild(),
  urlStore,
  tokenStore,
  httpGet,
  appVersion,
}: NativeAppProps) {
  const resolvedUrlStore = useMemo<ServerUrlStore>(
    () => urlStore ?? createServerUrlStore(),
    [urlStore],
  );
  const resolvedTokenStore = useMemo<SecureTokenStore>(
    () => tokenStore ?? createSecureTokenStore(),
    [tokenStore],
  );
  const [shellState, setShellState] = useState<NativeShellState>({
    status: "booting",
  });
  const activeServerUrlRef = useRef<string | null>(null);

  const handleChangeServer = useCallback((currentUrl: string) => {
    void clearNativeBearerToken().finally(() => {
      resetAuthTransport();
      setShellState({
        status: "onboarding",
        initialServerUrl: currentUrl,
        initialError: null,
      });
    });
  }, []);

  const activateServer = useCallback(
    async (serverUrl: string, info: SystemInfo) => {
      if (
        activeServerUrlRef.current !== null &&
        activeServerUrlRef.current !== serverUrl
      ) {
        await resolvedTokenStore.clear();
      }
      activeServerUrlRef.current = serverUrl;
      const storedToken = await resolvedTokenStore.get();
      configureNativeBearerTransport({
        serverUrl,
        initialToken: storedToken,
        saveToken: (token) => resolvedTokenStore.set(token),
        clearToken: () => resolvedTokenStore.clear(),
        getDefaultDeviceLabel: () => resolvedTokenStore.getDeviceLabel(),
        onChangeServer: () => {
          handleChangeServer(serverUrl);
        },
      });
      setShellState((previous) => ({
        status: "ready",
        serverUrl,
        info,
        sessionKey: previous.status === "ready" ? previous.sessionKey + 1 : 1,
      }));
    },
    [handleChangeServer, resolvedTokenStore],
  );

  useEffect(() => {
    const controller = new AbortController();
    const isAborted = (): boolean => controller.signal.aborted;
    async function boot() {
      const saved = await resolvedUrlStore.load();
      if (isAborted()) return;
      activeServerUrlRef.current = saved;
      if (saved === null) {
        setShellState({
          status: "onboarding",
          initialServerUrl: null,
          initialError: null,
        });
        return;
      }

      const validation = validateServerUrl(saved, { allowDebugHttp });
      if (!validation.ok) {
        setShellState({
          status: "onboarding",
          initialServerUrl: saved,
          initialError: {
            category: "invalid-url",
            heading: onboardingErrorHeading("invalid-url"),
            message: validation.error,
          },
        });
        return;
      }

      const compatibility = await checkServerCompatibility(
        validation.normalizedUrl,
        {
          httpGet,
          allowDebugHttp,
          appVersion,
        },
      );
      if (isAborted()) return;
      if (!compatibility.ok) {
        setShellState({
          status: "onboarding",
          initialServerUrl: validation.normalizedUrl,
          initialError: {
            category: compatibility.kind,
            heading: onboardingErrorHeading(compatibility.kind),
            message: compatibility.message,
          },
        });
        return;
      }

      await activateServer(compatibility.serverUrl, compatibility.info);
    }

    void boot();
    return () => {
      controller.abort();
      resetAuthTransport();
    };
  }, [activateServer, allowDebugHttp, appVersion, httpGet, resolvedUrlStore]);

  if (shellState.status === "booting") {
    return (
      <main className="mobile-onboarding">
        <section aria-labelledby="mobile-boot-title" className="card">
          <p className="eyebrow">Florabase Android</p>
          <h1 id="mobile-boot-title">Florabase</h1>
          <p aria-live="polite" className="notice">
            Connecting to your server…
          </p>
        </section>
      </main>
    );
  }

  if (shellState.status === "onboarding") {
    return (
      <NativeServerOnboarding
        allowDebugHttp={allowDebugHttp}
        store={resolvedUrlStore}
        httpGet={httpGet}
        appVersion={appVersion}
        initialServerUrl={shellState.initialServerUrl}
        initialError={shellState.initialError}
        onConnected={(serverUrl, info) => {
          void activateServer(serverUrl, info);
        }}
      />
    );
  }

  return (
    <App key={`${shellState.serverUrl}#${String(shellState.sessionKey)}`} />
  );
}
