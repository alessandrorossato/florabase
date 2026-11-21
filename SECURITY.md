# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| Latest 1.x release | Yes, once v1.0.0 is published |
| `main` | Fixes are made here and released in the next version |
| Betas, release candidates and earlier releases | No |

No stable release is published yet. See the [versioning policy](docs/versioning.md).

## Reporting a vulnerability

Report privately through GitHub: on the repository's **Security** tab, choose **Report a
vulnerability**. This is the only private reporting channel; no email address is published.

If that button is not shown, private reporting is not active for the repository. Open a public
issue that asks the maintainer for a private contact and says nothing else about the problem.

Do not include secrets, credentials, private collection data, or exploit details in a public issue.
No response time is promised.

## Security model

Florabase uses backend-owned local accounts, opaque PostgreSQL-backed sessions in HttpOnly cookies,
same-origin checks, and session-bound CSRF tokens. Public deployments require an operator-managed
HTTPS reverse proxy and exact canonical-origin configuration. See the detailed
[security architecture](docs/security.md) and [installation guide](docs/installation.md).

Never commit `.env`, database dumps, uploads, access tokens, or real credentials. If a secret is
exposed, revoke or rotate it immediately and remove it from current and historical publication as
appropriate; deleting only the latest file is not sufficient.
