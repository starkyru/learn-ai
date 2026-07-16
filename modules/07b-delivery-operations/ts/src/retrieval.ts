/**
 * Tenant-scoped retrieval + a privileged document write.
 *
 * Retrieval is a NAIVE keyword match over the T2.2 `chunks` table — a stand-in
 * for the embedding retrieval taught in Module 05. The point of this module is
 * the TENANT FILTER: `tenant_id = ?` is applied INSIDE the query, so no row from
 * another tenant is ever returned (the filter runs before rows reach the caller,
 * not after rendering). Every statement is parameterised.
 */

import { randomUUID } from "node:crypto";

import { openDb } from "./db.js";

export interface RetrievedChunk {
  id: string;
  documentId: string;
  content: string;
}

/**
 * Return chunks in `tenantId` whose content contains `query` (toy match).
 *
 * The `tenant_id = ?` predicate is FIRST and load-bearing: a caller can never
 * retrieve another tenant's chunks, even one that would match the query.
 */
export function retrieve(
  dbPath: string,
  tenantId: string,
  query: string,
  limit = 5,
): RetrievedChunk[] {
  const db = openDb(dbPath);
  try {
    const rows = db
      .prepare(
        "SELECT id, document_id, content FROM chunks " +
          "WHERE tenant_id = ? AND content LIKE '%' || ? || '%' " +
          "ORDER BY ordinal LIMIT ?",
      )
      .all(tenantId, query, limit);
    return rows.map((row) => ({
      id: String(row.id),
      documentId: String(row.document_id),
      content: String(row.content),
    }));
  } finally {
    db.close();
  }
}

/** Create a document in the CALLER'S tenant (an operator-only write). Returns id. */
export function createDocument(
  dbPath: string,
  args: { tenantId: string; title: string },
): string {
  const id = randomUUID();
  const db = openDb(dbPath);
  try {
    db.prepare("INSERT INTO documents (id, tenant_id, title) VALUES (?, ?, ?)").run(
      id,
      args.tenantId,
      args.title,
    );
  } finally {
    db.close();
  }
  return id;
}

/**
 * True iff `documentId` exists AND belongs to `tenantId` (tenant-scoped).
 *
 * Used before enqueuing an ingestion job so a caller gets a clean 404 for a
 * missing or another tenant's document, rather than a foreign-key 500.
 */
export function documentExists(
  dbPath: string,
  tenantId: string,
  documentId: string,
): boolean {
  const db = openDb(dbPath);
  try {
    const row = db
      .prepare("SELECT 1 AS ok FROM documents WHERE tenant_id = ? AND id = ?")
      .get(tenantId, documentId);
    return row !== undefined;
  } finally {
    db.close();
  }
}
