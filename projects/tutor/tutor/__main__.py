"""CLI entrypoint for the learn-ai tutor.

Run it with:
    uv run python -m tutor ask
    uv run python -m tutor exam --module 04

It uses the course's provider-agnostic client (`llm_core`), so it runs against
whatever LLM_PROVIDER is configured — for free on a local Ollama model by default.
"""

from __future__ import annotations

import argparse
import sys

from .content import discover_modules


def _make_provider():
    """Construct the configured provider, with a friendly error if it can't."""
    try:
        from llm_core import get_provider
    except Exception as exc:  # noqa: BLE001
        print(f"Could not import llm_core: {exc}", file=sys.stderr)
        print("Run from the repo (so the workspace install is active): "
              "`uv run python -m tutor ...`", file=sys.stderr)
        raise SystemExit(2)
    try:
        return get_provider()
    except Exception as exc:  # noqa: BLE001
        print(f"Could not initialize the LLM provider: {exc}", file=sys.stderr)
        print(
            "Check your .env (LLM_PROVIDER and the matching key). The zero-cost "
            "path is Ollama: install it, `ollama pull llama3.2`, leave "
            "LLM_PROVIDER=ollama.",
            file=sys.stderr,
        )
        raise SystemExit(2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tutor",
        description=(
            "Interactive study tool for the learn-ai course — a Q&A tutor and an "
            "exam grader, grounded in the module READMEs. Provider-agnostic via "
            "llm_core; runs free on a local Ollama model by default."
        ),
        epilog=(
            "examples:\n"
            "  uv run python -m tutor ask\n"
            "  uv run python -m tutor ask --module 05\n"
            "  uv run python -m tutor exam --module 04\n"
            "  uv run python -m tutor exam --module rag --num 3 --difficulty hard\n"
            "  uv run python -m tutor modules\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    p_ask = sub.add_parser(
        "ask",
        help="start an interactive Q&A REPL about the course",
        description="Open a REPL that answers questions about the course and "
        "advises next coding steps, grounded in the most relevant module README(s).",
    )
    p_ask.add_argument(
        "--module", "-m", default=None,
        help="focus a module from the start (e.g. 04 or rag); otherwise auto-selected per question",
    )

    p_exam = sub.add_parser(
        "exam",
        help="take a graded quiz on a module",
        description="Generate N questions from a module's README, ask them one at "
        "a time, then grade your answers with an LLM-as-judge and print a report.",
    )
    p_exam.add_argument(
        "--module", "-m", required=True,
        help="module to quiz on: id (04), slug (05-rag), or topic (embeddings)",
    )
    p_exam.add_argument(
        "--num", "-n", type=int, default=5,
        help="number of questions (default: 5)",
    )
    p_exam.add_argument(
        "--difficulty", "-d", default="medium",
        choices=["easy", "medium", "hard"],
        help="question difficulty (default: medium)",
    )

    sub.add_parser("modules", help="list the modules discovered in this repo")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "modules":
        modules = discover_modules()
        if not modules:
            print("No module READMEs found under modules/*/README.md.")
            return 1
        print("Modules in this repo:")
        for m in modules:
            print(f"  {m.module_id}  {m.title}")
        return 0

    if args.command == "ask":
        from .qa import run_repl

        provider = _make_provider()
        return run_repl(provider, focus=args.module)

    if args.command == "exam":
        from .exam import run_exam

        if args.num < 1:
            print("--num must be >= 1", file=sys.stderr)
            return 2
        provider = _make_provider()
        return run_exam(
            provider, module_ref=args.module, num=args.num, difficulty=args.difficulty
        )

    parser.print_help()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nbye!")
        raise SystemExit(130)
