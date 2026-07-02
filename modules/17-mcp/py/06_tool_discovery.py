"""06_tool_discovery.py — Semantic tool discovery: the toolbox.  🟡

What this teaches:
    Tasks 2-5 always passed EVERY tool schema to the model on every call.
    That works with 3 tools. It breaks with 30: published evals (e.g. the
    Berkeley Function-Calling Leaderboard, Anthropic's Tool Search) show
    tool-selection accuracy DROPS as the schema list grows — lexically
    confusable descriptions start to win — while the token cost of shipping
    every schema climbs regardless of relevance.

    The fix is the **toolbox pattern** (a.k.a. semantic tool discovery):
      1. Index every tool definition in a vector store — embed an
         LLM-augmented description (intent + use-cases), not just the raw
         signature.
      2. Per user query, retrieve only the top-k semantically relevant tools.
      3. Pass just those k schemas to the model.

    You implement the four pieces: augment_description(), index_toolbox(),
    retrieve_tools(), measure_token_cost(). The registry of 20 tools, the
    fixed 10-query eval set, and the deterministic "selector" stand-in for
    the model are provided, so the accuracy comparison runs offline.

    The scripted selector models the measured failure mode: with a small,
    focused schema list it reliably picks the right tool; past its "focus
    budget" a wrong tool whose raw description merely LOOKS more like the
    query can win. Deterministic, so the experiment is reproducible.

The math (same bag-of-words cosine as module 06c):
    bow(text)[w]  = count of word w in text
    cosine(a, b)  = dot(a, b) / (||a|| * ||b||),  0.0 if either norm is 0
    top-k         = sort docs by cosine desc (stable), take the first k

How to run (from repo root):
    uv run python modules/17-mcp/py/06_tool_discovery.py            # offline
    LLM_PROVIDER=ollama uv run python modules/17-mcp/py/06_tool_discovery.py --embed
    LLM_PROVIDER=ollama uv run python modules/17-mcp/py/06_tool_discovery.py --live

    --embed  retrieve with real provider.embed() vectors instead of
             bag-of-words (any provider except Anthropic — no embeddings there).
    --live   replace the scripted selector with the real model choosing a
             tool via get_provider().chat().

Python deps: none beyond the base install (llm_core only for --embed/--live).
"""

from __future__ import annotations

import argparse
import json  # noqa: F401 — the measure_token_cost() TODO below uses json.dumps
import math
import re
from collections import Counter
from collections.abc import Callable

# A vector is either a sparse bag-of-words Counter or a dense embedding list.
Vec = Counter | list[float]
VectorizeFn = Callable[[list[str]], list[Vec]]
SelectorFn = Callable[[str, list[dict], str], str]


# ---------------------------------------------------------------------------
# Toolbox registry  (provided — do not edit)
# ---------------------------------------------------------------------------


def _tool(name: str, description: str, props: dict[str, str], required: list[str]) -> dict:
    """Build one tool definition in the JSON-Schema shape MCP/OpenAI use."""
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": {k: {"type": "string", "description": v} for k, v in props.items()},
            "required": required,
        },
    }


