# Reusable governance templates

Fill-in-the-blank governance artifacts for a real (or capstone) AI product. Each
is a checklist-shaped Markdown file with `<…>` placeholders — copy it next to your
app, replace the placeholders, and keep it under review. Together they cover the
data lifecycle, decisions, and accountability that Module 20b's tasks ask for, and
that the Module 23 capstone's **M6 — Accountable release** milestone requires.

> **Not legal advice.** These teach engineering habits, not compliance
> certification. A real system needs legal, privacy, security, accessibility, and
> domain review of its jurisdiction, contracts, and high-impact uses.

| Template                                                         | Use it to…                                                                                           | Lesson tie-in |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ------------- |
| [`DATA_INVENTORY.md`](DATA_INVENTORY.md)                         | Map every store (source, embeddings, traces, cache, feedback, backups): owner, purpose, retention.   | Task 1        |
| [`RETENTION_SCHEDULE.md`](RETENTION_SCHEDULE.md)                 | Set a retention period, lawful/contractual basis, deletion mechanism, and exception per store.       | Task 2        |
| [`DPIA.md`](DPIA.md)                                             | Run a data-protection-impact-style risk review before shipping a higher-risk feature.                | Task 1–2      |
| [`MODEL_AND_DATA_CARD.md`](MODEL_AND_DATA_CARD.md)               | Record product purpose, model/provider, data, licences, limitations, prohibited uses, escalation.    | Task 3        |
| [`LICENCE_AND_USE_DECISIONS.md`](LICENCE_AND_USE_DECISIONS.md)   | Decide source licence, attribution, generated-content ownership, redistribution, and provider terms. | Task 3        |
| [`INCIDENT_AND_RECOURSE.md`](INCIDENT_AND_RECOURSE.md)           | Classify incidents, respond, notify, and give users a way to contest/appeal a decision.              | Task 4        |
| [`ACCESSIBILITY_AND_FAIRNESS.md`](ACCESSIBILITY_AND_FAIRNESS.md) | Define representative scenarios, accessibility checks, fairness/harm review, escalation & appeal.    | Task 4        |

**How to use.** At each point where data is **stored, embedded, cached, or sent to
a provider**, the relevant template has a row to fill — this is the same lifecycle
that document ingestion (module 11), agent memory (module 06d), and advanced /
enterprise RAG (module 05b) create data at, so those lessons link back here.
