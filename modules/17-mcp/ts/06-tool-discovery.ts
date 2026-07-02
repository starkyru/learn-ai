/**
 * 06-tool-discovery.ts — Semantic tool discovery: the toolbox.  🟡
 *
 * What this teaches:
 *   Tasks 2-5 always passed EVERY tool schema to the model on every call.
 *   That works with 3 tools. It breaks with 30: published evals (e.g. the
 *   Berkeley Function-Calling Leaderboard, Anthropic's Tool Search) show
 *   tool-selection accuracy DROPS as the schema list grows — lexically
 *   confusable descriptions start to win — while the token cost of shipping
 *   every schema climbs regardless of relevance.
 *
 *   The fix is the **toolbox pattern** (a.k.a. semantic tool discovery):
 *     1. Index every tool definition in a vector store — embed an
 *        LLM-augmented description (intent + use-cases), not just the raw
 *        signature.
 *     2. Per user query, retrieve only the top-k semantically relevant tools.
 *     3. Pass just those k schemas to the model.
 *
 *   You implement the four pieces: augmentDescription(), indexToolbox(),
 *   retrieveTools(), measureTokenCost(). The registry of 20 tools, the fixed
 *   10-query eval set, and the deterministic "selector" stand-in for the
 *   model are provided, so the accuracy comparison runs offline.
 *
 *   The scripted selector models the measured failure mode: with a small,
 *   focused schema list it reliably picks the right tool; past its "focus
 *   budget" a wrong tool whose raw description merely LOOKS more like the
 *   query can win. Deterministic, so the experiment is reproducible.
 *
 * The math (same bag-of-words cosine as module 06c):
 *   bow(text)[w]  = count of word w in text
 *   cosine(a, b)  = dot(a, b) / (||a|| * ||b||),  0.0 if either norm is 0
 *   top-k         = sort docs by cosine desc (stable), take the first k
 *
 * How to run (from repo root):
 *   pnpm tsx modules/17-mcp/ts/06-tool-discovery.ts            # offline
 *   LLM_PROVIDER=ollama pnpm tsx modules/17-mcp/ts/06-tool-discovery.ts --embed
 *   LLM_PROVIDER=ollama pnpm tsx modules/17-mcp/ts/06-tool-discovery.ts --live
 *
 *   --embed  retrieve with real provider.embed() vectors instead of
 *            bag-of-words (any provider except Anthropic — no embeddings there).
 *   --live   replace the scripted selector with the real model choosing a
 *            tool via getProvider().chat().
 *
 * TS deps: @learn-ai/llm-core only (and only for --embed/--live).
 */

import { getProvider } from "@learn-ai/llm-core";

// A vector is either a sparse bag-of-words map or a dense embedding array.
type Vec = Map<string, number> | number[];
type VectorizeFn = (texts: string[]) => Promise<Vec[]>;
type SelectorFn = (
  query: string,
  toolsPassed: ToolDef[],
  labeled: string,
) => Promise<string>;

interface ToolDef {
  name: string;
  description: string;
  parameters: {
    type: "object";
    properties: Record<string, { type: string; description: string }>;
    required: string[];
  };
}

// ---------------------------------------------------------------------------
// Toolbox registry  (provided — do not edit)
// ---------------------------------------------------------------------------

/** Build one tool definition in the JSON-Schema shape MCP/OpenAI use. */
function tool(
  name: string,
  description: string,
  props: Record<string, string>,
  required: string[],
): ToolDef {
  const properties: ToolDef["parameters"]["properties"] = {};
  for (const [key, desc] of Object.entries(props)) {
    properties[key] = { type: "string", description: desc };
  }
  return { name, description, parameters: { type: "object", properties, required } };
}

