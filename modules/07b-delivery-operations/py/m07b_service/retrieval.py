"""Tenant-scoped retrieval + a privileged document write.

Retrieval is a NAIVE keyword match over the T2.2 ``chunks`` table — a stand-in
for the embedding retrieval taught in Module 05. The point of this module is the
TENANT FILTER: ``tenant_id = ?`` is applied INSIDE the query, so no row from
another tenant is ever returned (the filter runs before rows reach the caller,
not after rendering). Every statement is parameterised.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from .db import connect


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    document_id: str
    content: str


def retrieve(db_path: str, tenant_id: str, query: str, limit: int = 5) -> list[RetrievedChunk]:
    """Return chunks in ``tenant_id`` whose content contains ``query`` (toy match).

    The ``tenant_id = ?`` predicate is FIRST and load-bearing: a caller can never
    retrieve another tenant's chunks, even one that would match the query.
    """
    conn = connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, document_id, content FROM chunks "
            "WHERE tenant_id = ? AND content LIKE '%' || ? || '%' "
            "ORDER BY ordinal LIMIT ?",
            (tenant_id, query, limit),
        ).fetchall()
    finally:
        conn.close()
    return [RetrievedChunk(row["id"], row["document_id"], row["content"]) for row in rows]


def document_exists(db_path: str, tenant_id: str, document_id: str) -> bool:
    """True iff ``document_id`` exists AND belongs to ``tenant_id`` (tenant-scoped).

    Used before enqueuing an ingestion job so a caller gets a clean 404 for a
    missing or another tenant's document, rather than a foreign-key 500.
    """
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT 1 FROM documents WHERE tenant_id = ? AND id = ?",
            (tenant_id, document_id),
        ).fetchone()
    finally:
        conn.close()
    return row is not None


def create_document(db_path: str, *, tenant_id: str, title: str) -> str:
    """Create a document in the CALLER'S tenant (an operator-only write). Returns id."""
    doc_id = str(uuid4())
    conn = connect(db_path)
    try:
        conn.execute(
            "INSERT INTO documents (id, tenant_id, title) VALUES (?, ?, ?)",
            (doc_id, tenant_id, title),
        )
    finally:
        conn.close()
    return doc_id
