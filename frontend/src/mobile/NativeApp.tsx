import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { App } from "../App";
import { useAuth } from "../auth/context";
import {
  clearNativeBearerToken,
  configureNativeBearerTransport,
  resetAuthTransport,
} from "../auth/transport";
import {
  applyMapRuntimeConfig,
  resetMapRuntimeConfig,
} from "../provenance-map/config";
import { onScheduleChanged } from "../schedule/changes";
import {
  cleanupNativeSharedCache,
  registerNativeImageViewerHandler,
  type NativeImageViewerRequest,
} from "./fileActions";
import type { HttpGetFn } from "./healthProbe";
import { NativeImageViewer } from "./NativeImageViewer";
import { NativeServerOnboarding } from "./NativeServerOnboarding";
import { NativeUpdateBanner } from "./NativeUpdateBanner";
import { createServerUrlStore, type ServerUrlStore } from "./preferences";
import {
  createReminderCoordinator,
  registerActiveReminderCoordinator,
  subscribeAppResume,
  subscribeNotificationTap,
  type ReminderCoordinator,
} from "./reminders";
import { getDeviceTimeZone } from "./remindersPlan";
import { isNativeDebugBuild } from "./runtime";
import { createSecureTokenStore, type SecureTokenStore } from "./secureToken";
import { validateServerUrl } from "./serverUrl";
import {
  checkServerCompatibility,
  getAppVersion,
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
  reminderCoordinator?: ReminderCoordinator;
}

function applyDeepLinkRoute(route: string): void {
  if (window.location.hash === route) {
    window.dispatchEvent(new Event("hashchange"));
    return;
  }
  window.location.hash = route;
}

function NativeReminderBridge({
  coordinator,
}: {
  coordinator: ReminderCoordinator;
}) {
  const { state, capability } = useAuth();
  const authorized =
    state.status === "authenticated" && capability.isAuthorized();
  const lastTimeZoneRef = useRef<string>(getDeviceTimeZone());

  useEffect(() => {
    if (!authorized) return;

    const triggerSync = () => {
      const currentTimeZone = getDeviceTimeZone();
      lastTimeZoneRef.current = currentTimeZone;
      void coordinator.syncNow(capability, { timeZone: currentTimeZone });
    };

    triggerSync();
    const unsubSchedule = onScheduleChanged(triggerSync);
    const unsubResume = subscribeAppResume(() => {
      const nextTimeZone = getDeviceTimeZone();
      if (nextTimeZone !== lastTimeZoneRef.current) {
        lastTimeZoneRef.current = nextTimeZone;
      }
      void coordinator.syncNow(capability, { timeZone: nextTimeZone });
    });

    return () => {
      unsubSchedule();
      unsubResume();
    };
  }, [authorized, capability, coordinator]);

  return null;
}