TOOLS: list[dict] = [
    _tool(
        "get_weather",
        "Get the current weather conditions for a city.",
        {"city": "City name", "units": "metric or imperial"},
        ["city"],
    ),
    _tool(
        "get_forecast",
        "Get the multi-day weather forecast for a city.",
        {"city": "City name", "days": "Number of days ahead"},
        ["city"],
    ),
    _tool(
        "send_email",
        "Send an email message to a recipient.",
        {"to": "Recipient address", "subject": "Subject line", "body": "Message body"},
        ["to", "subject", "body"],
    ),
    _tool(
        "create_calendar_event",
        "Create an event on the user's calendar.",
        {"title": "Event title", "start_time": "ISO start", "end_time": "ISO end"},
        ["title", "start_time"],
    ),
    _tool(
        "list_calendar_events",
        "List the events on the user's calendar between two dates.",
        {"start_date": "ISO date", "end_date": "ISO date"},
        ["start_date"],
    ),
    _tool(
        "set_reminder",
        "Set a reminder that fires at a chosen time.",
        {"message": "Reminder text", "time": "When to fire"},
        ["message", "time"],
    ),
    _tool(
        "read_file", "Read the contents of a file at a given path.", {"path": "File path"}, ["path"]
    ),
    _tool(
        "write_file",
        "Write text content to a file at a given path.",
        {"path": "File path", "content": "Text to write"},
        ["path", "content"],
    ),
    _tool("delete_file", "Delete the file at a given path.", {"path": "File path"}, ["path"]),
    _tool(
        "calculator",
        "Evaluate an arithmetic expression and return the numeric result.",
        {"expression": "Arithmetic expression"},
        ["expression"],
    ),
    _tool(
        "unit_convert",
        "Convert a value from one unit to another, such as miles to kilometers.",
        {"value": "Quantity", "from_unit": "Source unit", "to_unit": "Target unit"},
        ["value", "from_unit", "to_unit"],
    ),
    _tool(
        "currency_convert",
        "Exchange an amount of money between two currencies at the current rate.",
        {"amount": "Amount of money", "from_currency": "Source code", "to_currency": "Target code"},
        ["amount", "from_currency", "to_currency"],
    ),
    _tool(
        "web_search",
        "Look up information online and return short result snippets.",
        {"query": "Search terms"},
        ["query"],
    ),
    _tool(
        "news_search",
        "Search the web's news sources for the latest articles about a topic.",
        {"topic": "News topic", "days": "How far back to look"},
        ["topic"],
    ),
    _tool(
        "db_query",
        "Run a read-only SQL statement against the analytics database.",
        {"sql": "SQL SELECT statement"},
        ["sql"],
    ),
    _tool(
        "db_schema",
        "Describe the tables and columns available in the analytics database.",
        {"table": "Table name, or empty for all"},
        [],
    ),
    _tool(
        "run_python",
        "Execute a Python snippet in a sandbox and return its stdout.",
        {"code": "Python source code"},
        ["code"],
    ),
    _tool(
        "translate_text",
        "Translate text from one language to another.",
        {"text": "Text to translate", "target_language": "Target language"},
        ["text", "target_language"],
    ),
    _tool(
        "generate_image",
        "Generate an image from a text description.",
        {"prompt": "Image description", "size": "Pixel dimensions"},
        ["prompt"],
    ),
    _tool(
        "describe_image",
        "Describe what is shown in an image at a URL.",
        {"image_url": "Image URL"},
        ["image_url"],
    ),
]

# The "LLM-augmented" use-case line per tool: what a user might actually SAY
# when they need it. In production you'd generate these once with a strong
# model ("list 3 requests this tool answers"); here they're pre-generated so
# the task stays offline.
USE_CASES: dict[str, str] = {
    "get_weather": "what is it like outside right now, temperature in a city today, is it raining",
    "get_forecast": "will it rain tomorrow, weather for the next few days, weekend forecast",
    "send_email": "write to a colleague, send a message about a report, follow up with a client",
    "create_calendar_event": "schedule a meeting, book a call with someone, block time next week",
    "list_calendar_events": "what is on my agenda, am I free on Friday, upcoming appointments",
    "set_reminder": "remind me to do something later, nudge me at 5pm, do not let me forget",
    "read_file": "open a document, show the contents of notes.txt, what does the file say",
    "write_file": "save this text to disk, create a new file with content, overwrite a document",
    "delete_file": "remove an old file, clean up a document, get rid of report.txt",
    "calculator": "what is 15 percent of a number, add up expenses, quick arithmetic",
    "unit_convert": "miles to kilometers, celsius to fahrenheit, pounds to kilograms",
    "currency_convert": "dollars to euros, how much is 100 USD in yen, exchange money",
    "web_search": "look up release notes online, research a topic, find documentation on the internet",
    "news_search": "current events, headlines from the last few days, what happened today",
    "db_query": "how many users signed up last week, count rows in a table, monthly revenue numbers",
    "db_schema": "what tables exist, which columns does a table have, database structure",
    "run_python": "run a script, compute something with code, test a snippet",
    "translate_text": "translate a paragraph into Japanese, say this in French, localise a sentence",
    "generate_image": "draw a picture of a cat, create an illustration, make a logo concept",
    "describe_image": "what is in this photo, caption an image, identify objects in a picture",
}

