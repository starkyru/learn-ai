/**
 * Task 2 🟡 — Schema-aware prompting.
 *
 * A richer schema prompt — with table descriptions, sample rows, and explicit
 * JOIN hints — dramatically improves LLM-generated SQL for multi-table queries.
 *
 * What you'll learn:
 *   - How few-shot examples steer the LLM away from wrong column names /
 *     wrong JOIN conditions
 *   - How to auto-generate a schema description from live database metadata
 *     (sqlite_master + PRAGMA table_info)
 *   - How to handle multi-table queries with explicit JOIN instructions
 *
 * How to run:
 *   pnpm tsx modules/12-text-to-sql/ts/02-schema-aware-prompting.ts
 */

import { getProvider } from "@learn-ai/llm-core";
import Database from "better-sqlite3";
import { existsSync } from "node:fs";
import { DB_PATH } from "./seed-db.js";
import { extractSql } from "./01-nl-to-sql.js";

// ---------------------------------------------------------------------------
// Dynamic schema extraction
// ---------------------------------------------------------------------------

/**
 * Auto-generate a schema description from the live database.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Open a better-sqlite3 connection.
 *   2. Get table names:
 *        db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
 *          .all() → Array<{name: string}>
 *   3. For each table:
 *      a. PRAGMA table_info(<table>) → rows with columns: cid, name, type, notnull, dflt_value, pk
 *      b. Fetch 3 sample rows: SELECT * FROM <table> LIMIT 3.
 *      c. Format as:
 *           TABLE: <name>
 *           COLUMNS: col1 (TYPE), col2 (TYPE), ...
 *           SAMPLE ROWS:
 *             [val1, val2, ...]
 *             [val1, val2, ...]
 *   4. Close DB.
 *   5. Return joined string with "\n\n" between tables.
 */
export function getSchemaDescription(dbPath = DB_PATH): string {
  // TODO: implement getSchemaDescription().
  throw new Error("TODO: implement getSchemaDescription()");
}

// ---------------------------------------------------------------------------
// Rich system prompt
// ---------------------------------------------------------------------------

/**
 * Build a detailed system prompt for multi-table SQL generation.
 *
 * TODO: implement this function.
 *
 * Include:
 *   1. Role: "You are an expert SQL analyst working with SQLite."
 *   2. The schema description.
 *   3. JOIN guidance:
 *        orders JOIN customers ON orders.customer_id = customers.id
 *        orders JOIN products  ON orders.product_id  = products.id
 *   4. Rules:
 *        - Return ONLY a single SQL SELECT statement.
 *        - No markdown, no explanation.
 *        - Use table aliases (o for orders, c for customers, p for products).
 *        - Always use explicit column names; never SELECT *.
 *   5. One or two few-shot examples (question + correct SQL pair).
 *
 * Return the system prompt string.
 */
export function buildSystemPrompt(schema: string): string {
  // TODO: implement buildSystemPrompt().
  throw new Error("TODO: implement buildSystemPrompt()");
}

// ---------------------------------------------------------------------------
// Generation + execution
// ---------------------------------------------------------------------------

/**
 * Generate SQL using the rich schema-aware prompt.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. system = buildSystemPrompt(schema).
 *   2. Call provider.chat([systemMsg, userMsg], { temperature: 0 }).
 *   3. Return extractSql(result.text).
 */
export async function generateSqlRich(
  question: string,
  schema: string,
  provider: ReturnType<typeof getProvider>
): Promise<string> {
  // TODO: implement generateSqlRich().
  throw new Error("TODO: implement generateSqlRich()");
}

function executeSql(sql: string): { columns: string[]; rows: unknown[][] } {
  const db = new Database(DB_PATH);
  try {
    const stmt = db.prepare(sql);
    const rows = stmt.all() as Record<string, unknown>[];
    const columns = rows.length > 0 ? Object.keys(rows[0]) : [];
    return { columns, rows: rows.map((r) => Object.values(r)) };
  } finally {
    db.close();
  }
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

const MULTI_TABLE_QUESTIONS = [
  "Which customers placed orders for Electronics products?",
  "What is the total spend per customer, sorted from highest to lowest?",
  "List all orders with the customer name and product name, for orders that are 'shipped'.",
  "Which product category generates the most revenue from delivered orders?",
];

async function main() {
  if (!existsSync(DB_PATH)) {
    console.error(`Database not found: ${DB_PATH}`);
    console.error("Run `pnpm tsx modules/12-text-to-sql/ts/seed-db.ts` first.");
    process.exit(1);
  }

  const schema = getSchemaDescription();
  console.log("\n--- Live Schema ---");
  console.log(schema);
  console.log("---\n");

  const provider = getProvider();
  console.log(`Provider: ${provider.name}  |  Model: ${provider.chatModel}\n`);

  for (const q of MULTI_TABLE_QUESTIONS) {
    console.log(`Q: ${q}`);
    const sql = await generateSqlRich(q, schema, provider);
    console.log(`   SQL: ${sql}`);
    try {
      const { columns, rows } = executeSql(sql);
      console.log(`   Cols: ${columns.join(", ")}`);
      for (const row of rows.slice(0, 5)) {
        console.log(`   Row:  ${JSON.stringify(row)}`);
      }
    } catch (e) {
      console.log(`   ERROR: ${e}`);
    }
    console.log();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
