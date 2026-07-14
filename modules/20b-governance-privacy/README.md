# Module 20b — AI Governance, Privacy & Responsible Product Practice

> **Depth tags** 🟢 app-level · 🟡 build-one-piece-by-hand

Module 20 asks “can an attacker make this AI (Artificial Intelligence) system do the wrong thing?” This
module asks the adjacent product questions: “should we collect this data?”,
“who may use it?”, “can we explain and delete it?”, and “what happens when the
system is wrong?” Security controls are necessary; they are not a substitute for
data governance and accountable product decisions.

> **Prerequisite:** Modules 11 and 20. Module 21 helps for monitoring and
> evidence. Complete this before a capstone processes data belonging to anyone
> other than you.

## What you will learn

- Map data from collection through prompts, embeddings, logs, caches, vendors,
  and deletion.
- Minimise collection, set retention rules, and handle access/deletion requests.
- Evaluate third-party model, dataset, and generated-content licensing risks.
- Design accessible, inclusive user experiences and test for harmful disparate
  outcomes in the product context.
- Create an accountable release record: purpose, owner, limits, human escalation,
  and incident response.

## Concepts

### The data lifecycle is longer than the request

A user's text can appear in an application database, an embedding index, a
prompt cache, a tracing vendor, a human-review queue, a provider request, and a
backup. “We do not train on it” does not mean “we do not retain it.” Make a data
map before collecting data, and give every store a purpose, access rule, and
retention period.

### Minimise, classify, and separate

Collect only fields required for the feature. Classify them (public, internal,
confidential, restricted), separate tenants, encrypt data at rest and in transit,
and keep raw content out of logs by default. Pseudonymisation reduces exposure;
it is not automatically anonymisation.

### Governance turns values into repeatable decisions

Policies become useful when a team can answer: who owns this system, what uses
are prohibited, which model/data licences apply, what evidence was reviewed,
when a human must decide, and how a user appeals or reports harm. The answer is
often product- and jurisdiction-specific; involve qualified legal/privacy teams
for real regulatory advice.

### Responsible UX includes access and recourse

Users need understandable disclosure, accessible controls, a way to correct or
challenge an outcome, and a clear boundary between assistance and automated
decision-making. Never use a course exercise as a basis for high-impact decisions
about employment, credit, housing, education, healthcare, or legal outcomes.

## Tasks

### Task 1 — Data map and minimisation review 🟢

Pick one existing course app. Draw its data flow from collection through API,
prompt, retrieval, tools, logs, cache, vendor, and backups. For each hop record
data class, purpose, owner, access control, retention, and deletion mechanism.
Remove or redact one field that is not necessary.

**Done when**

- The map includes embeddings, traces, feedback, and derived artifacts—not only
  the source document.
- Every store has an owner, purpose, and retention/deletion decision.
- A test fixture demonstrates that a redacted field cannot reach the provider or
  an application log.

### Task 2 — Rights, retention, and auditability 🟡

Implement a small export/delete workflow for a user or document. It must locate
primary content, vectors, caches, feedback, and review records by stable id;
record the request and outcome in an audit log. Use fake data only.

**Done when**

- An export lists every known copy and its storage location.
- A deletion request removes or tombstones each copy according to a documented
  retention exception.
- The audit record has actor, time, scope, result, and reviewer where required.

### Task 3 — Model, data, and content review 🟢

Create a `MODEL_AND_DATA_CARD.md` for the capstone. Record the product purpose,
model/version/provider, input and output data, training or corpus licences,
known limitations, prohibited uses, human escalation path, and monitoring owner.

**Done when**

- Every corpus source and model has a documented allowed-use decision or is
  excluded.
- The card distinguishes factual claims, generated content, and user-provided
  content.
- The card has a review date and named owner.

### Task 4 — Inclusive and accountable experience 🟡

Define representative user scenarios, including assistive-technology and
language-clarity needs. Test the same task across scenarios, look for material
differences in error, refusal, latency, or helpfulness, and add an escalation or
appeal path for consequential mistakes.

**Done when**

- The product has clear disclosure of AI involvement, limitations, and source
  provenance where appropriate.
- Keyboard-only use and meaningful error/failure states are tested.
- A discovered disparity or accessibility issue becomes a tracked product/eval
  case, not an undocumented observation.

## Governance release checklist

- [ ] Data map, owners, classification, and retention rules are current.
- [ ] Collection is minimised; secrets and restricted data are redacted before
      logs, evals, and third-party calls where required.
- [ ] Export/delete and audit paths are tested with synthetic data.
- [ ] Model/data licences and intended/prohibited uses are recorded.
- [ ] Human escalation, incident ownership, and user recourse are documented.
- [ ] Accessibility and representative-scenario findings feed the eval backlog.

## Important boundary

This lesson teaches engineering habits, not legal advice or certification. Legal,
privacy, security, accessibility, and domain experts must review a real system's
jurisdiction, contracts, and high-impact use cases.
