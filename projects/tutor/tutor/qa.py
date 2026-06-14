"""Interactive Q&A REPL for the learn-ai course.

Loads the most relevant module README(s) as grounding context (light RAG) and
answers the learner's questions about the project, then advises concrete next
coding steps. Streams the answer when the provider supports it.

REPL commands:
    :module <id>   focus a specific module (e.g. ``:module 04``)
    :module        clear the focus (back to auto-selecting per question)
    :modules       list discovered modules
    :help          show commands
    :quit / :q     exit
"""

from __future__ import annotations

import sys

from llm_core import ChatMessage, ChatOptions

from .content import Module, discover_modules, get_module, select_relevant

SYSTEM_PROMPT = (
    "You are a patient, encouraging tutor for 'learn-ai', a personal, hands-on "
    "course on LLMs, embeddings, RAG, and agents (in both Python and TypeScript). "
    "You are given excerpts from the course's module README files as CONTEXT — "
    "treat them as the source of truth for what the learner is studying and "
    "ground your answer in them. Course conventions to keep in mind:\n"
    "- Exercise code uses a provider-agnostic client: get_provider()/ChatMessage "
    "from `llm_core` (Python) or getProvider() from `@learn-ai/llm-core` (TS). "
    "Never hardcode a provider.\n"
    "- Depth lanes per module: GREEN app / YELLOW balanced / RED from-scratch "
    "(RED tasks forbid the obvious library).\n"
    "- Run Python with `uv run python <path>.py`; run TS with `pnpm tsx <path>.ts`.\n\n"
    "Answer in two parts when relevant: (1) a short, clear explanation at the "
    "right level (be Socratic for pure concept questions — give intuition then a "
    "nudge, don't dump everything); (2) HOW TO PROCEED: concrete, ordered next "
    "coding steps, common pitfalls, and the command to run to verify. Do not "
    "write a full solution unless explicitly asked. Keep it concise and scannable. "
    "If the context doesn't cover the question, say so plainly instead of inventing."
)


def _context_block(modules: list[Module]) -> str:
    parts = []
    for m in modules:
        parts.append(
            f"### Module {m.module_id} — {m.title} (modules/{m.slug}/README.md)\n\n{m.excerpt}"
        )
    return "\n\n---\n\n".join(parts)


def _build_messages(question: str, modules: list[Module]) -> list[ChatMessage]:
    if modules:
        context = _context_block(modules)
        used = ", ".join(f"{m.module_id} ({m.title})" for m in modules)
        user = (
            f"CONTEXT (module README excerpts — grounding for your answer):\n\n{context}\n\n"
            f"---\n\n[Context drawn from modules: {used}]\n\n"
            f"LEARNER'S QUESTION:\n{question}"
        )
    else:
        user = (
            "No module README files were found in this repo, so answer from the "
            "general course description below.\n\n"
            f"LEARNER'S QUESTION:\n{question}"
        )
    return [ChatMessage("system", SYSTEM_PROMPT), ChatMessage("user", user)]


def _answer(provider, messages: list[ChatMessage]) -> None:
    """Stream the answer if the provider supports it; otherwise print at once.

    Falls back from chat_stream -> chat on any streaming error so a flaky local
    model never leaves the learner with nothing.
    """
    opts = ChatOptions(temperature=0.3)
    stream = getattr(provider, "chat_stream", None)
    if stream is not None:
        try:
            got_any = False
            for delta in stream(messages, opts):
                if delta:
                    got_any = True
                    sys.stdout.write(delta)
                    sys.stdout.flush()
            print()
            if got_any:
                return
        except KeyboardInterrupt:
            print("\n[interrupted]")
            return
        except Exception as exc:  # noqa: BLE001 — degrade gracefully for any provider
            print(f"\n[streaming failed: {exc}; retrying without streaming...]")
    # Non-streaming fallback.
    try:
        result = provider.chat(messages, opts)
        print(result.text)
    except KeyboardInterrupt:
        print("\n[interrupted]")
    except Exception as exc:  # noqa: BLE001
        print(f"[error talking to the model: {exc}]")


def run_repl(provider, focus: str | None = None) -> int:
    """Run the interactive Q&A loop. Returns a process exit code."""
    modules = discover_modules()
    if not modules:
        print(
            "Warning: no module README files found under modules/*/README.md. "
            "I'll answer from general course knowledge only.\n"
        )

    focused: Module | None = None
    if focus:
        focused = get_module(modules, focus)
        if focused is None:
            print(f"(No module matched '{focus}'; will auto-select per question.)\n")

    print("learn-ai tutor — ask me about the course. Type :help for commands, :quit to exit.")
    if focused:
        print(f"Focused on module {focused.module_id} — {focused.title}.")
    print()

    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye!")
            return 0

        if not line:
            continue

        if line in (":quit", ":q", ":exit"):
            print("bye!")
            return 0

        if line in (":help", ":h"):
            print(
                ":module <id>  focus a module (e.g. :module 04)\n"
                ":module       clear focus\n"
                ":modules      list modules\n"
                ":help         this help\n"
                ":quit         exit"
            )
            continue

        if line == ":modules":
            if not modules:
                print("(none found)")
            for m in modules:
                marker = " *" if focused and m is focused else ""
                print(f"  {m.module_id}  {m.title}{marker}")
            continue

        if line.startswith(":module"):
            arg = line[len(":module"):].strip()
            if not arg:
                focused = None
                print("Focus cleared — I'll auto-select the most relevant module per question.")
            else:
                m = get_module(modules, arg)
                if m is None:
                    print(f"No module matched '{arg}'. Try :modules to see the list.")
                else:
                    focused = m
                    print(f"Focused on module {m.module_id} — {m.title}.")
            continue

        if line.startswith(":"):
            print(f"Unknown command '{line}'. Type :help.")
            continue

        # A real question.
        if focused is not None:
            selected = [focused]
        else:
            selected = select_relevant(line, modules, provider=provider, top_k=2)
            if selected:
                names = ", ".join(f"{m.module_id} {m.title}" for m in selected)
                print(f"[grounding in: {names}]")

        messages = _build_messages(line, selected)
        print("tutor> ", end="", flush=True)
        _answer(provider, messages)
        print()
