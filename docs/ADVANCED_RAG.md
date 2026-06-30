# Advanced RAG Architectures — reference & cheat-sheet

Companion to **`modules/05b-advanced-rag/`**. Module 05 builds naive RAG (chunk →
embed → retrieve → rerank → generate → cite). This is the layer above: four named
architectures that each add a **feedback loop** or a **different index** to fix a
specific failure of the open-loop pipeline.

---

## Pick-by-failure table

| Your symptom                                                        | Reach for                | What it adds                                         |
| ------------------------------------------------------------------- | ------------------------ | ---------------------------------------------------- |
| Right chunk exists but retrieval never finds it (pronouns, context) | **Contextual Retrieval** | self-contained chunks _before_ embedding             |
| System hallucinates when the corpus doesn't contain the answer      | **Corrective RAG**       | a grader + rewrite/web-search fallback               |
| Wasted retrieval on closed-book queries; ungrounded answers slip by | **Self-RAG**             | adaptive retrieve + relevance + support gates        |
| Answer needs to connect facts across documents (multi-hop)          | **GraphRAG**             | entity/relation graph + traversal                    |
| "What are the themes across the whole corpus?" (global)             | **GraphRAG (global)**    | community summaries + map-reduce (out of scope here) |

These compose. Production stacks often run **Contextual embeddings + contextual
BM25 + reranking** (module 04/05) and wrap the result in a **CRAG or Self-RAG**
control loop, with **GraphRAG** for the multi-hop/global subset of queries.

---

## 1. Contextual Retrieval (Anthropic, 2024)

**Problem.** Chunking destroys context. "It grew 3%." — grew _what_? The nouns
that make a chunk findable live in _other_ chunks of the document.

**Fix.** At index time, for each chunk ask an LLM for a 1–2 sentence context that
situates it in its document, **prepend** that to the chunk, and embed the
_augmented_ text (and index it for BM25). Store the _original_ text for
generation — the embedded text and the shown text need not match.

```
embed(  "[ctx: From Acme's Q3 2024 report, on quarterly revenue.] It grew 3%..."  )
show (  "It grew 3% year over year..."  )   # generator sees the clean original
```

- **Result (Anthropic):** ~35% lower top-20 retrieval failure rate (contextual
  embeddings), ~49% adding contextual BM25, ~67% adding a reranker on top.
- **Cost:** one cheap LLM call per chunk, paid once at index time. **Prompt-cache
  the document** so the per-chunk marginal cost is tiny.
- **Pitfall:** don't let the context _replace_ the chunk — prepend, don't rewrite.
  Keep contexts short or they dominate the embedding.

## 2. Corrective RAG / CRAG (Yan et al., 2024)

**Problem.** Naive RAG assumes retrieved == relevant and generates regardless.

**Fix.** A **retrieval evaluator** scores the retrieved set, bucketed three ways:

| Verdict   | Trigger                 | Action                                   |
| --------- | ----------------------- | ---------------------------------------- |
| Correct   | a strongly relevant hit | refine + keep good chunks → generate     |
| Incorrect | nothing relevant        | discard → **rewrite query + web search** |
| Ambiguous | unsure                  | do both, merge                           |

- The paper uses a fine-tuned T5 evaluator + "knowledge refinement" (split chunks
  into strips, keep relevant strips). We use **LLM-as-judge** (0–1 score) and
  thresholds (`≥0.7` / `<0.3`).
- **Key value:** a system that _knows when it doesn't know_ and escalates beats a
  confidently-wrong one.
- **Pitfall:** calibrate thresholds on your corpus; a too-low "Incorrect" bar
  triggers needless web fallbacks.

## 3. Self-RAG (Asai et al., 2023)

**Problem.** Retrieval is unconditional; groundedness is unchecked.

**Fix.** The model emits **reflection tokens** to control itself:

| Token      | Decision                                  |
| ---------- | ----------------------------------------- |
| `Retrieve` | retrieve at all? (skip for closed-book)   |
| `IsRel`    | is this passage relevant? (filter)        |
| `IsSup`    | is my claim supported? (fully/partial/no) |
| `IsUse`    | is the answer useful? (1–5)               |

- Real Self-RAG **trains** a model to emit these. With no training budget you
  **emulate each token with a judge call** — identical control flow.
- **Payoff:** adaptive retrieval (cheaper, less distracting context) + a
  self-check that flags ungrounded answers instead of shipping them.

**CRAG vs Self-RAG:** CRAG = a fixed pipeline with one external grader on
_retrieval_. Self-RAG = _the model_ gating retrieval step-by-step **and**
critiquing its _own generation_. Self-RAG is finer-grained but chattier (more LLM
calls).

## 4. GraphRAG (Microsoft, 2024)

**Problem.** Vector top-k returns chunks similar to the query. Multi-hop ("which
colleague of X won a prize?") and global ("main themes?") questions have no single
"most similar" chunk — the answer is a _path_ or a _summary_.

**Fix.** Build a **knowledge graph**: LLM extracts `(entity, relation, entity)`
triples → entities are nodes, relations are edges.

- **Local / multi-hop search:** find query entities, BFS their neighbourhood,
  generate over the connected triples. (This is what module 05b builds, **by hand
  — no `networkx`/`graphrag`**: a graph is a dict of adjacency lists.)
- **Global / sense-making search:** cluster the graph (Leiden) into communities,
  summarise each, map-reduce the summaries. (Out of scope; see "Going deeper".)
- **Pitfall:** extraction quality caps everything — inconsistent entity names
  ("Marie Curie" vs "M. Curie") fragment the graph. Normalise entity keys.
- **Production sweet spot:** vector-retrieve seed nodes, then graph-traverse to
  expand — hybrid graph + vector.

---

## How module 05b maps to these

| Task | Pattern              | Depth | Core function you implement                                 |
| ---- | -------------------- | ----- | ----------------------------------------------------------- |
| 1    | Contextual Retrieval | 🟡    | `situate_chunk` + `build_contextual_index`                  |
| 2    | Corrective RAG       | 🟡    | `grade_retrieval` + `rewrite_query` + `corrective_rag`      |
| 3    | Self-RAG             | 🟡    | `should_retrieve` + `grade_relevance` + `grade_support`     |
| 4    | GraphRAG (multi-hop) | 🔴    | `extract_triples` + `KnowledgeGraph` + `multi_hop_subgraph` |

All exercise code goes through `get_provider()` / `getProvider()`. Only Task 1
embeds (use `LLM_PROVIDER=openai`/`ollama`/`nvidia`/`lmstudio`); Tasks 2–4 are
chat-only and run on any provider, Anthropic included.

## Papers

- Anthropic, _Introducing Contextual Retrieval_ (2024).
- Yan et al., _Corrective Retrieval Augmented Generation_ (CRAG, 2024) —
  [arXiv:2401.15884](https://arxiv.org/abs/2401.15884).
- Asai et al., _Self-RAG: Learning to Retrieve, Generate, and Critique through
  Self-Reflection_ (2023) — [arXiv:2310.11511](https://arxiv.org/abs/2310.11511).
- Edge et al. (Microsoft), _From Local to Global: A Graph RAG Approach to
  Query-Focused Summarization_ (2024) — [arXiv:2404.16130](https://arxiv.org/abs/2404.16130).
