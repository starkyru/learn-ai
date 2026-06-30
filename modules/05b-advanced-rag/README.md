# Module 05b — Advanced RAG Architectures

> **Depth tags** 🟢 app-level · 🟡 build-one-piece-by-hand · 🔴 from-scratch

Module 05 built the **naive RAG** pipeline (chunk → embed → retrieve → rerank →
generate → cite) and made it measurably better with reranking and HyDE. That
pipeline is _open-loop_: it retrieves once, trusts whatever comes back, and
generates. It has no answer to the three questions that break real RAG systems:

1. **"What if the chunk is meaningless on its own?"** — "It grew 3%." Grew by
   _what_, in _which_ quarter? Embedding a context-free chunk buries it.
2. **"What if retrieval returned garbage?"** — naive RAG generates anyway, and
   the LLM confidently hallucinates over off-topic context.
3. **"What if the answer needs two hops?"** — "Which colleague of Marie Curie
   also won two Nobel Prizes?" No single chunk contains that; you must _connect_
   facts across documents.

This module is the four named architectures the field built to answer those
questions. Each one adds a **feedback loop or a structure** that naive RAG lacks.

> **Prerequisite:** finish module 05 (at least Tasks 1–2). This module assumes you
> can already explain "chunk → embed → retrieve → generate" and have written a
> cosine retriever once. We reuse that retriever as a black box here.

---

## The mental model (one paragraph)

Naive RAG is a straight line. Every architecture here bends that line into a
**loop** or swaps the **index**. **Contextual Retrieval** fixes the _index_: it
rewrites each chunk to be self-contained _before_ embedding, so retrieval finds
it at all. **Corrective RAG (CRAG)** adds a _grader after retrieval_: score the
chunks, and if they're weak, correct course (rewrite the query, fall back to web
search) instead of generating over noise. **Self-RAG** moves the decisions _into
the generation loop_: the model itself decides whether to retrieve, judges each
passage's relevance, and critiques whether its own answer is actually supported.
**GraphRAG** throws out the flat vector list entirely and builds a _graph_ of
entities and relations, so multi-hop questions become graph traversals. Same
retriever underneath; radically different control flow around it.

```
  Naive RAG:     query ──▶ retrieve ──▶ generate ──▶ answer   (no feedback)

  Contextual:    [index time] chunk + doc-context ──▶ embed   (better recall)
  CRAG:          query ──▶ retrieve ──▶ GRADE ──┬─ good ─▶ generate
                                                └─ bad ──▶ rewrite + web search ──▶ generate
  Self-RAG:      query ──▶ retrieve? ──▶ judge each passage ──▶ generate ──▶ self-critique
  GraphRAG:      query ──▶ find entities ──▶ traverse graph ──▶ generate over connected facts
```

---

## Concepts

### 1. Contextual Retrieval — fix the chunk before you embed it

A chunk like _"The model scored 88.7% on the benchmark."_ is nearly useless in
isolation: which model? which benchmark? A query for _"Claude's MMLU score"_
won't match it, because the chunk never says "Claude" or "MMLU". The words that
would make it findable live in **other** chunks of the document.

**Contextual Retrieval** (Anthropic, 2024) fixes this at index time: for each
chunk, ask an LLM to write a short (1–2 sentence) context that situates the chunk
_within its source document_, then **prepend that context to the chunk before
embedding** (and before BM25 indexing). The chunk you store for retrieval becomes:

```
[context: This is from Anthropic's 2024 model card, describing Claude 3.5
 Sonnet's evaluation results.]  The model scored 88.7% on the benchmark.
```

Now the embedding carries the missing nouns, and the query matches. Anthropic
reported this cut the top-20 retrieval **failure rate** by ~35% (contextual
embeddings alone), ~49% (adding contextual BM25), and ~67% (adding a reranker on
top). The
cost: one cheap LLM call per chunk at index time — paid once, amortised over every
future query. Prompt caching the document makes it nearly free.

