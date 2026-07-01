"""
Task 5 🟡 — Permissions-aware retrieval.

In a real knowledge base, not every document is visible to every user.
This task teaches you to attach per-document access metadata (owner, group,
visibility) during ingestion and to enforce it at retrieval time so a user
only sees chunks they are authorised to read.

It also reinforces page/section-level citations: every chunk carries the
source document, section heading, and page number in its metadata so
answers can cite exactly where the information came from.

What you'll learn:
  - Attaching an ACL (Access Control List) to chunks at ingestion time
  - Filtering BEFORE and AFTER vector search (pre-filter vs post-filter)
  - Why pre-filtering reduces result-set size and protects privacy
  - Carrying source + section + page metadata for precise citations
  - How vector databases expose metadata filters (e.g. Qdrant's `must` clauses)

How to run:
  uv run python modules/11-document-ingestion/py/05_permissions_aware.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from llm_core import get_provider

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class ACL:
    """Access Control List for a document."""
    owner: str               # e.g. "alice"
    groups: list[str]        # e.g. ["engineering", "all"]
    visibility: str          # "private" | "group" | "public"


@dataclass
class PermissionedChunk:
    """A text chunk with embedded access metadata and citation info."""
    id: str
    text: str
    vector: list[float]
    # Citation metadata
    source: str              # file path or URL
    section: str             # heading text (e.g. "## Introduction")
    page: int                # page number (0 if not applicable)
    # Access metadata
    acl: ACL


@dataclass
class RetrievalResult:
    chunk: PermissionedChunk
    score: float             # cosine similarity (higher = more relevant)

    @property
    def citation(self) -> str:
        """Human-readable citation string."""
        parts = [f"source={self.chunk.source!r}"]
        if self.chunk.section:
            parts.append(f"section={self.chunk.section!r}")
        if self.chunk.page > 0:
            parts.append(f"page={self.chunk.page}")
        return ", ".join(parts)


# ---------------------------------------------------------------------------
# Sample corpus with ACLs
# ---------------------------------------------------------------------------

SAMPLE_DOCS = [
    {
        "text": "The quarterly revenue report shows a 12% increase in Q3.",
        "source": "finance/q3_report.pdf",
        "section": "## Revenue Summary",
        "page": 3,
        "acl": ACL(owner="cfo", groups=["finance", "exec"], visibility="group"),
    },
    {
        "text": "Employee handbook: all employees are entitled to 20 days of PTO.",
        "source": "hr/handbook.md",
        "section": "## Time Off Policy",
        "page": 0,
        "acl": ACL(owner="hr_team", groups=["all"], visibility="public"),
    },
    {
        "text": "The production database password is stored in the secrets vault.",
        "source": "ops/runbook.md",
        "section": "## Credentials",
        "page": 0,
        "acl": ACL(owner="ops_lead", groups=["sre", "devops"], visibility="group"),
    },
    {
        "text": "Our RAG pipeline uses section-aware chunking for better retrieval.",
        "source": "eng/architecture.md",
        "section": "## Document Ingestion",
        "page": 0,
        "acl": ACL(owner="alice", groups=["engineering", "all"], visibility="group"),
    },
    {
        "text": "The CEO's personal compensation details are strictly confidential.",
        "source": "exec/compensation.pdf",
        "section": "## Executive Pay",
        "page": 7,
        "acl": ACL(owner="board", groups=["board"], visibility="private"),
    },
]

# Users and their group memberships
USER_GROUPS: dict[str, list[str]] = {
    "alice": ["engineering", "all"],
    "bob": ["finance", "exec", "all"],
    "carol": ["sre", "devops", "all"],
    "guest": ["all"],
}


# ---------------------------------------------------------------------------
# Step 1 — Tag access metadata during ingestion
# ---------------------------------------------------------------------------


def tag_access(doc: dict[str, Any], acl: ACL, chunk_id: str, vector: list[float]) -> PermissionedChunk:
    """
    Create a PermissionedChunk by attaching ACL and citation metadata to a chunk.

    Hints:
      - Build and return a `PermissionedChunk`, copying the citation fields from
        `doc` (text, source, section, and page — default page to 0 when missing)
        and stamping on the passed-in `chunk_id`, `vector`, and `acl`.
    """
    raise NotImplementedError("TODO: implement tag_access()")


# ---------------------------------------------------------------------------
# Step 2 — Check whether a user may read a chunk
# ---------------------------------------------------------------------------


def user_can_access(user: str, chunk: PermissionedChunk) -> bool:
    """
    Return True if `user` is allowed to read `chunk`.

    Access rules (in order):
      1. If visibility == "public":  always allowed.
      2. If visibility == "private": only the owner is allowed.
      3. If visibility == "group":   allowed if the user belongs to at least one
         of the ACL's groups OR is the owner.

    Use USER_GROUPS to look up the user's group memberships.
    Unknown users have no groups.

    Hints:
      - Branch on `chunk.acl.visibility` and apply the three rules above.
      - For the "group" case, the user passes if they own the chunk OR any of
        their groups (from USER_GROUPS, defaulting to none for unknown users)
        intersects the chunk's ACL groups.
    """
    raise NotImplementedError("TODO: implement user_can_access()")


# ---------------------------------------------------------------------------
# Step 3 — Cosine similarity helper
# ---------------------------------------------------------------------------


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Compute cosine similarity between two equal-length vectors.

    Formula:  cos(a, b) = (a · b) / (‖a‖ · ‖b‖)

    Hints:
      - Compute the dot product of the paired components, and each vector's
        Euclidean norm (`math.sqrt` of its sum of squares).
      - Guard the divide: if either norm is 0, return 0.0 rather than dividing by
        zero.
      - Otherwise return the dot product divided by the product of the norms.
    """
    raise NotImplementedError("TODO: implement cosine_similarity()")


