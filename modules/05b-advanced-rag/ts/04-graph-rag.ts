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
 *   const messages: ChatMessage[] = [
 *     { role: "system", content: 'Extract knowledge-graph triples from the text. Respond with ONLY a JSON array of [subject, relation, object] arrays, e.g. [["Alice","works_at","Acme"]]. Use short snake_case relations.' },
 *     { role: "user", content: text },
 *   ];
 *   const r = await provider.chat(messages, { temperature: 0, maxTokens: 300 });
 *   try { const data = JSON.parse(stripCodeFences(r.text));
 *         return data.filter((t: unknown) => Array.isArray(t) && t.length === 3) as Triple[]; }
 *   catch { return []; }
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
   *   const sk = norm(subj), ok = norm(obj);
   *   if (!this.label.has(sk)) this.label.set(sk, subj.trim());
   *   if (!this.label.has(ok)) this.label.set(ok, obj.trim());
   *   push { relation: rel, other: ok, direction: "out" } into adj[sk]
   *   push { relation: rel, other: sk, direction: "in" }  into adj[ok]
   *   (create the array with this.adj.get(k) ?? [] then set it back)
   */
  addTriple(subj: string, rel: string, obj: string): void {
    // TODO: implement addTriple().
    throw new Error("TODO: implement addTriple()");
  }

  /** All edges touching `entity` (both directions), or []. */
  neighbors(entity: string): Edge[] {
    // TODO: return this.adj.get(norm(entity)) ?? [];
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
 *   const visited = new Set(seeds.map(norm));
 *   const queue: Array<[string, number]> = [...visited].map((k) => [k, 0]);
 *   const collected: Triple[] = []; const seen = new Set<string>();
 *   while (queue.length) {
 *     const [key, hop] = queue.shift()!;
 *     if (hop === depth) continue;
 *     for (const e of graph.neighbors(key)) {
 *       const triple: Triple = e.direction === "out"
 *         ? [graph.label.get(key) ?? key, e.relation, graph.label.get(e.other) ?? e.other]
 *         : [graph.label.get(e.other) ?? e.other, e.relation, graph.label.get(key) ?? key];
 *       const sig = triple.join("|");
 *       if (!seen.has(sig)) { seen.add(sig); collected.push(triple); }
 *       if (!visited.has(e.other)) { visited.add(e.other); queue.push([e.other, hop + 1]); }
 *     }
 *   }
 *   return collected;
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
 *   const seeds = findSeedEntities(query, graph);
 *   const triples = multiHopSubgraph(graph, seeds, 2);
 *   const context = triples.map(([s, r, o]) => `${s} --${r}--> ${o}`).join("\n");
 *   const messages: ChatMessage[] = [
 *     { role: "system", content: "Answer the question using ONLY these knowledge-graph facts." },
 *     { role: "user", content: `Facts:\n${context}\n\nQuestion: ${query}` },
 *   ];
 *   const r = await provider.chat(messages, { temperature: 0, maxTokens: 150 });
 *   return { answer: r.text.trim(), subgraph: triples };
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
