"""
Task 4 — Long-context strategies 🟡

What this teaches:
  - Even with a 200 K context window, fitting an entire corpus wastes tokens and
    often degrades quality due to the "lost in the middle" effect.
  - Map-reduce: process each chunk independently (map), then synthesise (reduce).
  - Refine: iteratively update an interim answer as each new chunk is processed.
  - Lost in the middle: LLMs recall facts near the start and end of context
    reliably; facts buried in the middle are frequently forgotten.

How to run:
  uv run python modules/16-context-engineering/py/04_long_context.py
"""

from __future__ import annotations

from llm_core import get_provider, ChatMessage, ChatOptions

# ---------------------------------------------------------------------------
# Rough token counter (replace with tiktoken from Task 1 for precision).
# ---------------------------------------------------------------------------
def count_tokens(text: str) -> int:
    return int(len(text.split()) * 1.3)


# ---------------------------------------------------------------------------
# Long document with a unique fact planted in three positions.
# We will test whether the model recalls each fact after map-reduce/refine.
# ---------------------------------------------------------------------------
_SECTION_A = """
## Section A: History of the Internet

The internet evolved from ARPANET, a research network funded by the U.S. Department of
Defense in the late 1960s. The first message sent over ARPANET was "LO" — the system
crashed after two letters of "LOGIN". By the 1980s, the TCP/IP protocol suite became the
standard, laying the foundation for the modern internet.

UNIQUE FACT ALPHA: The ARPANET had exactly 4 nodes when it first went live on October 29, 1969.

The World Wide Web was invented by Tim Berners-Lee at CERN in 1989 as a system for sharing
information among physicists. His original proposal was described by his manager as "vague
but exciting." The first website went live on August 6, 1991.
""".strip()

_SECTION_B = """
## Section B: How Search Engines Work

Search engines crawl the web using automated programs called spiders or bots. These bots
follow hyperlinks from page to page, downloading and indexing the content they find.
PageRank, invented by Larry Page and Sergey Brin at Stanford, ranks pages by counting how
many other pages link to them, weighted by the importance of the linking page.

UNIQUE FACT BETA: Google processed its first 1 billion search queries in a single day on August 16, 2012.

Modern search engines use machine learning extensively. BERT (2019) and MUM (2021) allow
Google to understand the intent behind queries rather than matching keywords literally.
Vector search complements keyword search for semantically rich queries.
""".strip()

_SECTION_C = """
## Section C: The Rise of Social Media

Social media transformed how humans communicate, share information, and form communities
online. Friendster launched in 2002, MySpace in 2003, and Facebook in 2004. Twitter
launched in 2006, Instagram in 2010, and TikTok (as Douyin in China) in 2016.

UNIQUE FACT GAMMA: Instagram was acquired by Facebook (now Meta) for approximately $1 billion in April 2012, making it one of the largest acquisitions of a startup with fewer than 20 employees in history.

Network effects are central to social media: the value of a platform grows roughly with the
square of the number of users (Metcalfe's Law). This creates strong winner-takes-all dynamics
and makes it extremely hard for new entrants to displace incumbents.
""".strip()

_SECTION_D = """
## Section D: Artificial Intelligence and the Future Web

Artificial intelligence is reshaping every layer of the internet stack. Large language models
generate text, images, code, and audio at a quality indistinguishable from human output in
many domains. Recommendation systems powered by deep learning drive the majority of content
consumed on social platforms, streaming services, and e-commerce sites.

Key challenges include: content moderation at scale, algorithmic amplification of harmful
content, privacy erosion through data collection, and the environmental cost of training and
serving large AI models. Governance frameworks are still nascent; regulators worldwide are
developing rules for AI liability, transparency, and copyright.

The semantic web — the original vision of machine-readable data — is finally becoming
practical through the combination of large language models and structured knowledge graphs.
Conversational interfaces are replacing search boxes as the primary way humans extract
information from the internet.
""".strip()

LONG_DOCUMENT = "\n\n".join([_SECTION_A, _SECTION_B, _SECTION_C, _SECTION_D])

MAX_TOKENS_PER_CHUNK = 350  # small to force chunking in this demo

# Questions designed to test recall of each unique fact.
RECALL_QUESTIONS = [
    ("ALPHA (start)",  "How many nodes did ARPANET have when it first went live?"),
    ("BETA  (middle)", "On what date did Google process its first 1 billion search queries in a day?"),
    ("GAMMA (middle)", "How much did Facebook pay to acquire Instagram?"),
]

SUMMARY_QUESTION = "What are the three most important facts in the document?"


# ---------------------------------------------------------------------------
# TODO 1: Implement split_into_chunks.
#         Split `text` into chunks of at most `max_tokens` tokens each.
#         Split at word boundaries (spaces) — do not cut mid-word.
#         Return a list of non-empty chunk strings.
# ---------------------------------------------------------------------------
def split_into_chunks(text: str, max_tokens: int = MAX_TOKENS_PER_CHUNK) -> list[str]:
    # TODO: implement — use count_tokens to check each candidate chunk
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for word in words:
        word_tokens = count_tokens(word)
        if current and current_tokens + word_tokens > max_tokens:
            chunks.append(" ".join(current))
            current = [word]
            current_tokens = word_tokens
        else:
            current.append(word)
            current_tokens += word_tokens
    if current:
        chunks.append(" ".join(current))
    return chunks


