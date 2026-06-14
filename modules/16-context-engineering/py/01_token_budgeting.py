"""
Task 1 — Token budgeting 🟢

What this teaches:
  - LLMs process tokens, not characters or words. Knowing the exact token count
    before you send a request lets you stay within context limits and predict cost.
  - When a document is too long to fit in the context window, you must choose a
    truncation strategy: keep the beginning (head), the end (tail), or sacrifice
    the middle while preserving both ends (middle-out).
  - Each strategy has different recall properties for downstream tasks — which
    part you keep matters.

Dependencies:
  tiktoken — install with: uv sync --extra context
  (or: pip install tiktoken)

How to run:
  uv run python modules/16-context-engineering/py/01_token_budgeting.py
"""

from __future__ import annotations

# TODO: uncomment once tiktoken is installed
# import tiktoken

# ---------------------------------------------------------------------------
# A long sample text to experiment with.
# ---------------------------------------------------------------------------
SAMPLE_TEXT = """
Retrieval-Augmented Generation (RAG) is a technique that improves large language model
outputs by retrieving relevant documents from an external knowledge base before generating
a response. Unlike pure parametric models that rely solely on weights learned during
training, RAG systems can incorporate up-to-date or domain-specific information at
inference time. This makes them particularly useful for question answering, enterprise
search, and chatbots that need factual grounding.

The core RAG pipeline consists of three stages. First, during indexing, documents are
split into chunks and embedded into dense vectors using an embedding model. These vectors
are stored in a vector database such as Chroma, Qdrant, or Pinecone. Second, during
retrieval, the user's query is embedded with the same model, and the top-K most similar
chunks are retrieved via approximate nearest-neighbour search. Third, during generation,
the retrieved chunks are prepended to the prompt (often in a "context" section) and the
language model generates an answer conditioned on both the query and the retrieved text.

A number of refinements improve basic RAG. Hybrid search combines dense vector similarity
with sparse keyword search (BM25), which helps for queries with rare or technical terms.
Re-ranking uses a cross-encoder model to re-score the top-K retrieved chunks and reorder
them before passing to the generator. Query expansion generates multiple paraphrases of
the user's question to broaden retrieval coverage. Reciprocal Rank Fusion merges result
lists from multiple retrievers without requiring score calibration.

Evaluating RAG pipelines requires specialised metrics. Faithfulness measures whether the
generated answer is grounded in the retrieved context (no hallucinations). Answer relevance
measures whether the answer actually addresses the question. Context precision and recall
measure whether the right chunks were retrieved. Tools such as RAGAS and TruLens automate
these evaluations on labelled datasets.

Production RAG systems face additional challenges: stale indexes (documents change but
embeddings don't), chunk boundary artefacts (a sentence split mid-concept loses meaning),
retrieval latency (embedding + ANN search adds hundreds of milliseconds), and context
window management (20 retrieved chunks × 300 tokens each = 6000 tokens of context, which
can crowd out reasoning space). Careful engineering of chunk size, overlap, and retrieval
count is required to balance quality and cost.
""".strip()

MAX_TOKEN_BUDGET = 200  # a tight budget to make truncation interesting


# ---------------------------------------------------------------------------
# TODO 1: Implement count_tokens using tiktoken.
#         Use the "cl100k_base" encoding (GPT-4 / GPT-3.5 tokeniser).
#         Steps:
#           enc = tiktoken.get_encoding("cl100k_base")
#           return len(enc.encode(text))
# ---------------------------------------------------------------------------
def count_tokens(text: str) -> int:
    # TODO: implement with tiktoken
    # enc = tiktoken.get_encoding("cl100k_base")
    # return len(enc.encode(text))

    # Rough fallback until you implement the above:
    return int(len(text.split()) * 1.3)


