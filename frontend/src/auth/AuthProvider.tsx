import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  ApiError,
  getSession,
  login as requestLogin,
  logout as requestLogout,
  recoverCsrf,
  type LoginRequest,
} from "./api";
import { AuthContext, type AuthContextValue, type AuthState } from "./context";

function serviceFailureMessage(): string {
  return "Florabase could not reach the authentication service. Please try again.";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "restoring" });
  const [restorationAttempt, setRestorationAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function restoreSession() {
      setState({ status: "restoring" });
      try {
        const session = await getSession(controller.signal);
        const csrf = await recoverCsrf(controller.signal);
        setState({
          status: "authenticated",
          session,
          csrfToken: csrf.csrf_token,
        });
      } catch (error: unknown) {
        if (controller.signal.aborted) return;
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
    setState({ status: "submitting-login" });
    let csrfToken: string;
    try {
      const csrf = await requestLogin(payload);
      csrfToken = csrf.csrf_token;
    } catch (error: unknown) {
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
      setState({
        status: "authenticated",
        session,
        csrfToken,
      });
    } catch {
      setState({
        status: "recovery-failed",
        message: serviceFailureMessage(),
      });
    }
  }, []);

  const logOut = useCallback(async () => {
    if (state.status !== "authenticated" && state.status !== "logout-failed")
      return;
    const { session, csrfToken } = state;
    setState({ status: "logging-out", session, csrfToken });
    try {
      await requestLogout(csrfToken);
      setState({ status: "unauthenticated" });
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401) {
        setState({ status: "unauthenticated" });
        return;
      }
      setState({
        status: "logout-failed",
        message:
          "Logout could not be confirmed. Your server session may still be active.",
        session,
        csrfToken,
      });
    }
  }, [state]);

  const value = useMemo<AuthContextValue>(
    () => ({
      state,
      logIn,
      logOut,
      sessionExpired: () => {
        setState({
          status: "unauthenticated",
          message: "Your session expired. Sign in again to continue.",
        });
      },
      retryRestoration: () => {
        setRestorationAttempt((attempt) => attempt + 1);
      },
      cancelLogout: () => {
        if (state.status === "logout-failed") {
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

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
