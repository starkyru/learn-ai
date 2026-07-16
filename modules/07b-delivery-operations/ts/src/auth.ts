/**
 * Toy identity + RBAC + tenant-scoped audit (framework-agnostic).
 *
 * TOY IDENTITY: the bearer token IS the user id, resolved against the `users`
 * table seeded in the DB. A real deployment uses opaque, short-lived, hashed
 * tokens or OIDC (see the README "going deeper"). The LOAD-BEARING parts here
 * are real: the role check (RBAC) and, in `retrieval.ts`, the tenant filter
 * applied inside the query.
 *
 * The Fastify glue (turning a null principal / failed role check into 401/403)
 * lives in the app factory; this module holds only the framework-agnostic
 * pieces so both languages share the same shape. Every SQL statement is
 * parameterised. Audit rows record who/what/decision — never the prompt content
 * or any secret.
 */

import { randomUUID } from "node:crypto";

import { openDb } from "./db.js";

// Roles ordered by privilege. A caller's role satisfies a requirement iff it
// ranks at or above the required role (operator ⊇ viewer). `admin` is reserved.
const ROLE_RANK: Record<string, number> = { viewer: 1, operator: 2, admin: 3 };

/** The authenticated caller. */
export interface Principal {
  userId: string;
  tenantId: string;
  role: string;
}

/** Return the token from an `Authorization: Bearer <token>` header, else null. */
export function parseBearerToken(authorization: string | undefined): string | null {
  if (!authorization) return null;
  const spaceIndex = authorization.indexOf(" ");
  if (spaceIndex < 0) return null;
  const scheme = authorization.slice(0, spaceIndex);
  if (scheme.toLowerCase() !== "bearer") return null;
  const token = authorization.slice(spaceIndex + 1).trim();
  return token.length > 0 ? token : null;
}

/** Resolve a token (TOY: the user id) to a Principal via the `users` table. */
export function lookupPrincipal(dbPath: string, token: string): Principal | null {
  let db;
  try {
    db = openDb(dbPath);
    const row = db
      .prepare("SELECT id, tenant_id, role FROM users WHERE id = ?")
      .get(token);
    if (!row) return null;
    return {
      userId: String(row.id),
      tenantId: String(row.tenant_id),
      role: String(row.role),
    };
  } catch {
    return null;
  } finally {
    db?.close();
  }
}

/** True iff the principal's role ranks at or above `required`. */
export function hasRole(principal: Principal, required: string): boolean {
  return (ROLE_RANK[principal.role] ?? 0) >= (ROLE_RANK[required] ?? 99);
}

export interface AuditEvent {
  actor: string | null;
  tenantId: string | null;
  action: string;
  decision: string;
  requestId: string | null;
}

/**
 * Append an audit event (actor, tenant, action, decision, request id).
 *
 * Deliberately stores NO prompt/question content or secrets — only who did what
 * and whether it was allowed or denied.
 */
export function recordAudit(dbPath: string, event: AuditEvent): void {
  const db = openDb(dbPath);
  try {
    db.prepare(
      "INSERT INTO audit_events (id, tenant_id, actor, action, decision, request_id) " +
        "VALUES (?, ?, ?, ?, ?, ?)",
    ).run(
      randomUUID(),
      event.tenantId,
      event.actor,
      event.action,
      event.decision,
      event.requestId,
    );
  } finally {
    db.close();
  }
}
