# ADR 0005: Backend-owned authentication and database sessions

Status: accepted

## Context

Florabase is initially a self-hosted application for one operator. It is served as one browser origin: the frontend proxy serves the React application and forwards `/api/` to FastAPI. The application has no authentication implementation yet, and protected botanical or administrative features must not be exposed until one exists.

The initial product does not require federation, native clients, third-party API access, or multiple independently scaled backend services. The boundary should remain simple without encoding the sole initial operator as an unchangeable singleton.

## Decision

### Accounts and trust boundary

- The first release supports exactly one enabled owner account. The data model and request context will use a real user identifier so later local multi-user accounts and per-user authorization do not require replacing the authentication boundary.
- FastAPI owns authentication, session validation, logout, and authorization. Only backend-created account and session records establish identity.
- Reverse-proxy headers never establish a user. The backend does not accept asserted usernames, roles, or authentication state from the frontend proxy or an outer proxy. Proxy authentication can be designed later as an explicit, separately reviewed adapter.
- Service methods that access protected data receive an authenticated actor. They must not rely on a process-global “current owner.” `DOMAIN-001` must state whether each mutable aggregate is user-owned or deliberately shared before its schema is created.

### Passwords and first-user bootstrap

- Passwords use Argon2id through a maintained library. Each encoded hash contains its unique salt, algorithm, version, and cost parameters. At implementation time, parameters are benchmarked on the supported container and may exceed, but must not fall below, the then-current OWASP floor (currently 19 MiB memory, 2 iterations, parallelism 1). A successful login transparently rehashes an older or weaker encoding.
- Passwords are never encrypted or logged. A pepper is deferred because secure distribution and rotation are not yet justified; adding one later requires a recovery and rotation design.
- The first owner is created by an explicit one-shot backend CLI command run by the operator. It reads the password interactively or from standard input, never from a command-line argument, image layer, Compose file, or unauthenticated HTTP setup endpoint. Creation is transactional and fails once any user exists. Concurrent attempts are constrained so only one initial owner can be created.
- Later account creation, invitations, recovery, email verification, password reset, MFA, and roles beyond owner are deferred.

### Browser session

- A successful login creates a server-side PostgreSQL session and returns only a cryptographically random opaque token with at least 256 bits of entropy. PostgreSQL stores a one-way SHA-256 digest of the high-entropy token, never the bearer token itself.
- The production cookie is named `__Host-florabase-session` and always uses `Secure`, `HttpOnly`, `SameSite=Strict`, and `Path=/`, with no `Domain` attribute. Authentication tokens are never stored in browser local or session storage.
- Loopback development over HTTP uses a clearly development-only cookie without the `__Host-` prefix and without `Secure`. Production configuration must reject that mode. The future authentication implementation must use an explicit canonical HTTPS origin rather than infer security decisions from forwarded headers.
- Sessions have a 24-hour inactivity limit and a 30-day absolute limit, with no initial “remember me” option. Activity may update `last_seen_at` at a bounded cadence rather than writing on every request. The session identifier is replaced after authentication or reauthentication and after password, account-status, or privilege changes.
- Logout deletes or revokes the server-side session and expires the cookie. Password changes, owner disablement, and security-sensitive account changes revoke all sessions for that user. Expired and revoked sessions are rejected immediately and cleaned up asynchronously or by an operator maintenance command.

### CSRF and request behavior

- Cookie-authenticated state-changing requests use a synchronizer CSRF token bound to the server-side session. The frontend obtains it from a non-cacheable session response and returns it in an `X-CSRF-Token` header. The token is never put in a URL or authentication cookie.
- The backend validates the CSRF token using constant-time comparison and also validates the request `Origin` against the configured canonical origin. `SameSite=Strict` and Fetch Metadata checks are defense in depth, not the only CSRF control.
- Login accepts only JSON and requires an allowed `Origin`; logout is a CSRF-protected state change. `GET`, `HEAD`, and `OPTIONS` endpoints never change state.
- Missing, invalid, revoked, or expired authentication returns a JSON `401` without an HTML redirect or account-existence detail. An authenticated actor lacking permission receives `403`. CSRF failures receive a generic `403`. Health and readiness endpoints remain unauthenticated; protected domain and administrative endpoints require a session by default.

