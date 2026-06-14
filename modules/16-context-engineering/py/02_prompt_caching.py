"""
Task 2 — Prompt caching 🟢

What this teaches:
  - Large, repeated prefixes (a long system prompt, a document, tool definitions)
    normally re-charge the full input cost on every API call.
  - Prompt caching avoids this: the provider stores the KV-cache of a prefix and
    re-uses it on subsequent calls, charging a fraction of the normal rate.
  - Measuring cache hits via the usage field confirms the saving is real.

Beyond the abstraction:
  llm_core.chat() does not expose caching parameters. This task uses the Anthropic
  and/or OpenAI SDKs directly. That is intentional — it teaches where the abstraction
  breaks and why dropping down to the raw SDK is sometimes necessary.

Environment variables:
  ANTHROPIC_API_KEY — required for the Anthropic path
  ANTHROPIC_MODEL   — model to use (default: claude-opus-4-8)
  OPENAI_API_KEY    — required for the OpenAI path
  OPENAI_CHAT_MODEL — model to use (default: gpt-4o-mini)

How to run:
  uv run python modules/16-context-engineering/py/02_prompt_caching.py
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# A long, reusable "document" that forms the cached prefix.
# This needs to exceed the cache-eligibility threshold:
#   - Anthropic: 1024 tokens minimum.
#   - OpenAI: 1024 tokens minimum (caching is automatic).
# ---------------------------------------------------------------------------
LARGE_DOCUMENT = """
# The Complete Guide to Retrieval-Augmented Generation

## Chapter 1: Introduction

Retrieval-Augmented Generation (RAG) is a paradigm for enhancing large language models
by grounding their responses in retrieved external knowledge rather than relying solely
on information encoded in their parameters during training.

The core insight is simple: language models are excellent at reasoning and language
generation, but their knowledge is frozen at training time. RAG decouples knowledge
storage (a searchable document store) from reasoning (the LLM), allowing the system
to access up-to-date, domain-specific, or private information without expensive fine-tuning.

## Chapter 2: Architecture

A typical RAG system consists of three subsystems:

### 2.1 The Indexing Pipeline
Documents are ingested, cleaned, split into chunks, embedded into dense vectors using an
embedding model, and stored in a vector database. The embedding model maps text into a
high-dimensional space where semantic similarity corresponds to geometric proximity.

Common chunking strategies:
- Fixed-size chunking: split every N characters (simple but may cut sentences).
- Sentence-boundary chunking: split at sentence ends to preserve linguistic units.
- Semantic chunking: split when the semantic similarity between adjacent sentences drops
  below a threshold.
- Hierarchical chunking: store both small (precise) and large (context-rich) chunks;
  retrieve small, expand to large for the LLM.

### 2.2 The Retrieval Engine
At query time, the user's query is embedded with the same model used during indexing.
The top-K nearest vectors are retrieved from the database, typically using Approximate
Nearest Neighbour (ANN) algorithms such as HNSW or IVF.

Retrieval can be improved with:
- Hybrid search: combine dense (vector) and sparse (BM25 keyword) retrieval using
  Reciprocal Rank Fusion (RRF) to merge the two ranked lists.
- Re-ranking: apply a cross-encoder model to the top-K results to re-order them by
  relevance. Cross-encoders are slower than bi-encoders but more accurate.
- Query expansion: generate multiple paraphrases of the user's query to broaden recall.
- HyDE (Hypothetical Document Embeddings): ask the LLM to generate a hypothetical
  answer, embed that, and use it as the query vector.

### 2.3 The Generation Stage
The retrieved chunks are formatted into a context section of the prompt and passed to
the LLM along with the original query. The model generates an answer grounded in the
provided context.

Prompt structure for RAG:
  System: You are a helpful assistant. Answer only using the provided context.
          If the answer is not in the context, say "I don't know."
  User:   Context: {retrieved_chunks}
          Question: {user_query}

## Chapter 3: Evaluation

RAG systems require specialised evaluation metrics:

- Faithfulness: does the generated answer contain only claims supported by the context?
  A faithful answer does not hallucinate facts not present in the retrieved chunks.
- Answer relevance: does the answer address the user's actual question?
- Context precision: what fraction of retrieved chunks were actually relevant?
- Context recall: what fraction of the relevant chunks were retrieved?

Automated evaluation tools include RAGAS, TruLens, and DeepEval. Human evaluation
remains important for nuanced tasks.

## Chapter 4: Production Concerns

Deploying RAG at scale introduces engineering challenges:

1. Stale indexes: documents change but embeddings don't. Implement incremental re-indexing
   triggered by document updates.
2. Latency: embedding + ANN search + LLM generation adds up. Profile each step. Cache
   frequent queries. Use faster (smaller) embedding models if retrieval quality allows.
3. Context window management: 20 chunks × 300 tokens = 6000 tokens of context. This
   competes with system prompts and conversation history. Apply the retrieval budget
   discipline: decide in advance how many tokens to allocate to retrieved context.
4. Chunk boundary artefacts: a sentence split at a chunk boundary loses meaning. Use
   overlap (duplicate the last N tokens of one chunk into the start of the next).
5. Security: retrieved content can contain prompt injections. Sanitise or sandbox the
   context section.
