/**
 * bpe.ts — a Byte-Pair Encoding tokenizer from scratch (Task 1, 🔴 WORKED).
 *
 * What it teaches:
 *   What a "token" actually is. We build BPE from the byte level up: start with
 *   256 base tokens (one per possible byte), then repeatedly merge the most
 *   frequent adjacent pair into a brand-new token id. encode() applies those
 *   learned merges; decode() reverses them. Because we start from raw UTF-8
 *   bytes, EVERY possible string is representable — there is no "unknown token".
 *
 *   No external tokenizer library is used. (The Python sibling, bpe.py, shows an
 *   optional tiktoken comparison; in TS we keep it pure.)
 *
 * How to run (from the repo root):
 *   pnpm tsx modules/01-fundamentals/ts/bpe.ts
 *
 * Key invariant (what makes it a tokenizer and not a lossy hash):
 *   decode(encode(s)) === s   for every string s.
 */

// A pair of token ids, keyed in a Map as the string "a,b" (Maps can't key on
// arrays by value). Base ids 0..255 are raw bytes; ids >= 256 are merged pairs.
type Pair = [number, number];

const pairKey = (a: number, b: number): string => `${a},${b}`;

// A tiny corpus, inline so the file is self-contained. Repetition is on purpose:
// BPE learns by merging FREQUENT pairs, so repeated substrings give the trainer
// something to merge.
export const CORPUS =
  "the quick brown fox jumps over the lazy dog. " +
  "tokenization turns text into tokens. tokens are the units a model reads. " +
  "byte pair encoding merges the most frequent pair, again and again. " +
  "the model reads tokens, the model predicts tokens, the model is a token machine. " +
  "reading and writing and reading and writing builds intuition. ";

const utf8Encoder = new TextEncoder();
const utf8Decoder = new TextDecoder("utf-8");

/** Count every adjacent pair of ids. For [1,2,3,2,3] -> {"2,3": 2, ...}. */
function getStats(ids: number[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (let i = 0; i < ids.length - 1; i++) {
    const key = pairKey(ids[i], ids[i + 1]);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return counts;
}

/** Replace every occurrence of `pair` in `ids` with `newId`. */
function merge(ids: number[], pair: Pair, newId: number): number[] {
  const out: number[] = [];
  let i = 0;
  while (i < ids.length) {
    if (i < ids.length - 1 && ids[i] === pair[0] && ids[i + 1] === pair[1]) {
      out.push(newId);
      i += 2;
    } else {
      out.push(ids[i]);
      i += 1;
    }
  }
  return out;
}

export class BPETokenizer {
  /** Ordered list of learned merges; index = learn order = re-apply order. */
  readonly merges: { pair: Pair; newId: number }[] = [];
  /** id -> the byte sequence it expands to, so decode() can reconstruct bytes. */
  private vocab = new Map<number, number[]>();

  constructor() {
    // Base vocabulary: ids 0..255 map to the single byte with that value.
    for (let i = 0; i < 256; i++) this.vocab.set(i, [i]);
  }

  /** Learn `numMerges` merges from `text`. */
  train(text: string, numMerges: number): void {
    // Start from raw UTF-8 bytes -> base ids (no unknowns possible).
    let ids = Array.from(utf8Encoder.encode(text));

    for (let i = 0; i < numMerges; i++) {
      const stats = getStats(ids);
      if (stats.size === 0) break; // collapsed to one token

      // Pick the most frequent pair. Ties broken by the pair key, so training
      // is deterministic (same corpus -> same merges every run).
      let bestKey = "";
      let bestCount = 0;
      for (const [key, count] of stats) {
        if (count > bestCount || (count === bestCount && key < bestKey)) {
          bestCount = count;
          bestKey = key;
        }
      }
      if (bestCount < 2) break; // nothing repeats; further merges memorise noise

      const [a, b] = bestKey.split(",").map(Number) as Pair;
      const newId = 256 + i;
      this.merges.push({ pair: [a, b], newId });
      // The new token's bytes = its two parts' bytes concatenated.
      this.vocab.set(newId, [...this.vocab.get(a)!, ...this.vocab.get(b)!]);
      ids = merge(ids, [a, b], newId);
    }
  }

  /** Turn a string into token ids by re-applying merges in learn order. */
  encode(text: string): number[] {
    let ids = Array.from(utf8Encoder.encode(text));
    for (const { pair, newId } of this.merges) {
      ids = merge(ids, pair, newId);
    }
    return ids;
  }

  /** Turn token ids back into the original string. */
  decode(ids: number[]): string {
    const bytes: number[] = [];
    for (const id of ids) bytes.push(...this.vocab.get(id)!);
    return utf8Decoder.decode(new Uint8Array(bytes));
  }

  get vocabSize(): number {
    return this.vocab.size;
  }
}

function main(): void {
  const tok = new BPETokenizer();
  tok.train(CORPUS, 50);

  const sample = "the model reads tokens";
  const ids = tok.encode(sample);
  const back = tok.decode(ids);

  console.log(
    `Trained vocab size : ${tok.vocabSize} (256 base + ${tok.merges.length} merges)`,
  );
  console.log(`Sample             : ${JSON.stringify(sample)}`);
  console.log(`Encoded (${ids.length} ids)    : [${ids.join(", ")}]`);
  console.log(`Decoded            : ${JSON.stringify(back)}`);
  console.log(`Round-trips losslessly: ${back === sample}`);

  const rawBytes = utf8Encoder.encode(sample).length;
  console.log(`\nRaw UTF-8 bytes    : ${rawBytes}`);
  console.log(`BPE tokens         : ${ids.length}  (fewer = better compression)`);

  // Prove byte-level handling is lossless for unseen / Unicode input.
  const tricky = "café — 日本語 😀";
  const ok = tok.decode(tok.encode(tricky)) === tricky;
  console.log(`\nUnseen/Unicode round-trip OK: ${ok} (${JSON.stringify(tricky)})`);
}

// Run only when invoked directly (so the test file can import without executing).
// tsx sets import.meta.url to the entry file's URL.
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