> **Key idea:** the chunk you _embed_ and the chunk you _show the generator_ need
> not be identical. Contextual Retrieval embeds an _augmented_ chunk but can store
> the original text for generation.

### 2. Corrective RAG (CRAG) — grade retrieval, then self-correct

Naive RAG's fatal assumption: _retrieved == relevant_. CRAG (Yan et al., 2024)
breaks it with a **lightweight retrieval evaluator** that scores how well the
retrieved set answers the query, producing one of three verdicts:

| Verdict       | Meaning                              | Action                                  |
| ------------- | ------------------------------------ | --------------------------------------- |
| **Correct**   | at least one strongly relevant chunk | refine + keep the good chunks, generate |
| **Incorrect** | nothing relevant                     | discard all; **fall back** (web search) |
| **Ambiguous** | unsure                               | do both — keep chunks _and_ fall back   |

The "correction" is the loop naive RAG lacks: when the local corpus can't answer,
CRAG **rewrites the query** and reaches for an external source instead of
hallucinating. The evaluator is the heart of it — a fast model (or fine-tuned
T5 in the paper; we use the LLM-as-judge you already know) that returns a
relevance score per chunk, which we threshold into the three buckets.

> **Why it matters:** a RAG system that _knows when it doesn't know_ can say "I
> couldn't find this" or escalate — far safer than a confident wrong answer.

### 3. Self-RAG — let the model gate retrieval and critique itself

CRAG grades retrieval from the outside. **Self-RAG** (Asai et al., 2023) moves
every decision _inside_ the generation loop using **reflection tokens** — special
tokens the model emits to control its own behaviour:

| Reflection token | Question it answers                               |
| ---------------- | ------------------------------------------------- |
| **Retrieve**     | Do I need to retrieve for this query at all?      |
| **IsRel**        | Is this retrieved passage relevant?               |
| **IsSup**        | Is my generated claim _supported_ by the passage? |
| **IsUse**        | Is the answer actually useful (1–5)?              |

The real Self-RAG _trains_ a model to emit these tokens. We can't fine-tune here,
so we **emulate each reflection token with a prompted LLM-as-judge call** — same
control flow, no training. (The paper's `Retrieve` token actually has three values
— `yes` / `no` / `continue`, where `continue` reuses the already-retrieved passage;
our yes/no emulation collapses that third value away.) The payoff is **adaptive retrieval**: for _"What is
2+2?"_ the model answers `Retrieve=No` and skips the index entirely (faster,
cheaper, no irrelevant context); for _"What did the Q3 report say about
churn?"_ it retrieves, filters to relevant passages with `IsRel`, generates, then
verifies each sentence is grounded with `IsSup`.

> **CRAG vs Self-RAG:** CRAG is a fixed pipeline with one grader bolted on.
> Self-RAG is _the model_ deciding, step by step, whether to retrieve and whether
> to trust what it got. CRAG corrects retrieval; Self-RAG also critiques
> generation.

### 4. GraphRAG — when the answer lives _between_ documents

Vector RAG retrieves the top-k chunks _most similar to the query_. That fails for
two query shapes:

- **Multi-hop:** _"Which physicist who worked with Rutherford later led the
  Manhattan Project?"_ No chunk contains the whole chain; the answer is a _path_.
- **Global / "sense-making":** _"What are the main themes across all these
  reports?"_ No single chunk is "most similar"; the answer is a _summary of the
  whole corpus_.

**GraphRAG** (Microsoft, 2024) builds a **knowledge graph** instead of (or
alongside) a flat vector index: an LLM extracts **(entity, relation, entity)**
triples from each chunk; entities become **nodes**, relations become **edges**.
Now:

- **Local search** (multi-hop): find the entities in the query, walk their edges
  to gather _connected_ facts, generate over that neighbourhood.
- **Global search** (themes): cluster the graph into communities, summarise each,
  then map-reduce the summaries — but that's beyond this module's scope; we build
  local/multi-hop search.

