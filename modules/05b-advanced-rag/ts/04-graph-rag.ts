/**
 * Task 4 🔴 — GraphRAG: multi-hop retrieval over a hand-built knowledge graph.
 *
 * What you'll learn:
 *   - Why vector top-k fails on multi-hop questions (the answer is a PATH)
 *   - How an LLM extracts (subject, relation, object) triples from text
 *   - How to build a graph BY HAND (adjacency map) and traverse it with BFS
 *
 * How to run:
 *   pnpm tsx modules/05b-advanced-rag/ts/04-graph-rag.ts
 *   (extraction + final answer are chat() calls — works on ANY provider)
 *
 * 🔴 Constraint: NO graph library. A graph is a Map of adjacency lists; building
 * and walking it is the whole point. Fill in the four TODO sections.
 */

import { getProvider, type ChatMessage } from "@learn-ai/llm-core";

type Provider = ReturnType<typeof getProvider>;

// ---------------------------------------------------------------------------
// Corpus — the answer to the demo question spans TWO documents (two hops).
// ---------------------------------------------------------------------------

const CORPUS: string[] = [
  "Marie Curie collaborated with Pierre Curie on research into radioactivity.",
  "Pierre Curie won the Nobel Prize in Physics in 1903.",
  "Ernest Rutherford mentored Niels Bohr at the University of Manchester.",
  "Niels Bohr won the Nobel Prize in Physics for his model of the atom.",
];

type Triple = [subject: string, relation: string, object: string];

function stripCodeFences(text: string): string {
  // Remove ```json ... ``` fences some models add around JSON.
  return text
    .trim()
    .replace(/^```(?:json)?/, "")
    .replace(/```$/, "")
    .trim();
}

function norm(entity: string): string {
  // Canonical key for an entity (case/space-insensitive).
  return entity.toLowerCase().split(/\s+/).join(" ");
}

// ---------------------------------------------------------------------------
// TODO 1: extract triples from a chunk with the LLM
// ---------------------------------------------------------------------------

/**
 * Ask the LLM to extract (subject, relation, object) triples and return them.
 *
 * TODO: implement this.
 *
 * Steps:
 *   - Build a `ChatMessage[]`: a system message telling the model to extract
 *     knowledge-graph triples and respond with ONLY a JSON array of
 *     [subject, relation, object] arrays using short snake_case relations (giving one
 *     tiny example helps), and a user message with the text.
 *   - Call `provider.chat(messages, { temperature: 0, maxTokens: ... })`.
 *   - Parse the reply: run it through the provided `stripCodeFences()`, then
 *     `JSON.parse`. Keep only entries that are 3-element arrays (skip malformed rows),
 *     and wrap the whole parse in try/catch so a bad reply yields [] instead of
 *     throwing.
 */
async function extractTriples(text: string, provider: Provider): Promise<Triple[]> {
  // TODO: implement extractTriples().
  throw new Error("TODO: implement extractTriples()");
}

// ---------------------------------------------------------------------------
// TODO 2: the knowledge graph (adjacency map, both directions)
// ---------------------------------------------------------------------------

interface Edge {
  relation: string;
  other: string; // neighbour entity (canonical key)
  direction: "out" | "in"; // out: self -> other ; in: other -> self
}

class KnowledgeGraph {
  // adjacency: entity-key -> edges
  readonly adj = new Map<string, Edge[]>();
  // display label per entity-key (first spelling we saw)
  readonly label = new Map<string, string>();

  /**
   * Store the triple in BOTH directions so traversal can move either way.
   *
   * TODO: implement this.
   *
   * Steps:
   *   - Canonicalise both entities with `norm()` to get their keys.
   *   - Remember a display label for each key the first time you see it (keep the
   *     first spelling; don't overwrite).
   *   - Append an Edge to the subject key's adjacency list with direction "out"
   *     pointing at the object key, AND an Edge to the object key's list with
   *     direction "in" pointing back at the subject key (both carry `rel`). Lazily
   *     create each list via `this.adj.get(k) ?? []` then set it back.
   */
  addTriple(subj: string, rel: string, obj: string): void {
    // TODO: implement addTriple().
    throw new Error("TODO: implement addTriple()");
  }

