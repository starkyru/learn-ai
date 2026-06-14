"""
Task 3 — Tokens & cost 🟡

What this teaches:
  - LLMs don't see words, they see tokens (sub-word pieces). Knowing
    how many tokens a text costs lets you stay within context windows
    and predict API spend.
  - Context window = max (input + output) tokens a model can handle.
    Exceeding it truncates or errors; managing it is YOUR job.
  - Cost = (input_tokens * price_in) + (output_tokens * price_out).
    Prices differ wildly between models — this exercise makes it concrete.

Dependencies:
  tiktoken is already in the base deps (pyproject.toml).

How to run:
  uv run python modules/02-llm-integration/py/03_tokens_cost.py
"""

from __future__ import annotations

import tiktoken

from llm_core import get_provider

# ---------------------------------------------------------------------------
# Price table — $ per 1 000 000 tokens (as of mid-2025; check current prices).
# Add or update rows as you learn about new models.
# ---------------------------------------------------------------------------
PRICE_TABLE: dict[str, dict[str, float]] = {
    # model                   input_per_1m   output_per_1m   context_k
    "gpt-4o-mini":         {"in": 0.15,   "out": 0.60,   "ctx": 128},
    "gpt-4o":              {"in": 5.00,   "out": 15.00,  "ctx": 128},
    "claude-haiku-4-5":    {"in": 0.80,   "out": 4.00,   "ctx": 200},
    "claude-opus-4-8":     {"in": 15.00,  "out": 75.00,  "ctx": 200},
    "llama3.2":            {"in": 0.00,   "out": 0.00,   "ctx": 128},
}

SAMPLE_TEXT = """
Retrieval-Augmented Generation (RAG) is a technique that improves large language
model outputs by retrieving relevant documents from an external knowledge base before
generating a response. Unlike pure parametric models that rely solely on weights
learned during training, RAG systems can incorporate up-to-date or domain-specific
information at inference time. This makes them particularly useful for question
answering, enterprise search, and chatbots that need factual grounding.
""".strip()


# ---------------------------------------------------------------------------
# TODO 1: Implement count_tokens using tiktoken.
#         tiktoken.get_encoding("cl100k_base") returns an encoder.
#         Call encoder.encode(text) to get a list of token ids; len() is the count.
#         "cl100k_base" is used by GPT-3.5/4 and also a reasonable estimate
#         for other models. For Claude, token counts differ slightly.
# ---------------------------------------------------------------------------
def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    # TODO: implement
    enc = tiktoken.get_encoding(encoding_name)
    # tokens = enc.encode(text)
    # return len(tokens)
    _ = enc  # remove this line once you use enc above
    return len(text.split())  # rough placeholder


# ---------------------------------------------------------------------------
# TODO 2: Implement estimate_cost.
#         Look up the model in PRICE_TABLE. If not found, return None.
#         Cost formula:  (input_tokens / 1_000_000) * price["in"]
#                      + (output_tokens / 1_000_000) * price["out"]
# ---------------------------------------------------------------------------
def estimate_cost(
    model: str, input_tokens: int, output_tokens: int
) -> dict[str, float] | None:
    # TODO: implement
    if model not in PRICE_TABLE:
        return None
    prices = PRICE_TABLE[model]
    cost = 0.0  # TODO: apply the formula
    return {"cost": cost, "ctx_k": prices["ctx"]}


def main() -> None:
    llm = get_provider()
    print(f"Provider: {llm.name} / {llm.chat_model}\n")

    # -------------------------------------------------------------------------
    # TODO 3: Count tokens in SAMPLE_TEXT and print alongside char/word count.
    #         Notice: tokens < chars but > words typically, because tokens are
    #         sub-word units (common words = 1 token, rarer = 2–3 tokens).
    # -------------------------------------------------------------------------
    token_count = count_tokens(SAMPLE_TEXT)
    print("--- token counting ---")
    print(f"Characters : {len(SAMPLE_TEXT)}")
    print(f"Words      : {len(SAMPLE_TEXT.split())}")
    print(f"Tokens     : {token_count}  (TODO: make sure count_tokens uses tiktoken)")

    # -------------------------------------------------------------------------
    # TODO 4: Make a real API call and use result.usage to get exact provider
    #         token counts. Compare against your tiktoken estimate.
    # -------------------------------------------------------------------------
    print("\n--- real API call ---")
    prompt = "Summarise this in one sentence: " + SAMPLE_TEXT
    # result = llm.chat([{"role": "user", "content": prompt}])
    # print(f"Response: {result.text}")
    # print(f"Provider says — input: {result.usage.input_tokens}, output: {result.usage.output_tokens}")
    # print(f"Tiktoken estimate — input: {count_tokens(prompt)}")
    print("TODO: make the real API call above.")

    # -------------------------------------------------------------------------
    # TODO 5: Estimate cost for all models and print a comparison table.
    #         Format: model | ctx window | estimated cost
    # -------------------------------------------------------------------------
    print("\n--- cost comparison ---")
    example_in, example_out = 500, 200
    print(f"Assuming {example_in} input tokens, {example_out} output tokens:\n")
    print(f"{'Model':<24} {'Context':<12} {'Est. cost'}")
    print("-" * 50)
    for model, prices in PRICE_TABLE.items():
        result = estimate_cost(model, example_in, example_out)
        cost_str = f"${result['cost']:.6f}" if result else "TODO"
        ctx_str = f"{int(prices['ctx'])}K"
        print(f"{model:<24} {ctx_str:<12} {cost_str}")

    # -------------------------------------------------------------------------
    # TODO 6 (stretch): Given a budget in dollars and a model, how many "turns"
    #         (assume avg 500 input + 200 output tokens per turn) can you afford?
    # -------------------------------------------------------------------------


if __name__ == "__main__":
    main()
