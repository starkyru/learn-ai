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

    TODO: implement this function.

    Steps:
      1. If MANIFEST_PATH does not exist, return {}.
      2. Read JSON: `json.loads(MANIFEST_PATH.read_text())`.
      3. Convert each value dict back to a ManifestEntry dataclass.
      4. Return dict keyed by `source`.
    """
    raise NotImplementedError("TODO: implement load_manifest()")


def save_manifest(manifest: dict[str, ManifestEntry]) -> None:
    """
    Persist the manifest to disk as JSON.

    TODO: implement this function.

    Steps:
      1. Convert each ManifestEntry to a dict with `asdict()`.
      2. Serialise to JSON with indent=2.
      3. Write to MANIFEST_PATH (create parent dirs if needed).
    """
    raise NotImplementedError("TODO: implement save_manifest()")


# ---------------------------------------------------------------------------
# Content hashing
# ---------------------------------------------------------------------------


def content_hash(text: str) -> str:
    """
    Return a short SHA-256 hex digest of the document text.

    TODO: implement this function.

    Steps:
      1. hashlib.sha256(text.encode()).hexdigest()
      2. Return the first 16 characters (enough for collision resistance here).
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

    TODO: implement this function.

    Returns (new_count, changed_count, skipped_count).

    Algorithm for each path:
      1. Read the file text: Path(path).read_text(encoding="utf-8").
      2. Compute hash = content_hash(text).
      3. Look up path in manifest:
         - If present and manifest[path].content_hash == hash:
             skipped_count += 1; continue (no re-embedding needed).
         - If present but hash differs: changed_count += 1 (will re-embed).
         - If absent: new_count += 1.
      4. Chunk the text: chunks_text = simple_chunks(text, path).
      5. Embed all chunks in one call:
           result = provider.embed(chunks_text)
      6. Build IndexedChunk objects and append to in_memory_index.
         (In production you'd upsert to a vector DB here.)
      7. Update manifest[path] = ManifestEntry(
             source=path,
             content_hash=hash,
             ingested_at=<current ISO timestamp>,
             num_chunks=len(chunks_text),
             model=provider.embed_model,
         )
      8. Return (new_count, changed_count, skipped_count).

    Tip: use `from datetime import datetime, timezone` and
    `datetime.now(timezone.utc).isoformat()` for the timestamp.
    """
    raise NotImplementedError("TODO: implement ingest_documents()")


def remove_stale_entries(
    manifest: dict[str, ManifestEntry], current_paths: list[str]
) -> list[str]:
    """
    Remove manifest entries for documents that no longer exist.

    TODO: implement this function.

    Steps:
      1. Find keys in manifest that are NOT in current_paths.
      2. Delete them from manifest.
      3. Return the list of removed source paths.
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
