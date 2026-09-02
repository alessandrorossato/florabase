# Security policy

Florabase has not published a stable release or formal supported-version policy. Security fixes are
currently evaluated against the latest `main` branch.

Do not include secrets, credentials, private collection data, or exploit details in a public issue.
If GitHub private vulnerability reporting is enabled for this repository, use it. No other private
reporting address is published here; configuring and documenting one remains a repository-owner
decision.

Florabase uses backend-owned local accounts, opaque PostgreSQL-backed sessions in HttpOnly cookies,
same-origin checks, and session-bound CSRF tokens. Public deployments require an operator-managed
HTTPS reverse proxy and exact canonical-origin configuration. See the detailed
[security architecture](docs/security.md) and [deployment guide](docs/deployment.md).

Never commit `.env`, database dumps, uploads, access tokens, or real credentials. If a secret is
exposed, revoke or rotate it immediately and remove it from current and historical publication as
appropriate; deleting only the latest file is not sufficient.
