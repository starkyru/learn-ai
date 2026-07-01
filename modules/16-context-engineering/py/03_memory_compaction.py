"""
Task 3 — Conversation memory / compaction 🟡

What this teaches:
  - In a long chat, the context window fills up with old turns. The model sees the
    full history on every request — you are responsible for keeping it within budget.
  - Sliding window (keep the last K turns) is simple but loses early context entirely.
  - Running summary (summarise old turns when the budget is exceeded) is more powerful:
    the model retains the gist of the conversation without the verbatim transcript.
  - A hybrid (summary + recent turns) is the most robust production approach.

How to run:
  uv run python modules/16-context-engineering/py/03_memory_compaction.py
"""

from __future__ import annotations

from llm_core import get_provider, ChatMessage, ChatOptions

# ---------------------------------------------------------------------------
# Rough token counter (replace with tiktoken in Task 1 if you want precision).
# ---------------------------------------------------------------------------
def count_tokens(text: str) -> int:
    return int(len(text.split()) * 1.3)


def count_history_tokens(messages: list[ChatMessage]) -> int:
    return sum(count_tokens(m.content) for m in messages)


# Budget is intentionally small to trigger compaction during the demo.
TOKEN_BUDGET = 800

# ---------------------------------------------------------------------------
# Simulated conversation — 15 turns covering several distinct topics.
# The early turns (the movie recommendation) will eventually be compacted.
# ---------------------------------------------------------------------------
CONVERSATION_SCRIPT = [
    ("user",      "What's a good sci-fi movie to watch tonight?"),
    ("assistant", "I'd recommend 'Arrival' (2016). It's a cerebral sci-fi film about a linguist who helps decode an alien language. Thoughtful, slow-paced, and emotionally resonant."),
    ("user",      "Sounds great! Is it suitable for kids?"),
    ("assistant", "It's rated PG-13. The themes are abstract rather than violent, but younger children might find the pacing slow. I'd say fine for teenagers and adults."),
    ("user",      "OK. Now let's talk about Python. How do I read a file line by line?"),
    ("assistant", "Use `with open('file.txt') as f: for line in f: print(line.strip())`. The `with` statement ensures the file is closed even if an exception occurs."),
    ("user",      "What about writing to a file?"),
    ("assistant", "Use `with open('output.txt', 'w') as f: f.write('hello\\n')`. For appending instead of overwriting, use mode `'a'` instead of `'w'`."),
    ("user",      "How does Python's GIL affect multi-threading?"),
    ("assistant", "The Global Interpreter Lock (GIL) prevents true parallel execution of Python threads for CPU-bound work. Use `multiprocessing` for CPU parallelism; threading is fine for I/O-bound work where threads spend most time waiting."),
    ("user",      "Got it. Can you explain async/await?"),
    ("assistant", "Async/await is Python's syntax for cooperative concurrency. An `async def` function is a coroutine. `await` suspends the coroutine until a result is ready, yielding control to the event loop. It's ideal for I/O-bound workloads without threads."),
    ("user",      "Thanks! Switching topics — what's the capital of France?"),
    ("assistant", "Paris."),
    ("user",      "And Germany?"),
    ("assistant", "Berlin."),
    ("user",      "One more — what was the movie you recommended earlier?"),
    ("user",      "Do you remember? It was at the start of our conversation."),
]


# ---------------------------------------------------------------------------
# TODO 1: Implement summarise_turns.
#         Given a list of ChatMessage objects, ask the LLM to compress them.
#         - Flatten `turns` into a single transcript string ("<role>: <content>" per line).
#         - Build a prompt asking the model to summarise the exchange in 2–3 sentences,
#           keeping key facts / decisions / topics and dropping conversational filler,
#           followed by the transcript.
#         - Send it as one ChatMessage("user", ...) via `llm.chat(...)` with
#           ChatOptions(temperature=0) so the summary is deterministic.
#         - Return a single ChatMessage with role "system" whose content begins with
#           "Summary of earlier conversation: " and then the model's text (this prefix
#           is what maybe_compact and the model rely on to recognise the summary).
# ---------------------------------------------------------------------------
def summarise_turns(turns: list[ChatMessage], llm) -> ChatMessage:
    raise NotImplementedError("TODO: implement summarise_turns")


# ---------------------------------------------------------------------------
# TODO 2: Implement maybe_compact.
#         1. Count the total tokens in `messages`.
#         2. If the count exceeds `budget`:
#            a. Separate system messages from non-system messages.
#            b. Identify the oldest non-system turns to summarise
#               (enough to bring the total below budget).
#            c. Call summarise_turns on those oldest turns.
#            d. Return: [system_messages] + [summary_message] + [remaining_turns].
#         3. If within budget, return messages unchanged.
#         4. Print a line when compaction fires so you can observe it.
# ---------------------------------------------------------------------------
def maybe_compact(
    messages: list[ChatMessage],
    budget: int,
    llm,
) -> list[ChatMessage]:
    # - Use count_history_tokens(messages); if it is within `budget`, return messages
    #   unchanged (fast path — no LLM call).
    # - Otherwise print a line noting compaction fired (so you can watch it in the demo),
    #   then partition messages into system messages and conversation (non-system) turns.
    # - Pick how many of the OLDEST conversation turns to compress — summarising roughly
    #   the first half (at least one) is a reasonable split. Call summarise_turns on that
    #   oldest slice and keep the rest verbatim.
    # - Reassemble in order: system messages, then the single summary message, then the
    #   kept recent turns — and return that new list.
    raise NotImplementedError("TODO: implement maybe_compact")


def main() -> None:
    print("=== Task 3: Conversation Memory / Compaction ===\n")
    print(f"Token budget: {TOKEN_BUDGET} tokens\n")

    try:
        llm = get_provider()
        print(f"Provider: {llm.name} / {llm.chat_model}\n")
    except Exception as e:
        print(f"Could not load provider: {e}")
        return

    # -------------------------------------------------------------------------
    # TODO 3: Simulate the conversation.
    #         For each turn in CONVERSATION_SCRIPT:
    #           1. Append the scripted message to history.
    #           2. If the turn is a "user" message, call maybe_compact, then
    #              call llm.chat(history) to get the assistant's reply.
    #           3. Append the assistant's reply to history.
    #           4. Print the current token count after each turn.
    # -------------------------------------------------------------------------

    history: list[ChatMessage] = [
        ChatMessage("system", "You are a helpful, knowledgeable assistant.")
    ]

    for role, content in CONVERSATION_SCRIPT:
        # Append the scripted message (both user and pre-written assistant turns).
        history.append(ChatMessage(role, content))  # type: ignore[arg-type]
        tokens = count_history_tokens(history)
        print(f"[{role:>9}] tokens={tokens:4d} | {content[:60]}...")

        if role == "user":
            try:
                # Compact if needed, then get a real LLM response.
                history = maybe_compact(history, TOKEN_BUDGET, llm)
                result = llm.chat(history)
                history.append(ChatMessage("assistant", result.text))
                print(f"[assistant] {result.text[:80]}...")
            except NotImplementedError:
                print("  [TODO: implement maybe_compact and summarise_turns]")
                # Append a placeholder so the loop can continue.
                history.append(ChatMessage("assistant", "(not implemented)"))
            except Exception as e:
                print(f"  ERROR: {e}")
                break

    print()
    print("Observation:")
    print("  When compaction fires, observe whether the model still answers questions")
    print("  about early turns (e.g. the movie recommendation) via the summary.")


if __name__ == "__main__":
    main()
