/**
 * bigram.ts — a count-based bigram "language model" (Task 5, 🟡 optional STUB).
 *
 * What it teaches:
 *   Demystifies "prediction". A language model is just a next-token predictor.
 *   The simplest real one: count how often each token follows each other token,
 *   then generate by sampling the next token from those counts. No neural net,
 *   no attention — yet it IS a language model (a bad one). A transformer is this
 *   same idea with a much longer memory and learned representations.
 *
 * How to run (from the repo root):
 *   pnpm tsx modules/01-fundamentals/ts/bigram.ts
 */

const CORPUS =
  "the cat sat on the mat the cat ran to the dog the dog sat on the log " +
  "the cat and the dog sat on the mat the dog ran to the cat";

/** A tiny seeded PRNG (mulberry32) so generation is reproducible. */
function makeRng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

type Counts = Map<string, Map<string, number>>;

/**
 * Build token -> (next-token -> count) from a token sequence.
 * TODO: walk every adjacent pair (a token and the one right after it) and tally
 *   how often each follower appears after each token, into the nested
 *   `Map<string, Map<string, number>>`. Return it.
 */
function buildBigramCounts(_tokens: string[]): Counts {
  throw new Error("Count token -> next-token frequencies — see the TODO.");
}

/**
 * Sample the next token given the current one, weighted by counts.
 * TODO:
 *   1. Look up the follower counts for `token`. If none (unseen token), fall
 *      back to a random known token from counts.keys().
 *   2. Sample a follower with probability proportional to its count (walk a
 *      cumulative sum against rng() * total).
 */
function predictNext(_counts: Counts, _token: string, _rng: () => number): string {
  throw new Error("Sample the next token from the counts — see the TODOs.");
}

function generate(counts: Counts, start: string, length: number, rng: () => number): string[] {
  const out = [start];
  for (let i = 0; i < length - 1; i++) out.push(predictNext(counts, out[out.length - 1], rng));
  return out;
}

function main(): void {
  const rng = makeRng(0);
  const tokens = CORPUS.split(/\s+/);
  const counts = buildBigramCounts(tokens);

  console.log("Learned followers for 'the':", counts.get("the"));
  console.log();
  console.log("Generated:", generate(counts, "the", 20, rng).join(" "));
  console.log(
    "\nLocally plausible, globally nonsense — because it only remembers the " +
      "PREVIOUS token. Attention is what gives a transformer a longer memory.",
  );
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
