# Retention schedule — `<product name>`

> Owner: `<name / team>` · Last reviewed: `<YYYY-MM-DD>` · Review cadence: `<quarterly>`

Every store in the [data inventory](DATA_INVENTORY.md) needs a **retention
period**, a **basis** for keeping it that long, a **deletion mechanism**, and any
**exception** that overrides erasure. Erasure is not uniform: some stores tombstone
rather than hard-delete, some are held longer under a legal/contractual basis.

## Schedule

| Store               | Data class        | Retention period | Basis (why this long)         | Deletion mechanism          | Exceptions                        |
| ------------------- | ----------------- | ---------------- | ----------------------------- | --------------------------- | --------------------------------- |
| Primary DB          | `<PII / content>` | `<e.g. 24 mo>`   | `<contract / legitimate use>` | `<hard delete / tombstone>` | `<legal hold; billing records>`   |
| Vector store        | derived           | `<= source>`     | tied to source lifecycle      | delete by id / re-index     | `<none>`                          |
| Prompt / trace logs | may contain PII   | `<e.g. 30 d>`    | debugging window              | rotation / purge            | `<incident evidence hold>`        |
| Cache               | derived           | `<TTL>`          | latency / cost                | TTL expiry / flush          | `<none>`                          |
| Feedback / review   | user text         | `<e.g. 12 mo>`   | quality improvement           | delete by id                | `<anonymise then keep aggregate>` |
| Backups / snapshots | all               | `<e.g. 35 d>`    | disaster recovery             | snapshot expiry             | deletion propagates on next cycle |

## Deletion & exception rules

- On an erasure request, deletion must reach **every** store above (see the
  [data inventory](DATA_INVENTORY.md)), not just the primary record.
- A store kept past a user's erasure request must name its **exception** and the
  basis (legal hold, contractual, aggregate-only anonymised). Record the exception
  in the audit trail.

## Review

- Recompute and re-approve this schedule every `<cadence>`; a store added to the
  inventory without a retention decision is a release blocker.
