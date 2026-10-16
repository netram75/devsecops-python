# syntax=docker/dockerfile:1

# ---------- stage 1: install dependencies into a venv ----------
FROM python:3.12-slim AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY requirements.txt .
RUN pip install -r requirements.txt \
 && pip uninstall -y pip

# ---------- stage 2: runtime without any packaging tools ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH

# pip is only needed to build. Its vendored urllib3, msgpack and setuptools
# (pkg_resources) were the HIGH CVEs Trivy found in the first image, so the
# runtime image does not ship pip at all.
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/* \
 && python -m pip uninstall -y pip setuptools wheel || true \
 && rm -rf /usr/local/lib/python3.12/ensurepip /usr/local/bin/pip*

WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}
LABEL org.opencontainers.image.title="gearloop-backend" \
      org.opencontainers.image.source="https://github.com/netram75/devsecops-python" \
      org.opencontainers.image.version="${APP_VERSION}"

# Non-root runtime user with a fixed UID (Kubernetes runAsNonRoot checks the number).
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app \
 && chmod 0755 /usr/local/bin/docker-entrypoint.sh
USER 10001

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

ENTRYPOINT ["docker-entrypoint.sh"]
