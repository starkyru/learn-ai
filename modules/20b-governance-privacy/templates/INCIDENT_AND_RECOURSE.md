# Incident response & user recourse — `<product name>`

> Owner: `<name / team>` · On-call: `<rotation>` · Last reviewed: `<YYYY-MM-DD>`

Two accountabilities in one place: how the team **responds** to a governance/privacy
incident, and how a **user contests or appeals** a consequential automated decision.
For the operational/reliability runbook, see the 07b
[`RUNBOOK.md`](../../07b-delivery-operations/RUNBOOK.md).

## Incident severity

| Severity | Definition                                                        | Response time |
| -------- | ----------------------------------------------------------------- | ------------- |
| SEV1     | Confirmed exposure of restricted data, or user harm at scale      | `<immediate>` |
| SEV2     | Suspected exposure / rights failure / material fairness disparity | `<hours>`     |
| SEV3     | Contained policy violation, no confirmed exposure                 | `<days>`      |

## Response steps

1. **Contain** — stop the offending flow (disable the feature / rotate a leaked
   key / halt an export).
2. **Assess** scope via the [data inventory](DATA_INVENTORY.md).
3. **Notify** — see below.
4. **Remediate** — delete/tombstone affected copies, fix the cause.
5. **Review** — blameless write-up (07b RUNBOOK template).

## Notification

- Who is notified, by when: affected users `<when/how>`, internal owners `<who>`,
  regulator/partner if required `<criteria>`.

## User recourse & appeal

- How a user learns a decision was automated: `<disclosure>`.
- How a user **contests / appeals** a consequential decision (wrong answer,
  refusal, account action): `<channel>` → routed to `<human owner>` within
  `<SLA>`. The appeal outcome and rationale are recorded.
- Link to the escalation path in
  [`ACCESSIBILITY_AND_FAIRNESS.md`](ACCESSIBILITY_AND_FAIRNESS.md) and the model
  card's human-escalation path.

## Post-incident review

- Every SEV1/SEV2 gets a blameless review with root cause and tracked action items
  (owners + due dates).