# Fixed eval set: (user query, name of the single correct tool).
EVAL_SET: list[tuple[str, str]] = [
    ("What's the weather like in Paris right now?", "get_weather"),
    ("Send an email to Alice about the quarterly report", "send_email"),
    ("Schedule a 30 minute meeting with Bob next Tuesday", "create_calendar_event"),
    ("How many users signed up last week?", "db_query"),
    ("Convert 250 US dollars to euros", "currency_convert"),
    ("Search the web for the latest TypeScript release notes", "web_search"),
    ("Read the contents of notes.txt", "read_file"),
    ("What is 15 percent of 240?", "calculator"),
    ("Translate this paragraph into Japanese", "translate_text"),
    ("What's on my calendar next Friday?", "list_calendar_events"),
]

TOP_K = 3


# ---------------------------------------------------------------------------
# Vector helpers  (provided — do not edit)
# ---------------------------------------------------------------------------


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens (letters/digits)."""
    return re.findall(r"[a-z0-9]+", text.lower())


def bag_of_words(text: str) -> Counter[str]:
    """Sparse count vector: word -> count."""
    return Counter(tokenize(text))


def cosine(a: Vec, b: Vec) -> float:
    """Cosine similarity for sparse Counters OR dense embedding lists."""
    if isinstance(a, Counter) and isinstance(b, Counter):
        dot = sum(count * b[word] for word, count in a.items())
        norm_a = math.sqrt(sum(c * c for c in a.values()))
        norm_b = math.sqrt(sum(c * c for c in b.values()))
    else:
        assert isinstance(a, list) and isinstance(b, list)
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def bow_vectorize(texts: list[str]) -> list[Vec]:
    """Offline default vectorizer: one bag-of-words Counter per text."""
    return [bag_of_words(t) for t in texts]


def make_embed_vectorize() -> VectorizeFn:
    """--embed path: real embeddings through llm_core (never a vendor SDK)."""
    from llm_core import get_provider  # noqa: PLC0415

    provider = get_provider()

    def vectorize(texts: list[str]) -> list[Vec]:
        return list(provider.embed(texts).vectors)

    return vectorize


def tool_signature(tool: dict) -> str:
    """The raw signature text: name (de-underscored) + description. This is
    what naive retrieval indexes — and what the selector below 'reads'."""
    return tool["name"].replace("_", " ") + " " + tool["description"]


# ---------------------------------------------------------------------------
# The selector  (provided — do not edit)
# ---------------------------------------------------------------------------

# Up to this many schemas the scripted "model" stays reliable; beyond it,
# lexically confusable schemas can distract it (the measured failure mode).
FOCUS_BUDGET = 5


def scripted_selector(query: str, tools_passed: list[dict], labeled: str) -> str:
    """Deterministic stand-in for the model's tool choice.

    - Scores every passed schema: cosine(query, raw signature text).
    - Picks the labeled (correct) tool IF it was passed AND either the schema
      list fits the focus budget or no wrong tool outscores it.
    - Otherwise picks the highest-scoring WRONG tool (a 'confusion').

    This makes the full-list-vs-top-k accuracy comparison offline and exactly
    reproducible, while behaving the way evals show real models behave.
    """
    q_vec = bag_of_words(query)
    scores = {t["name"]: cosine(q_vec, bag_of_words(tool_signature(t))) for t in tools_passed}
    wrong = [(name, s) for name, s in scores.items() if name != labeled]
    best_wrong_name, best_wrong_score = max(wrong, key=lambda pair: pair[1])
    if labeled in scores and (
        len(tools_passed) <= FOCUS_BUDGET or scores[labeled] >= best_wrong_score
    ):
        return labeled
    return best_wrong_name


def make_live_selector() -> SelectorFn:
    """--live path: the real model picks the tool, via llm_core."""
    from llm_core import ChatOptions, get_provider  # noqa: PLC0415

    provider = get_provider()

    def selector(query: str, tools_passed: list[dict], labeled: str) -> str:
        del labeled  # the real model never sees the answer key
        menu = "\n".join(f"- {t['name']}: {t['description']}" for t in tools_passed)
        prompt = (
            "Pick the single best tool for the user request.\n"
            f"Tools:\n{menu}\n\nRequest: {query}\n"
            "Reply with ONLY the tool name."
        )
        reply = provider.chat(
            [{"role": "user", "content": prompt}],
            ChatOptions(temperature=0.0, max_tokens=20),
        ).text
        names = {t["name"] for t in tools_passed}
        for token in re.findall(r"[a-z0-9_]+", reply.lower()):
            if token in names:
                return token
        return reply.strip()

    return selector


# ---------------------------------------------------------------------------
# Core functions — YOU implement these four
# ---------------------------------------------------------------------------


def augment_description(tool: dict) -> str:
    """Build the RETRIEVAL text for one tool — richer than the raw signature.

    A user says "how much is 100 USD in yen?", not "exchange an amount of
    money between two currencies", so indexing the signature alone misses
    intent-phrased queries. Combine everything that carries meaning:

      - the tool name, with underscores turned into spaces (so "db_query"
        matches the words "db" and "query"),
      - the raw description string,
      - the parameter names (the keys under tool["parameters"]["properties"]),
      - the tool's pre-generated use-case line from USE_CASES.

    Join all of those pieces, space-separated, into one string and return it.
    """
    # TODO: implement augment_description (name + description + param names + use-case)
    raise NotImplementedError("TODO: implement augment_description()")


def index_toolbox(
    tools: list[dict],
    vectorize: VectorizeFn,
    text_fn: Callable[[dict], str] | None = None,
) -> list[tuple[dict, Vec]]:
    """Index the toolbox: one vector per tool, paired with its definition.

    `text_fn` decides what text represents each tool (when None, use
    augment_description; the harness also passes tool_signature to build the
    naive baseline index).

      - Build the list of texts by applying text_fn to every tool.
      - Vectorize them in ONE vectorize(texts) call (one batch — this matters
        when the vectorizer is a real embeddings API).
      - Pair each tool with its vector (zip with strict=True) and return the
        list of (tool, vector) tuples.
    """
    # TODO: implement index_toolbox (texts -> one vectorize batch -> pairs)
    raise NotImplementedError("TODO: implement index_toolbox()")


def retrieve_tools(
    index: list[tuple[dict, Vec]],
    query: str,
    vectorize: VectorizeFn,
    k: int = TOP_K,
) -> list[dict]:
    """Return the k tool definitions most semantically similar to the query.

    - Vectorize the query with the SAME vectorize function used to build the
      index (it takes a list of texts — take the first vector back out).
    - Score every (tool, vector) entry in the index with cosine().
    - Sort by score descending; Python's sort is stable, so equal scores
      keep registry order (deterministic).
    - Return just the tool dicts (not the scores) of the first k entries.
    """
    # TODO: implement retrieve_tools (top-k by cosine, descending, stable)
    raise NotImplementedError("TODO: implement retrieve_tools()")


def measure_token_cost(tools_passed: list[dict]) -> int:
    """Estimate the prompt-token cost of shipping these tool schemas.

    Every schema you pass is prompt tokens on EVERY call, relevant or not.
    Serialize each tool dict to a JSON string (json.dumps), sum the string
    lengths over all passed tools, and return the total divided by 4 with
    integer division — the standard ~4-characters-per-token heuristic.
    """
    # TODO: implement measure_token_cost (serialized-schema chars // 4)
    raise NotImplementedError("TODO: implement measure_token_cost()")


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description="Semantic tool discovery: the toolbox (Task 6).")
    ap.add_argument(
        "--embed",
        action="store_true",
        help="retrieve with real provider.embed() instead of bag-of-words",
    )
    ap.add_argument(
        "--live",
        action="store_true",
        help="let the real model pick the tool instead of the scripted selector",
    )
    args = ap.parse_args()

    vectorize = make_embed_vectorize() if args.embed else bow_vectorize
    selector = make_live_selector() if args.live else scripted_selector
    print("Task 6 — Semantic tool discovery: the toolbox")
    print(f"  retrieval: {'provider.embed()' if args.embed else 'bag-of-words (offline)'}")
    print(f"  selector : {'live model' if args.live else 'scripted (deterministic)'}")
    print(f"  toolbox  : {len(TOOLS)} tools, eval set: {len(EVAL_SET)} queries, k={TOP_K}\n")

    aug_index = index_toolbox(TOOLS, vectorize)  # what you ship
    raw_index = index_toolbox(TOOLS, vectorize, text_fn=tool_signature)  # naive baseline

    full_cost = measure_token_cost(TOOLS)

    hits_aug = 0
    hits_raw = 0
    full_correct: list[bool] = []
    topk_correct: list[bool] = []
    topk_costs: list[int] = []
    aug_only_win: tuple[str, str] | None = None

    print(f"{'query':<44} {'full-list pick':<22} {'top-3 pick':<22} tokens (top-3/full)")
    print("-" * 110)
    for query, labeled in EVAL_SET:
        top_aug = retrieve_tools(aug_index, query, vectorize)
        top_raw = retrieve_tools(raw_index, query, vectorize)
        aug_hit = any(t["name"] == labeled for t in top_aug)
        raw_hit = any(t["name"] == labeled for t in top_raw)
        hits_aug += aug_hit
        hits_raw += raw_hit
        if aug_hit and not raw_hit and aug_only_win is None:
            aug_only_win = (query, labeled)

        pick_full = selector(query, TOOLS, labeled)
        pick_topk = selector(query, top_aug, labeled)
        full_correct.append(pick_full == labeled)
        topk_correct.append(pick_topk == labeled)

        cost_k = measure_token_cost(top_aug)
        topk_costs.append(cost_k)
        mark_f = "✓" if pick_full == labeled else "✗"
        mark_k = "✓" if pick_topk == labeled else "✗"
        print(
            f"{query:<44} {mark_f} {pick_full:<20} {mark_k} {pick_topk:<20} "
            f"{cost_k:>4}/{full_cost} ({100 * cost_k / full_cost:.0f}%)"
        )

    acc_full = sum(full_correct)
    acc_topk = sum(topk_correct)
    print("-" * 110)
    print(
        f"retrieval hit-rate (top-{TOP_K}): augmented {hits_aug}/{len(EVAL_SET)}, "
        f"raw-signature {hits_raw}/{len(EVAL_SET)}"
    )
    print(
        f"selection accuracy: full-list {acc_full}/{len(EVAL_SET)}, "
        f"top-{TOP_K} {acc_topk}/{len(EVAL_SET)}"
    )
    if aug_only_win:
        q, t = aug_only_win
        print(
            f"augmentation win: {q!r} -> {t} is in the augmented top-{TOP_K} "
            f"but NOT in the raw-signature top-{TOP_K}\n  (the use-case line "
            f"carries the intent words the signature lacks)"
        )

    # ── Acceptance checks ────────────────────────────────────────────────────
    print("\nAcceptance:")
    ok_hits = hits_aug >= 9
    ok_acc = (
        acc_topk >= acc_full
        and acc_full <= len(EVAL_SET) - 2
        and all(k or not f for f, k in zip(full_correct, topk_correct, strict=True))
    )
    ok_cost = all(c < 0.25 * full_cost for c in topk_costs)
    ok_aug = aug_only_win is not None
    print(
        f"  [{'x' if ok_hits else ' '}] correct tool in top-{TOP_K} for >= 9/10 queries "
        f"({hits_aug}/10)"
    )
    print(
        f"  [{'x' if ok_acc else ' '}] top-{TOP_K} selection beats the full-list baseline "
        f"({acc_topk} vs {acc_full}; full list makes >= 2 mistakes; "
        f"top-{TOP_K} wins or ties on every query)"
    )
    print(
        f"  [{'x' if ok_cost else ' '}] top-{TOP_K} schema cost < 25% of full-list on every "
        f"query (max {max(topk_costs)}/{full_cost} = {100 * max(topk_costs) / full_cost:.0f}%)"
    )
    print(
        f"  [{'x' if ok_aug else ' '}] augmented descriptions beat raw-signature retrieval "
        f"on at least one query"
    )

    if ok_hits and ok_acc and ok_cost and ok_aug:
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
