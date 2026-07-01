/**
 * Task 4 🟢 — Hybrid routing.
 *
 * Not every question should go to SQL. Questions about what happened in
 * structured data belong to SQL. Questions about why / how — or general
 * knowledge — belong to vector retrieval (RAG from module 05).
 *
 * A router classifies intent and dispatches to the right backend.
 *
 * What you'll learn:
 *   - The key distinction between structured (SQL) and unstructured (RAG) queries
 *   - How to prompt an LLM to classify query intent with a small set of categories
 *   - How a router composes two retrieval backends
 *   - When each backend wins and when they complement each other
 *
 * How to run:
 *   pnpm tsx modules/12-text-to-sql/ts/04-hybrid-routing.ts
 */

import { getProvider, type ChatMessage } from "@learn-ai/llm-core";
import Database from "better-sqlite3";
import { existsSync } from "node:fs";
import { DB_PATH } from "./seed-db.js";
import { extractSql } from "./01-nl-to-sql.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type Route = "sql" | "vector" | "both" | "unknown";

export interface RouterDecision {
  route: Route;
  reasoning: string;   // one-sentence explanation from the LLM
}

export interface HybridAnswer {
  question: string;
  route: Route;
  reasoning: string;
  sqlResult?: { sql: string; columns: string[]; rows: unknown[][] };
  ragResult?: string;
}

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------

/**
 * Ask the LLM to classify the question's retrieval intent.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Build a system prompt explaining the two backends:
 *        "sql"    — counts, aggregations, filters, rankings, trends from
 *                   sales/orders/customers/products tables.
 *        "vector" — concepts, explanations, how-to, background knowledge
 *                   not in the database (RAG, embeddings, AI, etc.).
 *        "both"   — the question has a structured AND a knowledge sub-question.
 *        "unknown"— intent unclear; needs rephrasing.
 *      Instruct the model to reply as a JSON object with two fields — a
 *      "route" (one of the four categories) and a one-sentence "reasoning" —
 *      and nothing else.
 *   2. Call `provider.chat(messages, { temperature: ... })` with the
 *      deterministic setting.
 *   3. Strip any ```json ... ``` fence from the response, then `JSON.parse` it.
 *   4. Return the parsed value as a `RouterDecision`.
 */
export async function classifyIntent(
  question: string,
  provider: ReturnType<typeof getProvider>
): Promise<RouterDecision> {
  // TODO: implement classifyIntent().
  throw new Error("TODO: implement classifyIntent()");
}

// ---------------------------------------------------------------------------
// SQL backend
// ---------------------------------------------------------------------------

const SCHEMA = `
customers(id, name, email, region, signup_date)
products(id, name, category, price_usd)
orders(id, customer_id→customers, product_id→products, quantity, order_date, status)
`.trim();

async function sqlAnswer(
  question: string,
  provider: ReturnType<typeof getProvider>
): Promise<{ sql: string; columns: string[]; rows: unknown[][] }> {
  const messages: ChatMessage[] = [
    {
      role: "system",
      content: `You are a SQL expert. Schema:\n${SCHEMA}\nReturn ONLY a SQL SELECT statement, no explanation, no fences.`,
    },
    { role: "user", content: question },
  ];
  const result = await provider.chat(messages, { temperature: 0 });
  const sql = extractSql(result.text);

  const db = new Database(DB_PATH);
  try {
    const rows = db.prepare(sql).all() as Record<string, unknown>[];
    const columns = rows.length > 0 ? Object.keys(rows[0]) : [];
    return { sql, columns, rows: rows.map((r) => Object.values(r)) };
  } finally {
    db.close();
  }
}

// ---------------------------------------------------------------------------
// Vector backend (stub — simulated RAG with inline knowledge)
// ---------------------------------------------------------------------------

