"""
Task 2 🟡 — Reimplement LangChain memory + a retriever, wire a tiny RAG chain.

What you'll learn:
  - ConversationBufferMemory: memory is *just* a list of turns you save and
    reload. `save_context(user, ai)` appends; `load_memory_variables()` renders
    the buffer back into a string the next prompt can carry.
  - A retriever is *just* a ranker over documents: score each doc against the
    query, sort, take the top-k. Here we rank with bag-of-words cosine — no
    embeddings, no network — so it's fully offline and deterministic.
  - RAG = retrieve context, stuff it into the prompt, then ask the model. The
    "chain" is the same left-to-right threading as Task 1, plus memory carried
    alongside.

The math:

  1) Bag-of-words vector. Tokenise a text into lowercase word tokens, then count
     occurrences. For vocabulary V, a doc becomes a vector v where v[w] = count
     of word w. (We keep it sparse as a dict word -> count.)

  2) Cosine similarity between two sparse count vectors a and b:

         cosine(a, b) = (a . b) / (||a|| * ||b||)

     where the dot product sums a[w]*b[w] over shared words, and
     ||a|| = sqrt(sum_w a[w]^2). Range [0, 1] for non-negative counts; higher
     means more lexical overlap. If either norm is 0, similarity is 0.

  3) top-k retrieval: score every doc, sort by cosine descending, return the
     first k docs.

The pieces we reimplement (and the real LangChain equivalent):

  ours                                real langchain
  --------------------------------    ------------------------------------------
  ConversationBufferMemory            langchain.memory.ConversationBufferMemory
    .save_context / .load_memory_...    (same method names)
  Retriever.get_relevant(q, k)        VectorStoreRetriever.invoke(q) (k in config)
  build_rag_prompt(...)               a PromptTemplate with {context}{question}

OFFLINE: takes `chat_fn: Callable[[list[dict]], str]`. With --stub it uses a
deterministic fake model; without --stub it wraps get_provider().chat.

How to run:
  uv run python modules/06c-agent-frameworks/py/02_memory_retriever.py --stub
  uv run python modules/06c-agent-frameworks/py/02_memory_retriever.py
"""

from __future__ import annotations

import argparse
import math  # noqa: F401 — the cosine() TODO below uses math.sqrt
import re
from collections import Counter
from collections.abc import Callable

ChatFn = Callable[[list[dict[str, str]]], str]


# ---------------------------------------------------------------------------
# Conversation memory
# ---------------------------------------------------------------------------


class ConversationBufferMemory:
    """A list of (user, ai) turns, rendered back as a transcript string.

    Real LangChain's ConversationBufferMemory does exactly this: it keeps the
    raw messages and, on load, formats them as "Human: ...\\nAI: ..." lines.
    """

    def __init__(self) -> None:
        self.turns: list[tuple[str, str]] = []

    def save_context(self, user_input: str, ai_output: str) -> None:
        """Append one (user, ai) turn to the buffer.

        TODO: implement.
          - Append a single (user_input, ai_output) tuple to self.turns so the
            buffer grows by one turn per call.
        """
        # TODO: implement save_context (append the turn)
        raise NotImplementedError("TODO: implement ConversationBufferMemory.save_context()")

    def load_memory_variables(self) -> dict[str, str]:
        """Render the buffer as {"history": "Human: ...\\nAI: ...\\n..."}.

        Each turn becomes two lines:
            Human: <user_input>
            AI: <ai_output>
        Join all lines with "\\n". An empty buffer yields "".

        TODO: implement.
          - Turn each stored turn into two lines — a "Human: ..." line for the
            user input and an "AI: ..." line for the ai output.
          - Join every line with newlines into one transcript string and return
            it under the "history" key (an empty buffer must yield "").
        """
        # TODO: implement load_memory_variables (render buffer to a string)
        raise NotImplementedError(
            "TODO: implement ConversationBufferMemory.load_memory_variables()"
        )


