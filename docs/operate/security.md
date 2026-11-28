# Security baseline

> Summary: Authentication, session cookies, CSRF, network isolation, and the optional hardened container override.

- Secrets live outside version control. `.env` is ignored; `.env.example` contains replaceable
  examples and a valid representative production HTTPS origin, while the development Compose
  override supplies the loopback origin.
- Settings are centrally validated. Production requires an HTTPS canonical origin and secure
  cookies, rejects CORS and wildcard origins for the same-origin browser architecture, and
  defaults to debug off.
- PostgreSQL and the backend are internal-only in the production-oriented Compose file.
- API input must use Pydantic validation and database invariants must use constraints where appropriate.
- Uncaught backend errors stay visible in container logs; clients must not receive production stack traces or secret details.
- Attachment uploads accept only decoder-validated still JPEG, PNG, and WebP content, stream to a
  25 MiB application limit, treat bounded filenames only as display metadata, and resolve
  server-owned keys beneath a backend-only persistent trusted root. The production proxy permits
  32 MiB requests for multipart overhead; SVG and other active or unsupported content is rejected.
  Metadata and content retrieval require the owner session and use private, no-store responses.
- An external media reference stores validated HTTPS image and source URLs with attribution.
  Metadata writes, reads and migrations make no request to the image host. **Preview once**
  separately authorizes the browser to load a remote image in Media detail, Quick Preview or
  Photos. The UI discloses the remote host and the browser sends no referrer. The preview stores
  no snapshot and has no automatic retry.
