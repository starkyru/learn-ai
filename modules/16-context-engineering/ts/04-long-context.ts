/**
 * Task 4 — Long-context strategies 🟡
 *
 * What this teaches:
 *   - Even with a 200 K context window, fitting an entire corpus wastes tokens and
 *     often degrades quality due to the "lost in the middle" effect.
 *   - Map-reduce: process each chunk independently (map), then synthesise (reduce).
 *   - Refine: iteratively update an interim answer as each new chunk is processed.
 *   - Lost in the middle: LLMs recall facts near the start and end of context
 *     reliably; facts in the middle are frequently forgotten.
 *
 * How to run:
 *   pnpm tsx modules/16-context-engineering/ts/04-long-context.ts
 */

import "dotenv/config";
import { getProvider, ChatMessage, ChatOptions } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Rough token counter (replace with tiktoken from Task 1 for precision).
// ---------------------------------------------------------------------------
function countTokens(text: string): number {
  return Math.ceil(text.split(/\s+/).length * 1.3);
}

// ---------------------------------------------------------------------------
// Long document with unique facts planted at start, middle, and middle-late.
// ---------------------------------------------------------------------------
const SECTION_A = `
## Section A: History of the Internet

The internet evolved from ARPANET, a research network funded by the U.S. Department of
Defense in the late 1960s. The first message sent over ARPANET was "LO" — the system
crashed after two letters of "LOGIN". By the 1980s, the TCP/IP protocol suite became the
standard, laying the foundation for the modern internet.

UNIQUE FACT ALPHA: The ARPANET had exactly 4 nodes when it first went live on October 29, 1969.

The World Wide Web was invented by Tim Berners-Lee at CERN in 1989. The first website went
live on August 6, 1991.
`.trim();

const SECTION_B = `
## Section B: How Search Engines Work

Search engines crawl the web using automated programs called spiders or bots. PageRank,
invented by Larry Page and Sergey Brin at Stanford, ranks pages by counting how many other
pages link to them, weighted by the importance of the linking page.

UNIQUE FACT BETA: Google processed its first 1 billion search queries in a single day on August 16, 2012.

Modern search engines use machine learning extensively. BERT (2019) and MUM (2021) allow
Google to understand the intent behind queries rather than matching keywords literally.
`.trim();

const SECTION_C = `
## Section C: The Rise of Social Media

Social media transformed how humans communicate and form communities online. Friendster
launched in 2002, MySpace in 2003, Facebook in 2004, Twitter in 2006, Instagram in 2010,
and TikTok (as Douyin in China) in 2016.

UNIQUE FACT GAMMA: Instagram was acquired by Facebook (now Meta) for approximately $1 billion
in April 2012, making it one of the largest acquisitions of a startup with fewer than 20 employees.

Network effects are central to social media: the value of a platform grows roughly with the
square of the number of users (Metcalfe's Law).
`.trim();

const SECTION_D = `
## Section D: AI and the Future Web

Artificial intelligence is reshaping every layer of the internet stack. Large language models
generate text, images, code, and audio at a quality indistinguishable from human output in
many domains. Recommendation systems powered by deep learning drive the majority of content
consumed on social platforms, streaming services, and e-commerce sites.

The semantic web vision is finally becoming practical through LLMs and structured knowledge
graphs. Conversational interfaces are replacing search boxes as the primary way humans
extract information from the internet.
`.trim();

const LONG_DOCUMENT = [SECTION_A, SECTION_B, SECTION_C, SECTION_D].join("\n\n");

const MAX_TOKENS_PER_CHUNK = 350;

const RECALL_QUESTIONS: Array<[string, string]> = [
  ["ALPHA (start)",  "How many nodes did ARPANET have when it first went live?"],
  ["BETA  (middle)", "On what date did Google process its first 1 billion search queries in a day?"],
  ["GAMMA (middle)", "How much did Facebook pay to acquire Instagram?"],
];

const SUMMARY_QUESTION = "What are the three most important facts in the document?";

// ---------------------------------------------------------------------------
// TODO 1: Implement splitIntoChunks.
//         Split `text` into chunks of at most `maxTokens` tokens each.
//         Split at word boundaries — do not cut mid-word.
//         Return an array of non-empty chunk strings.
// ---------------------------------------------------------------------------
function splitIntoChunks(text: string, maxTokens = MAX_TOKENS_PER_CHUNK): string[] {
  // TODO: implement — use countTokens to check each candidate chunk
  const words = text.split(/\s+/);
  const chunks: string[] = [];
  let current: string[] = [];
  let currentTokens = 0;
  for (const word of words) {
    const wordTokens = countTokens(word);
    if (current.length > 0 && currentTokens + wordTokens > maxTokens) {
      chunks.push(current.join(" "));
      current = [word];
      currentTokens = wordTokens;
    } else {
      current.push(word);
      currentTokens += wordTokens;
    }
  }
  if (current.length > 0) chunks.push(current.join(" "));
  return chunks;
}