const TOOLS: ToolDef[] = [
  tool(
    "get_weather",
    "Get the current weather conditions for a city.",
    { city: "City name", units: "metric or imperial" },
    ["city"],
  ),
  tool(
    "get_forecast",
    "Get the multi-day weather forecast for a city.",
    { city: "City name", days: "Number of days ahead" },
    ["city"],
  ),
  tool(
    "send_email",
    "Send an email message to a recipient.",
    { to: "Recipient address", subject: "Subject line", body: "Message body" },
    ["to", "subject", "body"],
  ),
  tool(
    "create_calendar_event",
    "Create an event on the user's calendar.",
    { title: "Event title", start_time: "ISO start", end_time: "ISO end" },
    ["title", "start_time"],
  ),
  tool(
    "list_calendar_events",
    "List the events on the user's calendar between two dates.",
    { start_date: "ISO date", end_date: "ISO date" },
    ["start_date"],
  ),
  tool(
    "set_reminder",
    "Set a reminder that fires at a chosen time.",
    { message: "Reminder text", time: "When to fire" },
    ["message", "time"],
  ),
  tool(
    "read_file",
    "Read the contents of a file at a given path.",
    { path: "File path" },
    ["path"],
  ),
  tool(
    "write_file",
    "Write text content to a file at a given path.",
    { path: "File path", content: "Text to write" },
    ["path", "content"],
  ),
  tool("delete_file", "Delete the file at a given path.", { path: "File path" }, [
    "path",
  ]),
  tool(
    "calculator",
    "Evaluate an arithmetic expression and return the numeric result.",
    { expression: "Arithmetic expression" },
    ["expression"],
  ),
  tool(
    "unit_convert",
    "Convert a value from one unit to another, such as miles to kilometers.",
    { value: "Quantity", from_unit: "Source unit", to_unit: "Target unit" },
    ["value", "from_unit", "to_unit"],
  ),
  tool(
    "currency_convert",
    "Exchange an amount of money between two currencies at the current rate.",
    {
      amount: "Amount of money",
      from_currency: "Source code",
      to_currency: "Target code",
    },
    ["amount", "from_currency", "to_currency"],
  ),
  tool(
    "web_search",
    "Look up information online and return short result snippets.",
    { query: "Search terms" },
    ["query"],
  ),
  tool(
    "news_search",
    "Search the web's news sources for the latest articles about a topic.",
    { topic: "News topic", days: "How far back to look" },
    ["topic"],
  ),
  tool(
    "db_query",
    "Run a read-only SQL statement against the analytics database.",
    { sql: "SQL SELECT statement" },
    ["sql"],
  ),
  tool(
    "db_schema",
    "Describe the tables and columns available in the analytics database.",
    { table: "Table name, or empty for all" },
    [],
  ),
  tool(
    "run_python",
    "Execute a Python snippet in a sandbox and return its stdout.",
    { code: "Python source code" },
    ["code"],
  ),
  tool(
    "translate_text",
    "Translate text from one language to another.",
    { text: "Text to translate", target_language: "Target language" },
    ["text", "target_language"],
  ),
  tool(
    "generate_image",
    "Generate an image from a text description.",
    { prompt: "Image description", size: "Pixel dimensions" },
    ["prompt"],
  ),
  tool(
    "describe_image",
    "Describe what is shown in an image at a URL.",
    { image_url: "Image URL" },
    ["image_url"],
  ),
];

// The "LLM-augmented" use-case line per tool: what a user might actually SAY
// when they need it. In production you'd generate these once with a strong
// model ("list 3 requests this tool answers"); here they're pre-generated so
// the task stays offline.
const USE_CASES: Record<string, string> = {
  get_weather:
    "what is it like outside right now, temperature in a city today, is it raining",
  get_forecast:
    "will it rain tomorrow, weather for the next few days, weekend forecast",
  send_email:
    "write to a colleague, send a message about a report, follow up with a client",
  create_calendar_event:
    "schedule a meeting, book a call with someone, block time next week",
  list_calendar_events:
    "what is on my agenda, am I free on Friday, upcoming appointments",
  set_reminder:
    "remind me to do something later, nudge me at 5pm, do not let me forget",
  read_file: "open a document, show the contents of notes.txt, what does the file say",
  write_file:
    "save this text to disk, create a new file with content, overwrite a document",
  delete_file: "remove an old file, clean up a document, get rid of report.txt",
  calculator: "what is 15 percent of a number, add up expenses, quick arithmetic",
  unit_convert: "miles to kilometers, celsius to fahrenheit, pounds to kilograms",
  currency_convert: "dollars to euros, how much is 100 USD in yen, exchange money",
  web_search:
    "look up release notes online, research a topic, find documentation on the internet",
  news_search: "current events, headlines from the last few days, what happened today",
  db_query:
    "how many users signed up last week, count rows in a table, monthly revenue numbers",
  db_schema: "what tables exist, which columns does a table have, database structure",
  run_python: "run a script, compute something with code, test a snippet",
  translate_text:
    "translate a paragraph into Japanese, say this in French, localise a sentence",
  generate_image:
    "draw a picture of a cat, create an illustration, make a logo concept",
  describe_image:
    "what is in this photo, caption an image, identify objects in a picture",
};