Full Microsoft GraphRAG also does Leiden community detection and hierarchical
summarisation. We build the **core**: extraction → graph → multi-hop traversal,
**by hand** (🔴 — no `networkx`, no `graphrag` package; a graph is just a dict of
adjacency lists, and implementing it is the point).

---

## Tasks

All exercise code goes through the shared client — `get_provider()` /
`getProvider()` — never a hardcoded SDK. **Embeddings note:** Anthropic has no
`embed()`. Only **Task 1** embeds — for it use `LLM_PROVIDER=openai`, `ollama`,
`nvidia`, or `lmstudio`. Tasks 2–4 only call `chat()`, so any provider works
(Anthropic included).

### Task 1 🟡 — Contextual Retrieval

**Goal:** Cut retrieval failures by making each chunk self-contained before you
embed it.

**Files:**

- `py/01_contextual_retrieval.py`
- `ts/01-contextual-retrieval.ts`

**Steps:**

1. Implement `situate_chunk()` / `situateChunk()` — given the **whole document**
   and **one chunk**, prompt the LLM for a 1–2 sentence context that locates the
   chunk in the document.
2. Implement `build_contextual_index()` — for each chunk, prepend its generated
   context, then embed the **augmented** text. Keep the **original** text for
   display/generation.
3. The harness embeds the same corpus two ways — **naive** (raw chunk) and
   **contextual** — and runs queries whose answer chunks are context-poor (e.g.
   a pronoun-heavy chunk). Compare which index ranks the right chunk higher.

**Acceptance:**

- `situate_chunk` returns a non-empty string that names the document/topic, not a
  copy of the chunk.
- For the provided "context-poor" query, the contextual index ranks the correct
  chunk **at least as high** as the naive index — and strictly higher for at
  least one query.

### Task 2 🟡 — Corrective RAG (CRAG)

**Goal:** Stop generating over garbage. Grade retrieval; rewrite + fall back when
it's weak.

**Files:**

- `py/02_corrective_rag.py`
- `ts/02-corrective-rag.ts`

**Steps:**

1. Implement `grade_retrieval()` — LLM-as-judge scores each retrieved chunk's
   relevance to the query (0–1). Reduce to a verdict: **Correct** (max ≥ 0.7),
   **Incorrect** (max < 0.3), **Ambiguous** (in between).
2. Implement `rewrite_query()` — when the verdict is Incorrect/Ambiguous, ask the
   LLM to rewrite the query into a cleaner search query.
3. Implement `corrective_rag()` — wire the loop: retrieve → grade → on Correct,
   generate from kept chunks; on Incorrect, rewrite + use the `web_search_stub`
   fallback; on Ambiguous, do both and merge.
4. The harness runs an **in-corpus** query (→ Correct path) and an
   **out-of-corpus** query (→ Incorrect path → fallback) and prints which branch
   fired.

**Acceptance:**

- The in-corpus query takes the **Correct** branch; the out-of-corpus query takes
  the **Incorrect** branch and calls the fallback.
- `grade_retrieval` returns one score per chunk in `[0, 1]` and a correct verdict
  bucket for each.

### Task 3 🟡 — Self-RAG (reflection-token emulation)

**Goal:** Make retrieval _adaptive_ and make the model critique its own answer.

**Files:**

- `py/03_self_rag.py`
- `ts/03-self-rag.ts`

**Steps:**

1. Implement `should_retrieve()` — the **Retrieve** token: ask the LLM whether the
   query needs external knowledge (yes/no). Factual/closed-book → no.
2. Implement `grade_relevance()` — the **IsRel** token: per retrieved passage,
   relevant or not; keep only relevant ones.
3. Implement `grade_support()` — the **IsSup** token: given the generated answer
   and the kept passages, is the answer **fully / partially / not** supported?
4. Implement `self_rag()` — wire it: if `should_retrieve` is no, answer directly;
   else retrieve → filter by `IsRel` → generate → check `IsSup` and surface the
   verdict (a low-support answer is flagged, not silently returned).
