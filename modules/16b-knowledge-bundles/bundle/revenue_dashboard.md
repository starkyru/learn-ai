---
type: dashboard
title: Revenue dashboard
description: Executive dashboard sourced from the revenue rollup.
resource: looker://acme-retail/dashboards/revenue
tags: [analytics]
status: draft
sources:
  - resource: analytics/dashboard-spec.md
    title: Dashboard spec (draft)
generated:
  by: reference_agent/llama3.2
  at: 2026-07-20T11:00:00Z
---

# Revenue dashboard

Four tiles: takings today, takings week-to-date, order count, and average order
value. Every tile reads the [Daily revenue rollup](/metrics/daily_revenue.md);
none of them query the raw tables.

Discount attribution is still open — see [Promo codes](./promo_codes.md) — and
the tile definitions live in [the tile registry](/warehouse/missing.md), which
does not exist in this bundle. That dangling link is deliberate: Task 4 must
report it instead of crashing.

This concept has `status: draft` and **no `verified` entry**: it was written by an
agent and no human has signed it off. It is fresh, it is not deprecated, and it
is still the one concept here you would not want cited in an executive answer.