### Abuse resistance

- Login failures use the same external response for unknown users and incorrect passwords. Password verification behavior should minimize useful timing differences.
- The backend persists bounded per-account throttling state in PostgreSQL so restarts or future multiple backend processes do not reset it. An outer reverse proxy should additionally rate-limit by source address. Limits produce `429` with `Retry-After`, use temporary backoff rather than permanent account lockout, and are configurable with secure defaults. Exact thresholds and cleanup behavior are acceptance criteria for the implementation feature.
- Authentication failures, session revocations, and throttle decisions are security events, but logs must not contain passwords, raw session/CSRF tokens, cookies, or full request bodies.

### Proxy, HTTPS, CORS, and configuration

- The operator-managed outer proxy terminates HTTPS and forwards only to the frontend published port. It replaces untrusted forwarding headers and owns certificate renewal, HSTS after validation, request/body limits, and network-level rate limiting. PostgreSQL and FastAPI remain unpublished in production Compose.
- The initial browser application and API are same-origin. Production CORS therefore defaults to disabled. If explicit cross-origin support is added later, exact origins, credential handling, cookie `SameSite` behavior, and CSRF protections require a new review; CORS is never treated as authentication or authorization.
- Deployment configuration and database credentials remain outside version control. The canonical public origin, cookie security mode, password-cost parameters, and throttle settings will be validated centrally when authentication is implemented. Production must fail closed for an HTTP public origin, insecure cookies, wildcard CORS, or missing required secrets.
- Because sessions and CSRF state are stored server-side and session tokens are random, the initial design requires no JWT signing key or application-wide session secret. Future peppers, recovery codes, API tokens, or integration credentials would be separately managed secrets.

### Required later database representation

Authentication implementation requires Alembic-managed tables equivalent to:

- `users`: UUIDv7 primary key, normalized unique login name, display name, Argon2id password encoding, enabled/owner state, password-change time, and UTC creation/update timestamps;
- `auth_sessions`: identifier, user foreign key, unique token digest, CSRF-token digest, UTC creation/last-seen/idle-expiry/absolute-expiry/revocation timestamps, and indexes that support lookup, revocation, and cleanup;
- bounded login-throttle state keyed without requiring a matching user row, with expiry suitable for safe cleanup.

The precise table and column names belong to the implementation change. Raw passwords, raw bearer tokens, and raw CSRF tokens must never be persisted.

## Rejected alternatives

- **Trusted reverse-proxy identity:** rejected initially because it makes authorization depend on deployment-specific header sanitization and offers no portable application session or logout boundary. It can be added only through an explicit trusted-proxy configuration and account-mapping design.
- **JWT access/refresh tokens:** rejected because local opaque sessions provide simpler revocation, logout, rotation, and incident response. Florabase has no disconnected verifier or multi-service requirement.
- **Client-side bearer-token storage:** rejected because JavaScript-readable storage unnecessarily exposes long-lived credentials to cross-site scripting.
- **HTTP Basic authentication:** rejected because browser credential caching, logout, brute-force controls, and future per-session revocation are poor fits.
- **OAuth, OIDC, an identity provider, or social login:** deferred until federation or external account lifecycle is a concrete requirement.
- **Redis-backed sessions or rate limits:** rejected because PostgreSQL is already durable and adequate for the initial scale; another stateful service would add operational burden without a current need.

## Consequences

Authentication implementation will require migrations, a small backend-owned authentication capability, CSRF-aware frontend calls, production origin/cookie configuration, and PostgreSQL-backed integration tests. Until that implementation is verified, only unauthenticated system health behavior may be considered safe to expose.

The design follows the current [OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [CSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html), and [password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) guidance. Session timeout and login-throttling choices also follow the principles in [NIST SP 800-63B](https://pages.nist.gov/800-63-4/sp800-63b.html).
