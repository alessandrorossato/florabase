# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
FROM node:24.19.0-bookworm-slim@sha256:a9f5f7c91a432850b2a8a7797adf5eadb6c733ceed61167806cee7ea7fbc29df AS dependencies
ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
ENV COREPACK_HOME=/usr/local/share/corepack
RUN corepack enable
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
RUN pnpm install --frozen-lockfile

FROM dependencies AS build
COPY . .
ARG VERSION=0.1.0-beta.1
ARG REVISION=unknown
ARG SOURCE=https://github.com/alessandrorossato/florabase
RUN pnpm build && node build-notices.mjs > dist/THIRD_PARTY_NOTICES.txt && node -e 'require("fs").writeFileSync("dist/release.json", JSON.stringify({version: process.env.VERSION, revision: process.env.REVISION, source: process.env.SOURCE}))'

FROM nginxinc/nginx-unprivileged:stable-alpine-slim@sha256:5d8bb9437d74a600ec5dbf90c035451c724dc33eac8d3a71078f6f8612c345f6 AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY LICENSE /usr/share/nginx/html/LICENSE
ARG VERSION=0.1.0-beta.1
ARG REVISION=unknown
ARG SOURCE=https://github.com/alessandrorossato/florabase
LABEL org.opencontainers.image.title="Florabase frontend" \
    org.opencontainers.image.version=$VERSION \
    org.opencontainers.image.revision=$REVISION \
    org.opencontainers.image.source=$SOURCE \
    org.opencontainers.image.licenses="AGPL-3.0-or-later"
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=6 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1:8080/healthz
USER root
# Alpine fixes the pinned base predates (musl CVE-2026-107891, zlib CVE-2026-85091). Exact versions
# fail the build once Alpine supersedes them; remove this line when the base digest carries them.
RUN apk add --no-cache musl=1.2.6-r3 musl-utils=1.2.6-r3 zlib=1.4-r0 \
    && find /usr /bin /sbin -xdev -type f -perm /6000 -exec chmod a-s {} +
USER 101:101
EXPOSE 8080

FROM dependencies AS development
ENV HOME=/tmp/florabase-frontend-home
COPY . .
RUN chown -R node:node /app/node_modules \
    && chmod -R a+rX /usr/local/share/corepack \
    && install -m 0755 dev-entrypoint.sh /usr/local/bin/florabase-dev-entrypoint \
    && install -m 0755 dev-state-init.sh /usr/local/bin/florabase-dev-state-init
USER node
ENTRYPOINT ["florabase-dev-entrypoint"]
EXPOSE 5173
CMD ["pnpm", "dev"]
