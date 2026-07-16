# Reference container for the Module 07b TypeScript AI service.
#
# Build context MUST be the repository root (pnpm workspace + the shared
# @learn-ai/llm-core package):
#
#   docker build -f modules/07b-delivery-operations/ts/Dockerfile \
#     -t m07b-service-ts .
#
# Or, preferably, via Compose (see modules/07b-delivery-operations/compose.yaml).
#
# Security notes:
#   * Runs as the image's built-in non-root `node` user.
#   * Configuration comes ONLY from environment variables at runtime.
#   * We COPY explicit source paths — never `COPY . .` — so no `.env` or other
#     local secret can be baked into the image (belt-and-suspenders with
#     .dockerignore).
#
# The DB layer uses Node's built-in `node:sqlite` (zero-dependency, no native
# build). It is unflagged only on Node >= 24, so the base is pinned to a Node 24
# patch — CI must also run on Node 24.
#
# Reproducibility: the base is pinned to a specific patch tag and JS deps are
# pinned via pnpm-lock.yaml (`--frozen-lockfile`). For a byte-reproducible image
# in production, also pin the base by DIGEST, e.g.
#   FROM node:24.9.0-slim@sha256:<digest>
# (Omitted here as proportionate — these reference images are not built in CI.)
FROM node:24.9.0-slim

# HUSKY=0 skips the repo's `prepare` git-hook script during install (no .git here).
ENV NODE_ENV=production \
    HUSKY=0 \
    DB_PATH=/repo/data/07b-service.sqlite \
    MIGRATIONS_DIR=/repo/migrations

WORKDIR /repo

RUN corepack enable && corepack prepare pnpm@10.30.3 --activate

# 1) Manifests + the committed lockfile first (cached layer). `--frozen-lockfile`
#    pins exact versions for a reproducible image; the workspace globs for the
#    other modules simply match nothing inside the image.
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml ./
COPY packages/ts/llm-core/package.json packages/ts/llm-core/package.json
COPY modules/07b-delivery-operations/ts/package.json modules/07b-delivery-operations/ts/package.json
RUN pnpm install --frozen-lockfile --filter @learn-ai/m07b-service...

# 2) Sources ONLY (never the whole repo). The shared .sql migrations go to the
#    MIGRATIONS_DIR the runner reads at startup.
COPY packages/ts/llm-core packages/ts/llm-core
COPY modules/07b-delivery-operations/ts modules/07b-delivery-operations/ts
COPY modules/07b-delivery-operations/migrations /repo/migrations
RUN pnpm --filter @learn-ai/llm-core build

# 3) Create the datastore directory and hand it to the non-root user so the
#    default DB_PATH is writable and /readyz can go green. Compose mounts a named
#    volume here for persistence.
RUN mkdir -p /repo/data && chown -R node:node /repo/data

# 4) Drop privileges: the node image ships an unprivileged `node` user.
USER node

# Documented listen port (Compose maps it). Config is still env-driven.
EXPOSE 8001

# Startup validates config, applies migrations, and builds the provider (all
# fail-fast) before Fastify binds.
CMD ["pnpm", "--filter", "@learn-ai/m07b-service", "start"]