""".strip()

QUESTIONS = [
    "What is HyDE and how does it improve retrieval?",
    "Name three production challenges mentioned in the document.",
]


@dataclass
class CallStats:
    call_number: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    latency_ms: float

    def estimated_cost_anthropic(self, model: str = "claude-opus-4-8") -> float:
        # Pricing per million tokens (approximate, 2025):
        prices = {
            "claude-opus-4-8":  {"input": 15.00, "output": 75.00, "cache_write": 18.75, "cache_read": 1.50},
            "claude-haiku-4-5": {"input": 0.80,  "output": 4.00,  "cache_write": 1.00,  "cache_read": 0.08},
        }
        p = prices.get(model, prices["claude-haiku-4-5"])
        return (
            (self.input_tokens / 1_000_000) * p["input"]
            + (self.output_tokens / 1_000_000) * p["output"]
            + (self.cache_write_tokens / 1_000_000) * p["cache_write"]
            + (self.cache_read_tokens / 1_000_000) * p["cache_read"]
        )


def print_stats(stats: CallStats, provider: str) -> None:
    print(
        f"  Call #{stats.call_number}: "
        f"input={stats.input_tokens:5d}  "
        f"cache_read={stats.cache_read_tokens:5d}  "
        f"cache_write={stats.cache_write_tokens:5d}  "
        f"output={stats.output_tokens:4d}  "
        f"latency={stats.latency_ms:.0f}ms"
    )
    if provider == "anthropic":
        print(f"           estimated cost: ${stats.estimated_cost_anthropic():.6f}")


# ---------------------------------------------------------------------------
# TODO 1: Implement demo_anthropic_caching.
#         Use the anthropic SDK directly.
#
#         For caching, the system message must be sent as a structured content block
#         with cache_control. Example:
#
#         client.beta.messages.create(
#             model=...,
#             max_tokens=512,
#             system=[
#                 {
#                     "type": "text",
#                     "text": LARGE_DOCUMENT,
#                     "cache_control": {"type": "ephemeral"},
#                 }
#             ],
#             messages=[{"role": "user", "content": question}],
#             betas=["prompt-caching-2024-07-31"],
#         )
#
#         Read usage.cache_read_input_tokens and usage.cache_creation_input_tokens.
#         Make the same call twice and observe the difference in cached tokens.
# ---------------------------------------------------------------------------
def demo_anthropic_caching() -> None:
    import anthropic  # pip install anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("  ANTHROPIC_API_KEY not set — skipping Anthropic demo.")
        return

    # TODO: create the Anthropic client and call the API twice.
    # client = anthropic.Anthropic(api_key=api_key)
    # model = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
    # all_stats = []
    # for i, question in enumerate(QUESTIONS, 1):
    #     start = time.time()
    #     response = client.beta.messages.create(
    #         model=model,
    #         max_tokens=512,
    #         system=[{"type": "text", "text": LARGE_DOCUMENT, "cache_control": {"type": "ephemeral"}}],
    #         messages=[{"role": "user", "content": question}],
    #         betas=["prompt-caching-2024-07-31"],
    #     )
    #     elapsed_ms = (time.time() - start) * 1000
    #     usage = response.usage
    #     stats = CallStats(
    #         call_number=i,
    #         input_tokens=usage.input_tokens,
    #         output_tokens=usage.output_tokens,
    #         cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
    #         cache_write_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
    #         latency_ms=elapsed_ms,
    #     )
    #     all_stats.append(stats)
    #     print_stats(stats, "anthropic")
    raise NotImplementedError("TODO: implement demo_anthropic_caching")


# ---------------------------------------------------------------------------
# TODO 2: Implement demo_openai_caching.
#         OpenAI caches automatically for inputs > 1024 tokens — no extra params.
#
#         Use the openai SDK:
#         client.chat.completions.create(
#             model=...,
#             messages=[
#                 {"role": "system", "content": LARGE_DOCUMENT},
#                 {"role": "user", "content": question},
#             ],
#         )
#
#         Read usage.prompt_tokens_details.cached_tokens to confirm cache hits.
#         Make the same call twice and compare cached_tokens on the second call.
# ---------------------------------------------------------------------------
def demo_openai_caching() -> None:
    import openai as _openai  # pip install openai
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  OPENAI_API_KEY not set — skipping OpenAI demo.")
        return

    # TODO: create the OpenAI client and call the API twice.
    # client = _openai.OpenAI(api_key=api_key)
    # model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    # for i, question in enumerate(QUESTIONS, 1):
    #     start = time.time()
    #     response = client.chat.completions.create(
    #         model=model,
    #         messages=[
    #             {"role": "system", "content": LARGE_DOCUMENT},
    #             {"role": "user", "content": question},
    #         ],
    #     )
    #     elapsed_ms = (time.time() - start) * 1000
    #     usage = response.usage
    #     cached = getattr(getattr(usage, "prompt_tokens_details", None), "cached_tokens", 0) or 0
    #     stats = CallStats(
    #         call_number=i,
    #         input_tokens=usage.prompt_tokens or 0,
    #         output_tokens=usage.completion_tokens or 0,
    #         cache_read_tokens=cached,
    #         cache_write_tokens=0,
    #         latency_ms=elapsed_ms,
    #     )
    #     print_stats(stats, "openai")
    raise NotImplementedError("TODO: implement demo_openai_caching")


def main() -> None:
    print("=== Task 2: Prompt Caching ===\n")
    print(f"Large document: {len(LARGE_DOCUMENT)} chars")
    print(f"Questions: {QUESTIONS}\n")

    print("--- Anthropic (cache_control breakpoints) ---")
    try:
        demo_anthropic_caching()
    except NotImplementedError as e:
        print(f"  {e}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print()
    print("--- OpenAI (automatic caching) ---")
    try:
        demo_openai_caching()
    except NotImplementedError as e:
        print(f"  {e}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print()
    print("Observation:")
    print("  On the first call: cache_read_tokens = 0, cache_write_tokens > 0.")
    print("  On the second call: cache_read_tokens > 0, cost is lower.")
    print("  Cache TTL is ~5 minutes for Anthropic — re-run quickly to see the hit.")
    print("  OpenAI caching is automatic; the same input bytes within a session reuse the cache.")


if __name__ == "__main__":
    main()