// Tiny inline knowledge base (mirrors module 11 sample docs content)
const KNOWLEDGE_BASE = `
RAG (Retrieval-Augmented Generation) combines a retrieval system with an LLM.
It solves the problem of LLMs hallucinating by injecting relevant passages as
context. The key stages are: parse, chunk, embed, retrieve, generate.

Vector databases store high-dimensional embeddings and support approximate
nearest-neighbour (ANN) search. Popular options include Chroma, Qdrant, and
Pinecone. HNSW is the most common index structure.

Chunking splits documents into shorter passages before embedding because
embedding models have token limits (usually 256-512 tokens). Section-aware
chunking follows document structure; naive chunking uses fixed character counts.

Incremental indexing re-embeds only changed documents by comparing content
hashes, saving API costs. A manifest file tracks which documents have been
ingested and at what version.
`;

/**
 * Answer from the inline knowledge base using the LLM (simulated RAG).
 *
 * TODO: implement this function.
 *
 * In a real system this would embed the question, retrieve chunks from a
 * vector store, and call the LLM with context. For this exercise:
 *
 * Steps:
 *   1. Build a `ChatMessage[]`:
 *        - a system message constraining the model to answer ONLY from the
 *          supplied context and to admit when the context lacks the answer;
 *        - a user message that stitches together `KNOWLEDGE_BASE` (as the
 *          context) and the `question`.
 *   2. Call `provider.chat(messages)`.
 *   3. Return the model's text.
 *
 * Reflection: what would change if you replaced KNOWLEDGE_BASE with live
 * vector retrieval from module 05?
 */
export async function ragAnswer(
  question: string,
  provider: ReturnType<typeof getProvider>
): Promise<string> {
  // TODO: implement ragAnswer().
  throw new Error("TODO: implement ragAnswer()");
}

// ---------------------------------------------------------------------------
// Router dispatcher
// ---------------------------------------------------------------------------

/**
 * Classify intent, dispatch to the right backend(s), return a HybridAnswer.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Get a `RouterDecision` from `classifyIntent()` (await it).
 *   2. Seed a `HybridAnswer` carrying the question plus the decision's route
 *      and reasoning.
 *   3. Dispatch based on the route: call `sqlAnswer()` when the route covers SQL
 *      ("sql"/"both") and `ragAnswer()` when it covers knowledge
 *      ("vector"/"both"), storing each into the matching field.
 *   4. Return the answer (an "unknown" route leaves both result fields unset).
 */
export async function routeAndAnswer(
  question: string,
  provider: ReturnType<typeof getProvider>
): Promise<HybridAnswer> {
  // TODO: implement routeAndAnswer().
  throw new Error("TODO: implement routeAndAnswer()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

const TEST_QUESTIONS = [
  // Should route to SQL
  "How many orders were placed in Q1 2024?",
  "What is the average order value per region?",
  // Should route to vector / RAG
  "What is retrieval-augmented generation and how does it reduce hallucination?",
  "What is HNSW and why do vector databases use it?",
  // Ambiguous — might route to "both"
  "What products does the top-spending customer buy, and how does RAG help personalise recommendations?",
];

async function main() {
  if (!existsSync(DB_PATH)) {
    console.error(`Database not found: ${DB_PATH}`);
    console.error("Run `pnpm tsx modules/12-text-to-sql/ts/seed-db.ts` first.");
    process.exit(1);
  }

  const provider = getProvider();
  console.log(`\nProvider: ${provider.name}  |  Model: ${provider.chatModel}\n`);

  for (const q of TEST_QUESTIONS) {
    console.log(`Q: ${q}`);
    const answer = await routeAndAnswer(q, provider);
    console.log(`   Route    : ${answer.route}`);
    console.log(`   Reasoning: ${answer.reasoning}`);
    if (answer.sqlResult) {
      console.log(`   SQL      : ${answer.sqlResult.sql}`);
      for (const row of answer.sqlResult.rows.slice(0, 3)) {
        console.log(`   Row      : ${JSON.stringify(row)}`);
      }
    }
    if (answer.ragResult) {
      const preview = answer.ragResult.slice(0, 200).replace(/\n/g, " ");
      console.log(`   RAG      : ${preview}...`);
    }
    console.log();
  }

  console.log("Key insight: SQL excels at exact aggregations and filters over");
  console.log("structured tables; RAG excels at open-ended knowledge questions.");
  console.log("A router lets you serve both from one interface.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
