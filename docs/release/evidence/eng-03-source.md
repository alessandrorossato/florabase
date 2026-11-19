# ENG-03 production API route inventory

[ENG-03 acceptance](../acceptance-v1.md#optional-pre-10-improvements) requires a test of the
application's route table that fails if any operation besides sign-in, liveness and readiness lacks
the authentication dependency. [G-SEC](../scope-v1.md#release-gates) uses either the accepted
ENG-03 test or the recorded route review. [Batch 06](batch-06-hydrogen-security-remediation.md)
removed the four generated documentation and schema routes in production and added a production
allowlist regression. ENG-03 switches that regression to the same checker available at the command
line. The previously absent ENG-03 feature record enters as `implemented` with proposed
`best-effort` release membership, consistent with its optional PRE-1.0 scope.

## Run the check

From a source checkout with the locked backend dependencies installed, use the existing production
settings contract. This example uses a placeholder database location and an example origin. App
construction and enumeration require no database connection, server or lifespan startup.

```sh
cd backend
export FLORABASE_ENVIRONMENT=production
export FLORABASE_DATABASE_URL=postgresql+psycopg://placeholder@db/test
export FLORABASE_CANONICAL_ORIGIN=https://florabase.example
export FLORABASE_COOKIE_MODE=secure
export FLORABASE_CORS_ORIGINS='[]'
PYTHONPATH=src python scripts/check_api_routes.py
PYTHONPATH=src python -O scripts/check_api_routes.py --format json
```

The default format lists sorted operations and a summary. JSON includes each method, effective path
and declared access, totals, and separate lists for unexpected public operations and stale allowlist
entries. Exit `0` indicates a matching allowlist. Exit `1` indicates unexpected public operations or
approved entries that are missing or now authenticated. Exit `2` indicates an incomplete inventory
or CLI usage error. An incomplete inventory emits an error without partial counts. Application
construction failures report the exception type to avoid disclosing settings values.

On the Batch 06 base `fdc75e8`, both Python modes reported 234 operations with 231 declaring
authentication and three declaring no session authentication. The method totals were 105 GET,
73 POST, 25 PUT, 25 DELETE and six PATCH. The reviewed public operations are `POST /api/v1/auth/login`,
`GET /api/v1/health` and `GET /api/v1/ready`. The sign-in handler still validates the origin and
submitted credentials. Both violation lists were empty.

```text
ENG-03 PASS: 234 operations (3 public, 231 authenticated, 0 owner-restricted)
```

## What the inventory measures

- FastAPI's effective route contexts supply application, router, include-time and route-level
  dependencies, including nested dependencies. Mounted FastAPI apps are traversed under their
  mount prefixes and use their own dependency graphs. Uninspectable mounts, unsupported route types
  and dependency overrides fail the check. All registered HTTP paths, including hidden and
  unversioned routes, are in scope.
- The effective method set includes implicit methods registered by the framework, such as
  Starlette's `HEAD` for a plain `GET` route. The inventory preserves path converters and trailing
  slashes and refuses duplicate method and template shapes, ignoring parameter names and converter
  differences for collision detection.
- `authenticated` means the graph includes the actual `require_authenticated_actor` function.
  `owner-restricted` additionally requires the actual `require_owner` dependency to receive the
  actor from that authentication dependency. Current owner checks run inside handlers and are
  counted under `authenticated`. `public` means no recognized authentication dependency is
  declared. Function names and OpenAPI security metadata have no bearing on the result.
- This check describes registered routes at app construction. Runtime review covers handler and
  middleware behavior, route ordering for overlapping shapes, routes added during startup,
  trailing-slash redirects, session and owner enforcement, and the proxy and candidate images.
  Isolated tests separately exercise an anonymous `401` and a non-owner `403` on a disposable
  FastAPI app with the real dependencies. Existing production and development tests cover runtime
  sign-in, liveness, readiness, session access and the conditional docs paths.

## Regression and review

```sh
cd backend
PYTHONPATH=src python -m pytest -o addopts= scripts/test_check_api_routes.py
```

The negative control adds a hidden, unauthenticated `GET /unreviewed` to a disposable app. Its
normal and optimized Python processes both exit `1` and list precisely that route as unexpected.
The focused suite also exercises stale entries, inherited dependencies, mounts, multi-method
routes, implicit `HEAD`, template collisions, stable output and incomplete inventories.

The inspected Batch 07 AUTH worktree and certification sources have no changed path in common
with this increment. The approved ENG-02 source at `48cc11e` shares only an additive change to
`docs/progress.md`. The existing backend infrastructure test now runs the inventory. Portable
release smoke, Makefile and CI integration are outside this source increment.

Independent security review should rerun the standalone command and focused suite on the exact
source and again on the future integration base once Batch 07 lands. Add the standalone script
regressions to ongoing verification with the future batch's test ownership or invocation. Apply
the canonical gate to the integrated source and record operator acceptance before using this test
as G-SEC evidence. Candidate image, ingress and the other G-SEC clauses have their own evidence.