  /** All edges touching `entity` (both directions), or []. */
  neighbors(entity: string): Edge[] {
    // TODO: look up the adjacency list for the norm()-ed entity key, defaulting to [].
    throw new Error("TODO: implement neighbors()");
  }

  entities(): string[] {
    return [...this.adj.keys()];
  }
}

// ---------------------------------------------------------------------------
// TODO 3: multi-hop BFS subgraph
// ---------------------------------------------------------------------------

/**
 * BFS out from `seeds` up to `depth` hops, collecting the triples encountered.
 *
 * TODO: implement this.
 *
 * Steps:
 *   - Standard BFS. Seed a `visited` Set with the norm()-ed seed keys and a queue of
 *     [key, hop] pairs starting at hop 0. Keep a `collected: Triple[]` plus a Set to
 *     dedupe triples you've already emitted.
 *   - Pop from the queue; stop expanding a node once its hop equals `depth`. For each
 *     edge from graph.neighbors(key), reconstruct the triple in canonical
 *     subject -> object order using the edge's `direction` ("out" means key is the
 *     subject; "in" means key is the object) and the graph's label map for display
 *     names. Add it to `collected` if unseen.
 *   - Enqueue any unvisited neighbour at hop + 1. Return `collected`.
 */
function multiHopSubgraph(graph: KnowledgeGraph, seeds: string[], depth = 2): Triple[] {
  // TODO: implement multiHopSubgraph().
  throw new Error("TODO: implement multiHopSubgraph()");
}

// ---------------------------------------------------------------------------
// TODO 4: answer over the assembled subgraph
// ---------------------------------------------------------------------------

function findSeedEntities(query: string, graph: KnowledgeGraph): string[] {
  // Provided: graph entities whose label appears in the query.
  const ql = query.toLowerCase();
  return [...graph.label.entries()]
    .filter(([, lbl]) => ql.includes(lbl.toLowerCase()))
    .map(([key]) => key);
}

/**
 * Find seeds, gather the multi-hop subgraph, serialise triples as context, and
 * ask the LLM to answer over THAT.
 *
 * TODO: implement this.
 *
 * Steps:
 *   - Locate seed entities with the provided `findSeedEntities()`, then gather their
 *     2-hop neighbourhood with `multiHopSubgraph()`.
 *   - Serialise each triple into a readable one-line fact (e.g. `s --relation--> o`)
 *     and join them into a context string.
 *   - Build a `ChatMessage[]`: a system message telling the model to answer using
 *     ONLY these knowledge-graph facts, and a user message carrying the facts and the
 *     question. Call `provider.chat(messages, { temperature: 0, maxTokens: ... })`.
 *   - Return { answer: <trimmed reply>, subgraph: <the triples you used> }.
 */
async function graphRagAnswer(
  query: string,
  graph: KnowledgeGraph,
  provider: Provider,
): Promise<{ answer: string; subgraph: Triple[] }> {
  // TODO: implement graphRagAnswer().
  throw new Error("TODO: implement graphRagAnswer()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function buildGraph(
  corpus: string[],
  provider: Provider,
): Promise<KnowledgeGraph> {
  const graph = new KnowledgeGraph();
  for (const chunk of corpus) {
    for (const [s, r, o] of await extractTriples(chunk, provider)) {
      graph.addTriple(s, r, o);
    }
  }
  return graph;
}

async function main() {
  const provider = getProvider();
  console.log(`\nProvider: ${provider.name}\n`);

  console.log("Extracting triples + building graph...");
  const graph = await buildGraph(CORPUS, provider);
  console.log(`Graph: ${graph.entities().length} entities\n`);

  // A 2-hop question: no single sentence contains the answer.
  const query = "Which collaborator of Marie Curie won a Nobel Prize?";
  console.log(`Query: "${query}"\n`);

  const { answer, subgraph } = await graphRagAnswer(query, graph, provider);
  console.log("Subgraph used (the connecting path):");
  for (const [s, r, o] of subgraph) console.log(`  ${s} --${r}--> ${o}`);
  console.log(`\nAnswer: ${answer}`);

  console.log(
    "\nReflection: vector top-k would retrieve the 'Marie Curie' sentence and miss " +
      "the 'Pierre Curie won...' sentence — they share no query words. The graph " +
      "connects them via the shared entity Pierre Curie.",
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