5. The harness runs one closed-book query (→ skips retrieval) and one corpus query
   (→ full loop), printing each reflection decision.

**Acceptance:**

- The closed-book query (e.g. arithmetic) sets `Retrieve=No` and never calls the
  retriever; the corpus query sets `Retrieve=Yes`.
- `grade_relevance` drops at least one irrelevant passage on the corpus query.
- The final result carries an explicit `IsSup` verdict.

### Task 4 🔴 — GraphRAG (multi-hop, from scratch)

**Goal:** Answer a question whose answer is a _path_ across documents — with a
graph you build by hand.

**Files:**

- `py/04_graph_rag.py`
- `ts/04-graph-rag.ts`

**Constraint (🔴):** No `networkx`, no `graphrag` / `nano-graphrag` package. A
graph here is a plain dict of adjacency lists. Building it is the lesson.

**Steps:**

1. Implement `extract_triples()` — prompt the LLM to extract
   `(subject, relation, object)` triples from a chunk; parse the JSON.
2. Implement `KnowledgeGraph.add_triple()` / `.neighbors()` — store triples as an
   adjacency map `entity -> [(relation, other_entity), ...]` (both directions).
3. Implement `multi_hop_subgraph()` — BFS from the query's seed entities out to
   `depth` hops, collecting the triples encountered.
4. Implement `graph_rag_answer()` — find seed entities in the query, gather the
   multi-hop subgraph, serialise the triples into context, and ask the LLM to
   answer over **that** (not raw chunks).
5. The harness builds the graph from a small corpus and answers a 2-hop question
   that no single chunk contains.

**Acceptance:**

- `extract_triples` returns a list of 3-tuples (subject, relation, object).
- `KnowledgeGraph.neighbors(e)` returns edges in both directions.
- The 2-hop question is answered correctly using the assembled subgraph, and the
  printed subgraph shows the connecting path (e.g. A —works_with→ B —won→ Prize).

---

## Done when

- [ ] `01_contextual_retrieval` shows the contextual index out-ranks the naive
      index on at least one context-poor query.
- [ ] `02_corrective_rag` routes an in-corpus query to **Correct** and an
      out-of-corpus query to **Incorrect → fallback**.
- [ ] `03_self_rag` skips retrieval on a closed-book query, filters irrelevant
      passages on a corpus query, and reports an `IsSup` verdict.
- [ ] `04_graph_rag` answers a 2-hop question from a hand-built graph and prints
      the connecting path.

---

## Going deeper

- **Contextual Retrieval + reranking:** Anthropic's best result stacks contextual
  embeddings, contextual BM25 (module 04 Task 4), and a reranker (module 05 Task
  2). Combine all three on the same corpus and measure recall@10.
- **CRAG knowledge refinement:** the paper splits each chunk into "knowledge
  strips" and filters strip-by-strip, not chunk-by-chunk. Implement strip-level
  filtering and see if precision improves.
- **Self-RAG IsUse + tree decoding:** the real model scores answer usefulness
  (1–5) and can decode multiple candidate continuations, picking the one with the
  best weighted reflection score. Add an `IsUse` pass and a best-of-N selector.
- **GraphRAG global search:** add community detection (even naive connected
  components) + per-community summaries, then map-reduce them to answer a
  "what are the main themes?" query.
- **Hybrid graph + vector:** use vector retrieval to find seed nodes, then graph
  traversal to expand — the production sweet spot.

---

## Environment variables

No new env vars beyond module 00. Reminder:

```
LLM_PROVIDER=openai      # or ollama / nvidia / lmstudio — anything with embed()
                         # for Task 1. Tasks 2–4 work on any provider.
```

## Extra Python deps

None beyond the base install — these tasks use only `llm_core` plus the standard
library. (Task 4's graph is hand-rolled on purpose.)

```bash
uv sync                  # base deps are enough
```
