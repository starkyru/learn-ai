"""
Task 6 — Tool-output offloading 🟡

What this teaches:
  - In a multi-iteration agent loop, every tool result you append to the message
    history is re-sent to the model on EVERY later iteration. One 3–4 K-token
    web-search result therefore doesn't cost 3–4 K tokens once — it costs that
    much per remaining iteration.
  - The offloading pattern: persist the full tool output to a tool-log store
    keyed by an id, put only a one-line reference into the history
    ("[Tool Log #2] stored; call read_tool_log to retrieve"), and expose a
    read_tool_log(id) tool so the agent can pull the full text back on demand.
  - Correctness requirement: the store must round-trip the output exactly, and
    the loop must still reach answers whose supporting facts live only inside a
    stored payload.

Fully offline and deterministic: the "agent" is a scripted 5-iteration loop and
web_search returns large canned payloads — no provider, no network.

Dependencies:
  tiktoken — install with: uv sync --extra context   (same as Task 1)

How to run:
  uv run python modules/16-context-engineering/py/06_tool_offloading.py
"""

from __future__ import annotations

from itertools import pairwise

import tiktoken

# A chat message: {"role": "system" | "user" | "assistant" | "tool", "content": str}
Message = dict[str, str]
# A tool-log record: {"id": int, "tool_name": str, "output": str}
ToolLogStore = list[dict]

# ---------------------------------------------------------------------------
# Provided: token counting (same tooling as Task 1 — do not edit)
# ---------------------------------------------------------------------------

_ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Exact token count with tiktoken (cl100k_base), as in Task 1."""
    return len(_ENCODING.encode(text))


def count_context_tokens(messages: list[Message]) -> int:
    """Sum of token counts across every message currently in the context."""
    return sum(count_tokens(m["content"]) for m in messages)


# ---------------------------------------------------------------------------
# Provided: the fake web_search tool with large canned payloads (do not edit)
# ---------------------------------------------------------------------------

# The needle: this number exists ONLY inside the second search payload. The
# final answer must contain it — proving that on-demand retrieval worked.
NEEDLE_FACT = "-183.4"
_FINDING_LINE = (
    "FINDING: The Meridian-3 probe recorded a nightside surface temperature of "
    f"{NEEDLE_FACT} degrees Celsius at its polar landing site."
)

_FILLER_SENTENCES = [
    "Independent laboratories have replicated the measurement under a range of ambient conditions.",
    "The methodology section describes calibration runs, control groups, and error bars in detail.",
    "Commentators note that funding cycles and launch windows constrain how fast follow-ups appear.",
    "A meta-analysis is planned once at least five independent data sets become available.",
    "Reviewers flagged instrument drift as the dominant source of systematic uncertainty.",
]


def _make_payload(topic: str, n_results: int, finding: str | None = None) -> str:
    """Build a deterministic, large search-result payload (~3-4 K tokens)."""
    lines = [f"web_search results for: {topic}", ""]
    for i in range(n_results):
        a = _FILLER_SENTENCES[i % len(_FILLER_SENTENCES)]
        b = _FILLER_SENTENCES[(i + 2) % len(_FILLER_SENTENCES)]
        lines.append(f"[Result {i + 1}] {topic} — source {i + 1}: {a} {b}")
        if finding is not None and i == n_results // 2:
            lines.append(finding)
    return "\n".join(lines)


SEARCH_QUERIES = [
    "solar-sail propulsion field tests",
    "Meridian-3 probe landing telemetry",
    "cryogenic fuel storage benchmarks",
]

_CANNED_RESULTS = {
    SEARCH_QUERIES[0]: _make_payload(SEARCH_QUERIES[0], 80),
    SEARCH_QUERIES[1]: _make_payload(SEARCH_QUERIES[1], 80, finding=_FINDING_LINE),
    SEARCH_QUERIES[2]: _make_payload(SEARCH_QUERIES[2], 80),
}


def fake_web_search(query: str) -> str:
    """Deterministic stand-in for a web-search tool. Same query → same payload."""
    if query not in _CANNED_RESULTS:
        raise KeyError(f"no canned result for query: {query!r}")
    return _CANNED_RESULTS[query]


def extract_finding(text: str) -> str:
    """Return the first line starting with 'FINDING:' — the fact the task needs."""
    for line in text.splitlines():
        if line.startswith("FINDING:"):
            return line
    return "FINDING: (not located in the current context)"


# ---------------------------------------------------------------------------
# Provided: the scripted agent loop (do not edit)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a research agent. Use web_search to gather sources, then answer "
    "the user's question with the specific figure you found."
)
USER_TASK = (
    "What nightside surface temperature did the Meridian-3 probe record? "
    "Search the three assigned topics, then answer."
)

# A fixed 5-iteration script — the same sequence drives BOTH loops.
SCRIPT: list[dict] = [
    {"action": "web_search", "query": SEARCH_QUERIES[0]},
    {"action": "web_search", "query": SEARCH_QUERIES[1]},
    {"action": "web_search", "query": SEARCH_QUERIES[2]},
    {"action": "read_tool_log", "log_id": 2},
    {"action": "answer"},
]


def run_loop_naive(script: list[dict]) -> tuple[list[Message], list[int], str]:
    """
    Baseline: every full tool output is appended to the message history, so
    every later iteration re-carries it. Returns (messages, per-iteration
    context token counts, final answer).
    """
    messages: list[Message] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TASK},
    ]
    per_iteration: list[int] = []
    final_answer = ""

    for step in script:
        if step["action"] == "web_search":
            output = fake_web_search(step["query"])
            messages.append(
                {"role": "assistant", "content": f'Calling web_search("{step["query"]}")'}
            )
            messages.append({"role": "tool", "content": output})
        elif step["action"] == "read_tool_log":
            # Naive loop keeps everything inline — nothing to fetch.
            messages.append(
                {"role": "assistant", "content": "(full outputs already inline — no lookup needed)"}
            )
        elif step["action"] == "answer":
            finding = extract_finding("\n".join(m["content"] for m in messages))
            final_answer = f"Answer: {finding}"
            messages.append({"role": "assistant", "content": final_answer})
        per_iteration.append(count_context_tokens(messages))

    return messages, per_iteration, final_answer


# ---------------------------------------------------------------------------
# Core functions — YOU implement these four
# ---------------------------------------------------------------------------


def write_tool_log(store: ToolLogStore, tool_name: str, output: str) -> int:
    """
    Persist one full tool output into the store; return its new id.

    TODO: implement.
      - Compute the new id: ids are 1-based and sequential (the store's current
        length tells you the next one).
      - Append a record dict with keys "id", "tool_name", "output".
      - Return the new id.
    """
    # TODO: append the record and return its id
    raise NotImplementedError("TODO: implement write_tool_log()")


def make_reference(log_id: int, tool_name: str, output: str) -> str:
    """
    Build the compact one-liner that goes into the message history INSTEAD of
    the full output. A later iteration must be able to act on it, so it should:
      - name the tool and the log id (e.g. a "[Tool Log #<id>]" tag),
      - state the stored size in tokens (use count_tokens on the output),
      - include a short preview — the first ~80 characters of the output,
      - say that read_tool_log(<id>) retrieves the full text.

    Return a SINGLE line (no newlines), well under 100 tokens.

    TODO: implement — assemble and return that reference string.
    """
    # TODO: build the one-line reference (id + tool name + token count + preview + how to retrieve)
    raise NotImplementedError("TODO: implement make_reference()")


def read_tool_log(store: ToolLogStore, log_id: int) -> str:
    """
    Return the EXACT stored output for log_id (byte-for-byte round-trip).

    TODO: implement.
      - Find the record whose "id" equals log_id.
      - Return its "output" unmodified.
      - Raise KeyError if no record has that id.
    """
    # TODO: look the record up by id and return its stored output
    raise NotImplementedError("TODO: implement read_tool_log()")


def run_loop_with_offloading(
    script: list[dict], store: ToolLogStore
) -> tuple[list[Message], list[int], str]:
    """
    The same scripted loop as run_loop_naive, but full tool outputs never enter
    the message history — only references do.

    TODO: implement. Mirror run_loop_naive step by step:
      - Start from the same two seed messages (system + user), an empty
        per-iteration list, and an empty final answer.
      - "web_search": call fake_web_search, persist the full output with
        write_tool_log, append the same assistant "Calling web_search(...)"
        line, then append a tool message whose content is ONLY
        make_reference(...) — never the payload itself.
      - "read_tool_log": call read_tool_log with the step's "log_id", run
        extract_finding on the retrieved text, and append an assistant line
        (e.g. noting the lookup) plus a tool message containing just that
        finding line — the agent keeps the one sentence it needs, not the
        whole payload.
      - "answer": exactly as in the naive loop — extract the finding from the
        joined message contents and record "Answer: <finding>" as both the
        final answer and a new assistant message.
      - After EVERY iteration, append count_context_tokens(messages) to the
        per-iteration list.
    Return (messages, per_iteration, final_answer).
    """
    # TODO: implement the offloaded loop (use run_loop_naive above as your template)
    raise NotImplementedError("TODO: implement run_loop_with_offloading()")


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------

NAIVE_FLOOR = 9_000  # naive context must END above this many tokens
OFFLOADED_CEILING = 1_200  # offloaded context must STAY below this at every iteration


def main() -> None:
    print("=== Task 6: Tool-output offloading ===\n")

    naive_msgs, naive_counts, naive_answer = run_loop_naive(SCRIPT)
    store: ToolLogStore = []
    off_msgs, off_counts, off_answer = run_loop_with_offloading(SCRIPT, store)

    print(f"{'Iter':<5} {'Action':<28} {'Naive ctx tokens':>17} {'Offloaded ctx tokens':>21}")
    print("-" * 75)
    for i, (step, n, o) in enumerate(zip(SCRIPT, naive_counts, off_counts, strict=True), start=1):
        action = step["action"]
        if action == "web_search":
            action = f'web_search("{step["query"][:14]}…")'
        elif action == "read_tool_log":
            action = f"read_tool_log({step['log_id']})"
        print(f"{i:<5} {action:<28} {n:>17} {o:>21}")

    naive_total = sum(naive_counts)
    off_total = sum(off_counts)
    print("-" * 75)
    print(f"{'Tokens the model reads across all 5 iterations':<51}{naive_total:>7} {off_total:>14}")
    print(f"\nNaive final answer     : {naive_answer}")
    print(f"Offloaded final answer : {off_answer}")
    print(f"Tool-log store         : {len(store)} record(s), ids {[r['id'] for r in store]}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    ok_monotone = all(b > a for a, b in pairwise(naive_counts))
    ok_naive_big = naive_counts[-1] > NAIVE_FLOOR
    ok_off_small = max(off_counts) < OFFLOADED_CEILING
    original = fake_web_search(SEARCH_QUERIES[1])
    ok_roundtrip = read_tool_log(store, 2) == original
    ok_store = [r["id"] for r in store] == [1, 2, 3]
    ok_answer = NEEDLE_FACT in off_answer
    _ = (naive_msgs, off_msgs)  # kept for learner inspection in a debugger

    print("\nAcceptance:")
    print(f"  [{'x' if ok_monotone else ' '}] naive context grows monotonically every iteration")
    print(
        f"  [{'x' if ok_naive_big else ' '}] naive context ends above {NAIVE_FLOOR} tokens "
        f"(got {naive_counts[-1]})"
    )
    print(
        f"  [{'x' if ok_off_small else ' '}] offloaded context stays below {OFFLOADED_CEILING} "
        f"tokens at every iteration (max {max(off_counts)})"
    )
    print(f"  [{'x' if ok_store else ' '}] write_tool_log assigned sequential ids 1, 2, 3")
    print(
        f"  [{'x' if ok_roundtrip else ' '}] read_tool_log(2) round-trips the exact original payload"
    )
    print(
        f"  [{'x' if ok_answer else ' '}] offloaded final answer contains the needle fact "
        f"({NEEDLE_FACT}) that lives only inside stored payload #2"
    )

    if all([ok_monotone, ok_naive_big, ok_off_small, ok_store, ok_roundtrip, ok_answer]):
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