# ---------------------------------------------------------------------------
# TODO 2: Implement map_reduce.
#         MAP phase: for each chunk, call the LLM with:
#           "Based only on this excerpt, answer the question: {question}\nExcerpt: {chunk}"
#           Collect the mini-answers.
#         REDUCE phase: send all mini-answers to the LLM with:
#           "Synthesise these partial answers into one final answer: {mini_answers}"
#         Return the final synthesised answer.
# ---------------------------------------------------------------------------
def map_reduce(chunks: list[str], question: str, llm) -> str:
    # TODO: implement
    # mini_answers = []
    # for chunk in chunks:
    #     prompt = f"Based only on this excerpt, answer the question: {question}\nExcerpt:\n{chunk}"
    #     result = llm.chat([ChatMessage("user", prompt)], ChatOptions(temperature=0))
    #     mini_answers.append(result.text.strip())
    #
    # combined = "\n---\n".join(mini_answers)
    # reduce_prompt = (
    #     f"Original question: {question}\n\n"
    #     f"Partial answers from different sections:\n{combined}\n\n"
    #     "Synthesise these into one final, coherent answer."
    # )
    # final = llm.chat([ChatMessage("user", reduce_prompt)], ChatOptions(temperature=0))
    # return final.text
    raise NotImplementedError("TODO: implement map_reduce")


# ---------------------------------------------------------------------------
# TODO 3: Implement refine.
#         Start with an empty interim answer.
#         For each chunk, update the interim:
#           "Refine the current answer using any new information in the excerpt.
#            Current answer: {interim}
#            New excerpt: {chunk}
#            Question: {question}"
#         Return the final interim after all chunks.
# ---------------------------------------------------------------------------
def refine(chunks: list[str], question: str, llm) -> str:
    # TODO: implement
    # interim = "No answer yet."
    # for chunk in chunks:
    #     prompt = (
    #         f"Refine the current answer using any new information in the excerpt.\n"
    #         f"Question: {question}\n"
    #         f"Current answer: {interim}\n"
    #         f"New excerpt:\n{chunk}"
    #     )
    #     result = llm.chat([ChatMessage("user", prompt)], ChatOptions(temperature=0))
    #     interim = result.text.strip()
    # return interim
    raise NotImplementedError("TODO: implement refine")


def main() -> None:
    print("=== Task 4: Long-Context Strategies ===\n")

    chunks = split_into_chunks(LONG_DOCUMENT, MAX_TOKENS_PER_CHUNK)
    print(f"Document: {count_tokens(LONG_DOCUMENT)} tokens → {len(chunks)} chunks (max {MAX_TOKENS_PER_CHUNK} tokens each)")
    for i, c in enumerate(chunks):
        print(f"  Chunk {i}: {count_tokens(c)} tokens | {c[:60]}...")

    try:
        llm = get_provider()
        print(f"\nProvider: {llm.name} / {llm.chat_model}\n")
    except Exception as e:
        print(f"\nCould not load provider: {e}\n")
        return

    # -------------------------------------------------------------------------
    # Part A: Compare map-reduce vs refine on a summary question.
    # -------------------------------------------------------------------------
    print("--- Part A: Summary (map-reduce vs refine) ---")
    for strategy_name, fn in [("map-reduce", map_reduce), ("refine", refine)]:
        try:
            answer = fn(chunks, SUMMARY_QUESTION, llm)
            print(f"\n[{strategy_name}]\n{answer[:300]}...")
        except NotImplementedError:
            print(f"\n[{strategy_name}] TODO: not yet implemented")
        except Exception as e:
            print(f"\n[{strategy_name}] ERROR: {e}")

    # -------------------------------------------------------------------------
    # Part B: Lost in the middle — recall test.
    #         Plant a unique fact in ALPHA (start), BETA/GAMMA (middle), DELTA (end).
    #         Ask about each. Which placement is recalled most reliably?
    # -------------------------------------------------------------------------
    print("\n--- Part B: Lost in the Middle (recall test) ---")
    print(
        "Unique facts are planted in:\n"
        "  ALPHA  — Section A (start of document)\n"
        "  BETA   — Section B (middle)\n"
        "  GAMMA  — Section C (middle-late)\n"
    )
    print(f"\n{'Placement':<16} {'Strategy':<14} {'Answer (first 100 chars)'}")
    print("-" * 70)

    for label, question in RECALL_QUESTIONS:
        for strategy_name, fn in [("map-reduce", map_reduce), ("refine", refine)]:
            try:
                answer = fn(chunks, question, llm)
                print(f"{label:<16} {strategy_name:<14} {answer[:100]}")
            except NotImplementedError:
                print(f"{label:<16} {strategy_name:<14} (TODO: not yet implemented)")
            except Exception as e:
                print(f"{label:<16} {strategy_name:<14} ERROR: {e}")

    print()
    print("Observation:")
    print("  Facts at the START (ALPHA) and END of the document tend to be recalled better.")
    print("  Facts in the MIDDLE (BETA, GAMMA) are more likely to be missed or garbled.")
    print("  Map-reduce and refine handle this differently — map-reduce is chunk-parallel")
    print("  so every chunk gets equal attention; refine may down-weight middle chunks.")


if __name__ == "__main__":
    main()