# ---------------------------------------------------------------------------
# Bag-of-words cosine retriever (deterministic, offline)
# ---------------------------------------------------------------------------


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens (letters/digits). Complete — no need to edit."""
    return re.findall(r"[a-z0-9]+", text.lower())


def bag_of_words(text: str) -> Counter[str]:
    """Word -> count. Complete — no need to edit."""
    return Counter(tokenize(text))


def cosine(a: Counter[str], b: Counter[str]) -> float:
    """Cosine similarity between two sparse count vectors.

        cosine(a, b) = dot(a, b) / (||a|| * ||b||)

    dot(a, b) = sum over shared words of a[w]*b[w].
    ||a||     = sqrt(sum of a[w]^2 over all words in a).
    Return 0.0 if either vector has zero norm.

    TODO: implement.
      - Compute the dot product: sum a[w]*b[w] over the words the two vectors
        share (a Counter returns 0 for missing keys, so only shared words add).
      - Compute each vector's Euclidean norm with math.sqrt over its counts.
      - Guard the divide: if either norm is 0, return 0.0.
      - Otherwise return dot divided by the product of the two norms.
    """
    # TODO: implement cosine similarity over sparse count vectors
    raise NotImplementedError("TODO: implement cosine()")


class Retriever:
    """Ranks a fixed doc set against a query by bag-of-words cosine."""

    def __init__(self, docs: list[str]) -> None:
        self.docs = docs
        # Precompute each doc's bag-of-words once (complete).
        self.doc_vecs = [bag_of_words(d) for d in docs]

    def get_relevant(self, query: str, k: int = 1) -> list[str]:
        """Return the top-k docs most similar to `query` (highest cosine first).

        TODO: implement.
          - Turn the query into a bag-of-words vector.
          - Score every doc by cosine against the query, keeping each doc paired
            with its score (the precomputed self.doc_vecs align with self.docs).
          - Sort by score descending (ties keep original order — sorting on the
            negative score is stable, so equal scores stay in input order).
          - Return the docs (not the scores) of the first k pairs.
        """
        # TODO: implement top-k retrieval by cosine
        raise NotImplementedError("TODO: implement Retriever.get_relevant()")


# ---------------------------------------------------------------------------
# RAG prompt assembly
# ---------------------------------------------------------------------------

RAG_TEMPLATE = (
    "You are a helpful assistant. Use the context and prior conversation to "
    "answer.\n\n"
    "Conversation so far:\n{history}\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}\n"
    "Answer:"
)


def build_rag_prompt(history: str, context: str, question: str) -> str:
    """Fill RAG_TEMPLATE with the memory transcript, retrieved context, question.

    TODO: implement.
      - Substitute the three arguments into RAG_TEMPLATE's {history}, {context},
        and {question} slots (by name) and return the filled prompt string.
    """
    # TODO: implement RAG prompt assembly
    raise NotImplementedError("TODO: implement build_rag_prompt()")


# ---------------------------------------------------------------------------
# The RAG chain: retrieve -> prompt(context+question+history) -> model, + memory
# ---------------------------------------------------------------------------


class RagChain:
    """Ties the retriever, memory, and model into one `ask(question)` call.

    This method is complete: it calls the pieces you implement above. Read it to
    see how retrieval, prompt assembly, the model call, and memory-save connect.
    """

    def __init__(
        self, chat_fn: ChatFn, retriever: Retriever, memory: ConversationBufferMemory
    ) -> None:
        self.chat_fn = chat_fn
        self.retriever = retriever
        self.memory = memory
        self.last_prompt = ""  # exposed so tests can inspect what we sent

    def ask(self, question: str, k: int = 1) -> str:
        history = self.memory.load_memory_variables()["history"]
        docs = self.retriever.get_relevant(question, k=k)
        context = "\n".join(docs)
        prompt = build_rag_prompt(history, context, question)
        self.last_prompt = prompt
        answer = self.chat_fn([{"role": "user", "content": prompt}])
        self.memory.save_context(question, answer)
        return answer


# ---------------------------------------------------------------------------
# Stub + real model
# ---------------------------------------------------------------------------


def make_stub_chat_fn() -> ChatFn:
    """Deterministic fake: return a fixed short line so tests are exact.

    It ignores the prompt content (so we test the *chain*, not the model) but
    returns a stable string per call so memory has real content to store.
    """
    counter = {"n": 0}

    def chat_fn(messages: list[dict[str, str]]) -> str:
        counter["n"] += 1
        return f"stub-answer-{counter['n']}"

    return chat_fn


def make_real_chat_fn() -> ChatFn:
    from llm_core import get_provider

    provider = get_provider()

    def chat_fn(messages: list[dict[str, str]]) -> str:
        return provider.chat(messages).text

    return chat_fn


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

DOCS = [
    "Python is a dynamically typed programming language popular for data science.",
    "The mitochondria is the powerhouse of the cell and produces ATP energy.",
    "The Eiffel Tower is an iron lattice tower located in Paris, France.",
    "Basketball is a team sport where players score by shooting a ball through a hoop.",
]


def main() -> None:
    ap = argparse.ArgumentParser(description="Memory + retriever RAG chain (Task 2).")
    ap.add_argument("--stub", action="store_true", help="use the offline deterministic model")
    args = ap.parse_args()

    chat_fn = make_stub_chat_fn() if args.stub else make_real_chat_fn()
    mode = "STUB (offline)" if args.stub else "REAL (get_provider)"
    print(f"\n=== Task 2: memory + retriever — {mode} ===\n")

    retriever = Retriever(DOCS)
    memory = ConversationBufferMemory()
    chain = RagChain(chat_fn, retriever, memory)

    # ── Retriever sanity: most lexically similar doc wins ─────────────────
    top = retriever.get_relevant("Which language is used for data science?", k=1)[0]
    print("Query: 'Which language is used for data science?'")
    print(f"  top doc -> {top!r}")

    # ── Turn 1 ────────────────────────────────────────────────────────────
    q1 = "Tell me about Python."
    a1 = chain.ask(q1)
    print(f"\nTurn 1  Q: {q1}\n        A: {a1}")

    # ── Turn 2 (memory should now hold turn 1) ────────────────────────────
    q2 = "Where is the Eiffel Tower?"
    a2 = chain.ask(q2)
    print(f"Turn 2  Q: {q2}\n        A: {a2}")

    print("\nMemory buffer after two turns:")
    print(memory.load_memory_variables()["history"])

    if args.stub:
        # 1) Retriever picks the Python doc for a data-science query.
        assert top == DOCS[0], f"retriever picked wrong doc: {top!r}"
        # 2) Memory holds BOTH turns.
        hist = memory.load_memory_variables()["history"]
        assert q1 in hist and a1 in hist, "turn 1 missing from memory"
        assert q2 in hist and a2 in hist, "turn 2 missing from memory"
        assert len(memory.turns) == 2, f"expected 2 turns, got {len(memory.turns)}"
        # 3) The last prompt carried the retrieved context (Eiffel doc for q2).
        assert DOCS[2] in chain.last_prompt, "retrieved context not in prompt"
        assert "Question: Where is the Eiffel Tower?" in chain.last_prompt
        # 4) The prompt also carried turn-1 history.
        assert q1 in chain.last_prompt, "prior turn not carried into prompt"
        print(
            "\n[ok] retriever ranks correctly, memory holds both turns, "
            "prompt contains retrieved context + history"
        )

    print(
        "\nReal LangChain: swap Retriever for a VectorStoreRetriever and "
        "ConversationBufferMemory keeps the same save/load API."
    )


if __name__ == "__main__":
    main()
