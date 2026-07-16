# Data inventory — `<product name>`

> Owner: `<name / team>` · Last reviewed: `<YYYY-MM-DD>` · Next review: `<YYYY-MM-DD>`

The data lifecycle is longer than a single request. Record **every** place a copy
of user or source data comes to rest — not only the source document, but the
derived artifacts: embeddings, prompts/traces, caches, feedback, job records, and
backups.

## Data stores

| Store                         | Data class(es)         | Purpose            | Owner      | Access control     | Retention         | Deletion mechanism             |
| ----------------------------- | ---------------------- | ------------------ | ---------- | ------------------ | ----------------- | ------------------------------ |
| Primary DB (`<table>`)        | `<PII / content / …>`  | `<why held>`       | `<owner>`  | `<who / how>`      | `<period>`        | `<hard delete / tombstone>`    |
| Vector store (embeddings)     | derived from `<src>`   | retrieval          | `<owner>`  | `<who / how>`      | `<period>`        | `<delete by id / re-index>`    |
| Prompt / trace logs           | `<may contain PII>`    | debugging / eval   | `<owner>`  | `<who / how>`      | `<period>`        | `<rotation / purge>`           |
| Cache (responses/embeddings)  | `<derived>`            | latency / cost     | `<owner>`  | `<who / how>`      | `<TTL>`           | `<TTL expiry / flush>`         |
| Feedback / review records     | `<user text + labels>` | quality            | `<owner>`  | `<who / how>`      | `<period>`        | `<delete by id>`               |
| Background job records        | `<ids + status>`       | ingestion tracking | `<owner>`  | `<who / how>`      | `<period>`        | `<purge on completion>`        |
| Provider (LLM/embeddings API) | prompt + retrieved ctx | inference          | `<vendor>` | `<contract / DPA>` | `<vendor policy>` | `<opt-out of training / n/a>`  |
| Backups / snapshots           | all of the above       | recovery           | `<owner>`  | `<who / how>`      | `<period>`        | `<expiry; delete propagation>` |

## Data flow (collection → deletion)

Trace one record end to end; note each hop where a NEW copy is created:

`collection → API → prompt → provider → retrieval (embeddings) → tools → logs → cache → feedback → backups`

## Minimisation decisions

- Fields collected but **not necessary** → `<removed / redacted before which hop>`.
- Restricted fields that must **never** reach a prompt, trace, log, or provider →
  `<list; enforced by which control / test>`.
- Free-text fields that may contain unclassified secrets → `<content-DLP decision>`.
