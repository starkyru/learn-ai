---
type: table
title: Orders
description: One row per customer order, with order volume, status and totals.
resource: bigquery://acme-retail/warehouse/orders
tags: [sales, core]
status: stable
stale_after: 2027-01-01
sources:
  - resource: warehouse/ddl/orders.sql
    title: Orders DDL
  - resource: docs/order-lifecycle.md
    title: Order lifecycle notes
generated:
  by: reference_agent/llama3.2
  at: 2026-06-01T09:00:00Z
verified:
  - by: human:learner
    at: 2026-06-02T10:00:00Z
---

# Orders

The transactional spine of the warehouse: one row per placed order. `order_id` is
the primary key; `customer_id` joins to [Customers](/customers.md). Cancelled
orders keep their row with `status = 'cancelled'` rather than being deleted, so
order volume by day is always reconstructable.

Money columns (`subtotal_cents`, `tax_cents`, `total_cents`) are integer cents in
the store's settlement currency. Day-level takings are rolled up separately in
the [Daily revenue rollup](/metrics/daily_revenue.md) — query that instead of
re-aggregating this table.

## Schema

| column      | type      | notes                                    |
| ----------- | --------- | ---------------------------------------- |
| order_id    | STRING    | primary key                              |
| customer_id | STRING    | joins Customers                          |
| placed_at   | TIMESTAMP | UTC                                      |
| status      | STRING    | placed / shipped / delivered / cancelled |
| total_cents | INT64     | integer cents, settlement currency       |
