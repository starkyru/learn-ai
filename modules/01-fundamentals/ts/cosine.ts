/**
 * cosine.ts — embeddings & cosine similarity by hand (Task 2, 🟡 WORKED).
 *
 * What it teaches:
 *   Cosine similarity is the engine of semantic search and RAG. We implement it
 *   from first principles (no library), embed ~6 sentences with a real provider,
 *   then print a similarity matrix and a nearest-neighbour ranking so you can
 *   SEE that semantically related sentences score higher.
 *
 * How to run (from the repo root):
 *   pnpm tsx modules/01-fundamentals/ts/cosine.ts
 *
 * Provider note:
 *   Needs an embeddings model. Works out of the box with Ollama:
 *       ollama pull nomic-embed-text
 *   OpenAI and NVIDIA also have embeddings. Anthropic does NOT — Claude has no
 *   embeddings endpoint, so this script forces an embeddings-capable provider if
 *   LLM_PROVIDER is set to anthropic.
 */

// NOTE: the provider client is imported lazily inside main() (dynamic import)
// so that unit tests can import the pure dot/norm/cosine helpers below without
// loading the network client.

// Sentences in three loose topic clusters. Cosine should reveal the clusters:
//   0,1 -> dogs/pets   2,3 -> programming   4,5 -> weather
const SENTENCES = [
  "The dog chased the ball across the park.",
  "My puppy loves to play fetch outside.",
  "Python is a popular programming language.",
  "I write a lot of code in TypeScript and Python.",
  "It is raining heavily and the sky is grey.",
  "The weather today is wet and stormy.",
];

/** Dot product: a·b = Σ aᵢbᵢ. */
export function dot(a: number[], b: number[]): number {
  let sum = 0;
  for (let i = 0; i < a.length; i++) sum += a[i] * b[i];
  return sum;
}

/** Euclidean magnitude (L2 norm): ‖a‖ = √(Σ aᵢ²). */
export function norm(a: number[]): number {
  return Math.sqrt(dot(a, a));
}

/**
 * Cosine similarity: cos(a,b) = (a·b) / (‖a‖‖b‖), in [-1, 1].
 * Compares DIRECTION (meaning), not magnitude. Returns 0 for a zero vector
 * (the angle is otherwise undefined).
 */
export function cosine(a: number[], b: number[]): number {
  const denom = norm(a) * norm(b);
  if (denom === 0) return 0;
  return dot(a, b) / denom;
}

async function pickEmbeddingProvider() {
  const { getProvider } = await import("@learn-ai/llm-core");
  const requested = process.env.LLM_PROVIDER ?? "ollama";
  if (requested === "anthropic") {
    console.log("Anthropic has no embeddings endpoint — falling back to ollama.\n");
    return getProvider("ollama");
  }
  return getProvider();
}

function fmt(n: number): string {
  return (n >= 0 ? "+" : "") + n.toFixed(2);
}

async function main(): Promise<void> {
  const llm = await pickEmbeddingProvider();
  console.log(`Embedding with: ${llm.name} (${llm.embedModel})\n`);

  const { vectors: vecs } = await llm.embed(SENTENCES);
  const n = vecs.length;

  // --- Full similarity matrix ----------------------------------------
  console.log("Cosine similarity matrix (higher = more similar):\n");
  console.log("      " + Array.from({ length: n }, (_, j) => `  s${j} `).join(""));
  for (let i = 0; i < n; i++) {
    const row = Array.from({ length: n }, (_, j) => ` ${fmt(cosine(vecs[i], vecs[j]))}`).join("");
    console.log(`  s${i} ${row}`);
  }

  console.log(
    `\nSelf-similarity cosine(s0, s0) = ${cosine(vecs[0], vecs[0]).toFixed(4)} (expect ~1.0)`,
  );

  // --- Nearest neighbours of one query -------------------------------
  const queryIdx = 0;
  const ranked = Array.from({ length: n }, (_, j) => j)
    .filter((j) => j !== queryIdx)
    .sort((x, y) => cosine(vecs[queryIdx], vecs[y]) - cosine(vecs[queryIdx], vecs[x]));

  console.log(`\nNearest neighbours of s${queryIdx}: "${SENTENCES[queryIdx]}"`);
  ranked.forEach((j, rank) => {
    const sim = cosine(vecs[queryIdx], vecs[j]);
    console.log(`  ${rank + 1}. s${j} (${fmt(sim)})  ${SENTENCES[j]}`);
  });

  console.log(
    "\nNotice: the top neighbour should be the other pet sentence (s1), " +
      "scoring higher than the programming/weather sentences.",
  );
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
