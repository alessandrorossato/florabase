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

FROM nginxinc/nginx-unprivileged:1.29.4-alpine@sha256:a6c4f61f456b85b8fdf7ec7ab28cc3e299440e6fb4a9dea520e5fd8fd440025e AS runtime
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
