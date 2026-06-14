# Module 12 — Text-to-SQL

> **Depth tags** 🟢 app-level · 🟡 build-one-piece-by-hand

Not all enterprise data lives in documents. Sales figures, customer records,
inventory, and event logs live in relational databases — and an LLM can query
them in plain English if you give it the right schema context.

This module teaches you to build a NL→SQL pipeline that is both useful and safe:
generate SQL from questions, ground generation with schema metadata and sample
rows, guard against destructive queries, self-repair on errors, and route
between SQL and RAG based on question intent.

---

## Concepts

### Natural language → SQL

The core idea is simple: give the LLM your table definitions and ask it to write
SQL. The quality gap between a naive prompt and a careful one is enormous.

| Prompt quality | Typical failure modes |
| --- | --- |
| "Write SQL to answer: {question}" | Invented column names, wrong tables, no JOIN |
| + table names | Better table names, still wrong columns |
| + column names and types | Mostly correct for single-table queries |
| + sample rows and JOIN hints | Handles multi-table, picks right column values |
| + few-shot examples | Handles aggregations and edge cases reliably |

The lesson: schema grounding is not optional. A model with no schema will
hallucinate column names confidently.

### Schema grounding

A good schema prompt includes:
1. **Table name and column names with types** — `orders(id INTEGER, customer_id INTEGER, ...)`.
2. **Enum values** — `status: 'pending' | 'shipped' | 'delivered' | 'cancelled'`.
3. **Foreign key relationships** — `orders.customer_id → customers.id`.
4. **3–5 sample rows per table** — so the model knows realistic values.
5. **Explicit JOIN templates** — common joins written out in full.
6. **One or two few-shot examples** — question + correct SQL pair.

Generating the schema description from the live database (via `PRAGMA table_info`
and `SELECT ... LIMIT 3`) means it stays in sync automatically.

### Safety: why you must validate generated SQL

An LLM will comply with a question like "delete all orders" if you let it.
A RAG-style injection in user input can also trick the model into emitting
destructive SQL. Two mandatory guards:

