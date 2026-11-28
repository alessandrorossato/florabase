# Install Florabase with portable Docker Compose

The portable `portable-compose.yaml` and its manual initialization, owner and upgrade commands
were the installation of `v0.1.0-beta.6`. From `v0.1.0-beta.7`, the single self-initializing
`compose.yaml` replaces them ([ADR 0008](decisions/0008-self-initializing-single-compose.md)).
Follow [Install Florabase](operate/installation.md). For `v0.1.0-beta.6` itself, read this page at the
`v0.1.0-beta.6` tag.

### Reverse proxy example

See [Put Florabase behind HTTPS](operate/installation.md#5-put-florabase-behind-https-and-check-readiness).

## Recover a forgotten owner password

See [Recover a forgotten owner password](operate/installation.md#recover-a-forgotten-owner-password).

## Upgrade

See [Upgrade](operate/installation.md#upgrade). A `v0.1.0-beta.6` installation moves to the new layout
through its paired backup and an [isolated restore](operate/installation.md#isolated-restore).

## Isolated restore

See [Isolated restore](operate/installation.md#isolated-restore).
