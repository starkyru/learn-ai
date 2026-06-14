"""
Task 4 🟢 — Serving engines: pick by use case.

What you'll learn:
  - The concrete tradeoffs between Ollama, llama.cpp, vLLM, and TGI
  - A rules-based recommendation function (no ML needed for this decision)
  - How to call multiple engines with the same client code (OpenAI-compatible APIs)

Key insight: all four engines expose (roughly) the same OpenAI-compatible
/v1/chat/completions API. Switching between them is just a base_url change.
The differences are in performance characteristics, setup complexity, and
hardware requirements — not the API shape.

How to run:
  uv run python modules/14-local-inference-optimization/py/04_serving_engines.py
"""

from __future__ import annotations

from llm_core import ChatMessage, ChatOptions, OpenAICompatibleProvider, get_provider

# ---------------------------------------------------------------------------
# Engine reference table
# ---------------------------------------------------------------------------

ENGINES = [
    {
        "name": "Ollama",
        "use_case": "Local dev, single user, Mac/Windows/Linux",
        "key_features": "One-command setup, GGUF auto-download, cross-platform",
        "hardware": "CPU or GPU (any)",
        "api_compatible": True,
        "setup": "brew install ollama && ollama serve && ollama pull llama3.2",
        "keywords": ["local", "laptop", "dev", "single", "user", "easy", "quick", "start"],
    },
    {
        "name": "llama.cpp",
        "use_case": "Embedded, edge, CLI, CPU-only",
        "key_features": "Minimal deps, C++ binary, Metal GPU on Mac, GGUF native",
        "hardware": "CPU (Metal GPU on Mac)",
        "api_compatible": True,
        "setup": "brew install llama.cpp # then: llama-server -m model.gguf --port 8080",
        "keywords": ["edge", "embedded", "cpu", "minimal", "gguf", "metal", "offline"],
    },
    {
        "name": "vLLM",
        "use_case": "High-throughput server, 100s of concurrent users",
        "key_features": "PagedAttention, continuous batching, best GPU utilisation",
        "hardware": "NVIDIA GPU (Linux only)",
        "api_compatible": True,
        "setup": "pip install vllm && python -m vllm.entrypoints.openai.api_server --model ...",
        "keywords": ["throughput", "concurrent", "scale", "production", "server", "users", "batch", "gpu"],
    },
    {
        "name": "TGI (Text Generation Inference)",
        "use_case": "HuggingFace model hub + streaming, multi-GPU",
        "key_features": "Flash Attention, HF integration, Rust server, quantization",
        "hardware": "NVIDIA GPU recommended",
        "api_compatible": True,
        "setup": "docker run ghcr.io/huggingface/text-generation-inference --model-id ...",
        "keywords": ["huggingface", "hf", "multi-gpu", "streaming", "docker"],
    },
]


# ---------------------------------------------------------------------------
# Engine recommendation
# ---------------------------------------------------------------------------


def recommend_engine(use_case: str) -> dict:
    """
    Return the best serving engine for the given use-case description.

    Uses keyword matching against the ENGINES list above — no ML needed here.
    The decision table IS the knowledge; the function just makes it queryable.

    Returns a dict with keys:
      "engine"  : engine name (str)
      "reason"  : one-sentence explanation (str)
      "setup"   : setup command or instructions (str)

    TODO:
      1. Lowercase the use_case string.
      2. For each engine in ENGINES, count how many of its "keywords" appear
         in the use_case string.
      3. Return the engine with the highest keyword match count.
         If there's a tie, prefer the first matching engine (Ollama).
      4. If no keywords match at all, default to Ollama.
      5. Build the return dict from the matched engine.

    Example:
      recommend_engine("I need to serve 1000 concurrent users")  → vLLM
      recommend_engine("I want to run a model on my laptop")     → Ollama
    """
    # TODO: implement recommend_engine
    raise NotImplementedError("TODO: implement recommend_engine()")


# ---------------------------------------------------------------------------
# Run against available engines
# ---------------------------------------------------------------------------


def run_against_engines(prompt: str, engines_config: list[dict]) -> None:
    """
    Call `prompt` against all configured engines and print side-by-side responses.

    `engines_config` is a list of dicts, each with:
      "name"     : display name
      "base_url" : OpenAI-compatible endpoint (or None to skip)
      "model"    : model id to use

    TODO:
      1. For each engine in engines_config, if base_url is None, print "SKIPPED".
      2. Otherwise, create an OpenAICompatibleProvider pointing at base_url.
      3. Call provider.chat() with the prompt.
      4. Print: "--- <name> ---\n<response[:200]>\n".
      5. Handle exceptions gracefully (print the error, continue).
    """
    # TODO: implement run_against_engines
    raise NotImplementedError("TODO: implement run_against_engines()")


# ---------------------------------------------------------------------------
# Engine table
# ---------------------------------------------------------------------------


def print_engine_table() -> None:
    """
    Print a formatted markdown-style table of all four engines.

    Columns: Engine | Use case | Hardware | Key feature | OpenAI-compatible?

    TODO:
      1. Print header row with column separators.
      2. Print a divider row.
      3. Print one row per engine from ENGINES.
    """
    # TODO: implement print_engine_table
    raise NotImplementedError("TODO: implement print_engine_table()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    # Engine reference table
    print_engine_table()

    # Recommendation demo
    print("\n" + "=" * 60)
    print("RECOMMENDATION DEMO")
    print("=" * 60)
    test_cases = [
        "I need to serve 1000 concurrent users in production",
        "I want to run a model locally on my laptop with minimal setup",
        "I'm building an embedded device with no internet access",
        "I need to integrate with a HuggingFace model and multi-GPU server",
    ]
    for uc in test_cases:
        rec = recommend_engine(uc)
        print(f"\n  Use case: {uc[:60]}")
        print(f"  Recommended: {rec['engine']}")
        print(f"  Reason: {rec['reason']}")

    # Live demo against available engines
    print("\n" + "=" * 60)
    print("LIVE DEMO (Ollama only — others require separate installation)")
    print("=" * 60)

    PROMPT = "What is PagedAttention and why does it improve GPU utilisation? One paragraph."

    engines_to_try = [
        {
            "name": "Ollama (localhost:11434)",
            "base_url": "http://localhost:11434/v1",
            "model": "llama3.2",
        },
        # Add more engines here if running vLLM or TGI locally:
        # {"name": "vLLM (localhost:8000)", "base_url": "http://localhost:8000/v1", "model": "..."},
        # {"name": "llama.cpp (localhost:8080)", "base_url": "http://localhost:8080/v1", "model": "..."},
    ]

    run_against_engines(PROMPT, engines_to_try)


if __name__ == "__main__":
    main()
