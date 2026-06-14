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
#         Given a list of ChatMessage objects, ask the LLM to produce a 2–3 sentence
#         summary of that exchange. Return a single ChatMessage with role="system"
#         and content starting with "Summary of earlier conversation: ...".
#
#         Suggested prompt:
#           "Summarise the following conversation exchange in 2-3 sentences.
#            Focus on key facts, decisions, and topics discussed.
#            Do not include conversational filler.\n\n<turns>"
# ---------------------------------------------------------------------------
def summarise_turns(turns: list[ChatMessage], llm) -> ChatMessage:
    # transcript = "\n".join(f"{m.role}: {m.content}" for m in turns)
    # prompt = (
    #     "Summarise the following conversation exchange in 2-3 sentences. "
    #     "Focus on key facts, decisions, and topics discussed. "
    #     "Do not include conversational filler.\n\n" + transcript
    # )
    # result = llm.chat([ChatMessage("user", prompt)], ChatOptions(temperature=0))
    # return ChatMessage("system", "Summary of earlier conversation: " + result.text)
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
    # current = count_history_tokens(messages)
    # if current <= budget:
    #     return messages
    #
    # print(f"\n  [COMPACTION] tokens={current} > budget={budget}; compacting...")
    # system_msgs = [m for m in messages if m.role == "system"]
    # convo_msgs  = [m for m in messages if m.role != "system"]
    #
    # # Find the split point: how many old turns to summarise?
    # # Summarise the first half of the conversation turns.
    # split = max(1, len(convo_msgs) // 2)
    # to_summarise = convo_msgs[:split]
    # to_keep      = convo_msgs[split:]
    #
    # summary = summarise_turns(to_summarise, llm)
    # new_messages = system_msgs + [summary] + to_keep
    # new_count = count_history_tokens(new_messages)
    # print(f"  [COMPACTION] done — new token count={new_count}")
    # return new_messages
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
