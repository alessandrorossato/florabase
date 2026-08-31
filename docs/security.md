# Security baseline

- Secrets live outside version control. `.env` is ignored; `.env.example` contains localhost-only values.
- Settings are centrally validated. Production requires an HTTPS canonical origin and secure
  cookies, rejects CORS and wildcard origins for the same-origin browser architecture, and
  defaults to debug off.
- PostgreSQL and the backend are internal-only in the production-oriented Compose file.
- API input must use Pydantic validation and database invariants must use constraints where appropriate.
- Uncaught backend errors stay visible in container logs; clients must not receive production stack traces or secret details.
- Future upload endpoints must constrain size, media type, decoded content, filenames, and path resolution; files must live on persistent storage outside container layers.
- Backups contain sensitive collection and account data. Encrypt and restrict them, and test
  restoration.

Local owner authentication is implemented under `/api/v1/auth`. Health and readiness remain
public; application and administrative operations use the authenticated-actor dependency and an
explicit authorization dependency. No botanical operation is exposed by this change.

[ADR 0005](decisions/0005-authentication-and-sessions.md) defines the accepted boundary: FastAPI owns local accounts and opaque PostgreSQL-backed sessions; the browser receives a secure, HTTP-only, same-site cookie; state-changing requests require a session-bound CSRF token; and reverse-proxy headers never assert identity. The first release permits one owner but uses real user and session records so later multi-user authorization remains possible. JWTs, proxy authentication, OAuth/OIDC, Redis, and external identity providers are deliberately outside the initial design.

The internet-facing proxy is responsible for TLS, HSTS after validation, request/body limits, appropriate CSP and other security headers, replacing untrusted forwarded headers, and source-address rate limiting. Dependency updates are proposed by Dependabot; each update still requires tests and release-note review.

## Local owner bootstrap

After applying migrations, create the first owner from an interactive terminal:

```bash
docker compose run --rm backend python -m florabase.auth.bootstrap owner
```

The command prompts with `getpass`. For non-interactive automation, pass `--password-stdin` and
pipe one password line through standard input; never place the password in a command argument,
environment variable, Compose file, or image layer. The login name is normalized to lowercase
ASCII and must contain 3–64 letters, digits, dots, underscores, or hyphens. Passwords must contain
12–1024 characters. Bootstrap takes a PostgreSQL transaction-scoped advisory lock and refuses to
run once any user exists, including during concurrent attempts.

## Authentication implementation

The implementation deliberately stays within the small boundaries accepted by ADR 0005:

| Component                                             | Reuse boundary                                                                                                                                                                                                                             |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Password hashing and verification                     | `pwdlib[argon2]` 0.3.1 with Argon2id, `verify_and_update`, and a cached dummy Argon2id encoding for unknown users.                                                                                                                         |
| Session and CSRF token generation                     | Python `secrets` with an explicit 32-byte input.                                                                                                                                                                                           |
| Stored token digests and constant-time checks         | Python `hashlib.sha256` and `secrets.compare_digest`; SHA-256 is only for high-entropy tokens, never passwords.                                                                                                                            |
| Cookie handling                                       | Starlette `Response.set_cookie` and `delete_cookie`, with minimal Florabase policy selecting the production or loopback-development attributes.                                                                                            |
| Session persistence, expiry, rotation, and revocation | Alembic constraints/indexes, SQLAlchemy transactions, and PostgreSQL queries; Florabase code owns the required session policy and request dependency only.                                                                                 |
| CSRF and origin validation                            | FastAPI dependencies and Starlette request headers plus Python constant-time comparison. A small session-bound synchronizer-token check is required because the accepted design is application-specific; do not create generic middleware. |
| Login throttling                                      | An expiring PostgreSQL row created with `ON CONFLICT` and serialized with `SELECT ... FOR UPDATE`; nginx provides the separate source-address limit.                                                                                       |
| Bootstrap owner                                       | Python `getpass`/standard input, one SQLAlchemy transaction, and PostgreSQL constraints/locking. No HTTP bootstrap endpoint or custom CLI framework is needed.                                                                             |

The selected Argon2id parameters are 65,536 KiB memory, 3 iterations, and parallelism 1. Five
hashes in the supported `python:3.14.7-slim-bookworm` backend container took 182.5, 176.2, 177.5,
179.0, and 175.5 ms (177.5 ms median) on the verification host. This exceeds ADR 0005's accepted
OWASP floor of 19 MiB, 2 iterations, and parallelism 1.

Login creates fresh, independent 32-byte random session and CSRF tokens. PostgreSQL stores only
their SHA-256 digests. The raw session token appears only in the session cookie; the successful
login JSON returns the CSRF token with `Cache-Control: no-store`. `GET /api/v1/auth/session` returns
only the authenticated owner identity and never rotates CSRF state. Clients retain the CSRF token
in memory and send it as `X-CSRF-Token` on state changes.

After a reload, the browser first reads `GET /api/v1/auth/session`. If the HttpOnly session cookie
is still valid, it then calls `POST /api/v1/auth/csrf` to replace that session's CSRF digest and
receive the new raw CSRF token once with `Cache-Control: no-store`. The recovery operation requires
the exact configured `Origin` and the valid HttpOnly/SameSite session cookie but intentionally does
not require the lost previous CSRF token. It neither creates nor rotates the session bearer, and
the previous CSRF token stops validating. Other state-changing endpoints retain both Origin and
synchronizer-token checks. Actor metadata and the current CSRF token exist only in React memory;
no authentication value is written to localStorage, sessionStorage, IndexedDB, URLs, or a
JavaScript-readable cookie.

Sessions expire after 24 hours of inactivity and after 30 days absolutely. Authentication refreshes
`last_seen_at` at most once every five minutes. Logout and the user-wide security-change primitive
revoke sessions immediately. Expired and revoked rows need no scheduler because they never
authenticate.

Five credential failures trigger a 5-second backoff. Further failures double the delay up to 15
minutes. Throttle rows expire after 24 hours, expired rows are removed opportunistically during
login, successful authentication removes the account row, and concurrent updates are serialized.
This account-keyed control complements rather than replaces reverse-proxy source-address limits.

Production uses `__Host-florabase-session` with `Secure`, `HttpOnly`, `SameSite=Strict`, `Path=/`,
and no `Domain`. Loopback development explicitly uses `florabase-session-dev` without `Secure`;
central validation forbids that mode outside development. Origin checks use only the configured
canonical origin and never forwarded headers.
