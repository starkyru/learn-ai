# Model & data card — `<product name>`

> Owner (monitoring): `<name / team>` · Review date: `<YYYY-MM-DD>` · Next review: `<YYYY-MM-DD>`

The card the Module 20b **Task 3** and the capstone **M6** milestone ask for.
Record what the product is, what it runs on, what data it uses, and where its edges
are — so a reviewer can judge allowed use without reading the code.

## Purpose

- Product purpose: `<what problem, for whom>`.
- Out of scope / not designed for: `<list>`.

## Model

| Field    | Value                                       |
| -------- | ------------------------------------------- |
| Model    | `<name>`                                    |
| Version  | `<version / snapshot>`                      |
| Provider | `<vendor>` (via `llm_core` / `getProvider`) |
| Fallback | `<alt model/provider, if any>`              |

## Data

- **Input data:** `<what the user/app sends>`.
- **Output data:** `<what is returned / stored>`.
- **Corpus / training or retrieval sources:** `<list>` — each with an allowed-use
  decision (see [`LICENCE_AND_USE_DECISIONS.md`](LICENCE_AND_USE_DECISIONS.md)) or
  marked **excluded**.

## Content types

Distinguish, in the UI and in this card:

- **Factual claims** grounded in retrieved sources (`<cited how>`).
- **Generated content** produced by the model (`<labelled how>`).
- **User-provided content** (`<handled how>`).

## Known limitations

- `<failure modes, hallucination risks, domains it is weak in>`.

## Prohibited uses

- `<uses the product must refuse or is not authorised for>`.

## Human escalation path

- How a user or operator reaches a human for a consequential decision:
  `<path>` (see [`INCIDENT_AND_RECOURSE.md`](INCIDENT_AND_RECOURSE.md)).

## Monitoring

- Owner: `<name>` · Signals watched: `<metrics / evals>` · Review cadence: `<cadence>`.
