import { createContext, useContext } from "react";

import type { LoginRequest, SessionResponse } from "./api";

export type AuthState =
  | { status: "restoring" }
  | { status: "unauthenticated"; message?: string }
  | { status: "submitting-login" }
  | {
      status: "authenticated";
      session: SessionResponse;
      csrfToken: string;
    }
  | { status: "logging-out"; session: SessionResponse; csrfToken: string }
  | { status: "recovery-failed"; message: string }
  | {
      status: "logout-failed";
      message: string;
      session: SessionResponse;
      csrfToken: string;
    };

export interface AuthContextValue {
  state: AuthState;
  logIn(payload: LoginRequest): Promise<void>;
  logOut(): Promise<void>;
  sessionExpired(): void;
  retryRestoration(): void;
  cancelLogout(): void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null)
    throw new Error("useAuth must be used within AuthProvider");
  return context;
}
