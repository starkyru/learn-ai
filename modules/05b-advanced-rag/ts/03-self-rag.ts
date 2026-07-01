/**
 * Task 3 🟡 — Self-RAG (Asai et al. 2023), reflection tokens emulated.
 *
 * What you'll learn:
 *   - Adaptive retrieval: let the model decide whether to retrieve at all
 *   - Relevance filtering (IsRel) and support-checking (IsSup) as gates
 *   - CRAG grades retrieval; Self-RAG also gates retrieval AND critiques generation
 *
 * How to run:
 *   pnpm tsx modules/05b-advanced-rag/ts/03-self-rag.ts
 *   (chat-only — works on ANY provider, including anthropic)
 *
 * The real Self-RAG trains a model to emit reflection tokens. We emulate each
 * token with a prompted LLM-as-judge call. Fill in the four TODO functions.
 */

import { getProvider, type ChatMessage } from "@learn-ai/llm-core";

type Provider = ReturnType<typeof getProvider>;

// ---------------------------------------------------------------------------
// Tiny corpus + provided lexical retriever
// ---------------------------------------------------------------------------

interface Chunk {
  id: string;
  text: string;
}

const CORPUS: Chunk[] = [
  {
    id: "churn",
    text: "In Q3, customer churn rose to 5.2%, driven mainly by the small-business segment after a price increase.",
  },
  {
    id: "hiring",
    text: "The company hired 40 new engineers in Q3, expanding the platform team.",
  },
  { id: "revenue", text: "Q3 revenue was 12 million dollars, up 8% from Q2." },
  {
    id: "office",
    text: "The new headquarters in Berlin opened in September with space for 300 staff.",
  },
];

function tokens(s: string): string[] {
  return s.toLowerCase().match(/[a-z0-9]+/g) ?? [];
}

function lexicalRetrieve(query: string, corpus: Chunk[], k = 3): Chunk[] {
  const q = new Set(tokens(query));
  const ranked = corpus
    .map((c) => ({ c, overlap: tokens(c.text).filter((t) => q.has(t)).length }))
    .sort((a, b) => b.overlap - a.overlap);
  const hits = ranked
    .filter((x) => x.overlap > 0)
    .slice(0, k)
    .map((x) => x.c);
  return hits.length ? hits : corpus.slice(0, k);
}

function isYes(text: string): boolean {
  const t = text.trim().toLowerCase();
  return t.startsWith("y") || t.startsWith("true") || t.startsWith("1");
}

// ---------------------------------------------------------------------------
// TODO 1: the Retrieve token — do we need retrieval at all?
// ---------------------------------------------------------------------------

/**
 * Decide whether the query needs external/document knowledge.
 * "What is 17 * 23?" -> false ; "What did the Q3 report say?" -> true.
 *
 * TODO: implement this.
 *   - Make ONE yes/no LLM-as-judge call. Build a `ChatMessage[]`: a system message
 *     telling the model to reply only yes/no about whether answering needs external
 *     documents (closed-book facts, math, and general reasoning do NOT), and a user
 *     message with the query.
 *   - Call `provider.chat(messages, { temperature: 0, maxTokens: ... })` (a tiny cap).
 *   - Convert the reply to a boolean with the provided `isYes()` helper.
 */
async function shouldRetrieve(query: string, provider: Provider): Promise<boolean> {
  // TODO: implement shouldRetrieve().
  throw new Error("TODO: implement shouldRetrieve()");
}

// ---------------------------------------------------------------------------
// TODO 2: the IsRel token — keep only relevant passages
// ---------------------------------------------------------------------------

/**
 * Return only the chunks relevant to the query.
 *
 * TODO: implement this.
 *   - Ask one yes/no judgement PER chunk, in parallel with `Promise.all`. For each
 *     chunk build a `ChatMessage[]`: a system message asking only yes/no whether the
 *     passage is relevant to the question, and a user message carrying the query plus
 *     that chunk's text.
 *   - Use `provider.chat(messages, { temperature: 0, maxTokens: ... })`.
 *   - Keep a chunk when `isYes()` of its reply, and return the surviving chunks.
 */
