# syntax=docker/dockerfile:1.7
FROM node:24.19.0-bookworm-slim AS dependencies
ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
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
COPY . .
RUN mkdir -p /app/node_modules/.tmp /app/node_modules/.vite \
    && chmod 1777 /app/node_modules/.tmp /app/node_modules/.vite
EXPOSE 5173
CMD ["pnpm", "dev"]
