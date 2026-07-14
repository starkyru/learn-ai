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

## Release-evidence checklist

- [ ] Development and held-out benchmarks are separate and versioned.
- [ ] Retriever, answer, and agent metrics are reported separately.
- [ ] Gold evidence, rubric, and test-case provenance are inspectable.
- [ ] Variant comparisons include uncertainty and a practical threshold.
- [ ] Human/LLM judge agreement and disagreements are tracked.
- [ ] Side-effecting agent paths have deterministic policy and trajectory tests.
