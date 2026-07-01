/**
 * Task 5 🟡 — Reimplement LlamaIndex: Documents -> VectorStoreIndex -> query engine.
 *
 * What you'll learn:
 *   - LlamaIndex's core RAG mental model in three moves: wrap raw text as
 *     `Document`s, build a `VectorStoreIndex.fromDocuments(docs)` (chunk each doc
 *     into Nodes and index them), then ask `index.asQueryEngine().query(q)`.
 *   - "Indexing" is just: split docs into nodes and precompute a vector per node.
 *     We use the SAME deterministic bag-of-words vector as Task 2 — no embeddings,
 *     no network — so the whole pipeline is offline and reproducible.
 *   - A query engine is retrieve-then-synthesize: rank nodes against the query,
 *     take top-k, stuff their text into a prompt, and call the model once.
 *
 * The math (retrieval, again — reused from Task 2):
 *
 *   Each node's text becomes a sparse count vector (word -> count). Rank nodes
 *   against the query by cosine similarity:
 *
 *       cosine(a, b) = (a . b) / (||a|| * ||b||)
 *
 *   top-k retrieval = score every node, sort by cosine descending, take first k.
 *   Then synthesis is one templated model call over the retrieved node texts.
 *
 * The pieces we reimplement (and the real @llamaindex/core equivalent):
 *
 *   ours                                real llama-index-core
 *   --------------------------------    ------------------------------------------
 *   Document(text)                      Document({ text })
 *   Node(text)                          a TextNode produced by the node parser
 *   VectorStoreIndex.fromDocuments      VectorStoreIndex.fromDocuments(docs)
 *   index.asQueryEngine()               index.asQueryEngine()
 *   queryEngine.query(q)                queryEngine.query({ query }) -> Response
 *
 * OFFLINE: this task takes a `chatFn: (msgs) => string`. With --stub it uses a
 * deterministic fake model that echoes the node texts it was handed, so we can
 * assert the retrieved context reached the synthesis prompt. Without --stub it
 * builds chatFn from `getProvider().chat` so the *same engine* runs on a real LLM.
 *
 * How to run:
 *   pnpm tsx modules/06c-agent-frameworks/ts/05-llamaindex.ts --stub   # offline, deterministic
 *   pnpm tsx modules/06c-agent-frameworks/ts/05-llamaindex.ts          # real model via getProvider()
 */

import { getProvider } from "@learn-ai/llm-core";

// A ChatFn is the whole model dependency narrowed to one function.
export interface Msg {
  role: string;
  content: string;
}
export type ChatFn = (messages: Msg[]) => string;

// ---------------------------------------------------------------------------
// Documents and Nodes
// ---------------------------------------------------------------------------

/** A raw piece of text to index. Real: Document({ text }). */
class Document {
  constructor(public text: string) {}
}

/**
 * A chunk of a Document plus its precomputed bag-of-words vector.
 * Real LlamaIndex parses each Document into TextNodes and attaches an embedding;
 * here the "embedding" is a sparse word-count vector (offline).
 */
class Node {
  constructor(
    public text: string,
    public vector: Map<string, number>,
  ) {}
}

// ---------------------------------------------------------------------------
// Bag-of-words cosine (same idea as Task 2; deterministic, offline)
// ---------------------------------------------------------------------------

/** Lowercase word tokens (letters/digits). Complete — no need to edit. */
function tokenize(text: string): string[] {
  return text.toLowerCase().match(/[a-z0-9]+/g) ?? [];
}

/** Word -> count. Complete — no need to edit. */
function bagOfWords(text: string): Map<string, number> {
  const counts = new Map<string, number>();
  for (const tok of tokenize(text)) counts.set(tok, (counts.get(tok) ?? 0) + 1);
  return counts;
}

/**
 * Cosine similarity between two sparse count vectors. Complete.
 * Provided so this task can focus on retrieval + synthesis (you built cosine by
 * hand in Task 2). dot over shared words / product of norms; 0 if a norm is 0.
 */
