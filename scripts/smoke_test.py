"""Python smoke test — verifies your provider is reachable and returns a response.

Run with:
    uv run python scripts/smoke_test.py

Note: this file is a runnable script, not a pytest test suite. pytest's
testpaths in pyproject.toml are modules/, packages/, and projects/ — scripts/
is excluded, so this file is never collected as a test (which is intentional).
"""

from __future__ import annotations


def main() -> None:
    try:
        from llm_core import ChatMessage, get_provider
    except ImportError as exc:
        print("Could not import llm_core:", exc)
        print("Run `uv sync` from the repo root to install it.")
        raise SystemExit(1) from None

    try:
        llm = get_provider()
    except RuntimeError as exc:
        print("Could not initialise provider:", exc)
        print(
            "Tip: copy .env.example to .env, set LLM_PROVIDER and the matching "
            "API key (or start Ollama for the free path)."
        )
        raise SystemExit(1) from None

    print(f"Provider : {llm.name}")
    print(f"Model    : {llm.chat_model}")

    try:
        result = llm.chat([ChatMessage(role="user", content="Reply with exactly: ok")])
    except Exception as exc:  # noqa: BLE001
        print("\nRequest failed:", exc)
        print(
            "Check that your API key is valid and the provider is reachable "
            "(Ollama: is the server running?)."
        )
        raise SystemExit(1) from None

    print(f"Reply    : {result.text.strip()}")

    usage = result.usage
    if usage.input_tokens is not None or usage.output_tokens is not None:
        print(f"Tokens   : {usage.input_tokens or '?'} in / {usage.output_tokens or '?'} out")

    print("\nSmoke test passed.")


if __name__ == "__main__":
    main()
