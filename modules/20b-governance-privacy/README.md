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

### Consent is one lawful basis, not a universal switch

Consent is only one of several bases that can make processing lawful — alongside
contract, legal obligation, legitimate interest, vital interest, and public
task. A processing activity should name the exact purpose it needs and which
basis authorises it. Two habits follow. **Purpose limitation:** consent for one
purpose never authorises a different one — there is no "blanket consent."
**Consent is revocable, other bases are not (by withdrawal):** when a subject
withdraws consent, consent-based processing for that purpose must stop, but the
same purpose may still be lawful under a _different_ basis (e.g. keeping order
records under contract or a tax obligation). Treating a consent withdrawal as if
it revoked every basis — or treating consent as always required — are both
common mistakes. The runnable exercise (`py/consent.py`, `ts/consent.ts`) models
this with an auditable decision record for every capture, withdrawal, and
authorisation. An authorisation decision is **point-in-time**: do not cache the
allow and act on it later, because the subject may withdraw consent in between
(a time-of-check/time-of-use gap). Re-check at the side-effect boundary — the
exercise provides `guarded_process` / `guardedProcess`, which re-checks
immediately before running the action. Which basis genuinely applies is product-
and jurisdiction-specific; this is not legal advice.

### Rights reach every store; erasure is not uniform

A subject-access export or an erasure request must reach **every** copy of the
data — the primary record, the embedding index, prompt/response caches,
feedback, human-review queues, and background-job records — not just the source
document. An **export** produces a manifest listing each copy and its storage
location. **Erasure is not one operation:** some stores hard-delete, while a
store under a documented **retention exception** (e.g. a legal-hold review
record) keeps a **tombstone** — the id and a reason, never the raw content — and
a reviewer sign-off is recorded where required. Separately, **retention expiry**
purges records (and eventually tombstones) once their period elapses. Every
export, delete, tombstone, and expiry appends an immutable audit record (actor,
time, scope, result, reviewer-where-required) using the same safe-logging
discipline — pseudonymous subjects, validated actor/reviewer, no raw content.
Erasure is **terminal and durable**: once a subject is erased the engine refuses
new writes for that id (an audit-sink outage cannot re-open collection). Clearing
that erased marker — `reactivate_subject` — is the **only** way to re-admit data,
so it is an **authorized, audited, erase-exclusive** transition: it demands a new
validated lawful basis plus a validated actor, writes a `reactivate` audit entry
before the marker is cleared, and is **rejected while any erasure is in progress**
(so a re-entrant audit sink can't quietly re-open collection mid-erase).
The runnable exercise (`py/rights.py`, `ts/rights.ts`) models all of this over
fake in-memory stores. Real retention exceptions are jurisdiction- and
contract-specific; this is not legal advice.

**Reviewer trust boundary (scope note):** the `reviewer` on an erase is a
_trusted, caller-supplied label_ — the fake-store engine **records** the reviewer
identity, it does **not** authenticate it (any in-process caller could pass
`legal-team`, the same in-process boundary already documented for `actor`). This
teaching engine deliberately does not add an auth layer. A production system
**must** bind the reviewer to an authenticated approval capability — a verified
reviewer principal or a signed approval carrying role and scope, derived from the
authorization layer — not a bare string.

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

Fill in the shipped [`templates/MODEL_AND_DATA_CARD.md`](templates/MODEL_AND_DATA_CARD.md)
for the capstone, and record allowed-use decisions in
[`templates/LICENCE_AND_USE_DECISIONS.md`](templates/LICENCE_AND_USE_DECISIONS.md).
Record the product purpose, model/version/provider, input and output data, training
or corpus licences, known limitations, prohibited uses, human escalation path, and
monitoring owner.

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

## Reusable governance templates

The tasks above don't start from a blank page — [`templates/`](templates/) ships
fill-in-the-blank artifacts you copy next to your app and keep under review:

- [`DATA_INVENTORY.md`](templates/DATA_INVENTORY.md) — every store (source,
  embeddings, traces, cache, feedback, backups) with owner, purpose, retention,
  deletion (Task 1).
- [`RETENTION_SCHEDULE.md`](templates/RETENTION_SCHEDULE.md) — retention period,
  lawful/contractual basis, deletion mechanism, and exception per store (Task 2).
- [`DPIA.md`](templates/DPIA.md) — a data-protection-impact-style risk review for a
  higher-risk feature (necessity, lawful basis, risks → mitigations, sign-off).
- [`MODEL_AND_DATA_CARD.md`](templates/MODEL_AND_DATA_CARD.md) — product purpose,
  model/provider, data, content types, limitations, prohibited uses, escalation
  (Task 3).
- [`LICENCE_AND_USE_DECISIONS.md`](templates/LICENCE_AND_USE_DECISIONS.md) — source
  licence, attribution, generated-content ownership, redistribution, provider terms.
- [`INCIDENT_AND_RECOURSE.md`](templates/INCIDENT_AND_RECOURSE.md) — incident
  severity/response/notification and how a user contests/appeals a decision (Task 4).
- [`ACCESSIBILITY_AND_FAIRNESS.md`](templates/ACCESSIBILITY_AND_FAIRNESS.md) —
  representative scenarios, accessibility checks, fairness/harm review, escalation
  and appeal (Task 4).

A curriculum test (`scripts/curriculum/test_governance_templates.py`) keeps the set
present and each template's required sections in place, so the governance artifacts
can't silently rot. Document ingestion (module 11), agent memory (module 06d), and
advanced / enterprise RAG (module 05b) link back here at the points where they store,
embed, cache, or send data to a provider.

## Important boundary

This lesson teaches engineering habits, not legal advice or certification. Legal,
privacy, security, accessibility, and domain experts must review a real system's
jurisdiction, contracts, and high-impact use cases.

The redaction exercise (`py/`, `ts/`) does **field-name-level classification and
data minimisation only**. It does **not** scan the _content_ of free-text
values: a secret typed into an allowed free-text field (for example an SSN
inside `support_topic` prose) is not caught, by design. Catching that requires
content-level DLP — a separate, larger, and itself-imperfect capability outside
this lesson's scope. Treat the redaction policy as a minimisation guardrail, not
a substitute for DLP.
