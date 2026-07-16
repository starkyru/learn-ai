"""Toy identity + RBAC + tenant-scoped audit (framework-agnostic).

TOY IDENTITY: the bearer token IS the user id, resolved against the ``users``
table seeded in the DB. A real deployment uses opaque, short-lived, hashed
tokens or OIDC (see the README "going deeper"). The LOAD-BEARING parts here are
real: the role check (RBAC) and, in :mod:`m07b_service.retrieval`, the tenant
filter applied inside the query.

The FastAPI/Fastify glue (raising 401/403) lives in the app factory; this module
holds only the framework-agnostic pieces so both languages share the same shape.
Every SQL statement is parameterised. Audit rows record who/what/decision — never
the prompt/question content or any secret.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from uuid import uuid4

from .db import connect

# Roles ordered by privilege. A caller's role satisfies a requirement iff it
# ranks at or above the required role (operator ⊇ viewer). ``admin`` is reserved.
_ROLE_RANK: dict[str, int] = {"viewer": 1, "operator": 2, "admin": 3}


@dataclass(frozen=True)
class Principal:
    """The authenticated caller."""

    user_id: str
    tenant_id: str
    role: str


def parse_bearer_token(authorization: str | None) -> str | None:
    """Return the token from an ``Authorization: Bearer <token>`` header, else None."""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


def lookup_principal(db_path: str, token: str) -> Principal | None:
    """Resolve a token (TOY: the user id) to a Principal via the ``users`` table."""
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT id, tenant_id, role FROM users WHERE id = ?", (token,)
        ).fetchone()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    if row is None:
        return None
    return Principal(user_id=row["id"], tenant_id=row["tenant_id"], role=row["role"])


def has_role(principal: Principal, required: str) -> bool:
    """True iff the principal's role ranks at or above ``required``."""
    return _ROLE_RANK.get(principal.role, 0) >= _ROLE_RANK.get(required, 99)


def record_audit(
    db_path: str,
    *,
    actor: str | None,
    tenant_id: str | None,
    action: str,
    decision: str,
    request_id: str | None,
) -> None:
    """Append an audit event (actor, tenant, action, decision, request id).

    Deliberately stores NO prompt/question content or secrets — only who did
    what and whether it was allowed or denied.
    """
    conn = connect(db_path)
    try:
        conn.execute(
            "INSERT INTO audit_events (id, tenant_id, actor, action, decision, request_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid4()), tenant_id, actor, action, decision, request_id),
        )
    finally:
        conn.close()
