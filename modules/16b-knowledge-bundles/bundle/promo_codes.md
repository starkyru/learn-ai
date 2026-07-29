---
type: table
title: Promo codes
description: Active discount codes with their redemption limits.
resource: bigquery://acme-retail/marketing/promo_codes
tags: [marketing]
status: stable
stale_after: 2026-06-30
sources:
  - resource: marketing/campaign-brief-q2.md
    title: Q2 campaign brief
generated:
  by: reference_agent/llama3.2
  at: 2026-04-11T08:00:00Z
verified:
  - by: human:learner
    at: 2026-04-11T09:00:00Z
---

# Promo codes

Campaign discount codes and their limits. Redemptions land on
[Orders](/orders.md) as a negative adjustment line, so this table alone does not
tell you what a campaign actually cost.

This concept carries `stale_after: 2026-06-30` because the code list is a
point-in-time snapshot of one quarter's campaigns: after that date the contents
are no longer trustworthy even though nothing about the file changed. Freshness is
a property of the knowledge, not of the file's mtime.

| code     | discount | max_redemptions |
| -------- | -------- | --------------- |
| SPRING10 | 10%      | 50000           |
| WELCOME5 | 5%       | unlimited       |
