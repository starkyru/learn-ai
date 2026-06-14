"""tutor — a standalone, provider-agnostic study CLI for the learn-ai course.

Two modes, both grounded in the course's module READMEs:

* ``ask``  — an interactive Q&A REPL that explains concepts and advises the next
  coding steps (light RAG over the module READMEs).
* ``exam`` — generates a quiz from a module README, asks it interactively, and
  grades your answers with an LLM-as-judge.

It talks to models through the shared ``llm_core`` client, so it runs against
whatever ``LLM_PROVIDER`` is configured — including a free, local Ollama model.

Usage::

    uv run python -m tutor ask
    uv run python -m tutor exam --module 04

This package is itself a small worked example of RAG + LLM-as-judge — the very
patterns you build in modules 05 and 07.
"""

from __future__ import annotations

from .content import (
    Module,
    discover_modules,
    get_module,
    select_relevant,
)

__all__ = [
    "Module",
    "discover_modules",
    "get_module",
    "select_relevant",
]

__version__ = "0.1.0"
