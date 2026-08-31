import { useEffect, useRef, useState, type SyntheticEvent } from "react";

import { useAuth } from "./context";

export function LoginForm() {
  const auth = useAuth();
  const [password, setPassword] = useState("");
  const errorRef = useRef<HTMLParagraphElement>(null);
  const submitting = auth.state.status === "submitting-login";
  const message =
    auth.state.status === "unauthenticated" ? auth.state.message : undefined;

  useEffect(() => {
    if (message) errorRef.current?.focus();
  }, [message]);

  async function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const loginNameValue = form.get("login_name");
    const loginName = typeof loginNameValue === "string" ? loginNameValue : "";
    const submittedPassword = password;
    setPassword("");
    await auth.logIn({ login_name: loginName, password: submittedPassword });
  }

  return (
    <form
      aria-busy={submitting}
      onSubmit={(event) => {
        void submit(event);
      }}
    >
      <div className="field">
        <label htmlFor="login-name">Login name</label>
        <input
          id="login-name"
          name="login_name"
          autoComplete="username"
          required
          disabled={submitting}
        />
      </div>
      <div className="field">
        <label htmlFor="password">Password</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          disabled={submitting}
          value={password}
          onChange={(event) => {
            setPassword(event.currentTarget.value);
          }}
        />
      </div>
      {message && (
        <p
          className="notice notice--error"
          role="alert"
          ref={errorRef}
          tabIndex={-1}
        >
          {message}
        </p>
      )}
      <button type="submit" disabled={submitting}>
        {submitting ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