- The owner can explicitly **Save local copy** or **Refresh local copy** through authenticated,
  CSRF-protected endpoints. The guarded backend fetch validates every destination and redirect,
  rejects non-public addresses, pins the connection to a validated address, verifies the hostname
  for HTTPS and bounds response size, time and image decoding. It sends no user credentials or
  cookies. The resulting protected local copy is served through Florabase without contacting the
  remote host. A failed refresh preserves the previous copy. The **Settings → Media** default only
  pre-selects the "Save a local copy" choice in the form; each fetch still requires the owner to save
  that image, and Florabase never fetches remote images automatically.
  [Media-library fetch safety](../features/explore/media-library.md#fetch-safety-and-snapshot-concurrency)
- Saving an external BotanicalIdentity cover requires a separate privacy acknowledgement. For a
  cover without a saved local copy, that acknowledgement permits later automatic browser display
  on the identity detail page. The browser sends no referrer, and Florabase adds no record or
  session data to the image URL. Failed image loads have no automatic retry. Media previews and
  online map tiles have their own controls.
- Collection origins uses local geography by default. Optional configured online tiles require an
  explicit visitor action and disclose IP, map tile area and app origin under the provider policy.
  Cross-origin Referer contains only the origin; no record path/query/hash. A tile error removes the
  layer without automatic retries. This is separate from external photo privacy described above.
- Backups contain sensitive collection and account data. Encrypt and restrict them, and test
  restoration.

Local owner authentication is implemented under `/api/v1/auth`. Health and readiness remain public;
application and administrative operations use the authenticated-actor dependency and an explicit
authorization dependency.

[ADR 0005](../decisions/0005-authentication-and-sessions.md) defines the accepted boundary: FastAPI owns local accounts and opaque PostgreSQL-backed sessions; the browser receives a secure, HTTP-only, same-site cookie; state-changing requests require a session-bound CSRF token; and reverse-proxy headers never assert identity. The first release permits one owner but uses real user and session records so later multi-user authorization remains possible. JWTs, proxy authentication, OAuth/OIDC, Redis, and external identity providers are deliberately outside the initial design.

The bundled production nginx sends `X-Content-Type-Options: nosniff`,
`Referrer-Policy: strict-origin-when-cross-origin`, `X-Frame-Options: DENY` and an enforcing
Content Security Policy. The policy restricts scripts, stylesheets, fonts, application requests
and service workers to the same origin. It permits HTTPS images for explicitly selected external
photos and online basemaps, and permits data and blob URLs only as image sources. Florabase's
existing opt-in controls govern when the browser contacts image and tile providers. The
`style-src-attr` exception permits style attributes in browser-generated original-image documents,
including blob originals. Inline `<style>` elements and inline scripts remain blocked.

The internet-facing proxy is responsible for TLS, HSTS after validation, request/body limits,
replacing untrusted forwarded headers, and source-address rate limiting. Preserve the bundled
headers through that proxy. Dependency updates are proposed by Dependabot; each update still
requires tests and release-note review.

## Local owner bootstrap

The release `compose.yaml` creates the first owner once from `FLORABASE_OWNER_LOGIN` and
`FLORABASE_OWNER_PASSWORD` ([ADR 0008](../decisions/0008-self-initializing-single-compose.md),
[ADR 0009](../decisions/0009-minimal-production-compose.md)). The backend container's guarded
`florabase-start` entrypoint runs `release_schema deploy` before starting `uvicorn`: it validates
both variables before any change, refuses one without the other or a password outside the policy,
creates the owner only while no user exists under the same advisory lock as the command below, and
never logs, echoes or stores the password outside its hash. Before `exec`ing `release_schema serve`
(`uvicorn`), `florabase-start` unsets both variables from the server process environment. A
database with users, including a restored one, never gets a new owner; the variables are then
ignored with a log notice.

Accepted trade-offs of the minimal three-service `compose.yaml` (ADR 0009):

- The initial owner password stays visible in the Compose manager's stack environment, `docker
  inspect florabase-backend`, and manager exports until the operator removes it. Mitigations:
  one-time use, process-environment scrubbing before `uvicorn` starts, the log notice and the
  documented password change at first sign-in ([installation](installation.md#4-sign-in-as-the-owner)).
- `florabase-backend` mounts `FLORABASE_BACKUP_DIR` read-write so `florabase-start` can write
  verified pre-upgrade dumps without a separate `migrate` container; keep encrypted off-host copies
  of paired backups.

Without those variables, and for source builds, create the first owner offline after applying
migrations, from an interactive terminal:

```bash
python3 ./scripts/workflow_environment.py prod compose -- run --rm backend python -m florabase.auth.bootstrap owner
```

The command prompts with `getpass`. For non-interactive automation, pass `--password-stdin` and
pipe one password line through standard input; never place the password in a command argument,
environment variable, Compose file, or image layer. The login name is normalized to lowercase
ASCII and must contain 3–64 letters, digits, dots, underscores, or hyphens. Passwords must contain
12–1024 characters. Bootstrap takes a PostgreSQL transaction-scoped advisory lock and refuses to
run once any user exists, including during concurrent attempts.

## Optional container hardening

Every image in the production `compose.yaml` runs as a dedicated non-root user (`db` `70:70`,
`backend` `10001:10001`, `frontend` `101:101`), strips setuid/setgid binaries (backend/frontend) or
removes `gosu` and refuses root with exit 64 (`florabase-postgres`), and publishes only `frontend`
on `127.0.0.1`.

To keep `compose.yaml` flat and readable for self-hosting managers (ADR 0009, ADR 0010), custom
networks and container-level hardening flags are omitted from the default file. What
defense-in-depth is absent by default:

- **Single default bridge network:** without separate `internal: true` and `app` networks, `db`
  and `frontend` share Docker's default project network (`db` still publishes no host port and
  requires `FLORABASE_DB_PASSWORD`).
- **Writable container overlay layer:** without `read_only: true`, a compromised runtime process
  can write inside its container overlay (root-owned `/app`, `/usr` and `/etc` remain non-writable
  to non-root UIDs).
- **Default Docker capability bounding set and `no-new-privileges`:** without `cap_drop: [ALL]` and
  `security_opt: ["no-new-privileges:true"]`, containers retain Docker's default capability
  bounding set (non-root processes still hold an empty effective/permitted capability set, and
  setuid/setgid bits are stripped from the images).

Operators who want those controls can layer a local override file alongside `compose.yaml`
(`docker compose -f compose.yaml -f compose.hardened.yaml up -d --wait`):

```yaml
services:
  db:
    read_only: true
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    tmpfs: ["/tmp", "/var/run/postgresql"]
    networks: [internal]
  backend:
    read_only: true
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    tmpfs: ["/tmp"]
    networks: [internal, app]
  frontend:
    read_only: true
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    tmpfs: ["/tmp"]
    networks: [app]

networks:
  internal:
    internal: true
  app:
```

## Owner credential management

In **Settings → Account**, enter the current password and a new password of 12–1,024
characters. The password, revocation of all old sessions, and issuance of the initiating
browser's replacement session commit together. Other browsers must sign in again. Tabs that
share the cookie may need to reload for a fresh CSRF token. If sign-out overlaps a password
change in another tab, use **Sign out** after that tab reports completion.

The password-change backoff bucket is separate from the public login bucket. The host-only
[offline recovery command](installation.md#recover-a-forgotten-owner-password)
bypasses both, clears both on success and revokes every session. It requires local deployment
administration and a healthy, writable database at the installed revision.

## Authentication implementation

The implementation deliberately stays within the small boundaries accepted by ADR 0005:

| Component                                             | Reuse boundary                                                                                                                                                                                                                             |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Password hashing and verification                     | `pwdlib[argon2]` 0.4.2 with Argon2id, `verify_and_update`, and a cached dummy Argon2id encoding for unknown users.                                                                                                                         |
| Session and CSRF token generation                     | Python `secrets` with an explicit 32-byte input.                                                                                                                                                                                           |
| Stored token digests and constant-time checks         | Python `hashlib.sha256` and `secrets.compare_digest`; SHA-256 is only for high-entropy tokens, never passwords.                                                                                                                            |
| Cookie handling                                       | Starlette `Response.set_cookie` and `delete_cookie`, with minimal Florabase policy selecting the production or loopback-development attributes.                                                                                            |
| Session persistence, expiry, rotation, and revocation | Alembic constraints/indexes, SQLAlchemy transactions, and PostgreSQL queries; Florabase code owns the required session policy and request dependency only.                                                                                 |
| CSRF and origin validation                            | FastAPI dependencies and Starlette request headers plus Python constant-time comparison. A small session-bound synchronizer-token check is required because the accepted design is application-specific; do not create generic middleware. |
| Login throttling                                      | An expiring PostgreSQL row created with `ON CONFLICT` and serialized with `SELECT ... FOR UPDATE`; the operator's HTTPS proxy provides any separate source-address limit.                                                                                       |
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