// ---------------------------------------------------------------------------
// TODO 2: Implement mapReduce.
//         MAP: for each chunk, call the LLM with:
//           "Based only on this excerpt, answer: {question}\nExcerpt: {chunk}"
//         Collect mini-answers.
//         REDUCE: combine mini-answers into one final answer with one LLM call.
// ---------------------------------------------------------------------------
async function mapReduce(
  chunks: string[],
  question: string,
  llm: ReturnType<typeof getProvider>,
): Promise<string> {
  // TODO: implement
  // const miniAnswers: string[] = [];
  // for (const chunk of chunks) {
  //   const prompt = `Based only on this excerpt, answer the question: ${question}\nExcerpt:\n${chunk}`;
  //   const result = await llm.chat([{ role: "user", content: prompt }], { temperature: 0 });
  //   miniAnswers.push(result.text.trim());
  // }
  // const combined = miniAnswers.join("\n---\n");
  // const reducePrompt =
  //   `Original question: ${question}\n\n` +
  //   `Partial answers from different sections:\n${combined}\n\n` +
  //   "Synthesise these into one final, coherent answer.";
  // const final = await llm.chat([{ role: "user", content: reducePrompt }], { temperature: 0 });
  // return final.text;
  throw new Error("TODO: implement mapReduce");
}

// ---------------------------------------------------------------------------
// TODO 3: Implement refine.
//         Start with an empty interim answer.
//         For each chunk, update the interim:
//           "Refine the current answer using any new information in this excerpt.
//            Question: {question}
//            Current answer: {interim}
//            New excerpt: {chunk}"
//         Return the final interim after all chunks.
// ---------------------------------------------------------------------------
async function refine(
  chunks: string[],
  question: string,
  llm: ReturnType<typeof getProvider>,
): Promise<string> {
  // TODO: implement
  // let interim = "No answer yet.";
  // for (const chunk of chunks) {
  //   const prompt =
  //     `Refine the current answer using any new information in the excerpt.\n` +
  //     `Question: ${question}\n` +
  //     `Current answer: ${interim}\n` +
  //     `New excerpt:\n${chunk}`;
  //   const result = await llm.chat([{ role: "user", content: prompt }], { temperature: 0 });
  //   interim = result.text.trim();
  // }
  // return interim;
  throw new Error("TODO: implement refine");
}

async function main() {
  console.log("=== Task 4: Long-Context Strategies ===\n");

  const chunks = splitIntoChunks(LONG_DOCUMENT, MAX_TOKENS_PER_CHUNK);
  console.log(`Document: ${countTokens(LONG_DOCUMENT)} tokens → ${chunks.length} chunks (max ${MAX_TOKENS_PER_CHUNK} tokens each)`);
  chunks.forEach((c, i) => console.log(`  Chunk ${i}: ${countTokens(c)} tokens | ${c.slice(0, 60)}...`));

  const llm = getProvider();
  console.log(`\nProvider: ${llm.name} / ${llm.chatModel}\n`);

  // -------------------------------------------------------------------------
  // Part A: Compare map-reduce vs refine on a summary question.
  // -------------------------------------------------------------------------
  console.log("--- Part A: Summary (map-reduce vs refine) ---");
  for (const [strategyName, fn] of [
    ["map-reduce", mapReduce],
    ["refine", refine],
  ] as Array<[string, typeof mapReduce]>) {
    try {
      const answer = await fn(chunks, SUMMARY_QUESTION, llm);
      console.log(`\n[${strategyName}]\n${answer.slice(0, 300)}...`);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      console.log(`\n[${strategyName}] ${msg.startsWith("TODO") ? "TODO: not yet implemented" : "ERROR: " + msg}`);
    }
  }

  // -------------------------------------------------------------------------
  // Part B: Lost in the middle — recall test.
  // -------------------------------------------------------------------------
  console.log("\n--- Part B: Lost in the Middle (recall test) ---");
  console.log(
    "Unique facts are planted in:\n" +
    "  ALPHA  — Section A (start)\n" +
    "  BETA   — Section B (middle)\n" +
    "  GAMMA  — Section C (middle-late)\n"
  );
  console.log("Placement".padEnd(16) + "Strategy".padEnd(14) + "Answer (first 100 chars)");
  console.log("-".repeat(70));

  for (const [label, question] of RECALL_QUESTIONS) {
    for (const [strategyName, fn] of [
      ["map-reduce", mapReduce],
      ["refine", refine],
    ] as Array<[string, typeof mapReduce]>) {
      try {
        const answer = await fn(chunks, question, llm);
        console.log(`${label.padEnd(16)}${strategyName.padEnd(14)}${answer.slice(0, 100)}`);
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        console.log(`${label.padEnd(16)}${strategyName.padEnd(14)}${msg.startsWith("TODO") ? "(TODO: not yet implemented)" : "ERROR: " + msg}`);
      }
    }
  }

  console.log();
  console.log("Observation:");
  console.log("  Facts at the START (ALPHA) and END of the document tend to be recalled best.");
  console.log("  Facts in the MIDDLE (BETA, GAMMA) are more likely to be missed or garbled.");
  console.log("  Map-reduce gives every chunk equal attention; refine may down-weight middle chunks.");
}

main().catch(console.error);
