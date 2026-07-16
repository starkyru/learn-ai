"""Shared test fixtures for the Module 07b Python service.

The only external boundary we fake is the LLM provider: everything else (config
validation, logging, the readiness probe, the FastAPI routing) is the real code
under test. ``FakeProvider`` implements the ``llm_core.LLMProvider`` protocol and
returns a deterministic answer, so the request path is exercised offline.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

import pytest
from llm_core import ChatMessage, ChatOptions, ChatResult, EmbeddingResult
from m07b_service.config import Settings
from m07b_service.db import connect
from m07b_service.migrations import apply_pending

# The FastAPI app (POST /ask, /readyz, auth, error handling) needs the
# `production` extra. When it is not installed — a base `uv run pytest` or the
# pre-push hook — skip only the tests that import it; the config, migration,
# redaction, and logging tests below run on base deps. CI installs the extra
# (see .github/workflows/ci.yml → py job) so these DO run there.
try:
    import fastapi  # noqa: F401
except ImportError:
    collect_ignore_glob = [
        "test_07b_ask.py",
        "test_07b_auth.py",
        "test_07b_bootstrap.py",
        "test_07b_errors.py",
        "test_07b_health.py",
        "test_07b_jobs_api.py",
        "test_07b_logging.py",
        "test_07b_startup.py",
    ]

# ── Synthetic identities + tenant-scoped corpus (TOY: the bearer token is the
#    user id). Two tenants; each with a viewer, and tenant A also has an operator.
TENANT_A = "tenant-a"
TENANT_B = "tenant-b"
VIEWER_A = "alice-viewer"
OPERATOR_A = "art-operator"
VIEWER_B = "bob-viewer"

# Both chunks share the query term "launch" but carry distinct markers, so a
# cross-tenant leak is detectable in BOTH directions.
RETRIEVAL_QUERY = "launch"
CHUNK_A_MARKER = "swordfish"
CHUNK_B_MARKER = "starfish"
CHUNK_A = f"Alpha team launch note: the code word is {CHUNK_A_MARKER}."
CHUNK_B = f"Bravo team launch note: the code word is {CHUNK_B_MARKER}."


def seed_identity(db_path: str) -> None:
    """Migrate + seed tenants, users (2 tenants; viewer+operator), docs, chunks."""
    apply_pending(db_path)
    conn = connect(db_path)
    try:
        conn.executemany(
            "INSERT INTO tenants (id, name) VALUES (?, ?)",
            [(TENANT_A, "Tenant A"), (TENANT_B, "Tenant B")],
        )
        conn.executemany(
            "INSERT INTO users (id, tenant_id, email, role) VALUES (?, ?, ?, ?)",
            [
                (VIEWER_A, TENANT_A, "alice@a.test", "viewer"),
                (OPERATOR_A, TENANT_A, "art@a.test", "operator"),
                (VIEWER_B, TENANT_B, "bob@b.test", "viewer"),
            ],
        )
        conn.executemany(
            "INSERT INTO documents (id, tenant_id, title) VALUES (?, ?, ?)",
            [("doc-a1", TENANT_A, "A doc"), ("doc-b1", TENANT_B, "B doc")],
        )
        conn.executemany(
            "INSERT INTO chunks (id, tenant_id, document_id, ordinal, content) VALUES (?, ?, ?, ?, ?)",
            [
                ("chunk-a1", TENANT_A, "doc-a1", 0, CHUNK_A),
                ("chunk-b1", TENANT_B, "doc-b1", 0, CHUNK_B),
            ],
        )
    finally:
        conn.close()


def bearer(token: str) -> dict[str, str]:
    """An ``Authorization: Bearer <token>`` header (TOY: the token is the user id)."""
    return {"Authorization": f"Bearer {token}"}


class FakeProvider:
    """A deterministic, offline stand-in for a real llm_core provider."""

    name = "fake"
    chat_model = "fake-chat"
    embed_model = "fake-embed"

    def __init__(self, answer: str = "CANNED-ANSWER") -> None:
        self.answer = answer
        self.calls: list[list[ChatMessage]] = []

    def chat(
        self,
        messages: Iterable[ChatMessage | dict[str, str]],
        options: ChatOptions | None = None,
    ) -> ChatResult:
        recorded = [
            m if isinstance(m, ChatMessage) else ChatMessage(m["role"], m["content"])  # type: ignore[index]
            for m in messages
        ]
        self.calls.append(recorded)
        return ChatResult(text=self.answer, model=self.chat_model)

    def chat_stream(
        self,
        messages: Iterable[ChatMessage | dict[str, str]],
        options: ChatOptions | None = None,
    ) -> Iterator[str]:
        yield self.answer

    def embed(self, input: list[str]) -> EmbeddingResult:  # noqa: A002 - protocol name
        raise NotImplementedError("FakeProvider does not embed")


@pytest.fixture
def make_provider():
    """Factory for a deterministic FakeProvider with a chosen canned answer."""

    def _make(answer: str = "CANNED-ANSWER") -> FakeProvider:
        return FakeProvider(answer)

    return _make


@pytest.fixture
def make_settings(tmp_path):
    """Build real Settings with a writable temp db path and sensible test defaults."""

    def _make(**overrides) -> Settings:
        base: dict[str, object] = {
            "service_env": "development",
            "provider": "ollama",
            "db_path": str(tmp_path / "service.sqlite"),
            "log_level": "INFO",
        }
        base.update(overrides)
        return Settings(**base)  # type: ignore[arg-type]

    return _make


@pytest.fixture
def seeded_settings(make_settings):
    """Settings whose DB is migrated AND seeded with tenants/users/docs/chunks."""
    settings = make_settings()
    seed_identity(settings.db_path)
    return settings
