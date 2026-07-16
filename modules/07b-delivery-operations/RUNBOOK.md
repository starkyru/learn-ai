# RUNBOOK — Module 07b reference AI service

Operational runbook for the reference service (`py/` FastAPI, `ts/` Fastify). It
is written so **another person can follow it without improvising**: owners,
alerts, canary thresholds, rollback triggers, and the exact recovery commands.
The staged-rollout wiring lives in [`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml);
this document is its source of truth for thresholds and commands.

> This is a teaching artifact — fill the `<…>` placeholders (owners, URLs,
> dashboard links) with your deployment's real values before you rely on it.

## Owners & on-call

| Role                   | Who             | Contact                    |
| ---------------------- | --------------- | -------------------------- |
| Service owner          | `<name / team>` | `<slack / email>`          |
| On-call (primary)      | `<rotation>`    | `<pager>`                  |
| Escalation (secondary) | `<name>`        | `<pager>`                  |
| Data / privacy contact | `<name>`        | `<email>` (see module 20b) |

- Working hours + escalation policy: `<link>`.
- Change freeze windows: `<when releases are NOT allowed>`.

## Dashboards & alerts

Wire these before first production traffic; the alert **is** the rollback trigger.

| Signal                   | Source / dashboard                | Alert fires when                              |
| ------------------------ | --------------------------------- | --------------------------------------------- |
| Availability (`/readyz`) | `<uptime dashboard link>`         | `/readyz` != 200 for 2 consecutive probes     |
| Error rate (5xx / total) | `<metrics dashboard>`             | > 1% over a 5-minute window                   |
| p95 request latency      | `<metrics dashboard>`             | > 1500 ms over a 5-minute window              |
| `provider_call_failed`   | log-based metric on the JSON logs | rate climbs (circuit likely open)             |
| 429 rate (rate-limited)  | `<metrics dashboard>`             | sustained > 5% (tune `RATE_LIMIT_PER_MINUTE`) |

The service emits structured JSON logs with a correlation id (`X-Request-Id`) on
every line; join API → queue → provider by that id. Logs carry the failure
**mode** (`provider_call_failed` with a `reason`), never a raw provider detail or
secret.

## Service-level objectives (SLOs)

- Availability: `<99.9%>` monthly (readiness-based).
- p95 latency: `< 1500 ms` for `/ask` at the configured `REQUEST_TIMEOUT_S`.
- These SLOs define the canary thresholds below.

## Staged release procedure

Run [`deploy.yml`](../../.github/workflows/deploy.yml) (manual `workflow_dispatch`):

1. **Pre-deploy gate** — offline service tests + the 21b eval gate must pass; a red
   gate blocks the deploy.
2. **Staging** — build/push the image, apply migrations, deploy the revision, then
   run an **authenticated smoke test** (`/readyz` + one `/ask`) proving the deployed
   revision, model config, and auth path work.
3. **Canary** (production) — shift `canary_percent` traffic to the new revision and
   bake for `<10 minutes>`.
4. **Compare** the canary against the thresholds below; **promote to 100%** only if
   all hold, otherwise **roll back** (automatic on a failed canary).

Record for every release: **image digest**, **config revision**, **model
version**, and the **migration versions applied** (`migrations_applied` log event).

## Canary thresholds

Promote only if, over the bake window, the canary revision stays within:

| Metric           | Promote if     | Roll back if   |
| ---------------- | -------------- | -------------- |
| Error rate (5xx) | ≤ 1%           | > 1%           |
| p95 latency      | ≤ 1500 ms      | > 1500 ms      |
| `/readyz`        | 200 throughout | any non-200    |
| 5xx count        | ≤ 0.5% of reqs | > 0.5% of reqs |

Any "roll back if" condition, or a fired alert above, is a **rollback trigger**.

## Rollback — triggers, command, verification

**Triggers:** a tripped canary threshold, a fired availability/error/latency
alert, or a failed authenticated smoke test. When in doubt, roll back first and
investigate after.

**Command (revision):** shift 100% traffic back to the last-good revision.

```bash
# Replace with your platform's revision-rollback command, e.g.:
#   gcloud run services update-traffic m07b --to-revisions=<LAST_GOOD>=100
#   flyctl deploy --image <LAST_GOOD_IMAGE>
```

**Command (migration):** if the release shipped a schema migration, roll back the
most recent one after traffic is off the new revision. Each migration ships a
paired `NNNN_name.down.sql`; the runner drops its objects and removes the
`schema_migrations` row:

```bash
# Python (from modules/07b-delivery-operations/py)
uv run python -c "from m07b_service.migrations import rollback; \
  print(rollback('data/07b-service.sqlite'))"

# TypeScript
pnpm --filter @learn-ai/m07b-service exec tsx -e \
  "import('./src/migrations.js').then(m => console.log(m.rollback('data/07b-service.sqlite')))"
```

**Verify recovery:** `/readyz` returns 200, error rate/latency back within SLO,
and one authenticated `/ask` succeeds.

## Recovery commands

- **Readiness / liveness:** `curl -fsS $URL/readyz` (200 = migrated + writable);
  `curl -fsS $URL/healthz` (process alive).
- **Restart the service:** `<platform restart command>` — startup re-applies
  pending migrations idempotently and fails fast on a missing config/credential.
- **Rebuild a local DB from empty:** delete the SQLite file and restart; startup
  re-applies every migration.
- **Circuit stuck open:** confirm the provider is healthy, then let the breaker
  half-open after `CIRCUIT_COOLDOWN_S`; do not hot-patch — fix the dependency.
- **Backlogged ingestion jobs:** inspect with `GET /jobs/{id}`; exhausted jobs sit
  in the `dead` state (dead-letter). After fixing the cause, requeue them
  (`m07b_service.jobs.requeue`) — the indexing handler is idempotent, so a requeue
  is safe.

## Incident review template

Copy this per incident (blameless):

```md
# Incident <YYYY-MM-DD> — <short title>

- Severity: <SEV1 | SEV2 | SEV3>
- Duration: <detected> → <resolved> (time-to-detect / time-to-mitigate)
- Owner (write-up): <name>

## Impact

<who / what was affected, how it was measured>

## Timeline (UTC)

- <t0> <first alert / detection>
- <t1> <mitigation: rollback / config change>
- <t2> <resolved / verified>

## Root cause

<the actual cause, not the symptom>

## What went well / poorly

- <detection, tooling, comms>

## Action items

- [ ] <owner> — <preventive fix> — <due>
- [ ] <owner> — <detection/alert improvement> — <due>
```
