"""hello.py — your first LLM call.

What it teaches:
    The minimal shape of every exercise in this course — get a provider, send
    one message, read the answer plus the model id and token usage off the
    result. There is no magic beyond this.

How to run (from the repo root):
    uv run python modules/00-setup/py/hello.py

    By default this uses LLM_PROVIDER from your .env (ollama unless you changed
    it). To try a different provider without editing .env, pass a name to
    get_provider(), e.g. get_provider("nvidia").
"""

from __future__ import annotations

from llm_core import ChatMessage, get_provider

PROMPT = "Explain what a large language model is, in 2 sentences."


def main() -> None:
    # No argument -> use the provider named in LLM_PROVIDER (default: ollama).
    # Swap to get_provider("anthropic") / ("openai") / ("nvidia") to force one.
    llm = get_provider()

    # A conversation is a list of messages. Here, a single user turn.
    messages = [ChatMessage(role="user", content=PROMPT)]

    result = llm.chat(messages)

    print(f"Provider : {llm.name}")
    print(f"Model    : {result.model}")
    print(f"Prompt   : {PROMPT}\n")
    print(result.text.strip())

    # Token usage is what paid providers bill on — keep it visible.
    usage = result.usage
    print(
        f"\nTokens   : input={usage.input_tokens}  output={usage.output_tokens}"
    )


if __name__ == "__main__":
    main()
