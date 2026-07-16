# Data-protection impact / risk review (DPIA-style) — `<feature name>`

> Owner: `<name / team>` · Date: `<YYYY-MM-DD>` · Decision: `<proceed / proceed-with-mitigations / do-not-ship>`

A lightweight, engineering-oriented risk review to run **before** shipping a
higher-risk feature (new data class, new provider, automated decision with user
impact). Not a substitute for legal review — a prompt to think, decide, and record.

## Processing description

- What the feature does: `<one paragraph>`.
- Data classes processed: `<list>` (cross-reference the [data inventory](DATA_INVENTORY.md)).
- Providers / third parties involved: `<list>`.
- Automated decisions with user impact? `<yes/no; describe>`.

## Necessity & proportionality

- Why this data is **necessary** for the purpose: `<justification>`.
- Less-intrusive alternative considered: `<what / why rejected>`.
- Minimisation applied: `<fields dropped / redacted / aggregated>`.

## Lawful basis

- Basis for processing: `<consent / contract / legitimate interest / … >` (consent
  is one basis, not a universal switch — see the consent exercise).
- If consent: how it is captured, and how withdrawal is honoured: `<mechanism>`.

## Risks to individuals

| Risk                             | Likelihood | Impact    | Mitigation                                 | Residual risk |
| -------------------------------- | ---------- | --------- | ------------------------------------------ | ------------- |
| `<re-identification of subject>` | `<L/M/H>`  | `<L/M/H>` | `<redaction / access control / retention>` | `<L/M/H>`     |
| `<sensitive data to provider>`   | `<L/M/H>`  | `<L/M/H>` | `<redact before call / provider DPA>`      | `<L/M/H>`     |
| `<unfair / harmful output>`      | `<L/M/H>`  | `<L/M/H>` | `<eval case; human review; refusal>`       | `<L/M/H>`     |
| `<over-retention>`               | `<L/M/H>`  | `<L/M/H>` | `<retention schedule + deletion test>`     | `<L/M/H>`     |

## Sign-off

- Reviewer(s): `<names / roles>` · Consultation (legal/privacy/security): `<who, when>`.
- Actions before ship: `<tracked items with owners>`.
