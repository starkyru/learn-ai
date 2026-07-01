# Module 04 — Embeddings & Vectors

> **Depth tags** 🟢 app-level · 🟡 build-one-piece-by-hand · 🔴 from-scratch

Embeddings turn meaning into geometry. Once text lives in a vector space, "find
related passages" becomes "find nearby points" — and that's the engine that
powers search, RAG (Retrieval-Augmented Generation), recommendations, and anomaly detection.

This module builds that engine in layers: first by hand, then with a real
vector database, then by exploring how chunking and hybrid search change what
you retrieve.

---

## Concepts

### What is an embedding?

An embedding model maps a string to a fixed-length list of floats — a _vector_
in high-dimensional space (often 768 or 1536 dimensions). The model is trained
so that semantically similar strings land close together in that space. "The
cat sat on the mat" and "A feline rested on the rug" will have vectors much
closer to each other than either is to "The stock market fell sharply."

### Cosine similarity

The standard distance metric is **cosine similarity**:

```
cosine(a, b) = dot(a, b) / (|a| × |b|)
```

It measures the _angle_ between two vectors regardless of their magnitudes.
Most embedding models L2-normalise their output (`|v| = 1`), which reduces
cosine to a plain dot product — fast and simple.

Values: 1 = identical direction, 0 = orthogonal (unrelated), −1 = opposite.

### Brute-force vs ANN

With _n_ documents of dimension _d_, brute-force similarity takes O(n·d) per
query. At 1 million docs × 1536 dims that's 1.5 billion multiplications per
query — too slow. **Approximate Nearest Neighbour** (ANN) algorithms like
**HNSW** (Hierarchical Navigable Small World) build a graph at index time and
only visit a tiny fraction of vectors at query time. Trade-off: a small risk of
missing the true nearest neighbour, usually negligible in practice (recall@10

> 99 % at typical settings).

### Chunking

Embedding models have a token limit (commonly 256–512 tokens). Stuffing a whole
10-page document into one embedding loses detail. **Chunking** splits a document
into smaller overlapping passages. Key trade-offs:

| Strategy       | Pro                           | Con                       |
| -------------- | ----------------------------- | ------------------------- |
| Fixed-size     | Simple, predictable           | Can split mid-sentence    |
| Sentence-based | Natural boundaries            | Variable chunk sizes      |
| Overlapping    | No lost context at boundaries | More storage, more embeds |

Good chunk size depends on your embedding model's window and the nature of your
queries (fine-grained fact questions vs. broad summaries).

### Hybrid search & Reciprocal Rank Fusion

Dense retrieval excels at _semantic_ queries ("find text about felines" matches
"cats"). Sparse retrieval (BM25, Best Matching 25) excels at _exact-match_ queries — product
codes, model names, rare technical terms. **Hybrid search** runs both and
merges the ranked lists with **Reciprocal Rank Fusion** (RRF):

```
RRF_score(d) = Σ_ranker  1 / (k + rank(d, ranker))
```

`k = 60` is the standard smoothing constant. RRF doesn't require calibrating
scores across rankers — it only uses rank order, which makes it robust.

---

## Tasks

### Task 1 🔴 — Vector store from scratch

**Goal:** Understand exactly what a vector DB does by implementing one without
any library.

**Files:**

- `py/01_vector_store_scratch.py`
- `ts/01-vector-store-scratch.ts`

**Steps:**

1. Implement `VectorStore.add()` — store `(id, vector, text, metadata)`.
2. Implement `_cosine_similarity()` / `cosineSimilarity()` — the full formula
   with magnitude normalisation.
3. Implement `VectorStore.query()` — brute-force top-k using cosine.
4. Run the harness; it embeds the inline corpus and prints top-3 results for
   three queries.

**Acceptance:**

- Queries return sensible results (e.g. "cosine similarity" query returns a
  similarity-topic chunk at the top).
- `_cosine_similarity([1,0], [1,0])` returns 1.0;
  `_cosine_similarity([1,0], [0,1])` returns 0.0.

---

### Task 2 🟢 — Real vector DB (ChromaDB + Qdrant)

**Goal:** Index and query the same corpus using a production vector database.

**Files:**

- `py/02_real_vector_db.py`
- `ts/02-real-vector-db.ts`

**Steps:**

