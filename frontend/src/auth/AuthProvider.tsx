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
  ApiError,
  attachAuthRequestGate,
  changePassword,
  type ChangePasswordRequest,
  getSession,
  invalidateProtectedWorkspace,
  isReauthenticationState,
  login as requestLogin,
  logout as requestLogout,
  recoverCsrf,
  syncAuthRequestGate,
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
  const changingPassword = useRef(false);
  const [passwordChangePending, setPasswordChangePending] = useState(false);
  const cookieOpQueue = useRef<Promise<void>>(Promise.resolve());

  const commitState = useCallback((next: AuthState) => {
    stateRef.current = next;
    setState(next);
  }, []);

  const enqueueCookieOp = useCallback(
    <T,>(op: () => Promise<T>): Promise<T> => {
      const nextRun = cookieOpQueue.current.then(op, op);
      cookieOpQueue.current = nextRun.then(
        () => undefined,
        () => undefined,
      );
      return nextRun;
    },
    [],
  );

  const expireAuthenticatedSession = useCallback(
    (expectedEpoch?: number) => {
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
    [commitState],
  );

  useLayoutEffect(() => {
    const cleanup = attachAuthRequestGate((originatingEpoch) => {
      expireAuthenticatedSession(originatingEpoch);
    }, true);
    const current = stateRef.current;
    const ownerId =
      current.status === "authenticated" || current.status === "logout-failed"
        ? current.session.user_id
        : isReauthenticationState(current)
          ? current.retainedIdentity.user_id
          : null;
    authEpochRef.current = syncAuthRequestGate({
      locked:
        current.status !== "authenticated" &&
        current.status !== "logout-failed",
      ownerId,
    });
    return cleanup;
  }, [expireAuthenticatedSession]);

  useEffect(() => {
    const controller = new AbortController();
    const attempt = ++generation.current;

    async function restoreSession() {
      authEpochRef.current = invalidateProtectedWorkspace();
      commitState({ status: "restoring" });
      try {
        const session = await getSession(controller.signal);
        if (attempt !== generation.current) return;
        const csrf = await recoverCsrf(controller.signal);
        if (attempt !== generation.current || controller.signal.aborted) return;
        authEpochRef.current = syncAuthRequestGate({
          locked: false,
          advanceEpoch: true,
          ownerId: session.user_id,
        });
        commitState({
          status: "authenticated",
          session,
          csrfToken: csrf.csrf_token,
        });
      } catch (error: unknown) {
        if (controller.signal.aborted || attempt !== generation.current) return;
        authEpochRef.current = invalidateProtectedWorkspace();
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
      controller.abort();
    };
  }, [commitState, restorationAttempt]);

  const logIn = useCallback(
    (payload: LoginRequest) =>
      enqueueCookieOp(async () => {
        const attempt = ++generation.current;
        authEpochRef.current = invalidateProtectedWorkspace();
        commitState({ status: "submitting-login" });
        let csrfToken: string;
        try {
          const csrf = await requestLogin(payload);
          if (attempt !== generation.current) return;
          csrfToken = csrf.csrf_token;
        } catch (error: unknown) {
          if (attempt !== generation.current) return;
          commitState({
            status: "unauthenticated",
            message: loginErrorMessage(error),
          });
          return;
        }

        try {
          const session = await getSession();
          if (attempt !== generation.current) return;
          authEpochRef.current = invalidateProtectedWorkspace();
          setWorkspaceKey((value) => value + 1);
          authEpochRef.current = syncAuthRequestGate({
            locked: false,
            advanceEpoch: true,
            ownerId: session.user_id,
          });
          commitState({
            status: "authenticated",
            session,
            csrfToken,
          });
        } catch {
          if (attempt !== generation.current) return;
          commitState({
            status: "recovery-failed",
            message: serviceFailureMessage(),
          });
        }
      }),
    [commitState, enqueueCookieOp],
  );

  const reauthenticate = useCallback(
    (payload: LoginRequest) =>
      enqueueCookieOp(async () => {
        const current = stateRef.current;
        if (current.status !== "unauthenticated" || !current.retainedIdentity)
          return;
        const { retainedIdentity } = current;
        const attempt = ++generation.current;
        authEpochRef.current = syncAuthRequestGate({
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
          if (attempt !== generation.current) return;
          csrfToken = csrf.csrf_token;
        } catch (error: unknown) {
          if (attempt !== generation.current) return;
          commitState({
            status: "unauthenticated",
            retainedIdentity,
            message: loginErrorMessage(error),
          });
          return;
        }

        try {
          const session = await getSession();
          if (attempt !== generation.current) return;
          const sameOwnerRecovery =
            session.user_id === retainedIdentity.user_id;
          if (!sameOwnerRecovery) {
            // Retire previous owner workspace & revoke all old-owner capabilities
            // synchronously before unlocking the gate for the replacement owner.
            authEpochRef.current = invalidateProtectedWorkspace();
            setWorkspaceKey((value) => value + 1);
          }
          authEpochRef.current = syncAuthRequestGate({
            locked: false,
            advanceEpoch: true,
            ownerId: session.user_id,
          });
          commitState({
            status: "authenticated",
            session,
            csrfToken,
          });
        } catch {
          if (attempt !== generation.current) return;
          commitState({
            status: "unauthenticated",
            retainedIdentity,
            message: serviceFailureMessage(),
          });
        }
      }),
    [commitState, enqueueCookieOp],
  );

  const discardRetainedSession = useCallback(
    () =>
      enqueueCookieOp(() => {
        const current = stateRef.current;
        if (
          (current.status !== "unauthenticated" &&
            current.status !== "submitting-login") ||
          !current.retainedIdentity
        ) {
          return Promise.resolve();
        }
        generation.current += 1;
        authEpochRef.current = invalidateProtectedWorkspace();
        setWorkspaceKey((value) => value + 1);
        commitState({ status: "unauthenticated" });
        return Promise.resolve();
      }),
    [commitState, enqueueCookieOp],
  );

  const logOut = useCallback(
    () =>
      enqueueCookieOp(async () => {
        const current = stateRef.current;
        if (
          changingPassword.current ||
          (current.status !== "authenticated" &&
            current.status !== "logout-failed")
        ) {
          return;
        }
        const attempt = ++generation.current;
        const { session } = current;
        let csrfToken = current.csrfToken;
        authEpochRef.current = syncAuthRequestGate({
          locked: true,
          advanceEpoch: true,
          ownerId: session.user_id,
        });
        commitState({ status: "logging-out", session, csrfToken });
        try {
          try {
            await requestLogout(csrfToken);
          } catch (error: unknown) {
            if (attempt !== generation.current) return;
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
              if (attempt !== generation.current) return;
              if (probeError instanceof ApiError && probeError.status === 401) {
                authEpochRef.current = invalidateProtectedWorkspace();
                setWorkspaceKey((value) => value + 1);
                commitState({ status: "unauthenticated" });
                return;
              }
              throw probeError;
            }
            if (attempt !== generation.current) return;
            if (!live.owner || live.user_id !== session.user_id) {
              throw error;
            }
            csrfToken = (await recoverCsrf()).csrf_token;
            if (attempt !== generation.current) return;
            await requestLogout(csrfToken);
          }
          if (attempt === generation.current) {
            authEpochRef.current = invalidateProtectedWorkspace();
            setWorkspaceKey((value) => value + 1);
            commitState({ status: "unauthenticated" });
          }
        } catch {
          if (attempt !== generation.current) return;
          commitState({
            status: "logout-failed",
            message:
              "Logout could not be confirmed. Your server session may still be active.",
            session,
            csrfToken,
          });
        }
      }),
    [commitState, enqueueCookieOp],
  );

  const submitPassword = useCallback(
    (payload: ChangePasswordRequest) =>
      enqueueCookieOp(async () => {
        const current = stateRef.current;
        if (
          current.status !== "authenticated" ||
          !current.session.owner ||
          changingPassword.current
        ) {
          return false;
        }
        const attempt = ++generation.current;
        changingPassword.current = true;
        setPasswordChangePending(true);
        try {
          const response = await changePassword(payload, current.csrfToken);
          if (attempt !== generation.current) return false;
          authEpochRef.current = syncAuthRequestGate({
            locked: false,
            advanceEpoch: true,
            ownerId: current.session.user_id,
          });
          commitState({ ...current, csrfToken: response.csrf_token });
          return true;
        } catch (error: unknown) {
          if (attempt !== generation.current) return false;
          if (error instanceof ApiError && error.status === 401) {
            expireAuthenticatedSession();
            return false;
          }
          throw error;
        } finally {
          changingPassword.current = false;
          setPasswordChangePending(false);
        }
      }),
    [commitState, enqueueCookieOp, expireAuthenticatedSession],
  );

  const passwordChange = useMemo(
    () => ({ pending: passwordChangePending, submit: submitPassword }),
    [passwordChangePending, submitPassword],
  );

  const sessionExpired = useCallback(() => {
    expireAuthenticatedSession();
  }, [expireAuthenticatedSession]);

  const retryRestoration = useCallback(() => {
    generation.current += 1;
    authEpochRef.current = invalidateProtectedWorkspace();
    setRestorationAttempt((attempt) => attempt + 1);
  }, []);

  const cancelLogout = useCallback(() => {
    const current = stateRef.current;
    if (current.status === "logout-failed") {
      generation.current += 1;
      authEpochRef.current = syncAuthRequestGate({
        locked: false,
        advanceEpoch: true,
        ownerId: current.session.user_id,
      });
      commitState({
        status: "authenticated",
        session: current.session,
        csrfToken: current.csrfToken,
      });
    }
  }, [commitState]);

  const value = useMemo<AuthContextValue>(
    () => ({
      state,
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
