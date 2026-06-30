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
 *   1. const scores = await Promise.all(chunks.map(async (chunk) => {
 *        const messages: ChatMessage[] = [
 *          { role: "system", content: "You are a retrieval evaluator. Output ONLY a number between 0 and 1 for how well the passage helps answer the question." },
 *          { role: "user", content: `Question: ${query}\nPassage: ${chunk.text}\nRelevance (0-1):` },
 *        ];
 *        const r = await provider.chat(messages, { temperature: 0, maxTokens: 5 });
 *        const n = parseFloat(r.text.trim());
 *        return Number.isNaN(n) ? 0 : Math.min(1, Math.max(0, n));
 *      }));
 *   2. const max = scores.length ? Math.max(...scores) : 0;
 *      verdict = max >= 0.7 ? "Correct" : max < 0.3 ? "Incorrect" : "Ambiguous";
 *   3. return { scores, verdict };
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
 *   const messages: ChatMessage[] = [
 *     { role: "system", content: "Rewrite the user's question into a concise web search query. Output only the query." },
 *     { role: "user", content: query },
 *   ];
 *   const r = await provider.chat(messages, { temperature: 0, maxTokens: 30 });
 *   return r.text.trim();
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
  // TODO: implement correctiveRag().
  //   const chunks = lexicalRetrieve(query, corpus, 2);
  //   const grade = await gradeRetrieval(query, chunks, provider);
  //   ...branch on grade.verdict to build `context` + `branch`...
  //   const answer = await generate(query, context, provider);
  //   return { answer, verdict: grade.verdict, branch, contextUsed: context };
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
