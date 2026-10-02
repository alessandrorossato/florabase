# syntax=docker/dockerfile:1.7
FROM node:24.19.0-bookworm-slim AS dependencies
ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
ENV COREPACK_HOME=/usr/local/share/corepack
RUN corepack enable
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
RUN pnpm install --frozen-lockfile

FROM dependencies AS build
COPY . .
RUN pnpm build

FROM nginxinc/nginx-unprivileged:1.29.4-alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
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