1. **Read-only whitelist:** check that the first keyword is `SELECT`. Reject
   `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `REPLACE`, `TRUNCATE`.
2. **Stacked query rejection:** count semicolons. More than one = injection attempt.
   (`SELECT 1; DROP TABLE users; --` is the classic pattern.)

These are simple but effective. They do not prevent all attacks (e.g. malicious
sub-selects that cause performance issues), but they block the most dangerous ones.

### Self-repair

LLM-generated SQL sometimes fails on the first try: wrong column name, syntax
error, incompatible SQLite function. Instead of surfacing the error to the user,
feed it back to the LLM in a multi-turn conversation:

```
System: [schema prompt]
User:   "How many orders were placed in Q1 2024?"
Asst:   "SELECT count(*) FROM orders WHERE order_date BETWEEN '2024-01-01' AND '2024-04-01';"
User:   "That SQL produced this error: ... Please fix it."
Asst:   [corrected SQL]
```

In practice this repairs ~70–80% of first-turn errors. Set `max_retries=2` — if
the model can't fix it in 3 tries, surface the error.

### Hybrid routing: SQL vs RAG

Not every user question should go to SQL:

| Question | Best backend |
| --- | --- |
| "How many orders did Alice place last month?" | SQL — exact count from database |
| "What is the average order value by region?" | SQL — aggregation over table |
| "What is RAG and how does it work?" | RAG — conceptual knowledge |
| "Why might customers in the West region churn?" | RAG — analysis / reasoning |
| "Show me Alice's orders and explain why RAG helps personalise them." | Both |

A router classifies intent and dispatches. The LLM is well-suited to classify
because it understands both natural language and the difference between a data
question and a knowledge question.

**When SQL wins:** exact numbers, counts, aggregations, filters on structured
fields, ranking, trend over time.

**When RAG wins:** conceptual questions, how-to, background knowledge, analysis
that requires reasoning over text rather than summing numbers.

---

## Tasks

### Task 1 🟢 — NL→SQL

**Goal:** Generate SQL from a question, execute it, print the rows.

**Files:**
- `py/01_nl_to_sql.py`
- `ts/01-nl-to-sql.ts`

**Steps:**
1. Implement `generate_sql()` / `generateSql()` — build a schema-grounded
   prompt, call the LLM, return the SQL string.
2. Implement `extract_sql()` / `extractSql()` — strip markdown fences and
   return a single SQL statement ending in ";".
3. Implement `execute_sql()` / `executeSql()` — open `sales.db`, execute,
   return (columns, rows).
4. Implement `query()` — chain generate + execute.
5. Run the harness; it answers 4 questions.

**Acceptance:**
- All 4 questions return rows (not an exception).
- The SQL generated is valid SQLite (check by reading the `sql` field in output).
- "Total revenue from delivered orders" returns a single number.

---

### Task 2 🟡 — Schema-aware prompting

**Goal:** Auto-generate the schema description from the live DB, add sample
rows and JOIN hints, handle multi-table questions.

**Files:**
- `py/02_schema_aware_prompting.py`
- `ts/02-schema-aware-prompting.ts`

**Steps:**
1. Implement `get_schema_description()` / `getSchemaDescription()` — query
   `sqlite_master` and `PRAGMA table_info`, fetch 3 sample rows per table,
   format as a readable schema string.
2. Implement `build_system_prompt()` / `buildSystemPrompt()` — combine the
   schema with JOIN hints, rules, and few-shot examples.
3. Implement `generate_sql_rich()` / `generateSqlRich()` — use the rich prompt.
4. Run the harness on 4 multi-table questions (JOINs required for all of them).

**Acceptance:**
- Schema description includes COLUMNS and SAMPLE ROWS for all 3 tables.
- All 4 multi-table questions return results without errors.
- "Total spend per customer" returns a list ordered highest → lowest.

---

### Task 3 🟡 — Safety & repair

**Goal:** Validate that generated SQL is read-only, block injection, and
self-repair on DB errors.

**Files:**
- `py/03_safety_repair.py`
- `ts/03-safety-repair.ts`

**Steps:**
1. Implement `validate_read_only()` / `validateReadOnly()` — check first keyword
   and scan for forbidden words; raise `UnsafeSQLError` / `UnsafeSqlError` on fail.
2. Implement `validate_no_stacked_queries()` / `validateNoStackedQueries()` —
   reject multiple semicolons.
3. Implement `repair_sql()` / `repairSql()` — multi-turn conversation to fix
   a broken SQL statement.
4. Implement `safe_query()` / `safeQuery()` — chain: generate → validate →
   execute → repair on error (up to `max_retries`).
5. Run the harness: 2 safe questions and 2 adversarial inputs.

**Acceptance:**
- Normal questions execute successfully (retries=0 on a good model).
- "DROP TABLE customers" is blocked before any DB execution.
- "DELETE FROM orders WHERE 1=1" is blocked.
- `UnsafeSQLError` / `UnsafeSqlError` is raised (not a generic exception) for
  dangerous inputs.

---

### Task 4 🟢 — Hybrid routing

**Goal:** Classify question intent and dispatch to SQL or RAG accordingly.

**Files:**
- `py/04_hybrid_routing.py`
- `ts/04-hybrid-routing.ts`

**Steps:**
1. Implement `classify_intent()` / `classifyIntent()` — build an intent-
   classification prompt; parse JSON response `{"route": "sql|vector|both|unknown",
   "reasoning": "..."}`.
2. Implement `rag_answer()` / `ragAnswer()` — answer from the inline knowledge
   base using the LLM (simulated RAG context stuffing).
3. Implement `route_and_answer()` / `routeAndAnswer()` — classify, dispatch to
   `sql_answer` and/or `rag_answer`, return a `HybridAnswer`.
4. Run the harness on 5 questions (2 SQL, 2 RAG, 1 ambiguous).

**Acceptance:**
- Pure database questions (`route="sql"`) produce rows.
- Knowledge questions (`route="vector"`) produce text answers, not SQL.
- Routing classification is printed so you can inspect the LLM's reasoning.
- The ambiguous question is handled without crashing (any route is acceptable).

---

## Done when

- [ ] `seed_db.py` / `seed-db.ts` builds `sales.db` with 8 customers, 10 products,
      20 orders.
- [ ] Task 1: 4 questions answered with valid SQL and rows.
- [ ] Task 2: all 4 multi-table questions answered with JOINs (no errors).
- [ ] Task 3: adversarial inputs blocked; `UnsafeSQLError` raised; normal
      questions pass.
- [ ] Task 4: SQL questions produce rows; RAG questions produce text; routing
      classification is printed.
- [ ] Both py and ts harnesses run without crashing.

---

## Going deeper

- **PostgreSQL:** The same NL→SQL pattern works with PostgreSQL via
  `psycopg2` / `asyncpg`. What changes? The system prompt needs to note
  PostgreSQL dialect (e.g. `ILIKE`, `::text` casts, `NOW()` vs `datetime()`).
- **Schema size:** With 100+ tables, you can't fit the whole schema in the
  context window. Add a table-selection step: ask the LLM which 3–5 tables
  are relevant to the question, then include only those in the schema prompt.
- **Parameterised queries:** For user-facing apps, never interpolate user input
  into SQL strings — use `?` placeholders (Python/sqlite3) or `$1` (PostgreSQL).
  The generated SQL should be inspected for interpolation risks.
- **Fine-tuning:** Spider and WikiSQL are standard benchmarks for NL→SQL models.
  Look at [DIN-SQL](https://arxiv.org/abs/2304.11015) and
  [DAIL-SQL](https://arxiv.org/abs/2308.15363) for state-of-the-art approaches.
- **Full hybrid RAG + SQL:** Wire the router from task 4 to the real RAG pipeline
  from module 05. Replace the inline `KNOWLEDGE_BASE` stub with live vector
  retrieval and observe the routing quality improve.
- **Streaming results:** For slow aggregations over large tables, stream partial
  results to the user using SQLite's `cursor.fetchmany()` pattern.

---

## Environment variables

No new env vars beyond module 00.

## Python dependencies

All dependencies are in stdlib:
- `sqlite3` — built into Python (no install needed)
- `llm_core` — the course package

## TypeScript dependencies

Added to `ts/package.json`:
- `better-sqlite3` — synchronous SQLite bindings for Node.js (native addon)
- `@types/better-sqlite3` — TypeScript types

Install: `pnpm install` from `modules/12-text-to-sql/ts/` or `pnpm -r install` from repo root.

## Sample database

`sales.db` is created by the seed script and contains:
- 8 customers across 4 regions
- 10 products across 3 categories
- 20 orders spanning 2024

Run the seed script before any other task:

```bash
# Python
uv run python modules/12-text-to-sql/py/seed_db.py

# TypeScript
pnpm tsx modules/12-text-to-sql/ts/seed-db.ts
```
