"""Exam mode: LLM-generated quiz on a module, graded by an LLM-as-judge.

Flow:
1. Resolve the requested module and load its README (the grounding).
2. Ask the LLM to generate N questions as a JSON list (parsed robustly).
3. Ask each question interactively and collect the learner's answer.
4. Grade ALL answers in one LLM-as-judge call returning a score (0-1) +
   feedback per question (also parsed robustly).
5. Print a final report: total score and study tips pointing back at the README.

You'll recognize the LLM-as-judge pattern from module 07 (eval & production).
Prompts are kept explicit and simple so small local models can follow them.
"""

from __future__ import annotations

import json
import re

from llm_core import ChatMessage, ChatOptions

from .content import Module, discover_modules, get_module

DIFFICULTY_HINTS = {
    "easy": "Keep questions introductory: definitions and recall of the README's core ideas.",
    "medium": "Mix recall with application: 'what would this code do' and small coding prompts.",
    "hard": "Include deeper, from-scratch (RED-lane) questions and subtle 'why' / debugging items.",
}


# --------------------------------------------------------------------------- #
# Robust JSON extraction (small models love to wrap JSON in prose / fences)
# --------------------------------------------------------------------------- #

def _extract_json(text: str):
    """Best-effort: pull the first JSON array/object out of a model response."""
    if not text:
        raise ValueError("empty response")
    # Strip ```json ... ``` fences if present.
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    candidates = []
    if fenced:
        candidates.append(fenced.group(1).strip())
    candidates.append(text.strip())
    # Also try the substring from the first bracket to the matching last one.
    for opener, closer in (("[", "]"), ("{", "}")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            candidates.append(text[start : end + 1])

    for cand in candidates:
        try:
            return json.loads(cand)
        except (json.JSONDecodeError, ValueError):
            continue
    raise ValueError("could not parse JSON from model response")


# --------------------------------------------------------------------------- #
# Question generation
# --------------------------------------------------------------------------- #

def generate_questions(provider, module: Module, num: int, difficulty: str) -> list[str]:
    diff_hint = DIFFICULTY_HINTS.get(difficulty, DIFFICULTY_HINTS["medium"])
    system = (
        "You write short exam questions for a hands-on AI course. You are given a "
        "module's README. Generate questions grounded ONLY in what that README "
        "teaches. Mix conceptual questions, 'what would this code do' questions, "
        "and small coding prompts. " + diff_hint
    )
    user = (
        f"MODULE: {module.title} (modules/{module.slug}/README.md)\n\n"
        f"README:\n{module.excerpt}\n\n"
        f"Write exactly {num} questions grounded in this README. "
        'Return ONLY a JSON array of strings, e.g. ["Q1 text", "Q2 text"]. '
        "No commentary, no numbering, no markdown fences."
    )
    result = provider.chat(
        [ChatMessage("system", system), ChatMessage("user", user)],
        ChatOptions(temperature=0.4),
    )
    data = _extract_json(result.text)
    if isinstance(data, dict):
        # Tolerate {"questions": [...]}.
        for key in ("questions", "items", "data"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        raise ValueError("expected a JSON array of questions")
    questions = [str(q).strip() for q in data if str(q).strip()]
    if not questions:
        raise ValueError("model returned no questions")
    return questions[:num]


# --------------------------------------------------------------------------- #
# Grading (LLM-as-judge)
# --------------------------------------------------------------------------- #

def grade_answers(
    provider,
    module: Module,
    qa_pairs: list[tuple[str, str]],
) -> list[dict]:
    """Grade all Q/A pairs at once. Returns a list of
    {"score": float 0..1, "feedback": str} dicts, one per question.
    """
    system = (
        "You are a fair, encouraging grader for an AI course. Grade each answer "
        "against the module README (the source of truth). Give partial credit. "
        "Be brief and concrete; cite the right idea when the answer is wrong."
    )
    block = "\n\n".join(
        f"Q{i + 1}: {q}\nLEARNER ANSWER: {a if a.strip() else '(no answer given)'}"
        for i, (q, a) in enumerate(qa_pairs)
    )
    user = (
        f"MODULE README (grounding):\n{module.excerpt}\n\n"
        f"Grade these {len(qa_pairs)} answers:\n\n{block}\n\n"
        "Return ONLY a JSON array with one object per question, in order, each: "
        '{"score": <number 0.0-1.0>, "feedback": "<1-2 sentence feedback>"}. '
        "No prose, no markdown fences."
    )
    result = provider.chat(
        [ChatMessage("system", system), ChatMessage("user", user)],
        ChatOptions(temperature=0.0),
    )
    data = _extract_json(result.text)
    if isinstance(data, dict):
        for key in ("grades", "results", "data"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        raise ValueError("expected a JSON array of grades")

    grades: list[dict] = []
    for i in range(len(qa_pairs)):
        if i < len(data) and isinstance(data[i], dict):
            raw = data[i]
            try:
                score = float(raw.get("score", 0.0))
            except (TypeError, ValueError):
                score = 0.0
            score = max(0.0, min(1.0, score))
            feedback = str(raw.get("feedback", "")).strip() or "(no feedback)"
        else:
            score, feedback = 0.0, "(grader returned no entry for this question)"
        grades.append({"score": score, "feedback": feedback})
    return grades


# --------------------------------------------------------------------------- #
# The interactive exam
# --------------------------------------------------------------------------- #

def run_exam(provider, module_ref: str, num: int = 5, difficulty: str = "medium") -> int:
    modules = discover_modules()
    if not modules:
        print("No module READMEs found under modules/*/README.md — nothing to quiz on.")
        return 1

    module = get_module(modules, module_ref)
    if module is None:
        available = ", ".join(f"{m.module_id} ({m.title})" for m in modules)
        print(f"Couldn't find module '{module_ref}'.")
        print(f"Available modules: {available}")
        return 1

    print(f"Exam — Module {module.module_id}: {module.title}")
    print(f"(difficulty: {difficulty}, questions: {num})\n")
    print("Generating questions from the module README...\n")

    try:
        questions = generate_questions(provider, module, num, difficulty)
    except KeyboardInterrupt:
        print("\n[cancelled]")
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"Could not generate questions: {exc}")
        print("Tip: a small local model may struggle with JSON — try again, lower --num, "
              "or set a stronger LLM_PROVIDER.")
        return 1

    qa_pairs: list[tuple[str, str]] = []
    total = len(questions)
    try:
        for i, q in enumerate(questions, 1):
            print(f"Question {i} of {total}:")
            print(f"  {q}\n")
            answer = input("your answer> ").strip()
            qa_pairs.append((q, answer))
            print()
    except (EOFError, KeyboardInterrupt):
        print("\n[exam interrupted — grading what you answered so far]\n")
        # Pad remaining as unanswered so indices line up.
        for q in questions[len(qa_pairs):]:
            qa_pairs.append((q, ""))

    print("Grading your answers...\n")
    try:
        grades = grade_answers(provider, module, qa_pairs)
    except KeyboardInterrupt:
        print("\n[cancelled]")
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"Grading failed: {exc}")
        print("Your answers were recorded; try re-running the exam.")
        return 1

    _print_report(module, qa_pairs, grades)
    return 0


def _print_report(module: Module, qa_pairs, grades) -> None:
    print("=" * 60)
    print(f"RESULTS — Module {module.module_id}: {module.title}")
    print("=" * 60)
    earned = sum(g["score"] for g in grades)
    total = len(qa_pairs)
    for i, ((q, a), g) in enumerate(zip(qa_pairs, grades), 1):
        pct = int(round(g["score"] * 100))
        print(f"\nQ{i} [{pct:>3}%] {q}")
        shown = a.strip() if a.strip() else "(no answer)"
        print(f"   your answer: {shown}")
        print(f"   feedback:    {g['feedback']}")

    print("\n" + "-" * 60)
    print(f"SCORE: {earned:.1f} / {total}  ({int(round(earned / total * 100)) if total else 0}%)")

    # Study tips: point back at the module README, focused on weak spots.
    weak = [i + 1 for i, g in enumerate(grades) if g["score"] < 0.7]
    print("\nStudy tips:")
    if not weak:
        print(f"  Strong run — revisit modules/{module.slug}/README.md to lock in the details,")
        print("  then move on. Try the harder depth lane (YELLOW/RED) if you stayed on GREEN.")
    else:
        qlist = ", ".join(f"Q{n}" for n in weak)
        print(f"  Re-read modules/{module.slug}/README.md, focusing on the topics behind {qlist}.")
        print("  Then re-run the relevant exercise to verify:")
        print(f"    uv run python modules/{module.slug}/py/<exercise>.py")
        print(f"    pnpm tsx modules/{module.slug}/ts/<exercise>.ts")
    print()
