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
 *   1. Build a `ChatMessage[]`:
 *      - a system message establishing the model as a SQLite SQL expert,
 *        embedding the `SCHEMA` constant, and forbidding any output other than
 *        the raw SQL (no prose, no markdown fences);
 *      - a user message carrying the `question`.
 *   2. Call `provider.chat(messages, { temperature: ... })` — pick the setting
 *      that makes generation deterministic.
 *   3. Clean the reply with `extractSql()` and return the SQL string.
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
 *   1. Trim surrounding whitespace.
 *   2. Strip any markdown code fences the model may have wrapped the SQL in
 *      (```sql ... ``` or plain ``` ... ```) with a case-insensitive replace,
 *      then trim stray backticks/spaces/newlines.
 *   3. Keep only the first statement: slice up to and including the first ";".
 *      If there is no ";", append one so the result ends in a semicolon.
 *   4. Trim again and return the single-statement string.
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
 *   1. Open a connection: `new Database(DB_PATH)`.
 *   2. Prepare the statement (`db.prepare(sql)`) and run `.all()` — it returns
 *      an array of row objects keyed by column name.
 *   3. Derive the `columns` from the keys of the first row, defaulting to an
 *      empty array when the result set is empty.
 *   4. Reduce each row object to its values so `rows` is `unknown[][]`.
 *   5. Close the DB and return the `QueryResult` shape ({ columns, rows }).
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
 *   1. Turn the question into SQL with `generateSql()` (await it).
 *   2. Run it through `executeSql()` to get columns and rows.
 *   3. Return the SQL merged with that result ({ sql } spread with the
 *      QueryResult fields).
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
