---
type: table
title: Legacy orders v1
description: Superseded pre-migration snapshot of order volume.
resource: bigquery://acme-retail/legacy/orders_v1
tags: [sales, legacy]
status: deprecated
sources:
  - resource: warehouse/ddl/orders_v1.sql
    title: Orders v1 DDL
generated:
  by: reference_agent/llama3.2
  at: 2026-06-01T09:07:00Z
verified:
  - by: human:learner
    at: 2026-06-02T10:09:00Z
---

# Legacy orders v1

Frozen copy of the pre-migration orders table. Kept for reconciliation only:
totals here are in whole units, not cents, and cancelled orders were deleted
rather than flagged, so day-level order volume disagrees with
[Orders](/orders.md).

`status: deprecated` is the signal that matters. This concept is verified and it
is not stale — it is simply the wrong answer to every question. A trust filter
that only checks freshness will happily hand it to the model.
