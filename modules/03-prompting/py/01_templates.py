"""
Task 1 — Templates & roles 🟢

What this teaches:
  - Raw string concatenation for prompts doesn't scale: typos in variable
    names are silent, escaping is error-prone, and the "shape" of the prompt
    is invisible. A tiny template helper solves all three.
  - The system role is the highest-trust part of the conversation. It sets
    persona, constraints, and output format. Users can't (easily) override it.
  - The user role is the request; the assistant role is the model's reply.
    Few-shot examples are also expressed as user/assistant pairs.

How to run:
  uv run python modules/03-prompting/py/01_templates.py
"""

from __future__ import annotations

import re

from llm_core import get_provider, ChatMessage

# ---------------------------------------------------------------------------
# TODO 1: Implement render_template.
#         Replace every {{variable}} placeholder in `template` with the
#         corresponding value from `variables`. Raise a ValueError if a
#         placeholder is referenced but not provided.
#         Example:
#           render_template("Hello, {{name}}! You are {{age}}.", {"name": "Alice", "age": "30"})
#           → "Hello, Alice! You are 30."
# ---------------------------------------------------------------------------
def render_template(template: str, variables: dict[str, str]) -> str:
    # TODO: implement
    # Hint: scan for {{name}} tokens with a regex (the `re` module is imported)
    #       and substitute each one with the matching value from `variables`.
    #       If a referenced placeholder isn't in `variables`, raise a ValueError
    #       rather than leaving the token in place.
    return template  # placeholder


# ---------------------------------------------------------------------------
# TODO 2: Define a library of reusable prompt templates.
#         Each template is a string with {{...}} placeholders.
#         Add at least two: one for a task (e.g. summarisation) and one for
#         structured output (e.g. extraction or classification).
# ---------------------------------------------------------------------------
TEMPLATES: dict[str, str] = {
    "summarise": """Summarise the following text in {{max_sentences}} sentences or fewer.
Be concise and capture only the key points.

Text:
{{text}}""",

    "classify": """Classify the sentiment of the following text as exactly one of:
positive, negative, or neutral.
Respond with only the label — no punctuation, no explanation.

Text: {{text}}""",

    # TODO: add your own template here
    "custom": "TODO: define your own template with at least one {{placeholder}}",
}


# ---------------------------------------------------------------------------
# TODO 3: Build a reusable helper that accepts a system prompt string and a
#         filled user message, sends them to the LLM, and returns the reply text.
#         This separates prompt construction from the API call.
# ---------------------------------------------------------------------------
def call_with_system(system_prompt: str, user_message: str) -> str:
    llm = get_provider()
    messages: list[ChatMessage] = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=user_message),
    ]
    # TODO: send `messages` with `llm.chat(...)` and return the reply's text.
    return "TODO: implement call_with_system"


def main() -> None:
    llm = get_provider()
    print(f"Provider: {llm.name} / {llm.chat_model}\n")

    # -------------------------------------------------------------------------
    # TODO 4: Use render_template + TEMPLATES["summarise"] to summarise the
    #         sample text below in at most 2 sentences. Print the result.
    # -------------------------------------------------------------------------
    sample_text = """Transformer models revolutionized natural language processing by replacing
recurrent architectures with a mechanism called self-attention. Instead of processing
tokens sequentially, transformers consider all tokens simultaneously, learning which
parts of the input are relevant to each other. This parallel processing makes them
much faster to train on modern GPUs and allows them to capture long-range dependencies
that were difficult for RNNs to model."""

    summary_prompt = render_template(
        TEMPLATES["summarise"],
        {"max_sentences": "2", "text": sample_text},
    )
    print("--- summarisation ---")
    print("Filled prompt:\n", summary_prompt, "\n")
    # summary = call_with_system("You are a precise summariser.", summary_prompt)
    # print("Summary:", summary, "\n")

    # -------------------------------------------------------------------------
    # TODO 5: Use TEMPLATES["classify"] to classify three short texts and print
    #         the label for each. The output should be ONLY the label word.
    #         If the model returns extra text, note it — you'll fix this in task 4.
    # -------------------------------------------------------------------------
    samples = [
        "This is the best product I've ever bought!",
        "Arrived broken. Terrible packaging.",
        "It does the job. Nothing special.",
    ]
    print("--- classification ---")
    for text in samples:
        prompt = render_template(TEMPLATES["classify"], {"text": text})
        # label = call_with_system("You are a sentiment classifier.", prompt)
        # print(f'"{text}" → {label.strip()}')
        print(f'TODO: classify: "{text}"')

    # -------------------------------------------------------------------------
    # TODO 6 (stretch): Add a template for your own task and test it.
    #         Does the system prompt or the user message have more influence
    #         on the output style? Experiment by swapping the same instructions
    #         between system and user role.
    # -------------------------------------------------------------------------


if __name__ == "__main__":
    main()