// Fixed eval set: [user query, name of the single correct tool].
const EVAL_SET: Array<[string, string]> = [
  ["What's the weather like in Paris right now?", "get_weather"],
  ["Send an email to Alice about the quarterly report", "send_email"],
  ["Schedule a 30 minute meeting with Bob next Tuesday", "create_calendar_event"],
  ["How many users signed up last week?", "db_query"],
  ["Convert 250 US dollars to euros", "currency_convert"],
  ["Search the web for the latest TypeScript release notes", "web_search"],
  ["Read the contents of notes.txt", "read_file"],
  ["What is 15 percent of 240?", "calculator"],
  ["Translate this paragraph into Japanese", "translate_text"],
  ["What's on my calendar next Friday?", "list_calendar_events"],
];

const TOP_K = 3;

// ---------------------------------------------------------------------------
// Vector helpers  (provided — do not edit)
// ---------------------------------------------------------------------------

/** Lowercase word tokens (letters/digits). */
function tokenize(text: string): string[] {
  return text.toLowerCase().match(/[a-z0-9]+/g) ?? [];
}

/** Sparse count vector: word -> count. */
function bagOfWords(text: string): Map<string, number> {
  const counts = new Map<string, number>();
  for (const token of tokenize(text)) {
    counts.set(token, (counts.get(token) ?? 0) + 1);
  }
  return counts;
}

/** Cosine similarity for sparse maps OR dense embedding arrays. */
function cosine(a: Vec, b: Vec): number {
  let dot = 0;
  let normA = 0;
  let normB = 0;
  if (a instanceof Map && b instanceof Map) {
    for (const [word, count] of a) dot += count * (b.get(word) ?? 0);
    for (const count of a.values()) normA += count * count;
    for (const count of b.values()) normB += count * count;
  } else if (Array.isArray(a) && Array.isArray(b)) {
    for (let i = 0; i < a.length; i++) {
      dot += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }
  } else {
    throw new Error("cosine: mixed vector kinds");
  }
  if (normA === 0 || normB === 0) return 0;
  return dot / (Math.sqrt(normA) * Math.sqrt(normB));
}

/** Offline default vectorizer: one bag-of-words map per text. */
async function bowVectorize(texts: string[]): Promise<Vec[]> {
  return texts.map(bagOfWords);
}

/** --embed path: real embeddings through llm-core (never a vendor SDK). */
function makeEmbedVectorize(): VectorizeFn {
  const provider = getProvider();
  return async (texts: string[]) => (await provider.embed(texts)).vectors;
}

/**
 * The raw signature text: name (de-underscored) + description. This is what
 * naive retrieval indexes — and what the selector below "reads".
 */
function toolSignature(t: ToolDef): string {
  return t.name.replace(/_/g, " ") + " " + t.description;
}

// ---------------------------------------------------------------------------
// The selector  (provided — do not edit)
// ---------------------------------------------------------------------------

// Up to this many schemas the scripted "model" stays reliable; beyond it,
// lexically confusable schemas can distract it (the measured failure mode).
const FOCUS_BUDGET = 5;

/**
 * Deterministic stand-in for the model's tool choice.
 *
 * - Scores every passed schema: cosine(query, raw signature text).
 * - Picks the labeled (correct) tool IF it was passed AND either the schema
 *   list fits the focus budget or no wrong tool outscores it.
 * - Otherwise picks the highest-scoring WRONG tool (a "confusion").
 *
 * This makes the full-list-vs-top-k accuracy comparison offline and exactly
 * reproducible, while behaving the way evals show real models behave.
 */
async function scriptedSelector(
  query: string,
  toolsPassed: ToolDef[],
  labeled: string,
): Promise<string> {
  const qVec = bagOfWords(query);
  const scores = new Map(
    toolsPassed.map((t) => [t.name, cosine(qVec, bagOfWords(toolSignature(t)))]),
  );
  let bestWrongName = "";
  let bestWrongScore = -1;
  for (const [name, score] of scores) {
    if (name !== labeled && score > bestWrongScore) {
      bestWrongName = name;
      bestWrongScore = score;
    }
  }
  const labeledScore = scores.get(labeled);
  if (
    labeledScore !== undefined &&
    (toolsPassed.length <= FOCUS_BUDGET || labeledScore >= bestWrongScore)
  ) {
    return labeled;
  }
  return bestWrongName;
}

