# ENG-03 production API route inventory

[ENG-03 acceptance](../acceptance-v1.md#optional-pre-10-improvements) requires a test of the
application's route table that fails if any operation besides sign-in, liveness and readiness lacks
the authentication dependency. [G-SEC](../scope-v1.md#release-gates) uses either the accepted
ENG-03 test or the recorded route review. [Batch 06](batch-06-hydrogen-security-remediation.md)
removed the four generated documentation and schema routes in production and added a production
allowlist regression. ENG-03 switches that regression to the same checker available at the command
line. The ENG-03 feature record is `implemented`. The manifest records `best-effort` as a
proposal for the optional PRE-1.0 scope. Release membership awaits the operator's decision.

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
  Starlette's `HEAD` for a plain `GET` route. The inventory checks dispatch order before sorting the
  report. A later literal is checked against Starlette's compiled matcher. Two templates can be
  separated by disjoint methods, an incompatible literal segment or a different segment count
  without a catch-all. Other potential template intersections fail closed. The locked integer
  and UUID converters, for example, both accept a 32-digit segment. An earlier literal can reserve
  its exact URL from a later template. An earlier mount consumes its prefix even if its child
  responds with 404 or 405. Custom converters require review before the checker can accept them.
- The production infrastructure test also checks that every effective route is a FastAPI `APIRoute`.
- `authenticated` means the graph includes the actual `require_authenticated_actor` function.
  `owner-restricted` additionally requires the actual `require_owner` dependency to receive the
  actor from that authentication dependency. Current owner checks run inside handlers and are
  counted under `authenticated`. `public` means no recognized authentication dependency is
  declared. Function names and OpenAPI security metadata have no bearing on the result.
- This check describes registered routes at app construction. Runtime review covers handler and
  middleware behavior, custom dispatch, routes added during startup,
  trailing-slash redirects, session and owner enforcement, and the proxy and candidate images.
  Isolated tests separately exercise an anonymous `401` and a non-owner `403` on a disposable
  FastAPI app with the real dependencies. Existing production and development tests cover runtime
  sign-in, liveness, readiness, session access and the conditional docs paths.

## Independent reproduction without Docker

Use an existing Python 3.14 interpreter and the repository's [local backend setup](../../develop/development.md).
From the repository root, create a temporary virtual environment. The two lockfile installs need
access to the configured package index or a wheel cache for the reviewer's platform.

```sh
cd backend
review_dir=$(mktemp -d)
python3.14 -m venv "$review_dir/venv"
. "$review_dir/venv/bin/activate"
python -m pip install --require-hashes -r requirements.lock
python -m pip install --no-deps -r requirements-dev.lock
python -m pip check
export PYTHONPATH="$PWD/src"
export FLORABASE_ENVIRONMENT=test
export FLORABASE_DATABASE_URL=postgresql+psycopg://placeholder@db/test
export FLORABASE_CANONICAL_ORIGIN=https://florabase.example
export FLORABASE_COOKIE_MODE=secure
export FLORABASE_CORS_ORIGINS='[]'
export FLORABASE_ATTACHMENT_STORAGE_ROOT="$review_dir/attachments"
mkdir "$FLORABASE_ATTACHMENT_STORAGE_ROOT"

python -m pytest -o addopts= --collect-only -m 'not integration' -k test_check_api_routes
python -m pytest -o addopts= -m 'not integration' \
  -k 'test_check_api_routes or test_infrastructure or test_auth_api or test_auth_security'
python -m pytest -o addopts= -k 'test_unexpected_public_route_exits_nonzero or test_shadowed_allowlist_exits_incomplete'

export FLORABASE_ENVIRONMENT=production
python scripts/check_api_routes.py --format json > "$review_dir/routes.json"
python -O scripts/check_api_routes.py --format json > "$review_dir/routes-optimized.json"
cmp "$review_dir/routes.json" "$review_dir/routes-optimized.json"
python scripts/export_openapi.py --check
```

The focused command uses the same pytest `testpaths` as `make test-backend`. The negative control
tests launch separate normal and optimized Python subprocesses and assert their exact exit codes.
An extra public `GET /unreviewed` exits `1`. A shadowed allowlist entry exits `2` without a partial
inventory. The tests use FastAPI 0.162.0 and Starlette 1.6.0 from the backend lockfiles. The temporary
directory contains the reviewer's virtual environment, isolated attachment directory and reports.

The inspected Batch 07 AUTH worktree and certification sources have no changed path in common
with this increment. The approved ENG-02 source at `48cc11e` shares only an additive change to
`docs/progress.md`. The existing backend infrastructure test now runs the inventory. Portable
release smoke, Makefile and CI integration are outside this source increment.

Independent security review should rerun the commands on the exact source and again on the future
integration base once Batch 07 lands. Apply the canonical gate to the integrated source and record
operator acceptance before using this test as G-SEC evidence. Candidate image, ingress and the other
G-SEC clauses have their own evidence.
