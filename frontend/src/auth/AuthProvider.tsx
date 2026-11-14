import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  ApiError,
  changePassword,
  type ChangePasswordRequest,
  getSession,
  login as requestLogin,
  logout as requestLogout,
  recoverCsrf,
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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "restoring" });
  const [restorationAttempt, setRestorationAttempt] = useState(0);

  const generation = useRef(0);
  const changingPassword = useRef(false);
  const [passwordChangePending, setPasswordChangePending] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    const attempt = ++generation.current;

    async function restoreSession() {
      setState({ status: "restoring" });
      try {
        const session = await getSession(controller.signal);
        if (attempt !== generation.current) return;
        const csrf = await recoverCsrf(controller.signal);
        if (attempt !== generation.current || controller.signal.aborted) return;
        setState({
          status: "authenticated",
          session,
          csrfToken: csrf.csrf_token,
        });
      } catch (error: unknown) {
        if (controller.signal.aborted || attempt !== generation.current) return;
        if (error instanceof ApiError && error.status === 401) {
          setState({ status: "unauthenticated" });
          return;
        }
        setState({
          status: "recovery-failed",
          message: serviceFailureMessage(),
        });
      }
    }

    void restoreSession();
    return () => {
      controller.abort();
    };
  }, [restorationAttempt]);

  const logIn = useCallback(async (payload: LoginRequest) => {
    const attempt = ++generation.current;
    setState({ status: "submitting-login" });
    let csrfToken: string;
    try {
      const csrf = await requestLogin(payload);
      if (attempt !== generation.current) return;
      csrfToken = csrf.csrf_token;
    } catch (error: unknown) {
      if (attempt !== generation.current) return;
      if (error instanceof ApiError && error.status === 401) {
        setState({
          status: "unauthenticated",
          message: "The login name or password was not accepted.",
        });
      } else if (error instanceof ApiError && error.status === 429) {
        const retry = error.retryAfter
          ? ` Try again in ${error.retryAfter} seconds.`
          : " Please wait before trying again.";
        setState({
          status: "unauthenticated",
          message: `Too many login attempts.${retry}`,
        });
      } else if (error instanceof ApiError && error.status === 422) {
        setState({
          status: "unauthenticated",
          message: "Check the login name and password, then try again.",
        });
      } else {
        setState({
          status: "unauthenticated",
          message: serviceFailureMessage(),
        });
      }
      return;
    }

    try {
      const session = await getSession();
      if (attempt !== generation.current) return;
      setState({
        status: "authenticated",
        session,
        csrfToken,
      });
    } catch {
      if (attempt !== generation.current) return;
      setState({
        status: "recovery-failed",
        message: serviceFailureMessage(),
      });
    }
  }, []);

  const logOut = useCallback(async () => {
    if (
      changingPassword.current ||
      (state.status !== "authenticated" && state.status !== "logout-failed")
    )
      return;
    const attempt = ++generation.current;
    const { session } = state;
    let csrfToken = state.csrfToken;
    setState({ status: "logging-out", session, csrfToken });
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
        let current;
        try {
          current = await getSession();
        } catch (probeError: unknown) {
          if (attempt !== generation.current) return;
          if (probeError instanceof ApiError && probeError.status === 401) {
            setState({ status: "unauthenticated" });
            return;
          }
          throw probeError;
        }
        if (attempt !== generation.current) return;
        if (!current.owner || current.user_id !== session.user_id) {
          throw error;
        }
        csrfToken = (await recoverCsrf()).csrf_token;
        if (attempt !== generation.current) return;
        await requestLogout(csrfToken);
      }
      if (attempt === generation.current)
        setState({ status: "unauthenticated" });
    } catch {
      if (attempt !== generation.current) return;
      setState({
        status: "logout-failed",
        message:
          "Logout could not be confirmed. Your server session may still be active.",
        session,
        csrfToken,
      });
    }
  }, [state]);

  const submitPassword = useCallback(
    async (payload: ChangePasswordRequest) => {
      if (
        state.status !== "authenticated" ||
        !state.session.owner ||
        changingPassword.current
      ) {
        return false;
      }
      const attempt = ++generation.current;
      changingPassword.current = true;
      setPasswordChangePending(true);
      try {
        const response = await changePassword(payload, state.csrfToken);
        if (attempt !== generation.current) return false;
        setState({ ...state, csrfToken: response.csrf_token });
        return true;
      } catch (error: unknown) {
        if (attempt !== generation.current) return false;
        if (error instanceof ApiError && error.status === 401) {
          ++generation.current;
          setState({
            status: "unauthenticated",
            message: "Your session expired. Sign in again to continue.",
          });
          return false;
        }
        throw error;
      } finally {
        changingPassword.current = false;
        setPasswordChangePending(false);
      }
    },
    [state],
  );

  const passwordChange = useMemo(
    () => ({ pending: passwordChangePending, submit: submitPassword }),
    [passwordChangePending, submitPassword],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      state,
      logIn,
      logOut,
      sessionExpired: () => {
        ++generation.current;
        setState({
          status: "unauthenticated",
          message: "Your session expired. Sign in again to continue.",
        });
      },
      retryRestoration: () => {
        ++generation.current;
        setRestorationAttempt((attempt) => attempt + 1);
      },
      cancelLogout: () => {
        if (state.status === "logout-failed") {
          ++generation.current;
          setState({
            status: "authenticated",
            session: state.session,
            csrfToken: state.csrfToken,
          });
        }
      },
    }),
    [logIn, logOut, state],
  );

  return (
    <AuthContext.Provider value={value}>
      <PasswordChangeContext.Provider value={passwordChange}>
        {children}
      </PasswordChangeContext.Provider>
    </AuthContext.Provider>
  );
}
