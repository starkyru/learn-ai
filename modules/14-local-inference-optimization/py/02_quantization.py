"""
Task 2 🟡 — Quantization: size vs speed vs quality.

What you'll learn:
  - What quantization is and why it matters for local inference
  - The fp32 → fp16 → int8 → int4 (GGUF Q4) ladder and tradeoffs
  - How to measure speed and quality differences between quant levels
  - The memory footprint reduction at each step

We compare two Ollama models of different sizes/quantization levels.
Default: llama3.2 (3B, Q4_K_M) vs llama3.2:1b (1B, Q4_K_M).

If you have pulled Q4 and Q8 variants of the same model, edit MODEL_A/MODEL_B
below to compare them directly. For example:
  ollama pull qwen2.5:7b-instruct-q4_K_M
  ollama pull qwen2.5:7b-instruct-q8_0
Then set MODEL_A = "qwen2.5:7b-instruct-q4_K_M" and MODEL_B = "qwen2.5:7b-instruct-q8_0".

How to run:
  uv run python modules/14-local-inference-optimization/py/02_quantization.py
"""

from __future__ import annotations

import time
import urllib.request
import json

from llm_core import ChatMessage, ChatOptions, OpenAICompatibleProvider

# The two models to compare — change these if you have pulled different variants
MODEL_A = "llama3.2:1b"    # smaller / faster
MODEL_B = "llama3.2"       # larger / slower / better quality

OLLAMA_BASE_URL = "http://localhost:11434"

BENCHMARK_PROMPT = (
    "In two concise paragraphs, explain the difference between machine learning "
    "and deep learning. Give one concrete example application for each."
)

JUDGE_PROMPT_TEMPLATE = (
    "Rate the following response on coherence and factual accuracy on a scale of 1-5.\n"
    "Respond with ONLY a single digit.\n\n"
    "Response:\n{response}"
)


# ---------------------------------------------------------------------------
# Model info
# ---------------------------------------------------------------------------


def get_model_info(model_name: str) -> dict:
    """
    Query the Ollama /api/show endpoint and return model metadata.

    Returns a dict with keys:
      "parameter_size"  : e.g. "3.2B" or "1.2B" (from modelinfo or details)
      "quantization"    : e.g. "Q4_K_M" (from details.quantization_level)
      "family"          : e.g. "llama" (from details.family)

    TODO:
      1. Build the request: POST to OLLAMA_BASE_URL + "/api/show"
         with body {"name": model_name}.
         Use urllib.request.urlopen() with a Request object.
      2. Parse the JSON response.
      3. Extract:
           quant = data.get("details", {}).get("quantization_level", "unknown")
           family = data.get("details", {}).get("family", "unknown")
           param_size = data.get("details", {}).get("parameter_size", "unknown")
      4. Return the dict.
      5. On error, return {"parameter_size": "unknown", "quantization": "unknown", "family": "unknown"}.

    Tip: Ollama must be running for this to work.
    """
    # TODO: implement get_model_info
    raise NotImplementedError("TODO: implement get_model_info()")


# ---------------------------------------------------------------------------
# Timed prompt
# ---------------------------------------------------------------------------


def run_timed_prompt(model_name: str, prompt: str, max_tokens: int = 200) -> dict:
    """
    Run `prompt` against `model_name` via Ollama and measure speed.

    Returns:
      "text"       : response text
      "tokens_out" : output token count
      "elapsed_s"  : wall-clock seconds
      "tokens_per_s": tokens_out / elapsed_s

    Uses OpenAICompatibleProvider with the given model_name.

    TODO:
      1. Create an OpenAICompatibleProvider with:
           name="ollama", api_key="ollama",
           base_url=OLLAMA_BASE_URL + "/v1",
           chat_model=model_name,
           embed_model="nomic-embed-text"
      2. Measure elapsed time around provider.chat().
      3. Return the dict.
    """
    # TODO: implement run_timed_prompt
    raise NotImplementedError("TODO: implement run_timed_prompt()")


# ---------------------------------------------------------------------------
# Quality scoring
# ---------------------------------------------------------------------------


def score_quality(response_text: str, judge_provider) -> int:
    """
    Ask `judge_provider` to score `response_text` on a 1–5 scale.

    Uses JUDGE_PROMPT_TEMPLATE. Returns an int (fallback 3 on parse error).

    TODO:
      1. Format JUDGE_PROMPT_TEMPLATE with the response.
      2. Call judge_provider.chat() with temperature=0.
      3. Parse the first digit from the result text. Return as int.
    """
    # TODO: implement score_quality
    raise NotImplementedError("TODO: implement score_quality()")


# ---------------------------------------------------------------------------
# Comparison table
# ---------------------------------------------------------------------------


def print_comparison_table(results: list[dict]) -> None:
    """
    Print a formatted table comparing models.

    Expected columns: Model | Quant | Params | Tokens/sec | Quality(1-5)

    TODO:
      1. Print a header row.
      2. For each result dict, print a row.
         result keys: "model", "quantization", "parameter_size",
                      "tokens_per_s", "quality_score"
    """
    # TODO: implement print_comparison_table
    raise NotImplementedError("TODO: implement print_comparison_table()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    print("Quantization comparison: measuring size vs speed vs quality")
    print("=" * 60)

    # Create a provider for the judge (uses the default LLM_PROVIDER)
    from llm_core import get_provider
    judge_provider = get_provider()

    results = []
    for model_name in [MODEL_A, MODEL_B]:
        print(f"\nBenchmarking {model_name}...")

        # Get model info from Ollama
        info = get_model_info(model_name)
        print(f"  Params: {info['parameter_size']}, Quant: {info['quantization']}")

        # Run timed prompt
        try:
            timed = run_timed_prompt(model_name, BENCHMARK_PROMPT)
            print(f"  Tokens/sec: {timed['tokens_per_s']:.1f}")
            print(f"  Response preview: {timed['text'][:80]}...")

            # Score quality
            quality = score_quality(timed["text"], judge_provider)
            print(f"  Quality score: {quality}/5")

            results.append({
                "model": model_name,
                "quantization": info["quantization"],
                "parameter_size": info["parameter_size"],
                "tokens_per_s": timed["tokens_per_s"],
                "quality_score": quality,
            })
        except Exception as e:
            print(f"  SKIPPED: {e}")
            print(f"  (Run: ollama pull {model_name})")

    if results:
        print("\n" + "=" * 60)
        print_comparison_table(results)

    print(
        "\nKey takeaway: quantization reduces size and increases speed with a"
        "\nsmall quality penalty. Q4 models often get within 5% of Q8 quality"
        "\nat 1/2 the memory footprint and noticeably higher tokens/sec."
    )


if __name__ == "__main__":
    main()
