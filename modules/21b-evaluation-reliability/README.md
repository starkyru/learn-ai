# Module 21b — Evaluation Science & Agent Reliability

> **Depth tags** 🟢 app-level · 🟡 build-one-piece-by-hand

Module 21 gives you an LLM (Large Language Model) eval lifecycle. This deep dive makes its measurements
credible: a retrieval benchmark with gold evidence, uncertainty around model
comparisons, calibrated human/LLM judging, and trajectory tests for agents.

> **Prerequisite:** Modules 05, 06, and 21. Do this before treating a capstone
> score as evidence that a system is ready for broader use.

## What you will learn

- Separate retriever, generator, and end-to-end metrics so a good answer cannot
  hide a broken retrieval layer.
- Build a held-out, versioned benchmark with gold passages and clear rubrics.
- Report uncertainty and paired comparisons rather than declaring a winner from
  a few noisy cases.
- Measure grader agreement and route ambiguous cases to a human.
- Test an agent's tool trajectory, approval behavior, side effects, and failure
  recovery deterministically.

## Concepts

### Measure the layer you intend to improve

For retrieval, label the passages that contain the evidence and calculate
Recall@k, MRR, and NDCG before generation. For answers, measure groundedness,
claim-level citation validity, completeness, and task success. For agents,
measure whether the sequence of tool calls was authorised and safe—not only the
last sentence it produced.

### A benchmark needs a protocol

Keep development cases separate from held-out release cases. Define the unit of
evaluation, inclusion/exclusion rules, label rubric, annotator instructions,
and model/prompt/index versions. Five hand-written examples are useful during
development; they are not enough evidence for a release decision.

### LLM judges are noisy instruments

Blind the judge to the system variant when possible, use a rubric with anchored
scores, inspect disagreements, and compare judge labels to a human sample.
Score distributions need uncertainty: use a paired bootstrap interval or a
paired permutation/sign test when comparing two systems over the same cases.

### An agent is a stateful system

Write deterministic fake tools and clocks for tests. Assert tool selection,
arguments, state transitions, approval gates, retries, idempotency, and bounded
termination. A final answer that happens to be correct is insufficient if the
agent leaked data or would have sent an unapproved email.

## Tasks

### Task 1 — Gold-evidence retrieval benchmark 🟡

Create at least 30 development cases and 20 held-out cases for a small corpus.
Each case records a query, one or more relevant chunk ids, relevance grade, and
why the evidence is sufficient. Implement Recall@k, Mean Reciprocal Rank (MRR),
and Normalized Discounted Cumulative Gain (NDCG), then compare
dense, hybrid, and reranked retrieval using identical cases.

**Done when**

- Retrieval metrics are written before the generator runs.
- Each result records corpus/index/chunker/embedder versions and `k`.
- A failure report lists the query and missing or mis-ranked gold evidence.

> **Runnable fixtures (this repo).** Task 1 ships as a deterministic, offline
> benchmark — no provider, no network, so it can gate a release in CI:
>
> ```bash
> uv run python modules/21b-evaluation-reliability/py/benchmark.py --split both
> pnpm tsx modules/21b-evaluation-reliability/ts/run.ts --split both
> ```
>
> The versioned corpus, development and held-out cases, rubric, and manifest
> live in `modules/21b-evaluation-reliability/fixtures/`. `dense` (a seedless
> character-n-gram hashing stand-in for an embedder), `bm25`, `hybrid` (RRF),
> and `reranked` are compared with from-scratch `Recall@k` / `MRR` / `NDCG@k`;
> the runner prints the comparison table plus a per-query failure report and
> writes a deterministic JSON report. The Python and TypeScript ports produce
> identical rankings. Verify with `uv run pytest modules/21b-evaluation-reliability`
> and `pnpm test`.

### Task 2 — Claim-level answer and citation evaluation 🟡

Break each answer into atomic claims. Grade whether every material claim is
supported by a cited passage, whether citations point to the right passage, and
whether the answer satisfies the task. Use deterministic checks wherever
possible and an LLM rubric only for the remaining judgement.

**Done when**

- Unsupported claims and invalid citations are reported separately.
- The rubric, judge model version, and prompt are versioned with the result.
- At least 10% of cases receive blind human review.

### Task 3 — Uncertainty, agreement, and release decisions 🟢

Run two variants against the same held-out cases. Report mean difference,
paired bootstrap confidence interval, win/tie/loss count, and a practical
minimum improvement threshold. Have two judges or a judge plus a human label a
sample; record agreement and queue disagreements.

**Done when**

- The release report can say “inconclusive” when the interval crosses the
  practical threshold.
- A model is not promoted merely because it won on a handful of cases.
- Judge disagreement becomes an annotation task and potential new eval case.

