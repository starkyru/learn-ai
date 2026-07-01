/**
 * Task 2 🟡 — Reimplement LangChain memory + a retriever, wire a tiny RAG chain.
 *
 * What you'll learn:
 *   - ConversationBufferMemory: memory is *just* a list of turns you save and
 *     reload. `saveContext(user, ai)` appends; `loadMemoryVariables()` renders
 *     the buffer back into a string the next prompt can carry.
 *   - A retriever is *just* a ranker over documents: score each doc against the
 *     query, sort, take the top-k. Here we rank with bag-of-words cosine — no
 *     embeddings, no network — so it's fully offline and deterministic.
 *   - RAG = retrieve context, stuff it into the prompt, then ask the model. The
 *     "chain" is the same left-to-right threading as Task 1, plus memory.
 *
 * The math:
 *
 *   1) Bag-of-words vector. Tokenise a text into lowercase word tokens, then
 *      count occurrences. A doc becomes a map word -> count.
 *
 *   2) Cosine similarity between two sparse count vectors a and b:
 *
 *          cosine(a, b) = (a . b) / (||a|| * ||b||)
 *
 *      where the dot product sums a[w]*b[w] over shared words, and
 *      ||a|| = sqrt(sum_w a[w]^2). If either norm is 0, similarity is 0.
 *
 *   3) top-k retrieval: score every doc, sort by cosine descending, take first k.
 *
 * The pieces we reimplement (and the real LangChain equivalent):
 *
 *   ours                                real langchain
 *   --------------------------------    ----------------------------------------
 *   ConversationBufferMemory            langchain memory ConversationBufferMemory
 *     .saveContext / .loadMemoryVars      (same idea)
 *   Retriever.getRelevant(q, k)         VectorStoreRetriever.invoke(q)
 *   buildRagPrompt(...)                 a PromptTemplate with {context}{question}
 *
 * OFFLINE: takes `chatFn: (msgs) => string`. With --stub it uses a deterministic
 * fake model; without --stub it wraps getProvider().chat.
 *
 * How to run:
 *   pnpm tsx modules/06c-agent-frameworks/ts/02-memory-retriever.ts --stub
 *   pnpm tsx modules/06c-agent-frameworks/ts/02-memory-retriever.ts
 */

import { getProvider } from "@learn-ai/llm-core";

export interface Msg {
  role: string;
  content: string;
}
export type ChatFn = (messages: Msg[]) => string;

// ---------------------------------------------------------------------------
// Conversation memory
// ---------------------------------------------------------------------------

/**
 * A list of (user, ai) turns, rendered back as a transcript string.
 * Real LangChain's ConversationBufferMemory keeps the raw messages and, on
 * load, formats them as "Human: ...\nAI: ..." lines.
 */
class ConversationBufferMemory {
  turns: [string, string][] = [];

  /**
   * Append one (user, ai) turn to the buffer.
   *
   * TODO: implement.
   *   - Push a single [userInput, aiOutput] pair onto this.turns so the buffer
   *     grows by one turn per call.
   */
  saveContext(_userInput: string, _aiOutput: string): void {
    // TODO: implement saveContext (append the turn)
    throw new Error("TODO: implement ConversationBufferMemory.saveContext()");
  }

  /**
   * Render the buffer as { history: "Human: ...\nAI: ...\n..." }.
   * Each turn becomes two lines ("Human: u", "AI: a"), joined with "\n".
   * An empty buffer yields "".
   *
   * TODO: implement.
   *   - Turn each stored turn into two lines — a "Human: ..." line for the user
   *     input and an "AI: ..." line for the ai output.
   *   - Join all lines with newlines into one transcript string and return it
   *     under the `history` key (an empty buffer must yield "").
   */
  loadMemoryVariables(): { history: string } {
    // TODO: implement loadMemoryVariables (render buffer to a string)
    throw new Error("TODO: implement ConversationBufferMemory.loadMemoryVariables()");
  }
}

// ---------------------------------------------------------------------------
// Bag-of-words cosine retriever (deterministic, offline)
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
 * Cosine similarity between two sparse count vectors.
 *
 *     cosine(a, b) = dot(a, b) / (||a|| * ||b||)
 *
 * dot(a, b) = sum over shared words of a[w]*b[w].
 * ||a||     = sqrt(sum of a[w]^2 over all words in a).
 * Return 0 if either vector has zero norm.
 *
 * TODO: implement.
 *   - Compute the dot product: for each word/count in `a`, if `b` also has that
 *     word, add the product of the two counts.
 *   - Compute each vector's Euclidean norm — sqrt of the sum of its squared
 *     counts (iterate the map values).
 *   - Guard the divide: if either norm is 0, return 0.
 *   - Otherwise return the dot product divided by the product of the two norms.
 */
function cosine(_a: Map<string, number>, _b: Map<string, number>): number {
  // TODO: implement cosine similarity over sparse count vectors
  throw new Error("TODO: implement cosine()");
}

/** Ranks a fixed doc set against a query by bag-of-words cosine. */
class Retriever {
  private docVecs: Map<string, number>[];

  constructor(private docs: string[]) {
    this.docVecs = docs.map((d) => bagOfWords(d));
  }

  /**
   * Return the top-k docs most similar to `query` (highest cosine first).
   *
   * TODO: implement.
   *   - Turn the query into a bag-of-words vector.
   *   - Score every doc by cosine against the query, keeping each doc paired
   *     with its score (the precomputed this.docVecs align with this.docs).
   *   - Sort by score descending (ties keep original order — subtracting scores
   *     is a stable comparator in modern JS engines).
   *   - Return the docs (not the scores) of the first k entries.
   */
  getRelevant(_query: string, _k = 1): string[] {
    // TODO: implement top-k retrieval by cosine
    throw new Error("TODO: implement Retriever.getRelevant()");
  }
}

