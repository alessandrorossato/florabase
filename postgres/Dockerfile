# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
# Florabase PostgreSQL: the approved official image with its unused gosu executable removed.
# Deterministic by design: the base digest, this file and the entrypoint guard are the only
# inputs, and the release builds it with SOURCE_DATE_EPOCH from release/inputs.json, so every
# application release reproduces the same image identity. Never add per-build labels.
#
# The removal is a whiteout: gosu's original bytes remain in the unchanged upstream layer, but the
# container filesystem has no gosu. See docs/security/beta-distribution-001/postgresql-image.md.
FROM docker.io/library/postgres:18.6-alpine@sha256:123b17998ccaf47e53b502e8c6a1e79afd8f579c6f3eec83c563da026f957395
COPY --chmod=0755 florabase-postgres-entrypoint.sh /usr/local/bin/florabase-postgres-entrypoint
COPY --chmod=0755 florabase-postgres-refuse-root.sh /usr/local/bin/florabase-postgres-refuse-root
COPY LICENSE /usr/share/licenses/florabase/LICENSE
# zlib fix the pinned base predates (CVE-2026-4738); the exact version fails the build once Alpine
# supersedes it. apk.log records wall-clock install times, so it is removed to stay reproducible.
# Then remove the unused gosu executable, and make the upstream entrypoint refuse root on its
# second line. docker-ensure-initdb.sh (and its docker-enforce-initdb.sh link) source it first, so
# every entry point, including an overridden --entrypoint, refuses root before touching disk.
RUN apk add --no-cache zlib=1.4-r0 \
    && rm -f /var/log/apk.log \
    && rm /usr/local/bin/gosu \
    && sed -i '1a florabase-postgres-refuse-root || exit 64' /usr/local/bin/docker-entrypoint.sh \
    && test "$(sed -n 2p /usr/local/bin/docker-entrypoint.sh)" = "florabase-postgres-refuse-root || exit 64" \
    && grep -q '^source /usr/local/bin/docker-entrypoint.sh$' /usr/local/bin/docker-ensure-initdb.sh
LABEL org.opencontainers.image.title="Florabase PostgreSQL" \
    org.opencontainers.image.description="Official postgres:18.6-alpine without gosu; runs only as 70:70" \
    org.opencontainers.image.version="18.6-alpine-florabase.1" \
    org.opencontainers.image.source="https://github.com/alessandrorossato/florabase" \
    org.opencontainers.image.licenses="PostgreSQL AND AGPL-3.0-or-later" \
    org.opencontainers.image.base.name="docker.io/library/postgres:18.6-alpine" \
    org.opencontainers.image.base.digest="sha256:123b17998ccaf47e53b502e8c6a1e79afd8f579c6f3eec83c563da026f957395"
USER 70:70
ENTRYPOINT ["florabase-postgres-entrypoint"]
CMD ["postgres"]
