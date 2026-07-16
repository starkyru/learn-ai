# Reference container for the Module 07b Python AI service.
#
# Build context MUST be the repository root, because the service depends on the
# shared workspace package `packages/py/llm_core`:
#
#   docker build -f modules/07b-delivery-operations/py/Dockerfile \
#     -t m07b-service-py .
#
# Or, preferably, via Compose (see modules/07b-delivery-operations/compose.yaml).
#
# Security notes:
#   * Runs as a non-root user.
#   * Configuration comes ONLY from environment variables at runtime.
#   * We COPY explicit source paths — never `COPY . .` — so no `.env` or other
#     local secret can be baked into the image (belt-and-suspenders with
#     .dockerignore).
#
# Reproducibility: the base image is pinned to a specific patch tag and the FULL
# runtime closure (service + llm_core deps, incl. transitive) is pinned in
# requirements.txt; llm_core is then installed with `--no-deps` so nothing
# resolves fresh at build time. For a byte-reproducible image in production,
# also pin the base by DIGEST and pin apt packages, e.g.
#   FROM python:3.11.14-slim@sha256:<digest>
#   RUN apt-get update && apt-get install -y --no-install-recommends <pkg>=<ver>
# (Omitted here as proportionate — these reference images are not built in CI.)
FROM python:3.11.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1) The full pinned runtime closure first (better layer caching). This includes
#    llm_core's own deps, so step 2 can install llm_core without re-resolving.
COPY modules/07b-delivery-operations/py/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 2) The shared provider-agnostic client (workspace package). `--no-deps` means
#    its `>=` ranges are NOT re-resolved — everything is already pinned above.
COPY packages/py/llm_core /tmp/llm_core
RUN pip install --no-cache-dir --no-deps /tmp/llm_core && rm -rf /tmp/llm_core

# 3) Service source + the shared .sql migrations the runner applies at startup.
COPY modules/07b-delivery-operations/py/m07b_service ./m07b_service
COPY modules/07b-delivery-operations/migrations ./migrations

# 4) Create the datastore directory and hand it to the non-root user, so the
#    default DB_PATH (/app/data/07b-service.sqlite) is writable and /readyz can
#    go green. Compose mounts a named volume here for persistence.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app/data
USER appuser

# The container's datastore + migrations locations (see Compose volume + DB_PATH).
ENV DB_PATH=/app/data/07b-service.sqlite \
    MIGRATIONS_DIR=/app/migrations

# Documented listen port (Compose maps it). Config is still env-driven.
EXPOSE 8000

# The `-m` entrypoint installs a redacting logger, validates config, and builds
# the provider at startup (fail-fast, no raw traceback on stderr) before binding.
CMD ["python", "-m", "m07b_service"]
