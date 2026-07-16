-- Migration 0001 — initial schema (UP).
--
-- SQLite-portable DDL shared by BOTH the Python (stdlib sqlite3) and the
-- TypeScript (node:sqlite) runners. Every tenant-scoped table carries a
-- `tenant_id` with a foreign key, and useful indexes back the tenant filter and
-- the lookups the service performs. `schema_migrations` is owned by the runner,
-- not created here.
--
-- Timestamps are TEXT ISO-8601 (UTC) via datetime('now') — portable across both
-- SQLite bindings. Foreign keys are enforced (the runner sets
-- `PRAGMA foreign_keys = ON` on every connection).

CREATE TABLE tenants (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE users (
    id         TEXT PRIMARY KEY,
    tenant_id  TEXT NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    email      TEXT NOT NULL,
    -- Role is an enum enforced by a CHECK (T2.3 uses viewer/operator; admin is
    -- reserved for later). Keeping it a column avoids a join on the hot path.
    role       TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('viewer', 'operator', 'admin')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (tenant_id, email)
);
CREATE INDEX idx_users_tenant ON users (tenant_id);

-- documents has a UNIQUE (tenant_id, id) so child rows can reference it with a
-- COMPOSITE foreign key, guaranteeing the referenced document belongs to the
-- SAME tenant (a plain document_id FK would let tenant B attach tenant A's doc).
CREATE TABLE documents (
    id         TEXT PRIMARY KEY,
    tenant_id  TEXT NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    title      TEXT NOT NULL,
    source_uri TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (tenant_id, id)
);
CREATE INDEX idx_documents_tenant ON documents (tenant_id);

CREATE TABLE chunks (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    document_id TEXT NOT NULL,
    ordinal     INTEGER NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (document_id, ordinal),
    -- Composite FK: the (tenant_id, document_id) pair must exist in documents,
    -- so a chunk can never point at another tenant's document.
    FOREIGN KEY (tenant_id, document_id)
        REFERENCES documents (tenant_id, id) ON DELETE CASCADE
);
CREATE INDEX idx_chunks_tenant ON chunks (tenant_id);
CREATE INDEX idx_chunks_document ON chunks (document_id);

CREATE TABLE ingest_jobs (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    -- Nullable (a job may exist before its document is materialised). When set,
    -- the composite FK requires the document to belong to the SAME tenant.
    document_id TEXT,
    status      TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'dead')),
    retries     INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 5,
    last_error  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (tenant_id, document_id)
        REFERENCES documents (tenant_id, id) ON DELETE CASCADE
);
CREATE INDEX idx_ingest_jobs_tenant ON ingest_jobs (tenant_id);
CREATE INDEX idx_ingest_jobs_status ON ingest_jobs (status);

CREATE TABLE idempotency_keys (
    key        TEXT NOT NULL,
    scope      TEXT NOT NULL,
    tenant_id  TEXT NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    result_ref TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (tenant_id, scope, key)
);

-- Audit events keep a NULLABLE tenant FK with ON DELETE SET NULL: NULL supports
-- system/unauthenticated events and the trail survives tenant deletion (the row
-- stays, tenant_id becomes NULL), but a NON-EXISTENT tenant id is rejected so an
-- event cannot be misattributed to an arbitrary tenant.
CREATE TABLE audit_events (
    id         TEXT PRIMARY KEY,
    tenant_id  TEXT REFERENCES tenants (id) ON DELETE SET NULL,
    actor      TEXT,
    action     TEXT NOT NULL,
    decision   TEXT,
    request_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_audit_events_tenant ON audit_events (tenant_id);
CREATE INDEX idx_audit_events_request ON audit_events (request_id);
