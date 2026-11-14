# ENG-01 focused verification

13 November 2026 · Linux amd64 development host · ENG-01 candidate based on
`dd1ecb7949211a67e592c81af85b8404daabb164`. This record accompanies the implementation commit.
All credentials and data were generated for isolated tests.

| Requirement | Evidence |
| --- | --- |
| T1–T2 | Mounted auth ASGI tests covered 200, wrong-current 403, 429 and injected commit failures before response headers. PostgreSQL confirmed failed attempts persist without touching sessions and that a failed commit rolls back the credential and revocations. Tests covered query, alias, streamed size, Unicode/JSON and access-log handling. |
| T3–T4 | PostgreSQL and unit checks covered Origin/CSRF failures, length and Unicode policy, reuse, new credential and cookie, old session rejection, isolated backoff, concurrent public first failures and capped cleanup with a locked row and a private bucket. |
| T5–T6 | Independent transactions and PostgreSQL lock-wait observations covered login/rehash, change, reset, logout and CSRF recovery in competing orders. A SavedView foreign-key insert completed while the User credential lock was held. The suite checked refreshed expiry and revocation, persisted hashes, session counts and synchronized credential timestamps. |
| T7 | A controlling PTY exercised non-echoing confirmation. Unit and subprocess checks covered JSON framing, policy, invalid input, commit uncertainty, real reset, refused owner and revision, and DB lock timeout. |
| T8 | Vitest exercised Account validation, focus, field clearing, pending sign-out, dirty shell navigation, new CSRF, stale logout retries and late provider completion after session expiry. |
| T9 | Disposable portable Compose with locally built runtime images and PostgreSQL 18.6 exercised rotation through nginx, old password and independent session rejection, reset with both web services stopped, new login after restart and clean nginx/Uvicorn access logs. The portable restart and restore suite passed. Chromium 157 over loopback TLS separately passed Account sign-in, password change, sign-out and sign-in with the replacement password on disposable runtime images. |

Focused commands included `./scripts/test-integration.sh backend/tests/integration/test_authentication.py`
(44 passed), targeted backend pytest (45 passed), targeted Vitest (151 passed), Ruff, mypy,
ESLint, TypeScript, `make api-generate`, `make api-check`, and the feature graph and
verification-impact unit checks. Portable smoke used `scripts/smoke-portable-compose.py`
with a rendered portable Compose file selecting the locally built image pair and a disposable DB.

The browser smoke exercised the primary account workflow. Cross-tab response order was covered
with controlled frontend responses, and PostgreSQL races were exercised in real independent
transactions. The release-candidate browser/device matrix and canonical security gate remain
pending independent QA and operator authorization.