// ---------------------------------------------------------------------------
// RAG prompt assembly
// ---------------------------------------------------------------------------

/**
 * Build the RAG prompt from the memory transcript, retrieved context, question.
 *
 * TODO: implement.
 *   Return one prompt string (a template literal is easiest) that, in order:
 *     - opens with a short instruction to answer using the context + prior
 *       conversation;
 *     - includes a labelled "Conversation so far" section holding `history`;
 *     - includes a labelled "Context" section holding `context`;
 *     - ends with a "Question:" line carrying `question`, then an "Answer:" cue.
 *   The stub tests only check that `context`, the question text, and prior-turn
 *   history all appear in the assembled prompt — so the exact wording is yours,
 *   but keep those three values in it.
 */
function buildRagPrompt(_history: string, _context: string, _question: string): string {
  // TODO: implement RAG prompt assembly
  throw new Error("TODO: implement buildRagPrompt()");
}

// ---------------------------------------------------------------------------
// The RAG chain: retrieve -> prompt(context+question+history) -> model, + memory
// ---------------------------------------------------------------------------

/**
 * Ties the retriever, memory, and model into one `ask(question)` call.
 * This class is complete: it calls the pieces you implement above.
 */
class RagChain {
  lastPrompt = ""; // exposed so tests can inspect what we sent

  constructor(
    private chatFn: ChatFn,
    private retriever: Retriever,
    private memory: ConversationBufferMemory,
  ) {}

  ask(question: string, k = 1): string {
    const history = this.memory.loadMemoryVariables().history;
    const docs = this.retriever.getRelevant(question, k);
    const context = docs.join("\n");
    const prompt = buildRagPrompt(history, context, question);
    this.lastPrompt = prompt;
    const answer = this.chatFn([{ role: "user", content: prompt }]);
    this.memory.saveContext(question, answer);
    return answer;
  }
}

// ---------------------------------------------------------------------------
// Stub + real model
// ---------------------------------------------------------------------------

/** Deterministic fake: return a fixed short line so tests are exact. */
function makeStubChatFn(): ChatFn {
  let n = 0;
  return () => {
    n += 1;
    return `stub-answer-${n}`;
  };
}

/** Wrap the shared provider. Sync signature; real chat is async — see README. */
function makeRealChatFn(): ChatFn {
  const provider = getProvider();
  void provider;
  return () => {
    throw new Error(
      "Real provider chat is async. Run with --stub for the offline check, " +
        "or adapt RagChain.ask to `await provider.chat(...)`.",
    );
  };
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

const DOCS = [
  "Python is a dynamically typed programming language popular for data science.",
  "The mitochondria is the powerhouse of the cell and produces ATP energy.",
  "The Eiffel Tower is an iron lattice tower located in Paris, France.",
  "Basketball is a team sport where players score by shooting a ball through a hoop.",
];

function main(): void {
  const useStub = process.argv.includes("--stub");
  const chatFn = useStub ? makeStubChatFn() : makeRealChatFn();
  const mode = useStub ? "STUB (offline)" : "REAL (getProvider)";
  console.log(`\n=== Task 2: memory + retriever — ${mode} ===\n`);

  const retriever = new Retriever(DOCS);
  const memory = new ConversationBufferMemory();
  const chain = new RagChain(chatFn, retriever, memory);

  // ── Retriever sanity: most lexically similar doc wins ─────────────────
  const top = retriever.getRelevant("Which language is used for data science?", 1)[0];
  console.log("Query: 'Which language is used for data science?'");
  console.log(`  top doc -> ${JSON.stringify(top)}`);

  // ── Turn 1 ──────────────────────────────────────────────────────────────
  const q1 = "Tell me about Python.";
  const a1 = chain.ask(q1);
  console.log(`\nTurn 1  Q: ${q1}\n        A: ${a1}`);

  // ── Turn 2 (memory should now hold turn 1) ────────────────────────────
  const q2 = "Where is the Eiffel Tower?";
  const a2 = chain.ask(q2);
  console.log(`Turn 2  Q: ${q2}\n        A: ${a2}`);

  console.log("\nMemory buffer after two turns:");
  console.log(memory.loadMemoryVariables().history);

  if (useStub) {
    if (top !== DOCS[0])
      throw new Error(`retriever picked wrong doc: ${JSON.stringify(top)}`);
    const hist = memory.loadMemoryVariables().history;
    if (!hist.includes(q1) || !hist.includes(a1))
      throw new Error("turn 1 missing from memory");
    if (!hist.includes(q2) || !hist.includes(a2))
      throw new Error("turn 2 missing from memory");
    if (memory.turns.length !== 2)
      throw new Error(`expected 2 turns, got ${memory.turns.length}`);
    if (!chain.lastPrompt.includes(DOCS[2]))
      throw new Error("retrieved context not in prompt");
    if (!chain.lastPrompt.includes("Question: Where is the Eiffel Tower?"))
      throw new Error("question not in prompt");
    if (!chain.lastPrompt.includes(q1))
      throw new Error("prior turn not carried into prompt");
    console.log(
      "\n[ok] retriever ranks correctly, memory holds both turns, " +
        "prompt contains retrieved context + history",
    );
  }

  console.log(
    "\nReal LangChain: swap Retriever for a VectorStoreRetriever and " +
      "ConversationBufferMemory keeps the same save/load API.",
  );
}

main();
