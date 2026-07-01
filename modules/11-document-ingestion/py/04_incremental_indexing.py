"""
Task 4 🟢 — Incremental indexing.

Re-embedding every document on every pipeline run is wasteful and slow.
Incremental indexing hashes each document's content, tracks which hashes
have already been embedded, and only re-embeds documents that changed or
are new.

What you'll learn:
  - Content-addressable storage: hash → no change → skip embedding
  - A simple on-disk manifest (JSON) to track ingested document hashes
  - Freshness: what to do when a document is deleted or renamed
  - How this pattern works at production scale (e.g. with Qdrant upserts)

How to run:
  uv run python modules/11-document-ingestion/py/04_incremental_indexing.py

Run it twice: the second run should report "0 new / 0 changed" for unchanged docs.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from llm_core import get_provider

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class ManifestEntry:
    source: str
    content_hash: str
    ingested_at: str          # ISO-8601 timestamp
    num_chunks: int
    model: str                # embedding model used


@dataclass
class IndexedChunk:
    id: str
    text: str
    source: str
    vector: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

MANIFEST_PATH = Path(__file__).parent.parent / ".index_manifest.json"


def load_manifest() -> dict[str, ManifestEntry]:
    """
    Load the manifest from disk.

    Hints:
      - If MANIFEST_PATH doesn't exist yet (first run), return an empty dict.
      - Otherwise parse its JSON and rebuild a `ManifestEntry` dataclass from each
        stored value (the JSON holds plain dicts — expand them into the dataclass).
      - Return a `dict[str, ManifestEntry]` keyed by each entry's `source`.
    """
    raise NotImplementedError("TODO: implement load_manifest()")


def save_manifest(manifest: dict[str, ManifestEntry]) -> None:
    """
    Persist the manifest to disk as JSON.

    Hints:
      - Turn each `ManifestEntry` dataclass into a plain dict (`asdict()`) so it is
        JSON-serialisable.
      - Serialise the whole mapping to indented JSON and write it to MANIFEST_PATH
        (ensure the parent dir exists first).
    """
    raise NotImplementedError("TODO: implement save_manifest()")


# ---------------------------------------------------------------------------
# Content hashing
# ---------------------------------------------------------------------------


def content_hash(text: str) -> str:
    """
    Return a short SHA-256 hex digest of the document text.

    Hints:
      - Hash the UTF-8 bytes of the text with SHA-256 (`hashlib`) and take the hex
        digest.
      - Truncate to the first 16 hex chars — enough collision resistance for a
        change-detection key, and keeps the manifest readable.
    """
    raise NotImplementedError("TODO: implement content_hash()")


# ---------------------------------------------------------------------------
# Chunker (simplified — reuse task 3 approach without import)
# ---------------------------------------------------------------------------


def simple_chunks(text: str, source: str, max_words: int = 150) -> list[str]:
    """Split text into word-bounded chunks of at most max_words words."""
    words = text.split()
    chunks: list[str] = []
    for i in range(0, len(words), max_words):
        chunks.append(" ".join(words[i : i + max_words]))
    return [c for c in chunks if c.strip()]


# ---------------------------------------------------------------------------
# Incremental indexer
# ---------------------------------------------------------------------------


def ingest_documents(
    paths: list[str],
    provider: Any,
    manifest: dict[str, ManifestEntry],
    in_memory_index: list[IndexedChunk],
) -> tuple[int, int, int]:
    """
    Ingest a list of document paths, skipping unchanged ones.

    Returns the tally (new_count, changed_count, skipped_count).

    Hints — loop over each path and let the content hash decide the work:
      - Read the file text and compute its `content_hash(...)`.
      - Compare against the manifest entry for that path (if any):
          * same hash  → nothing changed: bump the skipped tally and move on
            WITHOUT re-embedding (that's the whole point — save the API call).
          * different hash → count it as changed (fall through to re-embed).
          * no entry → count it as new (fall through to embed).
      - For new/changed docs: split with `simple_chunks(text, path)`, embed the
        whole batch in ONE `provider.embed(...)` call, wrap each result in an
        `IndexedChunk`, and append to `in_memory_index` (in production this is
        where you'd upsert to a vector DB).
      - Record the fresh state by writing a `ManifestEntry` back into the manifest
        for that path: its source, the new hash, a current UTC ISO-8601 timestamp,
        the chunk count, and `provider.embed_model`.
      - Return the three counts.

    Tip: `datetime.now(timezone.utc).isoformat()` gives you the timestamp.
    """
    raise NotImplementedError("TODO: implement ingest_documents()")


def remove_stale_entries(
    manifest: dict[str, ManifestEntry], current_paths: list[str]
) -> list[str]:
    """
    Remove manifest entries for documents that no longer exist.

    Hints:
      - Find the manifest keys that are absent from `current_paths` — those docs
        were deleted or renamed.
      - Delete each of them from the manifest (mutate it in place) and collect the
        removed source paths to return.
    """
    raise NotImplementedError("TODO: implement remove_stale_entries()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

SAMPLE_DIR = Path(__file__).parent.parent / "sample_docs"


def main() -> None:
    provider = get_provider()
    print(f"\nProvider: {provider.name}  |  Embed model: {provider.embed_model}\n")

    paths = [
        str(SAMPLE_DIR / "intro_to_rag.md"),
        str(SAMPLE_DIR / "vector_databases.html"),
    ]
    # Filter to files that actually exist on disk
    paths = [p for p in paths if Path(p).exists()]
    if not paths:
        print("No sample files found. Make sure sample_docs/ exists.")
        return

    manifest = load_manifest()
    index: list[IndexedChunk] = []

    print(f"[Run 1] Ingesting {len(paths)} documents...")
    new, changed, skipped = ingest_documents(paths, provider, manifest, index)
    save_manifest(manifest)
    print(f"  New: {new}  |  Changed: {changed}  |  Skipped: {skipped}")
    print(f"  Index size: {len(index)} chunks")

    print(f"\n[Run 2] Re-running with same files (should skip all)...")
    index2: list[IndexedChunk] = []
    new2, changed2, skipped2 = ingest_documents(paths, provider, manifest, index2)
    save_manifest(manifest)
    print(f"  New: {new2}  |  Changed: {changed2}  |  Skipped: {skipped2}")
    assert skipped2 == len(paths), "Second run should skip all unchanged docs"

    stale = remove_stale_entries(manifest, current_paths=paths)
    if stale:
        print(f"\n  Removed stale entries: {stale}")
    else:
        print("\n  No stale entries.")

    print("\nManifest saved to:", MANIFEST_PATH)
    print("Key insight: only changed or new docs get re-embedded — saves API costs.")


if __name__ == "__main__":
    main()