/** --live path: the real model picks the tool, via llm-core. */
function makeLiveSelector(): SelectorFn {
  const provider = getProvider();
  return async (query, toolsPassed, _labeled) => {
    // The real model never sees the answer key.
    const menu = toolsPassed.map((t) => `- ${t.name}: ${t.description}`).join("\n");
    const prompt =
      "Pick the single best tool for the user request.\n" +
      `Tools:\n${menu}\n\nRequest: ${query}\n` +
      "Reply with ONLY the tool name.";
    const reply = (
      await provider.chat([{ role: "user", content: prompt }], {
        temperature: 0,
        maxTokens: 20,
      })
    ).text;
    const names = new Set(toolsPassed.map((t) => t.name));
    for (const token of reply.toLowerCase().match(/[a-z0-9_]+/g) ?? []) {
      if (names.has(token)) return token;
    }
    return reply.trim();
  };
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these four
// ---------------------------------------------------------------------------

/**
 * Build the RETRIEVAL text for one tool — richer than the raw signature.
 *
 * A user says "how much is 100 USD in yen?", not "exchange an amount of money
 * between two currencies", so indexing the signature alone misses
 * intent-phrased queries. Combine everything that carries meaning:
 *
 *   - the tool name, with underscores turned into spaces (so "db_query"
 *     matches the words "db" and "query"),
 *   - the raw description string,
 *   - the parameter names (the keys of t.parameters.properties),
 *   - the tool's pre-generated use-case line from USE_CASES.
 *
 * Join all of those pieces, space-separated, into one string and return it.
 */
function augmentDescription(t: ToolDef): string {
  // TODO: implement augmentDescription (name + description + param names + use-case)
  throw new Error("TODO: implement augmentDescription()");
}

/**
 * Index the toolbox: one vector per tool, paired with its definition.
 *
 * `textFn` decides what text represents each tool (default:
 * augmentDescription; the harness also passes toolSignature to build the
 * naive baseline index).
 *
 *   - Build the list of texts by applying textFn to every tool.
 *   - Vectorize them in ONE vectorize(texts) call (one batch — this matters
 *     when the vectorizer is a real embeddings API).
 *   - Pair each tool with its vector (same order) and return the list of
 *     [tool, vector] tuples.
 */
async function indexToolbox(
  tools: ToolDef[],
  vectorize: VectorizeFn,
  textFn: (t: ToolDef) => string = augmentDescription,
): Promise<Array<[ToolDef, Vec]>> {
  // TODO: implement indexToolbox (texts -> one vectorize batch -> pairs)
  throw new Error("TODO: implement indexToolbox()");
}

/**
 * Return the k tool definitions most semantically similar to the query.
 *
 *   - Vectorize the query with the SAME vectorize function used to build the
 *     index (it takes a list of texts — take the first vector back out).
 *   - Score every [tool, vector] entry in the index with cosine().
 *   - Sort by score descending; Array.prototype.sort is stable, so equal
 *     scores keep registry order (deterministic).
 *   - Return just the tool objects (not the scores) of the first k entries.
 */
async function retrieveTools(
  index: Array<[ToolDef, Vec]>,
  query: string,
  vectorize: VectorizeFn,
  k: number = TOP_K,
): Promise<ToolDef[]> {
  // TODO: implement retrieveTools (top-k by cosine, descending, stable)
  throw new Error("TODO: implement retrieveTools()");
}

/**
 * Estimate the prompt-token cost of shipping these tool schemas.
 *
 * Every schema you pass is prompt tokens on EVERY call, relevant or not.
 * Serialize each tool object to a JSON string (JSON.stringify), sum the
 * string lengths over all passed tools, and return the total divided by 4
 * (rounded down) — the standard ~4-characters-per-token heuristic.
 */
function measureTokenCost(toolsPassed: ToolDef[]): number {
  // TODO: implement measureTokenCost (serialized-schema chars / 4, rounded down)
  throw new Error("TODO: implement measureTokenCost()");
}

// ---------------------------------------------------------------------------
// Harness  (provided — do not edit)
// ---------------------------------------------------------------------------

async function main() {
  const useEmbed = process.argv.includes("--embed");
  const useLive = process.argv.includes("--live");
  const vectorize = useEmbed ? makeEmbedVectorize() : bowVectorize;
  const selector: SelectorFn = useLive ? makeLiveSelector() : scriptedSelector;

  console.log("Task 6 — Semantic tool discovery: the toolbox");
  console.log(
    `  retrieval: ${useEmbed ? "provider.embed()" : "bag-of-words (offline)"}`,
  );
  console.log(`  selector : ${useLive ? "live model" : "scripted (deterministic)"}`);
  console.log(
    `  toolbox  : ${TOOLS.length} tools, eval set: ${EVAL_SET.length} queries, k=${TOP_K}\n`,
  );

  const augIndex = await indexToolbox(TOOLS, vectorize); // what you ship
  const rawIndex = await indexToolbox(TOOLS, vectorize, toolSignature); // naive baseline

  const fullCost = measureTokenCost(TOOLS);

  let hitsAug = 0;
  let hitsRaw = 0;
  const fullCorrect: boolean[] = [];
  const topkCorrect: boolean[] = [];
  const topkCosts: number[] = [];
  let augOnlyWin: [string, string] | null = null;

  console.log(
    `${"query".padEnd(44)} ${"full-list pick".padEnd(22)} ${"top-3 pick".padEnd(22)} tokens (top-3/full)`,
  );
  console.log("-".repeat(110));
  for (const [query, labeled] of EVAL_SET) {
    const topAug = await retrieveTools(augIndex, query, vectorize);
    const topRaw = await retrieveTools(rawIndex, query, vectorize);
    const augHit = topAug.some((t) => t.name === labeled);
    const rawHit = topRaw.some((t) => t.name === labeled);
    if (augHit) hitsAug++;
    if (rawHit) hitsRaw++;
    if (augHit && !rawHit && augOnlyWin === null) augOnlyWin = [query, labeled];

    const pickFull = await selector(query, TOOLS, labeled);
    const pickTopk = await selector(query, topAug, labeled);
    fullCorrect.push(pickFull === labeled);
    topkCorrect.push(pickTopk === labeled);

    const costK = measureTokenCost(topAug);
    topkCosts.push(costK);
    const markF = pickFull === labeled ? "✓" : "✗";
    const markK = pickTopk === labeled ? "✓" : "✗";
    console.log(
      `${query.padEnd(44)} ${markF} ${pickFull.padEnd(20)} ${markK} ${pickTopk.padEnd(20)} ` +
        `${String(costK).padStart(4)}/${fullCost} (${((100 * costK) / fullCost).toFixed(0)}%)`,
    );
  }

  const accFull = fullCorrect.filter(Boolean).length;
  const accTopk = topkCorrect.filter(Boolean).length;
  console.log("-".repeat(110));
  console.log(
    `retrieval hit-rate (top-${TOP_K}): augmented ${hitsAug}/${EVAL_SET.length}, ` +
      `raw-signature ${hitsRaw}/${EVAL_SET.length}`,
  );
  console.log(
    `selection accuracy: full-list ${accFull}/${EVAL_SET.length}, ` +
      `top-${TOP_K} ${accTopk}/${EVAL_SET.length}`,
  );
  if (augOnlyWin) {
    const [q, t] = augOnlyWin;
    console.log(
      `augmentation win: '${q}' -> ${t} is in the augmented top-${TOP_K} ` +
        `but NOT in the raw-signature top-${TOP_K}\n  (the use-case line ` +
        `carries the intent words the signature lacks)`,
    );
  }

  // ── Acceptance checks ──────────────────────────────────────────────────
  console.log("\nAcceptance:");
  const okHits = hitsAug >= 9;
  const okAcc =
    accTopk >= accFull &&
    accFull <= EVAL_SET.length - 2 &&
    fullCorrect.every((f, i) => topkCorrect[i] || !f);
  const okCost = topkCosts.every((c) => c < 0.25 * fullCost);
  const okAug = augOnlyWin !== null;
  const maxCost = Math.max(...topkCosts);
  console.log(
    `  [${okHits ? "x" : " "}] correct tool in top-${TOP_K} for >= 9/10 queries (${hitsAug}/10)`,
  );
  console.log(
    `  [${okAcc ? "x" : " "}] top-${TOP_K} selection beats the full-list baseline ` +
      `(${accTopk} vs ${accFull}; full list makes >= 2 mistakes; ` +
      `top-${TOP_K} wins or ties on every query)`,
  );
  console.log(
    `  [${okCost ? "x" : " "}] top-${TOP_K} schema cost < 25% of full-list on every ` +
      `query (max ${maxCost}/${fullCost} = ${((100 * maxCost) / fullCost).toFixed(0)}%)`,
  );
  console.log(
    `  [${okAug ? "x" : " "}] augmented descriptions beat raw-signature retrieval ` +
      `on at least one query`,
  );

  if (okHits && okAcc && okCost && okAug) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

main().catch(console.error);