export function NativeApp({
  allowDebugHttp = isNativeDebugBuild(),
  urlStore,
  tokenStore,
  httpGet,
  appVersion,
  reminderCoordinator,
}: NativeAppProps) {
  const resolvedUrlStore = useMemo<ServerUrlStore>(
    () => urlStore ?? createServerUrlStore(),
    [urlStore],
  );
  const resolvedTokenStore = useMemo<SecureTokenStore>(
    () => tokenStore ?? createSecureTokenStore(),
    [tokenStore],
  );
  const resolvedReminderCoordinator = useMemo<ReminderCoordinator>(
    () => reminderCoordinator ?? createReminderCoordinator(),
    [reminderCoordinator],
  );
  const [shellState, setShellState] = useState<NativeShellState>({
    status: "booting",
  });
  const [viewerRequest, setViewerRequest] =
    useState<NativeImageViewerRequest | null>(null);
  const activeServerUrlRef = useRef<string | null>(null);
  const shellReadyRef = useRef(false);
  const pendingDeepLinkRef = useRef<string | null>(null);
  const resolvedAppVersion = appVersion ?? getAppVersion();

  const closeImageViewer = useCallback(() => {
    setViewerRequest(null);
  }, []);

  useEffect(() => {
    shellReadyRef.current = shellState.status === "ready";
    if (shellState.status === "ready" && pendingDeepLinkRef.current !== null) {
      const pending = pendingDeepLinkRef.current;
      pendingDeepLinkRef.current = null;
      applyDeepLinkRoute(pending);
    }
  }, [shellState.status]);

  useEffect(() => {
    void cleanupNativeSharedCache();
    registerActiveReminderCoordinator(resolvedReminderCoordinator);
    registerNativeImageViewerHandler((request) => {
      setViewerRequest(request);
    });
    const unsubTap = subscribeNotificationTap((route) => {
      if (shellReadyRef.current) {
        applyDeepLinkRoute(route);
      } else {
        pendingDeepLinkRef.current = route;
      }
    });
    return () => {
      unsubTap();
      registerNativeImageViewerHandler(null);
      registerActiveReminderCoordinator(null);
    };
  }, [resolvedReminderCoordinator]);

  const handleChangeServer = useCallback((currentUrl: string) => {
    void clearNativeBearerToken().finally(() => {
      setViewerRequest(null);
      resetMapRuntimeConfig();
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
        await resolvedReminderCoordinator.clearOnTrustLoss();
      }
      activeServerUrlRef.current = serverUrl;
      const storedToken = await resolvedTokenStore.get();
      applyMapRuntimeConfig(info.runtimeConfig);
      configureNativeBearerTransport({
        serverUrl,
        initialToken: storedToken,
        saveToken: (token) => resolvedTokenStore.set(token),
        clearToken: () => resolvedTokenStore.clear(),
        getDefaultDeviceLabel: () => resolvedTokenStore.getDeviceLabel(),
        onChangeServer: () => {
          handleChangeServer(serverUrl);
        },
        onTrustLost: () => resolvedReminderCoordinator.clearOnTrustLoss(),
      });
      setShellState((previous) => ({
        status: "ready",
        serverUrl,
        info,
        sessionKey: previous.status === "ready" ? previous.sessionKey + 1 : 1,
      }));
    },
    [handleChangeServer, resolvedReminderCoordinator, resolvedTokenStore],
  );

  useEffect(() => {
    const controller = new AbortController();
    const isAborted = (): boolean => controller.signal.aborted;
    async function boot() {
      const saved = await resolvedUrlStore.load();
      if (isAborted()) return;
      activeServerUrlRef.current = saved;
      if (saved === null) {
        await resolvedReminderCoordinator.clearOnTrustLoss();
        if (isAborted()) return;
        setShellState({
          status: "onboarding",
          initialServerUrl: null,
          initialError: null,
        });
        return;
      }

      const validation = validateServerUrl(saved, { allowDebugHttp });
      if (!validation.ok) {
        await resolvedReminderCoordinator.clearOnTrustLoss();
        if (isAborted()) return;
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
        if (compatibility.kind !== "unreachable") {
          await resolvedReminderCoordinator.clearOnTrustLoss();
          if (isAborted()) return;
        }
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
      resetMapRuntimeConfig();
      resetAuthTransport();
    };
  }, [
    activateServer,
    allowDebugHttp,
    appVersion,
    httpGet,
    resolvedReminderCoordinator,
    resolvedUrlStore,
  ]);

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
        onForgetServer={() => {
          void resolvedReminderCoordinator.clearOnTrustLoss();
        }}
      />
    );
  }

  return (
    <>
      <App
        key={`${shellState.serverUrl}#${String(shellState.sessionKey)}`}
        nativeChildren={
          <NativeReminderBridge coordinator={resolvedReminderCoordinator} />
        }
      />
      <NativeUpdateBanner
        key={shellState.info.serverVersion}
        serverVersion={shellState.info.serverVersion}
        appVersion={resolvedAppVersion}
      />
      {viewerRequest !== null && (
        <NativeImageViewer request={viewerRequest} onClose={closeImageViewer} />
      )}
    </>
  );
}