async function gradeRelevance(
  query: string,
  chunks: Chunk[],
  provider: Provider,
): Promise<Chunk[]> {
  // TODO: implement gradeRelevance().
  throw new Error("TODO: implement gradeRelevance()");
}

// ---------------------------------------------------------------------------
// TODO 3: the IsSup token — is the answer supported by the passages?
// ---------------------------------------------------------------------------

type Support = "fully" | "partially" | "no";

/**
 * Judge whether `answer` is supported by the kept passages.
 *
 * TODO: implement this.
 *   - Join the kept chunk texts into one context string.
 *   - Build a `ChatMessage[]`: a system message telling the model to judge how well
 *     the ANSWER is supported by the CONTEXT and reply with exactly one word —
 *     fully, partially, or no — and a user message carrying the context and answer.
 *   - Call `provider.chat(messages, { temperature: 0, maxTokens: ... })` (a few tokens).
 *   - Normalise the reply to one of "fully" | "partially" | "no", defaulting to "no".
 */
async function gradeSupport(
  answer: string,
  chunks: Chunk[],
  provider: Provider,
): Promise<Support> {
  // TODO: implement gradeSupport().
  throw new Error("TODO: implement gradeSupport()");
}

// ---------------------------------------------------------------------------
// TODO 4: wire the Self-RAG loop
// ---------------------------------------------------------------------------

interface SelfRagResult {
  answer: string;
  retrieved: boolean;
  keptChunkIds: string[];
  support: Support | "n/a";
}

async function generate(
  query: string,
  context: string | null,
  provider: Provider,
): Promise<string> {
  // Provided: answer with context if given, else closed-book.
  const messages: ChatMessage[] = context
    ? [
        { role: "system", content: "Answer the question using the context." },
        { role: "user", content: `Context:\n${context}\n\nQuestion: ${query}` },
      ]
    : [
        { role: "system", content: "Answer the question directly and concisely." },
        { role: "user", content: query },
      ];
  return (
    await provider.chat(messages, { temperature: 0, maxTokens: 200 })
  ).text.trim();
}

/**
 * Self-RAG control flow:
 *   shouldRetrieve? --no--> generate closed-book (support "n/a")
 *                   --yes-> retrieve -> gradeRelevance (IsRel) -> generate ->
 *                           gradeSupport (IsSup) -> surface verdict
 *
 * TODO: implement this.
 */
async function selfRag(
  query: string,
  corpus: Chunk[],
  provider: Provider,
): Promise<SelfRagResult> {
  // TODO: implement selfRag(), returning a SelfRagResult.
  //   - If shouldRetrieve() says no: generate closed-book (pass null context) and
  //     return with retrieved:false, no kept ids, and support "n/a".
  //   - Otherwise: retrieve with lexicalRetrieve(), filter with gradeRelevance(),
  //     generate() over the kept chunks' joined text, then gradeSupport() the answer.
  //     Return retrieved:true with the kept chunk ids and the support verdict.
  throw new Error("TODO: implement selfRag()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  const provider = getProvider();
  console.log(`\nProvider: ${provider.name}\n`);

  const queries = [
    "What is 17 times 23?", // closed-book -> Retrieve=No
    "What did the Q3 report say about customer churn?", // corpus -> full loop
  ];

  for (const q of queries) {
    console.log(`\nQuery: "${q}"`);
    const result = await selfRag(q, CORPUS, provider);
    console.log(`  Retrieve=${result.retrieved ? "Yes" : "No"}`);
    if (result.retrieved) {
      console.log(`  kept (IsRel) = [${result.keptChunkIds.join(", ")}]`);
      console.log(`  IsSup = ${result.support}`);
    }
    console.log(`  answer: ${result.answer.slice(0, 200)}`);
  }

  console.log(
    "\nReflection: the arithmetic query should skip retrieval entirely; the churn " +
      "query should retrieve, drop the off-topic chunks (hiring/revenue), and report " +
      "whether the answer is actually supported.",
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
