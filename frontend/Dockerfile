# syntax=docker/dockerfile:1

# ---------- stage 1: build the static bundle ----------
FROM node:22-alpine AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY index.html vite.config.js ./
COPY public ./public
COPY src ./src
RUN npm run build

# ---------- stage 2: serve it with unprivileged nginx ----------
FROM nginxinc/nginx-unprivileged:1.31-alpine AS runtime

# Drop nginx modules GearLoop never loads. image-filter pulls in libtiff, which is
# where the image's HIGH CVEs come from; no module, no package, no CVE.
USER root
RUN apk del --no-cache nginx-module-image-filter nginx-module-xslt nginx-module-geoip nginx-module-njs \
 && apk upgrade --no-cache \
 && rm -f /etc/nginx/conf.d/default.conf
USER 101

# The image runs envsubst on *.template at start: ${BACKEND_URL} becomes the
# backend address (compose: http://backend:8000, k8s: the backend Service).
COPY --chown=101:101 nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build --chown=101:101 /src/dist /usr/share/nginx/html

ARG APP_VERSION=dev
LABEL org.opencontainers.image.title="gearloop-frontend" \
      org.opencontainers.image.source="https://github.com/netram75/devsecops-python" \
      org.opencontainers.image.version="${APP_VERSION}"

ENV BACKEND_URL=http://backend:8000
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
