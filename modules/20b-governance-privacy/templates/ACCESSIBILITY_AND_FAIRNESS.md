# Accessibility & fairness review — `<product name>`

> Owner: `<name / team>` · Last reviewed: `<YYYY-MM-DD>`

Responsible UX includes **access** (people using assistive tech or needing clear
language) and **fairness** (the product works comparably across representative
users). A discovered disparity or accessibility issue becomes a **tracked eval /
product case**, never an undocumented observation.

## Representative user scenarios

Define scenarios that stress real differences — do not test only the happy path:

| Scenario                             | Need it represents     | Task tested  |
| ------------------------------------ | ---------------------- | ------------ |
| `<screen-reader user>`               | assistive technology   | `<the task>` |
| `<keyboard-only user>`               | no-pointer access      | `<the task>` |
| `<non-native / low-literacy reader>` | language clarity       | `<the task>` |
| `<name/dialect/locale variation>`    | fairness across groups | `<the task>` |

## Accessibility checks

- [ ] Keyboard-only completion of the primary task.
- [ ] Meaningful error / failure states (not a spinner or a raw stack).
- [ ] Clear **disclosure of AI involvement**, limitations, and source provenance.
- [ ] Assistive-tech labels on interactive elements.

## Fairness / harm review

Ask, and record answers, for each representative scenario:

- Are there **material differences** in error rate, refusal, latency, or
  helpfulness across scenarios? `<measured how / result>`.
- What is the **worst-case harm** if the product is wrong for this user? `<…>`.
- Does any output stereotype, demean, or exclude a group? `<review result>`.

## Escalation & appeal

- Consequential mistake → escalation path to a human: `<path / SLA>` (mirrors the
  model card and [`INCIDENT_AND_RECOURSE.md`](INCIDENT_AND_RECOURSE.md)).
- How a user appeals an accessibility/fairness failure: `<channel>`.

## Tracking

- Each disparity or accessibility gap becomes a tracked case:
  `<issue/eval id>` — owner `<name>` — status `<open/closed>`. It feeds the eval
  backlog (module 21b), not a one-off note.