# ---------------------------------------------------------------------------
# TODO 2: Implement truncate_head.
#         Keep the FIRST max_tokens tokens; discard the tail.
#         Steps:
#           enc = tiktoken.get_encoding("cl100k_base")
#           tokens = enc.encode(text)
#           return enc.decode(tokens[:max_tokens])
# ---------------------------------------------------------------------------
def truncate_head(text: str, max_tokens: int) -> str:
    # TODO: implement with tiktoken
    words = text.split()
    approx = int(max_tokens / 1.3)
    return " ".join(words[:approx])


# ---------------------------------------------------------------------------
# TODO 3: Implement truncate_tail.
#         Keep the LAST max_tokens tokens; discard the head.
# ---------------------------------------------------------------------------
def truncate_tail(text: str, max_tokens: int) -> str:
    # TODO: implement with tiktoken
    words = text.split()
    approx = int(max_tokens / 1.3)
    return " ".join(words[-approx:])


# ---------------------------------------------------------------------------
# TODO 4: Implement truncate_middle_out.
#         Keep the first (max_tokens // 2) tokens AND the last (max_tokens // 2) tokens.
#         Drop everything in the middle.
#         Hint: build the two halves, join with a "[...TRUNCATED...]" marker.
# ---------------------------------------------------------------------------
def truncate_middle_out(text: str, max_tokens: int) -> str:
    # TODO: implement with tiktoken
    half = max_tokens // 2
    head = truncate_head(text, half)
    tail = truncate_tail(text, half)
    return head + "\n\n[...TRUNCATED...]\n\n" + tail


# ---------------------------------------------------------------------------
# TODO 5 (stretch): Implement a smarter sentence-boundary truncation.
#         Instead of cutting mid-token, find the nearest sentence boundary
#         before or after the token limit.
# ---------------------------------------------------------------------------
def truncate_sentence_boundary(text: str, max_tokens: int) -> str:
    # TODO: split by sentence, accumulate until limit, return at boundary
    raise NotImplementedError("TODO: implement sentence-boundary truncation")


def main() -> None:
    print("=== Task 1: Token Budgeting ===\n")

    original_tokens = count_tokens(SAMPLE_TEXT)
    print(f"Original text      : {len(SAMPLE_TEXT):6d} chars / {original_tokens:5d} tokens")
    print(f"Token budget       : {MAX_TOKEN_BUDGET:5d} tokens")
    print(f"Reduction required : {max(0, original_tokens - MAX_TOKEN_BUDGET):5d} tokens\n")

    # -------------------------------------------------------------------------
    # TODO 6: Apply each strategy and print a results table.
    #         For each strategy: strategy name, result token count, what was lost
    #         (head / tail / middle).
    # -------------------------------------------------------------------------

    strategies = [
        ("head   (keep start)", truncate_head,          "lost: tail"),
        ("tail   (keep end  )", truncate_tail,          "lost: head"),
        ("middle-out         ", truncate_middle_out,    "lost: middle"),
    ]

    print(f"{'Strategy':<30} {'Result tokens':>13} {'Within budget?':>14}  Lost")
    print("-" * 70)

    for name, fn, lost in strategies:
        result = fn(SAMPLE_TEXT, MAX_TOKEN_BUDGET)
        result_tokens = count_tokens(result)
        within = "yes" if result_tokens <= MAX_TOKEN_BUDGET else "no  (approx only)"
        print(f"{name:<30} {result_tokens:>13}  {within:<14}  {lost}")

    print()
    print("Observation:")
    print("  head   — best for tasks that need the opening context (introductions, premises).")
    print("  tail   — best for tasks that need the latest information (recent events, conclusions).")
    print("  middle-out — preserves both ends; useful when start AND end matter (e.g. Q&A at end,")
    print("             definitions at start). The middle is typically the least recalled anyway")
    print("             (see 'lost in the middle' — module task 4).")

    # -------------------------------------------------------------------------
    # TODO 7 (stretch): Print the first 200 chars of each truncated version so
    #         you can visually inspect what was kept.
    # -------------------------------------------------------------------------


if __name__ == "__main__":
    main()
