/**
 * Task 2 🟢 — Use a real vector database (ChromaDB).
 *
 * What you'll learn:
 *   - How a production vector DB manages storage, indexing, and querying
 *   - ChromaDB's client/collection API (embedded mode — no server needed)
 *   - How Qdrant differs (HTTP-first, server required — see note at bottom)
 *   - The difference between ephemeral and persistent collections
 *
 * How to run:
 *   pnpm tsx modules/04-embeddings-vectors/ts/02-real-vector-db.ts
 *
 * Dependencies: "chromadb" is declared in this module's package.json.
 * Chroma runs in embedded/in-memory mode — no separate server needed.
 *
 * QDRANT VARIANT: At the bottom of this file there is a commented-out
 * skeleton for Qdrant. To try it:
 *   docker run -p 6333:6333 qdrant/qdrant
 *   QDRANT_URL=http://localhost:6333   # already in .env.example
 *   Then implement the QdrantVariant class.
 */

import { getProvider } from "@learn-ai/llm-core";
// ChromaDB JS client (v1.x API — embedded mode, no server)
import { ChromaClient, Collection } from "chromadb";

// ---------------------------------------------------------------------------
// Inline corpus (same as task 1 — real corpus at data/corpus/ if present)
// ---------------------------------------------------------------------------

interface Document {
  id: string;
  text: string;
  metadata?: Record<string, string | number | boolean>;
}

const CORPUS: Document[] = [
  { id: "doc-1", text: "Embeddings are dense vector representations of text that capture semantic meaning.", metadata: { topic: "embeddings" } },
  { id: "doc-2", text: "Cosine similarity measures the angle between two vectors, ignoring magnitude.", metadata: { topic: "similarity" } },
  { id: "doc-3", text: "A neural network is composed of layers of interconnected nodes called neurons.", metadata: { topic: "neural networks" } },
  { id: "doc-4", text: "Retrieval-Augmented Generation combines search with text generation.", metadata: { topic: "rag" } },
  { id: "doc-5", text: "Approximate nearest neighbour algorithms trade accuracy for huge speed gains.", metadata: { topic: "ann" } },
  { id: "doc-6", text: "Large language models are trained to predict the next token in a sequence.", metadata: { topic: "llm" } },
  { id: "doc-7", text: "Chunking splits long documents into smaller pieces before indexing.", metadata: { topic: "chunking" } },
  { id: "doc-8", text: "BM25 is a classic keyword-based ranking function used in search engines.", metadata: { topic: "bm25" } },
];

// ---------------------------------------------------------------------------
// ChromaDB helper
// ---------------------------------------------------------------------------

/**
 * Upsert documents into a Chroma collection.
 *
 * TODO: Fill in the upsert call.
 *
 * collection.upsert() takes:
 *   { ids: string[], embeddings: number[][], documents: string[], metadatas: object[] }
 *
 * "Upsert" means insert-or-update — safe to call multiple times.
 */
async function indexIntoChroma(
  collection: Collection,
  docs: Document[],
  vectors: number[][]
): Promise<void> {
  // TODO: call collection.upsert({
  //   ids:        docs.map(d => d.id),
  //   embeddings: vectors,
  //   documents:  docs.map(d => d.text),
  //   metadatas:  docs.map(d => d.metadata ?? {}),
  // });
  throw new Error("TODO: implement indexIntoChroma()");
}

/**
 * Query the collection and return top-k results.
 *
 * TODO: call collection.query() and map the response.
 *
 * collection.query() takes { queryEmbeddings, nResults } and returns:
 *   { ids: string[][], documents: string[][], distances: number[][], metadatas: object[][] }
 * (nested arrays because you can pass multiple query vectors at once)
 */