> **Runnable answer eval, judge reliability & release gate (Tasks 2–3).**
> These ship as deterministic, offline modules that reuse the Task 1 fixtures:
>
> - `answer_eval` / `answer-eval.ts` — decompose answers into atomic claims and
>   check support + citation validity deterministically; the residual
>   task-success judgement uses an LLM rubric via the shared `llm_core`
>   client, faked by a canned, keyed-by-input `FakeJudge` (no network). Reports
>   unsupported claims and invalid citations separately and versions the rubric +
>   judge model/prompt. Fixtures: `answers.json`, `answer_rubric.json`,
>   `judge.json`, `human_labels.json`.
> - `agreement` — Cohen's kappa (from scratch) + percent agreement between the
>   judge and a blind human sample, with a disagreement queue.
> - `uncertainty` — paired bootstrap CI (from scratch, seeded/deterministic),
>   win/tie/loss, and a verdict that is `inconclusive` when the interval crosses
>   the practical threshold.
> - The **enforceable release gate** exits nonzero on a policy violation (a
>   held-out floor breached, an improvement required but inconclusive, or golden
>   drift) and 0 otherwise — the CI hook for this module:
>
> ```bash
> uv run python modules/21b-evaluation-reliability/py/gate.py   # exit 0/nonzero
> pnpm tsx modules/21b-evaluation-reliability/ts/gate-cli.ts
> ```
>
> The Python and TypeScript answer/release reports are byte-identical
> (`fixtures/golden/*.golden`), and `fixtures/release_policy.json` is the policy.

### Task 4 — Agent trajectory and safety suite 🔴

Build deterministic fake tools for a read-only lookup, a slow/failing tool, and
a side-effecting action. For each test define allowed tools, expected arguments,
approval requirement, maximum steps, expected final state, and idempotency key.

**Done when**

- The suite catches an unauthorised tool call even if the final text is correct.
- Timeout, retry, duplicate request, malformed tool arguments, and denial paths
  have deterministic tests.
- Results report task success, policy compliance, tool-argument accuracy, step
  count, latency, and cost separately.

> **Runnable agent-safety suite & gate (Task 4).** Deterministic and offline:
>
> - `agent_tools` / `agent-tools.ts` — a read-only lookup, a transient-failure
>   tool, a timeout tool, and an idempotent side-effecting `send_email`, driven by
>   an injectable integer clock. No LLM, no network.
> - `agent_eval` / `agent-eval.ts` — replays each canned trajectory
>   (`fixtures/agent_scenarios.json`) against a per-scenario policy (allowed
>   tools, expected args, approval, max steps, expected final state, idempotency)
>   and reports task success, policy compliance, tool-argument accuracy, step
>   count, latency, and cost **separately**. The load-bearing rule: an
>   unauthorised side effect fails **even if the final answer is correct**.
> - The **agent-safety release gate** exits nonzero on any policy-violating
>   trajectory (unauthorised tool, side effect without approval, exceeded steps,
>   non-idempotent duplicate) or on agent-report drift, and 0 on a clean one:
>
> ```bash
> uv run python modules/21b-evaluation-reliability/py/agent_gate.py
> pnpm tsx modules/21b-evaluation-reliability/ts/agent-gate-cli.ts
> ```
>
> The Python and TypeScript agent reports are byte-identical
> (`fixtures/golden/agent_report.golden`); `fixtures/agent_gate_policy.json` is
> the policy.

## Release-evidence checklist

- [ ] Development and held-out benchmarks are separate and versioned.
- [ ] Retriever, answer, and agent metrics are reported separately.
- [ ] Gold evidence, rubric, and test-case provenance are inspectable.
- [ ] Variant comparisons include uncertainty and a practical threshold.
- [ ] Human/LLM judge agreement and disagreements are tracked.
- [ ] Side-effecting agent paths have deterministic policy and trajectory tests.

## CI release gate (entrypoint contract)

The release gate is exposed as an **offline, deterministic CLI** so CI can run it
with no provider key:

- Python: `py/gate.py` — the release-gate entrypoint the active workflow runs.
- TypeScript: `ts/gate-cli.ts` — the equivalent CLI for the TS path.

The repository's active workflow
([`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)) has a guarded
`eval-gate` job that runs `uv run python modules/21b-evaluation-reliability/py/gate.py`
the moment this module lands on the branch (until then the job's detect step
reports "not present" and skips, so it never fails on a missing path). Keep
`py/gate.py` as that entrypoint — renaming it silently disables the gate.

**Done when** the gate exits non-zero on a failing release and zero on a passing
one, runs fully offline (no network/provider), and is wired into the active CI
workflow above.
