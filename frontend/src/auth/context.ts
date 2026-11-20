import { createContext, useContext } from "react";

import type {
  ChangePasswordRequest,
  LoginRequest,
  ProtectedRequestCapability,
  SessionResponse,
} from "./api";

export interface RetainedOwnerIdentity {
  user_id: string;
  login_name: string;
  display_name?: string | null;
}

export type AuthState =
  | { status: "restoring" }
  | {
      status: "unauthenticated";
      message?: string;
      retainedIdentity?: RetainedOwnerIdentity;
    }
  | {
      status: "submitting-login";
      retainedIdentity?: RetainedOwnerIdentity;
    }
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
  capability: ProtectedRequestCapability;
  workspaceKey?: number;
  logIn(payload: LoginRequest): Promise<void>;
  reauthenticate?: (payload: LoginRequest) => Promise<void>;
  discardRetainedSession?: () => Promise<void>;
  logOut(): Promise<void>;
  sessionExpired: () => void;
  retryRestoration(): void;
  cancelLogout(): void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useOptionalAuth(): AuthContextValue | null {
  return useContext(AuthContext);
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null)
    throw new Error("useAuth must be used within AuthProvider");
  return context;
}

export const PasswordChangeContext = createContext<{
  pending: boolean;
  submit(payload: ChangePasswordRequest): Promise<boolean>;
} | null>(null);
