"""
Task 1 🟢 — Run local models and measure tokens/sec.

What you'll learn:
  - How to measure tokens per second from any provider call
  - What "tokens/sec" means in practice (it varies a lot by model size + hardware)
  - The different local serving engines and when to use each

Default: uses Ollama (already set up in module 00). No extra downloads needed.

Optional local paths (documented, not required):
  llama.cpp:
    brew install llama.cpp   # or build from source
    llama-cli -m model.gguf -p "your prompt"
  vLLM (Linux + NVIDIA GPU only):
    pip install vllm
    python -m vllm.entrypoints.openai.api_server --model meta-llama/Llama-3.2-1B

How to run:
  uv run python modules/14-local-inference-optimization/py/01_run_local.py
"""

from __future__ import annotations

import time

from llm_core import ChatMessage, ChatOptions, get_provider

# The standard benchmark prompt — long enough to produce 50+ tokens
BENCHMARK_PROMPT = (
    "Explain how a transformer model works, focusing on the attention mechanism. "
    "Be concise but thorough. Cover: tokens, embeddings, self-attention, and the "
    "feed-forward layer."
)

# ---------------------------------------------------------------------------
# Throughput measurement
# ---------------------------------------------------------------------------


def measure_throughput(prompt: str, provider) -> dict:
    """
    Send `prompt` to `provider` and measure tokens per second.

    Returns a dict with keys:
      "text"        : the model's response text
      "tokens_out"  : number of output tokens (from result.usage.output_tokens)
      "elapsed_s"   : wall-clock seconds for the full call
      "tokens_per_s": tokens_out / elapsed_s (0 if no token count available)
      "model"       : provider.chat_model

    TODO:
      1. Record start time with time.perf_counter().
      2. Call provider.chat([ChatMessage("user", prompt)], ChatOptions(max_tokens=256)).
      3. Record end time.
      4. Compute elapsed_s = end - start.
      5. Get tokens_out from result.usage.output_tokens (may be None → use 0).
      6. Compute tokens_per_s = tokens_out / elapsed_s if elapsed_s > 0 else 0.
      7. Return the dict.
    """
    # TODO: implement measure_throughput
    raise NotImplementedError("TODO: implement measure_throughput()")


def run_benchmark(prompt: str, provider, n_runs: int = 3) -> None:
    """
    Run `prompt` n_runs times and report min/max/mean tokens/sec.

    TODO:
      1. Collect results from n_runs calls to measure_throughput().
      2. Extract tokens_per_s from each result (skip if 0).
      3. Print:
           Model      : <model_name>
           Runs       : <n_runs>
           Tokens/sec : min=X  max=Y  mean=Z
           Output     : <first 100 chars of response>
    """
    # TODO: implement run_benchmark
    raise NotImplementedError("TODO: implement run_benchmark()")


# ---------------------------------------------------------------------------
# Engine guide
# ---------------------------------------------------------------------------


ENGINE_TABLE = """
LOCAL SERVING ENGINES — QUICK REFERENCE
========================================

Engine        Use case                    Key features
----------    --------------------------  --------------------------------
Ollama        Local dev, single user      One-command setup, cross-platform,
                                          GGUF models, auto-downloads
llama.cpp     Embedded / edge / CLI       Minimal deps, CPU-first, Metal
                                          GPU on Mac, quantized GGUF
vLLM          High-throughput server      PagedAttention, continuous batching,
              (Linux + NVIDIA GPU)        OpenAI-compatible API, best GPU util
TGI           HuggingFace integration     HF model hub, streaming, Rust server
(Text Gen     Multi-GPU                   Flash Attention, quantization
 Inference)

Decision guide:
  Single user, Mac/Windows/Linux dev  → Ollama
  CPU-only or edge device             → llama.cpp directly
  Serving 100s of concurrent users    → vLLM (Linux + NVIDIA)
  HuggingFace model + streaming UI    → TGI

Both vLLM and Ollama expose the OpenAI-compatible /v1/chat/completions endpoint,
so you can point llm-core's OpenAICompatibleProvider at either.
"""


def print_engine_guide() -> None:
    """
    Print the engine reference table.

    TODO: just print ENGINE_TABLE.
    """
    # TODO: implement print_engine_guide
    raise NotImplementedError("TODO: implement print_engine_guide()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    print_engine_guide()

    print("\n" + "=" * 60)
    print("BENCHMARK")
    print("=" * 60)

    try:
        provider = get_provider()
        print(f"Provider: {provider.name} | Model: {provider.chat_model}")
        print(f"Prompt: {BENCHMARK_PROMPT[:80]}...\n")
        run_benchmark(BENCHMARK_PROMPT, provider, n_runs=3)
    except Exception as e:
        print(f"Provider unavailable ({e})")
        print("Make sure Ollama is running: ollama serve")
        print("Then pull a model: ollama pull llama3.2")

    print(
        "\nTip: Try different models by setting OLLAMA_CHAT_MODEL=llama3.2:1b"
        "\nand re-running. Smaller models = more tokens/sec."
    )


if __name__ == "__main__":
    main()
