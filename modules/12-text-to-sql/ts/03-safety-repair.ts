/**
 * Task 3 🟡 — Safety & repair.
 *
 * LLM-generated SQL can be dangerous (DROP TABLE) or broken (syntax error,
 * wrong column name). This task adds three defences:
 *   1. Read-only guard: reject any SQL that is not a SELECT statement.
 *   2. Injection guard: reject stacked queries (multiple statements).
 *   3. Error-and-retry: on DB error, feed it back to the LLM and ask for
 *      a corrected query (up to N retries).
 *
 * What you'll learn:
 *   - Why you must NEVER execute untrusted LLM SQL without validation
 *   - The read-only guard pattern (whitelist on statement type)
 *   - Self-healing agents: the LLM can fix its own mistakes when told what
 *     went wrong
 *   - The limits of self-repair (some errors are beyond the LLM's reach)
 *
 * How to run:
 *   pnpm tsx modules/12-text-to-sql/ts/03-safety-repair.ts
 */

import { getProvider, type ChatMessage } from "@learn-ai/llm-core";
import Database from "better-sqlite3";
import { existsSync } from "node:fs";
import { DB_PATH } from "./seed-db.js";
import { extractSql } from "./01-nl-to-sql.js";

const SCHEMA = `
customers(id, name, email, region, signup_date)
products(id, name, category, price_usd)
orders(id, customer_id→customers, product_id→products, quantity, order_date, status)
`.trim();

// ---------------------------------------------------------------------------
// Safety validators
// ---------------------------------------------------------------------------

export class UnsafeSqlError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "UnsafeSqlError";
  }
}

/**
 * Reject any SQL that is not a plain SELECT.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Strip leading whitespace and comment lines (lines starting with "--").
 *   2. Extract the first keyword: sql.trimStart().split(/\s+/)[0].toUpperCase().
 *   3. If not "SELECT": throw new UnsafeSqlError(`Rejected: starts with '${keyword}', not SELECT.`).
 *   4. Scan the full SQL for forbidden keywords as standalone words
 *      (regex: /\b(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|REPLACE|TRUNCATE)\b/i).
 *      If found: throw new UnsafeSqlError(`Rejected: contains forbidden keyword '${match}'.`).
 */
export function validateReadOnly(sql: string): void {
  // TODO: implement validateReadOnly().
  throw new Error("TODO: implement validateReadOnly()");
}

/**
 * Reject SQL containing multiple statements (stacked queries / injection).
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Count ";" in sql.
 *   2. If more than one ";", throw new UnsafeSqlError("Rejected: multiple statements.").
 *   3. If a ";" appears before the trimmed end of the string (e.g. "; --" suffix),
 *      also reject.
 *
 * Example to block: SELECT 1; DROP TABLE customers; --
 */
export function validateNoStackedQueries(sql: string): void {
  // TODO: implement validateNoStackedQueries().
  throw new Error("TODO: implement validateNoStackedQueries()");
}

// ---------------------------------------------------------------------------
// Error-and-retry loop
// ---------------------------------------------------------------------------

function generateSqlSimple(
  question: string,
  provider: ReturnType<typeof getProvider>
): Promise<string> {
  const messages: ChatMessage[] = [
    {
      role: "system",
      content: `You are a SQL expert. Schema:\n${SCHEMA}\nReturn ONLY a SQL SELECT statement, no explanation, no fences.`,
    },
    { role: "user", content: question },
  ];
  return provider.chat(messages, { temperature: 0 }).then((r) => extractSql(r.text));
}

/**
 * Ask the LLM to fix a broken SQL statement given the database error message.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Build a multi-turn conversation:
 *        [system, user(question), assistant(badSql), user(repair prompt)]
 *      The repair prompt should include the error message and ask for a
 *      corrected SQL statement only.
 *   2. Call provider.chat(messages, { temperature: 0 }).
 *   3. Return extractSql(result.text).
 */
export async function repairSql(
  question: string,
  badSql: string,
  errorMessage: string,
  provider: ReturnType<typeof getProvider>
): Promise<string> {
  // TODO: implement repairSql().
  throw new Error("TODO: implement repairSql()");
}

// ---------------------------------------------------------------------------
// Safe query pipeline
// ---------------------------------------------------------------------------

export interface SafeQueryResult {
  sql: string;
  columns: string[];
  rows: unknown[][];
  retries: number;
}

/**
 * Full safe pipeline: generate → validate → execute → repair on error.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. sql = await generateSqlSimple(question, provider).
 *   2. validateReadOnly(sql)            — throws UnsafeSqlError immediately (no retry).
 *   3. validateNoStackedQueries(sql).
 *   4. For attempt = 0 to maxRetries:
 *      a. Try:
 *           const db = new Database(DB_PATH);
 *           const stmt = db.prepare(sql);
 *           const rows = stmt.all() as Record<string, unknown>[];
 *           db.close();
 *           return { sql, columns: Object.keys(rows[0] ?? {}),
 *                    rows: rows.map(r => Object.values(r)), retries: attempt }.
 *      b. Catch any error:
 *           if attempt < maxRetries:
 *             sql = await repairSql(question, sql, String(error), provider);
 *             validateReadOnly(sql);       // re-validate
 *             validateNoStackedQueries(sql);
 *           else: throw.
 *   5. (Unreachable — for type safety) throw new Error("Exceeded retries").
 *
 * Note: UnsafeSqlError should never be caught here — let it propagate.
 */
export async function safeQuery(
  question: string,
  provider: ReturnType<typeof getProvider>,
  maxRetries = 2
): Promise<SafeQueryResult> {
  // TODO: implement safeQuery().
  throw new Error("TODO: implement safeQuery()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

const TEST_CASES: Array<[string, boolean]> = [
  // Normal — should succeed
  ["How many products are in the Electronics category?", true],
  ["What is the average price of all products?",          true],
  // Adversarial — should be blocked
  ["DROP TABLE customers",                                false],
  ["DELETE FROM orders WHERE 1=1",                       false],
];

async function main() {
  if (!existsSync(DB_PATH)) {
    console.error(`Database not found: ${DB_PATH}`);
    console.error("Run `pnpm tsx modules/12-text-to-sql/ts/seed-db.ts` first.");
    process.exit(1);
  }

  const provider = getProvider();
  console.log(`\nProvider: ${provider.name}  |  Model: ${provider.chatModel}\n`);

  for (const [question, expectSuccess] of TEST_CASES) {
    console.log(`Q: ${question}`);
    try {
      const result = await safeQuery(question, provider);
      if (expectSuccess) {
        console.log(`   OK — SQL: ${result.sql}`);
        console.log(`   Retries: ${result.retries}`);
        for (const row of result.rows.slice(0, 3)) {
          console.log(`   Row: ${JSON.stringify(row)}`);
        }
      } else {
        console.log("   UNEXPECTED SUCCESS (guard should have blocked this)");
      }
    } catch (e) {
      if (e instanceof UnsafeSqlError && !expectSuccess) {
        console.log(`   BLOCKED (expected): ${e.message}`);
      } else if (!expectSuccess) {
        console.log(`   BLOCKED by error: ${e}`);
      } else {
        console.log(`   ERROR: ${e}`);
      }
    }
    console.log();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