function cosine(a: Map<string, number>, b: Map<string, number>): number {
  let dot = 0;
  for (const [w, av] of a) {
    const bv = b.get(w);
    if (bv !== undefined) dot += av * bv;
  }
  let sa = 0;
  for (const av of a.values()) sa += av * av;
  let sb = 0;
  for (const bv of b.values()) sb += bv * bv;
  const normA = Math.sqrt(sa);
  const normB = Math.sqrt(sb);
  if (normA === 0 || normB === 0) return 0;
  return dot / (normA * normB);
}

/**
 * Chunk a document into Nodes. Complete — no need to edit.
 * A real node parser splits on tokens/sentences with overlap; to stay
 * deterministic and simple we split on blank lines (one Node per paragraph,
 * falling back to the whole text if there are no blank lines).
 */
function splitIntoNodes(text: string): Node[] {
  const chunks = text
    .split(/\n\s*\n/)
    .map((c) => c.trim())
    .filter((c) => c.length > 0);
  const parts = chunks.length > 0 ? chunks : [text.trim()];
  return parts.map((c) => new Node(c, bagOfWords(c)));
}

// ---------------------------------------------------------------------------
// The index + query engine
// ---------------------------------------------------------------------------

const SYNTHESIS_TEMPLATE = (context: string, query: string) =>
  `Context information is below.
---------------------
${context}
---------------------
Given the context information and not prior knowledge, answer the query.
Query: ${query}
Answer:`;

/**
 * An in-memory index of Nodes you can query. Built from Documents.
 * Real LlamaIndex: `VectorStoreIndex.fromDocuments(docs)` parses docs into nodes,
 * embeds them, and stores them in a vector store.
 */
class VectorStoreIndex {
  constructor(
    public nodes: Node[],
    private chatFn: ChatFn,
  ) {}

  /** Chunk every Document into Nodes and build the index. Complete. */
  static fromDocuments(documents: Document[], chatFn: ChatFn): VectorStoreIndex {
    const nodes: Node[] = [];
    for (const doc of documents) nodes.push(...splitIntoNodes(doc.text));
    return new VectorStoreIndex(nodes, chatFn);
  }

  /**
   * Return the top-k Nodes most similar to `query` (highest cosine first).
   * This is the retriever half of the query engine — the same top-k-by-cosine
   * ranking as Task 2's Retriever, but over Nodes instead of raw doc strings.
   *
   * TODO: implement.
   *   - Turn `query` into a bag-of-words vector (see bagOfWords above).
   *   - Score every node in this.nodes by cosine(queryVec, node.vector), keeping
   *     each node paired with its score.
   *   - Sort by score DESCENDING (ties keep original order — subtracting scores
   *     is stable in modern JS engines).
   *   - Return the Node objects of the first k pairs (a Node[]).
   */
  retrieve(_query: string, _k = 2): Node[] {
    // TODO: implement top-k node retrieval by cosine
    throw new Error("TODO: implement VectorStoreIndex.retrieve()");
  }

  /** Expose this index as a query engine. Complete. */
  asQueryEngine(k = 2): QueryEngine {
    return new QueryEngine(this, this.chatFn, k);
  }
}

/**
 * Retrieve top-k nodes, then synthesize one answer from them via the model.
 * Real LlamaIndex: `index.asQueryEngine().query({ query })` returns a Response
 * whose `.sourceNodes` are what was retrieved and `.response` is the synthesis.
 */
class QueryEngine {
  lastPrompt = ""; // exposed so tests can inspect what we synthesized from

  constructor(
    private index: VectorStoreIndex,
    private chatFn: ChatFn,
    private k = 2,
  ) {}

  /**
   * Answer `query` over the index: retrieve top-k nodes, then synthesize.
   *
   * TODO: implement.
   *   1. Retrieve the top-k nodes for `query` via this.index.retrieve(...).
   *   2. Assemble the retrieved node TEXTS into a single context block (join the
   *      nodes' `.text` fields, one per line).
   *   3. Fill SYNTHESIS_TEMPLATE(context, query) to make the synthesis prompt.
   *      Save it on this.lastPrompt (tests inspect it).
   *   4. Call the model with a single user message carrying that prompt (build a
   *      Msg[] with one { role, content } entry) and return the reply text.
   */
  query(_query: string): string {
    // TODO: implement retrieve-then-synthesize
    throw new Error("TODO: implement QueryEngine.query()");
  }
}

