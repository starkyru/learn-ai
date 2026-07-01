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
 *   1. Normalise first: drop leading whitespace and any comment lines (starting
 *      with "--") so the real first token is visible.
 *   2. Extract the leading keyword (split on whitespace, take the first token,
 *      upper-case it).
 *   3. If it is not "SELECT", throw an `UnsafeSqlError` naming the keyword.
 *   4. As defence-in-depth, scan the whole SQL for any mutating keyword — DROP,
 *      DELETE, UPDATE, INSERT, ALTER, CREATE, REPLACE, TRUNCATE — matched as
 *      standalone words (word-boundary `\b...\b`, case-insensitive) so
 *      substrings like "created_at" don't trip it, and throw if one is found.
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
 *   1. Look at where ";" characters fall. A legitimate single statement has at
 *      most one ";", and it must be the last non-whitespace character.
 *   2. If there is more than one ";", or a ";" sits before the trimmed end of
 *      the string (e.g. a "; --" suffix), throw an `UnsafeSqlError`.
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
 *   1. Generate the SQL with `generateSqlSimple()` (await it).
 *   2. Gate it through BOTH validators (`validateReadOnly`,
 *      `validateNoStackedQueries`) before touching the database — they throw on
 *      unsafe input and must NOT be retried.
 *   3. Loop from attempt 0 up to `maxRetries`:
 *      - Try to open the DB, run `.all()`, and build a `SafeQueryResult`
 *        (sql, columns from the first row's keys, rows as value arrays, and
 *        `retries` set to the current attempt number).
 *      - On any DB error, if attempts remain: ask `repairSql()` for a corrected
 *        query using `String(error)`, then re-run BOTH validators on the
 *        repaired SQL before looping. If none remain, rethrow.
 *   4. Add an unreachable guard after the loop (throw) so the function is
 *      provably total for the type checker.
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
