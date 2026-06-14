/**
 * Task 1 🟢 — Natural-language to SQL.
 *
 * Given a plain-English question, ask the LLM to generate a SQL SELECT,
 * execute it against the sample SQLite database, and return the rows.
 *
 * What you'll learn:
 *   - The NL→SQL prompt pattern: provide the schema, ask for one SQL statement
 *   - How to extract clean SQL from a model response (fencing, whitespace)
 *   - How better-sqlite3 executes queries synchronously
 *   - Why schema grounding is essential: without table definitions the LLM
 *     guesses column names and gets them wrong
 *
 * How to run:
 *   pnpm tsx modules/12-text-to-sql/ts/seed-db.ts   # first time only
 *   pnpm tsx modules/12-text-to-sql/ts/01-nl-to-sql.ts
 */

import { getProvider, type ChatMessage, type ChatOptions } from "@learn-ai/llm-core";
import Database from "better-sqlite3";
import { existsSync } from "node:fs";
import { DB_PATH } from "./seed-db.js";

// ---------------------------------------------------------------------------
// Schema (provided to the LLM for grounding)
// ---------------------------------------------------------------------------

const SCHEMA = `
Tables in the database:

customers(id INTEGER PK, name TEXT, email TEXT, region TEXT, signup_date TEXT)
  -- region: 'North' | 'South' | 'East' | 'West'

products(id INTEGER PK, name TEXT, category TEXT, price_usd REAL)
  -- category: 'Electronics' | 'Books' | 'Clothing'

orders(id INTEGER PK, customer_id INTEGER FK→customers, product_id INTEGER FK→products,
       quantity INTEGER, order_date TEXT, status TEXT)
  -- status: 'pending' | 'shipped' | 'delivered' | 'cancelled'
  -- dates are ISO-8601 strings (e.g. '2024-03-15')
`.trim();

// ---------------------------------------------------------------------------
// Step 1: generate SQL
// ---------------------------------------------------------------------------

/**
 * Ask the LLM to write a SQL SELECT for the given question.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Build a system prompt:
 *      - State the LLM is a SQL expert working with SQLite.
 *      - Include the SCHEMA constant.
 *      - Instruct: "Return ONLY the SQL statement, no explanation, no markdown fences."
 *   2. Build a user message with the question.
 *   3. Call provider.chat([systemMsg, userMsg], { temperature: 0 }).
 *   4. Clean the response with extractSql() and return the SQL string.
 */
export async function generateSql(
  question: string,
  provider: ReturnType<typeof getProvider>
): Promise<string> {
  // TODO: implement generateSql().
  throw new Error("TODO: implement generateSql()");
}

/**
 * Clean raw LLM output and return a single SQL statement.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Strip whitespace.
 *   2. Remove markdown code fences: replace /```(?:sql)?\n?/gi with "".
 *   3. Strip trailing backticks/spaces/newlines.
 *   4. Take text up to and including the first ";". If no ";" found, append one.
 *   5. Strip whitespace.
 *   6. Return the result.
 */
export function extractSql(raw: string): string {
  // TODO: implement extractSql().
  throw new Error("TODO: implement extractSql()");
}

// ---------------------------------------------------------------------------
// Step 2: execute SQL
// ---------------------------------------------------------------------------

export interface QueryResult {
  columns: string[];
  rows: unknown[][];
}

/**
 * Execute a SQL query against the sample database synchronously.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. const db = new Database(DB_PATH).
 *   2. const stmt = db.prepare(sql).
 *   3. const rows = stmt.all() — returns an array of row objects.
 *   4. Derive columns from Object.keys(rows[0]) (handle empty result: columns=[]).
 *   5. Convert rows to arrays: rows.map(r => Object.values(r)).
 *   6. db.close().
 *   7. Return { columns, rows }.
 *
 * Let better-sqlite3 errors propagate — task 3 adds retry logic.
 */
export function executeSql(sql: string): QueryResult {
  // TODO: implement executeSql().
  throw new Error("TODO: implement executeSql()");
}

// ---------------------------------------------------------------------------
// Combined pipeline
// ---------------------------------------------------------------------------

/**
 * Full NL→SQL→execute pipeline.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. sql = await generateSql(question, provider).
 *   2. result = executeSql(sql).
 *   3. Return { sql, ...result }.
 */
export async function query(
  question: string,
  provider: ReturnType<typeof getProvider>
): Promise<{ sql: string } & QueryResult> {
  // TODO: implement query().
  throw new Error("TODO: implement query()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

const QUESTIONS = [
  "How many customers are there in total?",
  "What are the top 3 most expensive products?",
  "Which customers are from the West region?",
  "What is the total revenue from delivered orders?",
];

async function main() {
  if (!existsSync(DB_PATH)) {
    console.error(`Database not found: ${DB_PATH}`);
    console.error("Run `pnpm tsx modules/12-text-to-sql/ts/seed-db.ts` first.");
    process.exit(1);
  }

  const provider = getProvider();
  console.log(`\nProvider: ${provider.name}  |  Model: ${provider.chatModel}\n`);

  for (const q of QUESTIONS) {
    console.log(`Q: ${q}`);
    const result = await query(q, provider);
    console.log(`   SQL:  ${result.sql}`);
    console.log(`   Cols: ${result.columns.join(", ")}`);
    for (const row of result.rows.slice(0, 5)) {
      console.log(`   Row:  ${JSON.stringify(row)}`);
    }
    console.log();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