1. Embed the corpus with `get_provider().embed()`.
2. Implement `index_into_chroma()` — upsert documents with their vectors.
3. Implement `query_chroma()` — call `collection.query()` and convert
   L2 distances to similarity scores: `score = 1 / (1 + distance)`.
4. Run and compare results to Task 1.
5. (Optional) Implement the `QdrantVariant` stub at the bottom of each file.
   Start Qdrant with `docker run -p 6333:6333 qdrant/qdrant`.

**Acceptance:**

- The program indexes 8 documents, prints collection count = 8, and returns
  top-3 results for each query without errors.

**Why use a real DB?**
Chroma handles: persistence, HNSW indexing (fast ANN), metadata filtering,
multi-tenancy, and collection management. Your hand-rolled store from Task 1
has none of that.

---

### Task 3 🟡 — Chunking strategies

**Goal:** See how chunk boundaries affect retrieval quality.

**Files:**

- `py/03_chunking_strategies.py`
- `ts/03-chunking-strategies.ts`

**Steps:**

1. Implement `fixed_size_chunker` — split on word boundaries every ~N chars.
2. Implement `sentence_chunker` — group N sentences per chunk.
3. Implement `overlapping_chunker` — fixed-size with a sliding overlap window.
4. The harness embeds the same query against all three strategies and shows
   which strategy's top chunk is most relevant.

**Acceptance:**

- Each chunker returns a non-empty list of non-empty strings.
- The long document produces more chunks with smaller chunk sizes.
- Overlapping always produces at least as many chunks as fixed-size.

**Reflection:** Run with `chunk_size=100` vs `chunk_size=500`. Which queries
benefit from smaller chunks? Which benefit from larger ones?

---

### Task 4 🟡 — Hybrid search

**Goal:** Combine BM25 and dense retrieval with Reciprocal Rank Fusion.

**Files:**

- `py/04_hybrid_search.py`
- `ts/04-hybrid-search.ts`

**Steps:**

1. (Python) Implement `build_bm25()` using `rank_bm25.BM25Okapi`.
   (TypeScript) Implement `BM25.rank()` — the BM25 scorer is provided; fill in
   the term-scoring loop.
2. Implement `reciprocal_rank_fusion()` — sum `1 / (k + rank)` per document
   across all rankers, sort descending.
3. Run all three queries. Compare dense-only, BM25-only, and hybrid rankings.

**Acceptance:**

- For the query `"BM25 keyword ranking function"`, the doc about BM25 appears
  in the top 3 for BM25-only and hybrid, even if dense misses it.
- For the semantic query, dense retrieval finds semantically related docs that
  BM25 misses due to different wording.

---

## Done when

- [ ] `01_vector_store_scratch` / `01-vector-store-scratch` runs end-to-end and
      returns plausible top-k results.
- [ ] `02_real_vector_db` / `02-real-vector-db` indexes and queries via Chroma
      without errors.
- [ ] `03_chunking_strategies` / `03-chunking-strategies` shows different chunk
      counts and best-chunk text per strategy.
- [ ] `04_hybrid_search` / `04-hybrid-search` demonstrates that BM25 finds
      exact-match docs and hybrid beats either alone.

---

## Going deeper

- **HNSW internals:** Read the [HNSW paper](https://arxiv.org/abs/1603.09320)
  and the Qdrant blog on how the index is built layer by layer.
- **Matryoshka embeddings:** OpenAI's `text-embedding-3-small` supports
  truncating vectors to smaller dimensions (e.g. 256) with minimal quality loss.
  Try `provider.embed(texts)` and then slice `vector[:256]` — does retrieval
  quality hold up?
- **Chunking overlap ablation:** Systematically vary `chunk_size` and `overlap`
  across 5 queries and measure mean reciprocal rank (MRR). What's the sweet spot?
- **SPLADE / learned sparse:** Beyond BM25, models like SPLADE learn sparse
  representations that combine keyword precision with semantic generalisation.
- **Metadata filtering:** Chroma and Qdrant support `where` clauses
  (`{"topic": "rag"}`). Add a metadata filter to Task 2 and verify only
  on-topic docs are returned.

---

## Environment variables

No new env vars beyond what module 00 set up.

For Qdrant (Task 2 optional):

```
QDRANT_URL=http://localhost:6333   # already in .env.example
```

## Extra Python deps

```bash
uv sync --extra vectors   # installs chromadb, qdrant-client, rank-bm25
```