# ---------------------------------------------------------------------------
# Step 4 — Retrieval with ACL enforcement
# ---------------------------------------------------------------------------


def retrieve_for_user(
    query_vector: list[float],
    user: str,
    index: list[PermissionedChunk],
    k: int = 3,
    pre_filter: bool = True,
) -> list[RetrievalResult]:
    """
    Retrieve the top-k chunks relevant to `query_vector` that `user` may read.

    Supports two filtering modes (both should return the same results):

    PRE-FILTER (pre_filter=True) — filter the candidate set BEFORE scoring:
      1. Restrict the index to chunks where user_can_access(user, chunk) is True.
      2. Score the filtered candidates with cosine_similarity.
      3. Return top-k by score.

    POST-FILTER (pre_filter=False) — score ALL chunks, then filter:
      1. Score every chunk with cosine_similarity.
      2. Sort descending by score.
      3. Keep only results where user_can_access(user, chunk) is True.
      4. Return the first k of those.

    Pre-filtering is preferred in production: it is faster and avoids scoring
    documents the user can never see. Post-filtering is shown here for comparison.

    TODO: implement both branches.

    Returns a list of RetrievalResult sorted by score (highest first).
    """
    # TODO: implement retrieve_for_user
    raise NotImplementedError("TODO: implement retrieve_for_user()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    provider = get_provider()
    print(f"\nProvider: {provider.name}  |  Embed model: {provider.embed_model}\n")

    # Embed all sample documents
    texts = [doc["text"] for doc in SAMPLE_DOCS]
    print(f"Embedding {len(texts)} sample documents...")
    embed_result = provider.embed(texts)

    # Build the index
    index: list[PermissionedChunk] = []
    for i, (doc, vector) in enumerate(zip(SAMPLE_DOCS, embed_result.vectors)):
        chunk = tag_access(doc, doc["acl"], chunk_id=f"chunk_{i}", vector=vector)
        index.append(chunk)
    print(f"Index built: {len(index)} chunks with ACLs attached.\n")

    # Embed the query
    query = "What is the company's time off policy?"
    print(f'Query: "{query}"\n')
    query_vector = provider.embed([query]).vectors[0]

    # Retrieve for each user
    users = ["alice", "bob", "carol", "guest"]
    for user in users:
        groups = USER_GROUPS.get(user, [])
        print(f"User: {user!r} (groups: {groups})")

        results_pre = retrieve_for_user(query_vector, user, index, k=3, pre_filter=True)
        results_post = retrieve_for_user(query_vector, user, index, k=3, pre_filter=False)

        assert [r.chunk.id for r in results_pre] == [r.chunk.id for r in results_post], (
            "Pre-filter and post-filter should return the same chunks in the same order"
        )

        if results_pre:
            top = results_pre[0]
            print(f"  Top result : {top.chunk.text[:70]!r}")
            print(f"  Citation   : {top.citation}")
            print(f"  Score      : {top.score:.4f}")
        else:
            print("  No accessible results.")

        print(f"  Chunks returned: {len(results_pre)} "
              f"(pre-filter), {len(results_post)} (post-filter)\n")

    # Demonstrate that "guest" cannot see private or group-restricted docs
    print("Access summary (guest vs bob):")
    for chunk in index:
        guest_ok = user_can_access("guest", chunk)
        bob_ok = user_can_access("bob", chunk)
        print(f"  {chunk.source:<35}  guest={guest_ok}  bob={bob_ok}")

    print(
        "\nKey insights:"
        "\n  1. ACL metadata is attached at ingestion time — not at query time."
        "\n  2. Pre-filter avoids scoring documents the user cannot read (faster + safer)."
        "\n  3. Every result carries source + section + page for precise citations."
        "\n  4. In production, vector DBs like Qdrant support metadata filters natively."
    )


if __name__ == "__main__":
    main()
