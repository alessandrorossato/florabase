# BATCH06_REMEDIATION_SCOPE_APPROVED

Sol approves the two bounded changes below for Hydrogen. Use exact main
`c555baabe916e3fea1ef2c8f834c747ced5aa926`. The production backend fix is required.

## Route verification

On 18 November 2026, Sol built both production runtime targets from the pinned Git tree and
used an internal Docker network with zero host-published ports. The backend used production
settings, secure cookies, an HTTPS canonical origin and an empty CORS list. The isolated
PostgreSQL 18.6 fixture used tmpfs and migrated to `20261110_0047`. This was a route check using
local application builds and a disposable database fixture. It supplies baseline route evidence
for G-SEC and leaves release image and real-host verification pending.

| Request without a session | Backend direct | Production nginx ingress |
| --- | --- | --- |
| `GET /docs` | 200, Swagger UI | 200, SPA index |
| `GET /docs/oauth2-redirect` | 200, Swagger OAuth redirect | 200, SPA index |
| `GET /openapi.json` | 200, OpenAPI JSON | 200, SPA index |
| `GET /redoc` | 200, ReDoc | 200, SPA index |
| `HEAD` on all four paths above | 200, empty body | 200, empty body |
| `POST /api/v1/auth/login` | 401, invalid synthetic credentials | 401, invalid synthetic credentials |
| `GET /api/v1/health` and `GET /api/v1/ready` | Both 200 | Both 200 |
| `GET /api/v1/auth/session` | 401, authentication required | 401, authentication required |
| `GET /healthz` | Frontend health probe | 200, plain text |

The four ingress GET bodies matched `/` byte for byte. The live application's resolved
dependency trees covered 234 API operations. Of these, 231 use the session authentication
dependency and three are callable without a prior session. Sign-in checks submitted credentials.
The three intentional public API operations match the G-SEC allowlist. The backend's four extra
unauthenticated documentation and schema routes violate the application-route clause. Nginx's
HTML is the public SPA shell. Offline `app.openapi()` produced all 234 operations before the fix.
Cleanup confirmed zero probe containers, networks and tagged images.

## Approved source changes

| Path | Authorization |
| --- | --- |
| `.github/workflows/ci.yml` | Replace exactly four `actions/checkout@v6` references and four `actions/upload-artifact@v7` references. Preserve triggers, jobs, permissions, credential settings, conditions and artifact uploads. |
| `scripts/test-beta-images.py` | Add focused regression coverage for the CI pins. |
| `backend/src/florabase/main.py` | Disable FastAPI's automatic HTTP schema and documentation routes in production at app construction. Preserve development access and offline `app.openapi()` generation. |
| `backend/tests/test_infrastructure.py` | Cover production route absence, development behavior and offline schema generation. Verify sign-in, health/readiness and an authenticated application endpoint on the disposable stack. |

The upstream GitHub API resolved each major tag and verified the signed commit. Both commits
also match the pins already used by the repository's release workflows.

- `actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803`, tag `v6.1.0`. [Upstream commit](https://github.com/actions/checkout/commit/d23441a48e516b6c34aea4fa41551a30e30af803)
- `actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9`, tag `v7.0.2`. [Upstream commit](https://github.com/actions/upload-artifact/commit/cf430e030ddbb5b0abf93d22962f4752f3646cd9)

## Ownership and stop point

Hydrogen creates `fix/batch-06-security-remediation` at the pinned base in a separate worktree,
runs `make feature-context`, and claims it as `AGENT_ID=hydrogen-batch06-security-remediation`
before editing. This is a scope handoff. Sol retains the evidence branch and claim `695d681f93a2`.
Hydrogen's reconnaissance and Batch 07 / Argon worktrees were clean at the pinned base. Argon
has no pending file changes in the approved paths. Recheck that boundary before writing.

The four approved paths are the entire implementation scope. Sol owns `docs/progress.md`,
`docs/release/evidence/batch-06-security-baseline.md`, this handoff, and
`docs/security/beta-distribution-001/postgresql-image.md`. Release inputs, PostgreSQL images and
pins, release workflows, generated API declarations, dependency locks and RC status records
are excluded. Require focused tests, exact-tree API drift checks, live negative and authenticated
controls, health/readiness and resource cleanup. Freeze the clean commit and return the commit,
tree, writer claim and evidence for independent QA before integration or canonical FULL.

Optional MEDIUM Python updates are deferred. Outstanding decisions include independent Grype
finding review, any advisory disposition or VEX, separate PostgreSQL maintenance approval,
final RC digest scans and attestations, and release immutability. Beta.6 and RC publication remain
operator actions. The Batch 06 implementation stops before push, PR, merge or publication.
