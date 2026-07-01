"""
Task 1 — Chat & system prompts 🟢

What this teaches:
  - How multi-turn chat works: the model never has memory — you send the
    full conversation history on every request.
  - How the "system" role shapes behaviour without being shown to users.
  - Why message ordering matters (system → user → assistant → user …).

How to run:
  uv run python modules/02-llm-integration/py/01_chat.py
"""

from llm_core import get_provider, ChatMessage

# ---------------------------------------------------------------------------
# TODO 1: Define a system prompt that gives the assistant a persona or scope.
#         Keep it short (1-3 sentences). Example: "You are a concise, helpful
#         coding tutor. Explain things simply. When in doubt, show a snippet."
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = "TODO: write your system prompt here."


def main() -> None:
    llm = get_provider()
    print(f"Using provider: {llm.name} / model: {llm.chat_model}\n")

    # -------------------------------------------------------------------------
    # TODO 2: Initialise the conversation history.
    #         The history starts with the system message and grows as the user
    #         and assistant take turns. Build a list of ChatMessage objects.
    # -------------------------------------------------------------------------
    #         Seed it with a single system-role entry carrying SYSTEM_PROMPT.
    history: list[ChatMessage] = []

    print('Multi-turn chat started. Type "exit" to quit.\n')

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "exit":
            break
        if not user_input:
            continue

        # -------------------------------------------------------------------------
        # TODO 3: Drive one turn of the conversation:
        #         - Append the user's line to `history` as a user-role ChatMessage.
        #         - Call llm.chat(history) with the WHOLE history (the model has no
        #           memory of its own — history IS the memory).
        #         - Append the reply back to `history` as an assistant-role message
        #           so the next turn sees it.
        #         - Print the reply with an "Assistant: " prefix.
        # -------------------------------------------------------------------------

        print("TODO: implement the chat loop above.\n")
        break  # remove this once you've implemented the loop

    # -------------------------------------------------------------------------
    # TODO 4 (stretch): Print the full conversation history at the end so you
    #         can see exactly what was sent to the model on the last request.
    #         Notice how it grows with each turn — this is the "context window"
    #         filling up. What happens when a long conversation exceeds the limit?
    # -------------------------------------------------------------------------


if __name__ == "__main__":
    main()