async function queryChroma(
  collection: Collection,
  queryVector: number[],
  k: number = 3
): Promise<Array<{ id: string; score: number; text: string }>> {
  // TODO: const results = await collection.query({
  //   queryEmbeddings: [queryVector],
  //   nResults: k,
  // });
  //
  // Chroma returns `distances` (L2 by default). Convert to a similarity score:
  //   score = 1 / (1 + distance)   — so distance 0 → score 1, distance ∞ → score 0
  //
  // Return: results.ids[0].map((id, i) => ({
  //   id,
  //   score: 1 / (1 + (results.distances![0][i])),
  //   text: results.documents![0][i] ?? "",
  // }));
  throw new Error("TODO: implement queryChroma()");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const provider = getProvider();
  console.log(`\nProvider: ${provider.name} | embed model: ${provider.embedModel}`);

  // ── Embed corpus ──────────────────────────────────────────────────────────
  console.log("\n[1/4] Embedding corpus...");
  const texts = CORPUS.map((d) => d.text);
  const { vectors, model } = await provider.embed(texts);
  console.log(`  ${texts.length} docs → dim ${vectors[0].length} (model: ${model})`);

  // ── Set up Chroma (in-memory / ephemeral) ─────────────────────────────────
  console.log("\n[2/4] Setting up ChromaDB collection...");

  // ChromaClient with no args = ephemeral in-memory mode.
  // For persistence: new ChromaClient({ path: "./chroma-data" })
  const chroma = new ChromaClient();

  const COLLECTION_NAME = "learn-ai-m04";

  // Delete if exists so we start fresh each run
  try {
    await chroma.deleteCollection({ name: COLLECTION_NAME });
  } catch {
    // doesn't exist yet — that's fine
  }

  const collection = await chroma.createCollection({ name: COLLECTION_NAME });
  console.log(`  Collection "${COLLECTION_NAME}" created.`);

  // ── Index ─────────────────────────────────────────────────────────────────
  console.log("\n[3/4] Indexing documents...");
  await indexIntoChroma(collection, CORPUS, vectors);
  const count = await collection.count();
  console.log(`  Collection now has ${count} documents.`);

  // ── Query ─────────────────────────────────────────────────────────────────
  console.log("\n[4/4] Querying...\n");

  const queries = [
    "How do I measure text similarity?",
    "What is a neural network?",
    "How does retrieval-augmented generation work?",
  ];

  for (const q of queries) {
    const qVec = await provider.embed([q]);
    const results = await queryChroma(collection, qVec.vectors[0], 3);

    console.log(`Query: "${q}"`);
    for (const r of results) {
      console.log(`  [score=${r.score.toFixed(4)}] ${r.id}: ${r.text.slice(0, 80)}`);
    }
    console.log();
  }

  // ── Cleanup ───────────────────────────────────────────────────────────────
  await chroma.deleteCollection({ name: COLLECTION_NAME });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

// ---------------------------------------------------------------------------
// QDRANT VARIANT (optional — requires `docker run -p 6333:6333 qdrant/qdrant`)
// ---------------------------------------------------------------------------
//
// To use this, add "qdrant-js" or "@qdrant/js-client-rest" to package.json.
//
// import { QdrantClient } from "@qdrant/js-client-rest";
//
// class QdrantVariant {
//   private client: QdrantClient;
//   private collection = "learn-ai-m04";
//
//   constructor() {
//     this.client = new QdrantClient({ url: process.env.QDRANT_URL ?? "http://localhost:6333" });
//   }
//
//   async createCollection(dim: number) {
//     // TODO: await this.client.recreateCollection(this.collection, {
//     //   vectors: { size: dim, distance: "Cosine" },
//     // });
//   }
//
//   async upsert(docs: Document[], vectors: number[][]) {
//     // TODO: await this.client.upsert(this.collection, {
//     //   points: docs.map((d, i) => ({
//     //     id: i,                   // Qdrant needs numeric or UUID ids
//     //     vector: vectors[i],
//     //     payload: { id: d.id, text: d.text, ...d.metadata },
//     //   })),
//     // });
//   }
//
//   async query(queryVec: number[], k = 3) {
//     // TODO: const results = await this.client.search(this.collection, {
//     //   vector: queryVec,
//     //   limit: k,
//     //   with_payload: true,
//     // });
//     // return results.map(r => ({ id: r.payload!["id"], score: r.score, text: r.payload!["text"] }));
//   }
// }
