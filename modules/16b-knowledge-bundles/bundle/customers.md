---
type: table
title: Customers
description: One row per customer account, with signup source and region.
resource: bigquery://acme-retail/warehouse/customers
tags: [crm, core]
status: stable
sources:
  - resource: warehouse/ddl/customers.sql
    title: Customers DDL
generated:
  by: reference_agent/llama3.2
  at: 2026-06-01T09:04:00Z
verified:
  - by: human:learner
    at: 2026-06-02T10:05:00Z
---

# Customers

One row per account. `customer_id` is the primary key and is referenced by
[Orders](/orders.md). Accounts are never hard-deleted; an erasure request sets
`redacted_at` and clears the contact columns, which keeps historical joins intact.

`region` is a three-letter internal code, not an ISO country code — the mapping
lives in the region dimension, not here.

## Schema

| column      | type      | notes                      |
| ----------- | --------- | -------------------------- |
| customer_id | STRING    | primary key                |
| signup_at   | TIMESTAMP | UTC                        |
| source      | STRING    | organic / paid / referral  |
| region      | STRING    | internal three-letter code |
| redacted_at | TIMESTAMP | set on an erasure request  |
