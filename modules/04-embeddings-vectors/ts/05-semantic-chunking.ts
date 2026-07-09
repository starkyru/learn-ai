/**
 * Task 5 🟡 — Semantic chunking.
 *
 * What you'll learn:
 *   - Fixed/sentence/overlap chunkers (Task 3) ignore *meaning* — they cut at a
 *     character count or a sentence count, so one chunk can straddle two topics.
 *   - Semantic chunking places boundaries where the *topic shifts*: embed each
 *     sentence, walk the document, and start a new chunk wherever consecutive
 *     sentences become embedding-distant (a "semantic breakpoint").
 *   - How a percentile threshold turns a noisy distance signal into breakpoints
 *     without hand-tuning an absolute cutoff per corpus.
 *
 * How to run:
 *   pnpm tsx modules/04-embeddings-vectors/ts/05-semantic-chunking.ts
 *
 * Needs an embedding provider (LLM_PROVIDER=openai|ollama|nvidia|lmstudio|gemini;
 * NOT anthropic — it has no embed()).
 */

import { getProvider } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Sample document — two clearly different topics glued together, so a good
// semantic chunker should place a boundary near the topic switch.
// ---------------------------------------------------------------------------

const DOC = `
The espresso machine forces near-boiling water through finely ground coffee
under nine bars of pressure. The result is a concentrated shot topped with
crema, the reddish-brown foam of emulsified oils. Grind size is the single
biggest lever: too coarse and the water rushes through sour and thin, too fine
and it chokes, over-extracting into bitterness. Baristas dial in a shot by
tasting and adjusting the grind until the flow takes roughly 25 to 30 seconds.

The transit protocol assigns each train a movement authority: a block of track
it may occupy exclusively. Signals at block boundaries turn red once a train
enters, and only clear again after it has left and the block is proven vacant.
This fixed-block scheme trades capacity for safety, because a whole block is
reserved even when the train occupies a few metres of it. Modern moving-block
systems shrink that reservation to a safety envelope around the train itself,
letting trains run far closer together.
`.trim();

// ---------------------------------------------------------------------------
// Sentence splitting (provided) — reused from Task 3's heuristic.
// ---------------------------------------------------------------------------

function splitSentences(text: string): string[] {
  return text
    .replace(/\n/g, " ")
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

function cosine(a: number[], b: number[]): number {
  let dot = 0,
    magA = 0,
    magB = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    magA += a[i] * a[i];
    magB += b[i] * b[i];
  }
  const denom = Math.sqrt(magA) * Math.sqrt(magB);
  return denom === 0 ? 0 : dot / denom;
}

// ---------------------------------------------------------------------------
// Semantic chunking — implement this
// ---------------------------------------------------------------------------

/**
 * Return the p-th percentile (0–100) of `values` via linear interpolation.
 *
 * TODO: implement this helper.
 *
 * Steps:
 *   1. Sort a copy of `values` ascending.
 *   2. Map p to a fractional rank: `rank = (p / 100) * (len - 1)`.
 *   3. Interpolate between the two neighbouring sorted samples
 *      (`floor(rank)` and `ceil(rank)`) by the fractional part of `rank`.
 *
 * Edge case: a single-element array returns that element.
 */
export function percentile(values: number[], p: number): number {
  throw new Error("TODO: implement percentile()");
}

/**
 * Chunk `text` at semantic breakpoints.
 *
 * A breakpoint sits *between* sentence i and i+1 when the two are unusually
 * embedding-distant — i.e. the topic just shifted.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. splitSentences(text). If ≤ 1, return [text].
 *   2. Embed ALL sentences in one `provider.embed(sentences)` call; use
 *      `.vectors`.
 *   3. For each adjacent pair (i, i+1), compute a *distance*
 *      `1 - cosine(v[i], v[i+1])`. You get `sentences.length - 1` distances.
 *   4. Threshold: `t = percentile(distances, breakpointPercentile)`. Any gap
 *      with distance > t is a breakpoint (start a new chunk after sentence i).
 *   5. Walk the sentences, accumulating into the current chunk; when you hit a
 *      breakpoint index, flush the accumulated sentences (joined with " ") and
 *      start fresh. Flush the trailing chunk at the end.
 *
 * Return: array of chunk strings. A higher percentile ⇒ fewer, larger chunks.
 */
export async function semanticChunks(
  text: string,
  provider: ReturnType<typeof getProvider>,
  breakpointPercentile = 90,
): Promise<string[]> {
  throw new Error("TODO: implement semanticChunks()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

function fixedSentenceBaseline(text: string, perChunk = 3): string[] {
  const sents = splitSentences(text);
  const out: string[] = [];
  for (let i = 0; i < sents.length; i += perChunk) {
    out.push(sents.slice(i, i + perChunk).join(" "));
  }
  return out;
}

function show(name: string, chunks: string[]): void {
  console.log(`\n[${name}] ${chunks.length} chunks`);
  chunks.forEach((c, i) => {
    console.log(`  ${i}: "${c.slice(0, 90)}${c.length > 90 ? "…" : ""}"`);
  });
}

async function main() {
  const provider = getProvider();
  console.log(`\nProvider: ${provider.name} | embed model: ${provider.embedModel}`);

  show("fixed 3-sentence baseline", fixedSentenceBaseline(DOC, 3));
  show("semantic", await semanticChunks(DOC, provider, 90));

  console.log("\nReflection:");
  console.log(
    "  1. Did the semantic chunker put a boundary at the coffee→trains switch?",
  );
  console.log("  2. Raise breakpointPercentile to 95 — do you get fewer chunks?");
  console.log("  3. Where would fixed-size chunking have split mid-topic?");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
