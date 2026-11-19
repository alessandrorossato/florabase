import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  acquireWorkspaceCapability,
  ApiError,
  attachAuthRequestGate,
  changePassword,
  type ChangePasswordRequest,
  enqueueAuthCookieOperation,
  getActiveAuthProviderId,
  getProtectedWorkspaceGeneration,
  getSession,
  invalidateProtectedWorkspace,
  isReauthenticationState,
  login as requestLogin,
  logout as requestLogout,
  type ManagedWorkspaceCapabilityHandle,
  type ProtectedRequestCapability,
  recoverCsrf,
  revokedAuthCapability,
  syncAuthRequestGate,
  waitForSettledAuthCookieOperations,
  type LoginRequest,
} from "./api";
import {
  AuthContext,
  PasswordChangeContext,
  type AuthContextValue,
  type AuthState,
} from "./context";

function serviceFailureMessage(): string {
  return "Florabase could not reach the authentication service. Please try again.";
}

function loginErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 401) {
    return "The login name or password was not accepted.";
  }
  if (error instanceof ApiError && error.status === 429) {
    const retry = error.retryAfter
      ? ` Try again in ${error.retryAfter} seconds.`
      : " Please wait before trying again.";
    return `Too many login attempts.${retry}`;
  }
  if (error instanceof ApiError && error.status === 422) {
    return "Check the login name and password, then try again.";
  }
  return serviceFailureMessage();
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "restoring" });
  const [workspaceKey, setWorkspaceKey] = useState(0);
  const [restorationAttempt, setRestorationAttempt] = useState(0);

  const stateRef = useRef<AuthState>(state);
  const generation = useRef(0);
  const authEpochRef = useRef(0);
  const providerIdRef = useRef(0);
  const mountedRef = useRef(true);
  const changingPassword = useRef(false);
  const [passwordChangePending, setPasswordChangePending] = useState(false);
  const workspaceCapRef = useRef<{
    ownerId: string;
    handle: ManagedWorkspaceCapabilityHandle;
  } | null>(null);
  const [capability, setCapability] = useState<ProtectedRequestCapability>(() =>
    revokedAuthCapability(),
  );

  const commitState = useCallback((next: AuthState) => {
    stateRef.current = next;
    setState(next);
  }, []);

  const isActiveProvider = useCallback((expectedProviderId?: number) => {
    const pid = expectedProviderId ?? providerIdRef.current;
    return (
      mountedRef.current &&
      pid !== 0 &&
      pid === providerIdRef.current &&
      pid === getActiveAuthProviderId()
    );
  }, []);

  const retireWorkspaceCapability = useCallback(() => {
    workspaceCapRef.current?.handle.revoke();
    workspaceCapRef.current = null;
    setCapability(revokedAuthCapability());
  }, []);

  const ensureWorkspaceCapability = useCallback(
    (providerId: number, ownerId: string) => {
      if (
        providerId === 0 ||
        providerId !== providerIdRef.current ||
        providerId !== getActiveAuthProviderId()
      ) {
        return;
      }
      if (workspaceCapRef.current?.ownerId === ownerId) {
        return;
      }
      workspaceCapRef.current?.handle.revoke();
      const handle = acquireWorkspaceCapability(providerId);
      workspaceCapRef.current = { ownerId, handle };
      setCapability(handle.capability);
    },
    [],
  );

  const expireAuthenticatedSession = useCallback(
    (expectedEpoch?: number) => {
      if (!isActiveProvider()) return;
      if (
        expectedEpoch !== undefined &&
        expectedEpoch !== authEpochRef.current
      ) {
        return;
      }
      const current = stateRef.current;
      if (
        current.status !== "authenticated" &&
        current.status !== "logout-failed"
      ) {
        return;
      }
      generation.current += 1;
      authEpochRef.current = syncAuthRequestGate({
        providerId: providerIdRef.current,
        locked: true,
        advanceEpoch: true,
        ownerId: current.session.user_id,
      });
      commitState({
        status: "unauthenticated",
        retainedIdentity: {
          user_id: current.session.user_id,
          login_name: current.session.login_name,
          display_name: current.session.display_name,
        },
        message: "Your session expired. Sign in again to continue.",
      });
    },
    [commitState, isActiveProvider],
  );

  useLayoutEffect(() => {
    mountedRef.current = true;
    const { providerId, detach } = attachAuthRequestGate(
      (originatingEpoch, callbackProviderId) => {
        if (callbackProviderId !== providerIdRef.current) return;
        expireAuthenticatedSession(originatingEpoch);
      },
      true,
    );
    providerIdRef.current = providerId;
    workspaceCapRef.current = null;
    const current = stateRef.current;
    const ownerId =
      current.status === "authenticated" || current.status === "logout-failed"
        ? current.session.user_id
        : isReauthenticationState(current)
          ? current.retainedIdentity.user_id
          : null;
    authEpochRef.current = syncAuthRequestGate({
      providerId,
      locked:
        current.status !== "authenticated" &&
        current.status !== "logout-failed",
      ownerId,
    });
    return () => {
      mountedRef.current = false;
      if (providerIdRef.current === providerId) {
        providerIdRef.current = 0;
      }
      workspaceCapRef.current = null;
      generation.current += 1;
      detach();
    };
  }, [expireAuthenticatedSession]);

  useEffect(() => {
    const controller = new AbortController();
    const attempt = ++generation.current;
    const capturedProviderId = providerIdRef.current;

    async function restoreSession() {
      if (!isActiveProvider(capturedProviderId)) return;
      authEpochRef.current = invalidateProtectedWorkspace(capturedProviderId);
      retireWorkspaceCapability();
      commitState({ status: "restoring" });

      const pendingCookies = waitForSettledAuthCookieOperations();
      if (pendingCookies) {
        await pendingCookies;
      }
      if (
        attempt !== generation.current ||
        !isActiveProvider(capturedProviderId)
      ) {
        return;
      }

      try {
        const session = await getSession(controller.signal);
        if (
          attempt !== generation.current ||
          !isActiveProvider(capturedProviderId)
        ) {
          return;
        }
        const csrf = await recoverCsrf(controller.signal);
        if (
          attempt !== generation.current ||
          !isActiveProvider(capturedProviderId)
        ) {
          return;
        }
        authEpochRef.current = syncAuthRequestGate({
          providerId: capturedProviderId,
          locked: false,
          advanceEpoch: true,
          ownerId: session.user_id,
        });
        ensureWorkspaceCapability(capturedProviderId, session.user_id);
        commitState({
          status: "authenticated",
          session,
          csrfToken: csrf.csrf_token,
        });
      } catch (error: unknown) {
        if (
          attempt !== generation.current ||
          !isActiveProvider(capturedProviderId)
        ) {
          return;
        }
        authEpochRef.current = invalidateProtectedWorkspace(capturedProviderId);
        retireWorkspaceCapability();
        if (error instanceof ApiError && error.status === 401) {
          commitState({ status: "unauthenticated" });
          return;
        }
        commitState({
          status: "recovery-failed",
          message: serviceFailureMessage(),
        });
      }
    }

    void restoreSession();
    return () => {
      generation.current += 1;
      controller.abort();
    };
  }, [
    commitState,
    ensureWorkspaceCapability,
    isActiveProvider,
    restorationAttempt,
    retireWorkspaceCapability,
  ]);

  const logIn = useCallback(
    (payload: LoginRequest) => {
      const capturedProviderId = providerIdRef.current;
      return enqueueAuthCookieOperation(async () => {
        if (!isActiveProvider(capturedProviderId)) return;
        const attempt = ++generation.current;
        authEpochRef.current = invalidateProtectedWorkspace(capturedProviderId);
        retireWorkspaceCapability();
        commitState({ status: "submitting-login" });
        let csrfToken: string;
        try {
          const csrf = await requestLogin(payload);
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedProviderId)
          ) {
            return;
          }
          csrfToken = csrf.csrf_token;
        } catch (error: unknown) {
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedProviderId)
          ) {
            return;
          }
          commitState({
            status: "unauthenticated",
            message: loginErrorMessage(error),
          });
          return;
        }

        try {
          const session = await getSession();
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedProviderId)
          ) {
            return;
          }
          authEpochRef.current =
            invalidateProtectedWorkspace(capturedProviderId);
          retireWorkspaceCapability();
          setWorkspaceKey((value) => value + 1);
          authEpochRef.current = syncAuthRequestGate({
            providerId: capturedProviderId,
            locked: false,
            advanceEpoch: true,
            ownerId: session.user_id,
          });
          ensureWorkspaceCapability(capturedProviderId, session.user_id);
          commitState({
            status: "authenticated",
            session,
            csrfToken,
          });
        } catch {
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedProviderId)
          ) {
            return;
          }
          commitState({
            status: "recovery-failed",
            message: serviceFailureMessage(),
          });
        }
      });
    },
    [
      commitState,
      ensureWorkspaceCapability,
      isActiveProvider,
      retireWorkspaceCapability,
    ],
  );

  const reauthenticate = useCallback(
    (payload: LoginRequest) => {
      const capturedProviderId = providerIdRef.current;
      const capturedWorkspace = getProtectedWorkspaceGeneration();
      return enqueueAuthCookieOperation(async () => {
        if (!isActiveProvider(capturedProviderId)) return;
        if (getProtectedWorkspaceGeneration() !== capturedWorkspace) return;
        const current = stateRef.current;
        if (current.status !== "unauthenticated" || !current.retainedIdentity)
          return;
        const { retainedIdentity } = current;
        const attempt = ++generation.current;
        authEpochRef.current = syncAuthRequestGate({
          providerId: capturedProviderId,
          locked: true,
          advanceEpoch: true,
          ownerId: retainedIdentity.user_id,
        });
        commitState({
          status: "submitting-login",
          retainedIdentity,
        });

        let csrfToken: string;
        try {
          const csrf = await requestLogin(payload);
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedProviderId)
          ) {
            return;
          }
          csrfToken = csrf.csrf_token;
        } catch (error: unknown) {
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedProviderId)
          ) {
            return;
          }
          commitState({
            status: "unauthenticated",
            retainedIdentity,
            message: loginErrorMessage(error),
          });
          return;
        }

        try {
          const session = await getSession();
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedProviderId)
          ) {
            return;
          }
          const sameOwnerRecovery =
            session.user_id === retainedIdentity.user_id;
          if (!sameOwnerRecovery) {
            // Retire previous owner workspace & revoke all old-owner capabilities
            // synchronously before unlocking the gate for the replacement owner.
            authEpochRef.current =
              invalidateProtectedWorkspace(capturedProviderId);
            retireWorkspaceCapability();
            setWorkspaceKey((value) => value + 1);
          }
          authEpochRef.current = syncAuthRequestGate({
            providerId: capturedProviderId,
            locked: false,
            advanceEpoch: true,
            ownerId: session.user_id,
          });
          ensureWorkspaceCapability(capturedProviderId, session.user_id);
          commitState({
            status: "authenticated",
            session,
            csrfToken,
          });
        } catch {
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedProviderId)
          ) {
            return;
          }
          commitState({
            status: "unauthenticated",
            retainedIdentity,
            message: serviceFailureMessage(),
          });
        }
      });
    },
    [
      commitState,
      ensureWorkspaceCapability,
      isActiveProvider,
      retireWorkspaceCapability,
    ],
  );

  const discardRetainedSession = useCallback(() => {
    const capturedProviderId = providerIdRef.current;
    const capturedWorkspace = getProtectedWorkspaceGeneration();
    return enqueueAuthCookieOperation(() => {
      if (
        !isActiveProvider(capturedProviderId) ||
        getProtectedWorkspaceGeneration() !== capturedWorkspace
      ) {
        return Promise.resolve();
      }
      const current = stateRef.current;
      if (
        (current.status !== "unauthenticated" &&
          current.status !== "submitting-login") ||
        !current.retainedIdentity
      ) {
        return Promise.resolve();
      }
      generation.current += 1;
      authEpochRef.current = invalidateProtectedWorkspace(capturedProviderId);
      retireWorkspaceCapability();
      setWorkspaceKey((value) => value + 1);
      commitState({ status: "unauthenticated" });
      return Promise.resolve();
    });
  }, [commitState, isActiveProvider, retireWorkspaceCapability]);

  const logOut = useCallback(() => {
    const capturedProviderId = providerIdRef.current;
    const initialState = stateRef.current;
    if (
      changingPassword.current ||
      !isActiveProvider(capturedProviderId) ||
      (initialState.status !== "authenticated" &&
        initialState.status !== "logout-failed")
    ) {
      return Promise.resolve();
    }
    const originatingWorkspace = getProtectedWorkspaceGeneration();
    const originatingOwnerId = initialState.session.user_id;

    return enqueueAuthCookieOperation(async () => {
      const current = stateRef.current;
      if (
        changingPassword.current ||
        !isActiveProvider(capturedProviderId) ||
        getProtectedWorkspaceGeneration() !== originatingWorkspace ||
        (current.status !== "authenticated" &&
          current.status !== "logout-failed") ||
        current.session.user_id !== originatingOwnerId
      ) {
        return;
      }
      const attempt = ++generation.current;
      const { session } = current;
      let csrfToken = current.csrfToken;
      authEpochRef.current = syncAuthRequestGate({
        providerId: capturedProviderId,
        locked: true,
        advanceEpoch: true,
        ownerId: session.user_id,
      });
      commitState({ status: "logging-out", session, csrfToken });
      try {
        try {
          await requestLogout(csrfToken);
        } catch (error: unknown) {
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedProviderId)
          ) {
            return;
          }
          if (
            !(error instanceof ApiError) ||
            (error.status !== 401 && error.status !== 403)
          ) {
            throw error;
          }
          let live;
          try {
            live = await getSession();
          } catch (probeError: unknown) {
            if (
              attempt !== generation.current ||
              !isActiveProvider(capturedProviderId)
            ) {
              return;
            }
            if (probeError instanceof ApiError && probeError.status === 401) {
              authEpochRef.current =
                invalidateProtectedWorkspace(capturedProviderId);
              retireWorkspaceCapability();
              setWorkspaceKey((value) => value + 1);
              commitState({ status: "unauthenticated" });
              return;
            }
            throw probeError;
          }
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedProviderId)
          ) {
            return;
          }
          if (!live.owner || live.user_id !== session.user_id) {
            throw error;
          }
          csrfToken = (await recoverCsrf()).csrf_token;
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedProviderId)
          ) {
            return;
          }
          await requestLogout(csrfToken);
        }
        if (
          attempt === generation.current &&
          isActiveProvider(capturedProviderId)
        ) {
          authEpochRef.current =
            invalidateProtectedWorkspace(capturedProviderId);
          retireWorkspaceCapability();
          setWorkspaceKey((value) => value + 1);
          commitState({ status: "unauthenticated" });
        }
      } catch {
        if (
          attempt !== generation.current ||
          !isActiveProvider(capturedProviderId)
        ) {
          return;
        }
        commitState({
          status: "logout-failed",
          message:
            "Logout could not be confirmed. Your server session may still be active.",
          session,
          csrfToken,
        });
      }
    });
  }, [commitState, isActiveProvider, retireWorkspaceCapability]);

  const submitPassword = useCallback(
    (payload: ChangePasswordRequest) => {
      const capturedProviderId = providerIdRef.current;
      const initialState = stateRef.current;
      if (
        !isActiveProvider(capturedProviderId) ||
        initialState.status !== "authenticated" ||
        !initialState.session.owner ||
        changingPassword.current
      ) {
        return Promise.resolve(false);
      }
      const originatingWorkspace = getProtectedWorkspaceGeneration();
      const originatingOwnerId = initialState.session.user_id;

      return enqueueAuthCookieOperation(async () => {
        const current = stateRef.current;
        if (
          !isActiveProvider(capturedProviderId) ||
          getProtectedWorkspaceGeneration() !== originatingWorkspace ||
          current.status !== "authenticated" ||
          !current.session.owner ||
          current.session.user_id !== originatingOwnerId ||
          changingPassword.current
        ) {
          return false;
        }
        const attempt = ++generation.current;
        changingPassword.current = true;
        setPasswordChangePending(true);
        try {
          const response = await changePassword(payload, current.csrfToken);
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedProviderId)
          ) {
            return false;
          }
          authEpochRef.current = syncAuthRequestGate({
            providerId: capturedProviderId,
            locked: false,
            advanceEpoch: true,
            ownerId: current.session.user_id,
          });
          commitState({ ...current, csrfToken: response.csrf_token });
          return true;
        } catch (error: unknown) {
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedProviderId)
          ) {
            return false;
          }
          if (error instanceof ApiError && error.status === 401) {
            expireAuthenticatedSession();
            return false;
          }
          throw error;
        } finally {
          changingPassword.current = false;
          setPasswordChangePending(false);
        }
      });
    },
    [commitState, expireAuthenticatedSession, isActiveProvider],
  );

  const passwordChange = useMemo(
    () => ({ pending: passwordChangePending, submit: submitPassword }),
    [passwordChangePending, submitPassword],
  );

  const sessionExpired = useCallback(() => {
    expireAuthenticatedSession();
  }, [expireAuthenticatedSession]);

  const retryRestoration = useCallback(() => {
    const pid = providerIdRef.current;
    if (!isActiveProvider(pid)) return;
    generation.current += 1;
    authEpochRef.current = invalidateProtectedWorkspace(pid);
    retireWorkspaceCapability();
    setRestorationAttempt((attempt) => attempt + 1);
  }, [isActiveProvider, retireWorkspaceCapability]);

  const cancelLogout = useCallback(() => {
    const pid = providerIdRef.current;
    if (!isActiveProvider(pid)) return;
    const current = stateRef.current;
    if (current.status === "logout-failed") {
      generation.current += 1;
      authEpochRef.current = syncAuthRequestGate({
        providerId: pid,
        locked: false,
        advanceEpoch: true,
        ownerId: current.session.user_id,
      });
      ensureWorkspaceCapability(pid, current.session.user_id);
      commitState({
        status: "authenticated",
        session: current.session,
        csrfToken: current.csrfToken,
      });
    }
  }, [commitState, ensureWorkspaceCapability, isActiveProvider]);

  const value = useMemo<AuthContextValue>(
    () => ({
      state,
      capability,
      workspaceKey,
      logIn,
      reauthenticate,
      discardRetainedSession,
      logOut,
      sessionExpired,
      retryRestoration,
      cancelLogout,
    }),
    [
      cancelLogout,
      capability,
      discardRetainedSession,
      logIn,
      logOut,
      reauthenticate,
      retryRestoration,
      sessionExpired,
      state,
      workspaceKey,
    ],
  );

  return (
    <AuthContext.Provider value={value}>
      <PasswordChangeContext.Provider value={passwordChange}>
        {children}
      </PasswordChangeContext.Provider>
    </AuthContext.Provider>
  );
}
