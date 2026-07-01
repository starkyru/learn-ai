"""compare_providers.py — same prompt, all six providers, side by side.

What it teaches:
    The provider abstraction in action: the exact same call works against six
    different backends. And a real-world habit — gracefully SKIP a provider
    whose key or server is missing (catch the error) instead of crashing the
    whole script.

How to run (from the repo root):
    uv run python modules/00-setup/py/compare_providers.py

    You only need ONE provider configured for this to be useful; the rest are
    reported as skipped with a friendly reason.
"""

from __future__ import annotations

from llm_core import ChatMessage, get_provider

PROMPT = "Explain what a large language model is, in 2 sentences."

PROVIDERS = ["openai", "anthropic", "ollama", "nvidia", "lmstudio", "gemini"]


def try_provider(name: str) -> None:
    """Run the prompt against one provider, or explain why it was skipped.

    Two things can go wrong and BOTH should be non-fatal:
      * get_provider() raises if a required API key env var is missing.
      * .chat() raises if the server is unreachable (e.g. Ollama not running)
        or the key is rejected.
    We catch broadly on purpose — this is a "best effort, show what works" tool.
    """
    print(f"\n=== {name} " + "=" * (40 - len(name)))
    try:
        llm = get_provider(name)
    except Exception as exc:  # noqa: BLE001 — intentional: skip, don't crash
        print(f"  [skipped] {exc}")
        return

    try:
        result = llm.chat([ChatMessage(role="user", content=PROMPT)])
    except Exception as exc:  # noqa: BLE001 — server down / key rejected / etc.
        print(f"  [skipped] call failed: {exc}")
        return

    usage = result.usage
    print(f"  model : {result.model}")
    print(f"  tokens: input={usage.input_tokens} output={usage.output_tokens}")
    print(f"  answer: {result.text.strip()}")


def main() -> None:
    print(f"Prompt: {PROMPT}")
    for name in PROVIDERS:
        try_provider(name)
    print("\nDone. Providers without a key/server were skipped, not fatal.")


if __name__ == "__main__":
    main()
