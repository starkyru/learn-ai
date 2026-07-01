/**
 * Task 2 🟡 — Corrective RAG (CRAG, Yan et al. 2024).
 *
 * What you'll learn:
 *   - Why "retrieved" must not be trusted as "relevant"
 *   - How a retrieval evaluator grades chunks into Correct / Incorrect / Ambiguous
 *   - How to self-correct: rewrite the query and fall back instead of hallucinating
 *
 * How to run:
 *   pnpm tsx modules/05b-advanced-rag/ts/02-corrective-rag.ts
 *   (chat-only — works on ANY provider, including anthropic)
 *
 * A simple lexical retriever (provided) stands in for the index so the lesson is
 * the correction loop. Fill in the three TODO functions.
 */

import { getProvider, type ChatMessage } from "@learn-ai/llm-core";

type Provider = ReturnType<typeof getProvider>;

// ---------------------------------------------------------------------------
// Tiny corpus + provided lexical retriever (a black box here)
// ---------------------------------------------------------------------------

interface Chunk {
  id: string;
  text: string;
}

const CORPUS: Chunk[] = [
  {
    id: "photosynth",
    text: "Photosynthesis converts light energy into chemical energy stored in glucose. It happens in the chloroplasts of plant cells.",
  },
  {
    id: "mitochondria",
    text: "Mitochondria are the powerhouse of the cell, producing ATP through cellular respiration.",
  },
  {
    id: "water-cycle",
    text: "The water cycle moves water through evaporation, condensation, and precipitation across the Earth.",
  },
  {
    id: "dna",
    text: "DNA stores genetic information in sequences of four nucleotide bases: adenine, thymine, guanine, and cytosine.",
  },
];

function tokens(s: string): string[] {
  return s.toLowerCase().match(/[a-z0-9]+/g) ?? [];
}

function lexicalRetrieve(query: string, corpus: Chunk[], k = 2): Chunk[] {
  // Crude on purpose: it WILL return weakly-related chunks for off-topic queries,
  // which is exactly what CRAG must catch.
  const q = new Set(tokens(query));
  return corpus
    .map((c) => ({ c, overlap: tokens(c.text).filter((t) => q.has(t)).length }))
    .sort((a, b) => b.overlap - a.overlap)
    .slice(0, k)
    .map((x) => x.c);
}

function webSearchStub(query: string): string {
  // In a real system this is a web search / API call; here it's deterministic.
  return (
    `[external source for '${query}']: The Eiffel Tower is a wrought-iron lattice ` +
    "tower in Paris, France, completed in 1889 and standing 330 metres tall."
  );
}

// ---------------------------------------------------------------------------
// TODO 1: grade retrieval
// ---------------------------------------------------------------------------

interface Grade {
  scores: number[];
  verdict: "Correct" | "Incorrect" | "Ambiguous";
}

/**
 * Score each chunk's relevance (0..1) with the LLM, then bucket MAX score:
 *   max >= 0.7 -> "Correct"  |  max < 0.3 -> "Incorrect"  |  else "Ambiguous"
 *
 * TODO: implement this.
 *
 * Steps:
 *   1. Score every chunk in parallel with `Promise.all`. For each chunk build a
 *      `ChatMessage[]`: a system message telling the model to act as a retrieval
 *      evaluator and output ONLY a number between 0 and 1 for how well the passage
 *      helps answer the question, and a user message carrying the query and the chunk
 *      text. Call `provider.chat(messages, { temperature: 0, maxTokens: ... })`, then
 *      parseFloat the reply, coerce NaN to 0, and clamp into [0, 1].
 *   2. Take the MAX score (0 if no chunks) and apply the buckets above to get the
 *      verdict.
 *   3. Return the { scores, verdict } Grade.
 */
async function gradeRetrieval(
  query: string,
  chunks: Chunk[],
  provider: Provider,
): Promise<Grade> {
  // TODO: implement gradeRetrieval().
  throw new Error("TODO: implement gradeRetrieval()");
}

// ---------------------------------------------------------------------------
// TODO 2: rewrite the query for the fallback search
// ---------------------------------------------------------------------------

/**
 * Turn the user's question into a clean standalone search query.
 *
 * TODO: implement this.
 *   - Build a `ChatMessage[]`: a system message asking the model to rewrite the user's
 *     question into a concise web search query and output only the query, plus a user
 *     message with the query.
 *   - Call `provider.chat(messages, { temperature: 0, maxTokens: ... })` (a short cap).
 *   - Return the reply text, trimmed.
 */
async function rewriteQuery(query: string, provider: Provider): Promise<string> {
  // TODO: implement rewriteQuery().
  throw new Error("TODO: implement rewriteQuery()");
}

// ---------------------------------------------------------------------------
// TODO 3: the corrective loop
// ---------------------------------------------------------------------------

interface CragResult {
  answer: string;
  verdict: string;
  branch: "kept-chunks" | "fallback" | "both";
  contextUsed: string;
}

async function generate(
  query: string,
  context: string,
  provider: Provider,
): Promise<string> {
  // Provided: answer grounded in context.
  const messages: ChatMessage[] = [
    {
      role: "system",
      content:
        "Answer the question using ONLY the context. If the context is insufficient, say so.",
    },
    { role: "user", content: `Context:\n${context}\n\nQuestion: ${query}` },
  ];
  return (
    await provider.chat(messages, { temperature: 0, maxTokens: 200 })
  ).text.trim();
}

/**
 * Wire the CRAG loop:
 *   retrieve -> grade -> {
 *     Correct:   generate from kept chunks                (branch "kept-chunks")
 *     Incorrect: rewrite -> webSearchStub -> generate     (branch "fallback")
 *     Ambiguous: chunks + fallback, then generate          (branch "both")
 *   }
 *
 * TODO: implement this.
 */
async function correctiveRag(
  query: string,
  corpus: Chunk[],
  provider: Provider,
): Promise<CragResult> {
  // TODO: implement correctiveRag(), returning a CragResult.
  //   - Retrieve with lexicalRetrieve(), then gradeRetrieval() to get the verdict.
  //   - Branch on the verdict to assemble `context` and the `branch` label per the
  //     table above (Correct: kept chunk texts; Incorrect: rewriteQuery() then
  //     webSearchStub(); Ambiguous: both merged).
  //   - generate() the answer over that context and return it with the verdict,
  //     branch, and the context you used.
  throw new Error("TODO: implement correctiveRag()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  const provider = getProvider();
  console.log(`\nProvider: ${provider.name}\n`);

  const queries = [
    "What do mitochondria do in a cell?", // in corpus     -> Correct
    "How tall is the Eiffel Tower?", // NOT in corpus -> Incorrect -> fallback
  ];

  for (const q of queries) {
    console.log(`\nQuery: "${q}"`);
    const result = await correctiveRag(q, CORPUS, provider);
    console.log(`  verdict=${result.verdict}  branch=${result.branch}`);
    console.log(`  answer: ${result.answer.slice(0, 200)}`);
  }

  console.log(
    "\nReflection: the biology query should grade Correct and stay in-corpus; the " +
      "Eiffel Tower query should grade Incorrect and trigger the fallback instead " +
      "of hallucinating over unrelated biology chunks.",
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