// ---------------------------------------------------------------------------
// Stub + real model
// ---------------------------------------------------------------------------

/**
 * Deterministic fake: echo back the context block it was given.
 * It returns a fixed prefix plus the context section pulled from the prompt so
 * tests can prove the *retrieved* node text reached the synthesis prompt — we
 * are testing the engine, not a real model's wording.
 */
function makeStubChatFn(): ChatFn {
  return (messages: Msg[]) => {
    const prompt = messages[messages.length - 1].content;
    const parts = prompt.split("---------------------");
    const context = parts.length >= 3 ? parts[1].trim() : "";
    return `[stub-answer from ${context}]`;
  };
}

/** Wrap the shared provider. Sync signature; real chat is async — see README. */
function makeRealChatFn(): ChatFn {
  const provider = getProvider();
  void provider;
  return () => {
    throw new Error(
      "Real provider chat is async. Run with --stub for the offline check, " +
        "or adapt QueryEngine.query to `await provider.chat(...)`.",
    );
  };
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

const DOCS = [
  new Document(
    "Python is a dynamically typed programming language popular for data " +
      "science and scripting.\n\n" +
      "It has a large ecosystem of libraries such as NumPy and pandas.",
  ),
  new Document(
    "The Eiffel Tower is an iron lattice tower on the Champ de Mars in " +
      "Paris, France.\n\n" +
      "It was completed in 1889 and is one of the most visited monuments in " +
      "the world.",
  ),
  new Document(
    "Retrieval-augmented generation (RAG) grounds a language model in " +
      "retrieved documents.\n\n" +
      "It reduces hallucination by giving the model relevant context at query " +
      "time.",
  ),
];

function main(): void {
  const useStub = process.argv.includes("--stub");
  const chatFn = useStub ? makeStubChatFn() : makeRealChatFn();
  const mode = useStub ? "STUB (offline)" : "REAL (getProvider)";
  console.log(`\n=== Task 5: LlamaIndex query engine — ${mode} ===\n`);

  const index = VectorStoreIndex.fromDocuments(DOCS, chatFn);
  console.log(`Indexed ${index.nodes.length} nodes from ${DOCS.length} documents.`);

  const queryEngine = index.asQueryEngine(2);
  const question = "Where is the Eiffel Tower located?";
  console.log(`\nQuery: ${JSON.stringify(question)}`);

  // Retrieval sanity: show which nodes the engine pulls before synthesis.
  const retrieved = index.retrieve(question, 2);
  console.log("Top-k retrieved nodes:");
  retrieved.forEach((node, i) => {
    console.log(`  [${i + 1}] ${JSON.stringify(node.text)}`);
  });

  const answer = queryEngine.query(question);
  console.log(`\nAnswer: ${JSON.stringify(answer)}`);

  if (useStub) {
    // 1) Retrieval returns the Eiffel-Tower node first (highest overlap).
    const top = index.retrieve(question, 1);
    if (!top.length || !top[0].text.includes("Eiffel Tower"))
      throw new Error(
        `top node should mention the Eiffel Tower, got ${JSON.stringify(top)}`,
      );
    // 2) The synthesis prompt carried the retrieved node text as context.
    if (!queryEngine.lastPrompt.includes("Eiffel Tower"))
      throw new Error("retrieved context not in synthesis prompt");
    if (!queryEngine.lastPrompt.includes(`Query: ${question}`))
      throw new Error("query not in synthesis prompt");
    // 3) The (stub) answer was synthesized FROM the retrieved context.
    if (!answer.includes("Eiffel Tower"))
      throw new Error("answer did not include retrieved context");
    console.log(
      "\n[ok] index chunked docs into nodes; query engine retrieved the " +
        "right node and synthesized from it",
    );
  }

  console.log(
    "\nReal LlamaIndex: VectorStoreIndex.fromDocuments(docs)" +
      ".asQueryEngine().query(q) runs the same retrieve-then-synthesize flow.",
  );
}

main();
