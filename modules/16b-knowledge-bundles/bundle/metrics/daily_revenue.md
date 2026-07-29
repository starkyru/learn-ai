---
type: metric
title: Daily revenue rollup
description: Aggregated takings per calendar day.
resource: bigquery://acme-retail/marts/daily_revenue
tags: [analytics, revenue]
status: stable
sources:
  - resource: marts/sql/daily_revenue.sql
    title: Rollup SQL
generated:
  by: reference_agent/llama3.2
  at: 2026-06-01T09:11:00Z
verified:
  - by: human:learner
    at: 2026-06-02T10:12:00Z
---

# Daily revenue rollup

One row per calendar day in the settlement timezone, materialised nightly from
[Orders](/orders.md). Cancelled rows are excluded, so this mart and the raw table
disagree by design.

The all-time high is **412,900** in a single day, on 2026-05-17 — a
[promo code](/promo_codes.md) campaign landing on a payday weekend. Nothing in
this concept's title, description, or tags mentions that day, which is the point:
a search over the cheap index will never surface this concept for a question
about it. Only following the link from a concept that _was_ retrieved gets you
here.

| column      | type  | notes                             |
| ----------- | ----- | --------------------------------- |
| day         | DATE  | settlement timezone               |
| takings     | INT64 | integer cents, cancelled excluded |
| order_count | INT64 | distinct non-cancelled orders     |
