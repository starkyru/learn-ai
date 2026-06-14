/**
 * Module 22 — AI Product UX: TypeScript backend (Express + SSE)
 *
 * What this teaches:
 *   - Streaming SSE responses from an LLM to a browser client.
 *   - Citations: the LLM returns structured JSON with answer + sources;
 *     the server sends typed SSE events the client renders.
 *   - Feedback capture: thumbs-up/down + "looks wrong" stored to JSONL.
 *   - Approval flow: a /actions/approve endpoint gates risky actions behind
 *     a server-side one-time token.
 *
 * How to run:
 *   pnpm tsx modules/22-ai-product-ux/ts/server.ts
 *
 *   Then open: modules/22-ai-product-ux/web/index.html
 *
 * Dependencies (in package.json): express, @types/express
 */

import express, { Request, Response, NextFunction } from "express";
import { createWriteStream, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { randomUUID, randomBytes } from "node:crypto";
import { getProvider, ChatMessage } from "@learn-ai/llm-core";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = 3100;
const FEEDBACK_LOG = resolve(__dirname, "feedback.jsonl");
const ACTIONS_LOG = resolve(__dirname, "actions.jsonl");

// In-memory approval token store (token → { action, payload, requestedAt })
const pendingApprovals = new Map<string, { action: string; payload: unknown; requestedAt: number }>();

// ---------------------------------------------------------------------------
// RAG stub corpus (same as Python server)
// ---------------------------------------------------------------------------

const CORPUS = [
  {
    id: "doc1", title: "learn-ai Course Overview", url: "README.md",
    content: "learn-ai is a hands-on AI course monorepo covering LLMs, RAG, and agents in both TypeScript and Python. It has modules numbered 00–23.",
  },
  {
    id: "doc2", title: "Module 05 — RAG", url: "modules/05-rag/README.md",
    content: "Module 05 covers Retrieval-Augmented Generation: chunk, embed, retrieve, rerank, generate, cite, and evaluate. It builds a full RAG pipeline.",
  },
  {
    id: "doc3", title: "LLM Providers", url: "packages/ts/llm-core/src/index.ts",
    content: "Supported providers: openai, anthropic, ollama, nvidia. Set LLM_PROVIDER env var to switch. Default is ollama. getProvider() reads the env var.",
  },
  {
    id: "doc4", title: "Module 07 — Advanced & Production", url: "modules/07-advanced-production/README.md",
    content: "Module 07 covers eval harnesses, JSONL observability logging, prompt caching, guardrails, and serving with FastAPI and Node.js.",
  },
  {
    id: "doc5", title: "Module 21 — LLMOps & Eval", url: "modules/21-llmops-eval/README.md",
    content: "Module 21 covers versioned eval sets, experiment comparison, regression gates in CI, human review queues, and production monitoring.",
  },
];

function retrieveContext(_question: string) {
  // TODO (task 2 extension): embed the question and rank by cosine similarity.
  return CORPUS;
}

function buildRagPrompt(question: string, docs: typeof CORPUS): string {
  const context = docs
    .map((d) => `[${d.id}] ${d.title}\n${d.content}`)
    .join("\n\n");
  return (
    "You are a helpful assistant for the learn-ai course. " +
    "Answer the question using ONLY the provided context documents. " +
    "If the context does not contain the answer, say so clearly.\n\n" +
    'IMPORTANT: After your answer, output a JSON block on its own line:\n' +
    '{"citations": ["<doc_id>", ...]}\n' +
    "Include only the doc IDs you actually used.\n\n" +
    `Context:\n${context}`
  );
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

const app = express();
app.use(express.json());

// CORS — allow the local HTML file to call us
app.use((_req: Request, res: Response, next: NextFunction) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  next();
});
app.options("*", (_req: Request, res: Response) => res.sendStatus(204));

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

app.get("/health", (_req: Request, res: Response) => {
  res.json({ status: "ok", module: "22-ai-product-ux" });
});

// ---------------------------------------------------------------------------
// Task 1 — POST /ask/stream  (SSE streaming)
// ---------------------------------------------------------------------------

app.post("/ask/stream", async (req: Request, res: Response) => {
  const { question = "" } = req.body as { question?: string };
  if (!question.trim()) {
    res.status(400).json({ error: "question is required" });
    return;
  }

  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("X-Accel-Buffering", "no");
  res.flushHeaders();

  const sse = (payload: object) => res.write(`data: ${JSON.stringify(payload)}\n\n`);

  const provider = getProvider();
  const docs = retrieveContext(question);
  const systemPrompt = buildRagPrompt(question, docs);

  const messages: ChatMessage[] = [
    { role: "system", content: systemPrompt },
    { role: "user", content: question },
  ];

  let accumulated = "";
  let sentCitations = false;
  const citationIds: string[] = [];

  try {
    for await (const chunk of provider.chatStream(messages)) {
      accumulated += chunk;

      // Detect citations JSON block
      if (!sentCitations && accumulated.includes('{"citations"')) {
        const idx = accumulated.indexOf('{"citations"');
        const jsonPart = accumulated.slice(idx);
        try {
          const parsed = JSON.parse(jsonPart) as { citations: string[] };
          citationIds.push(...parsed.citations);
          sentCitations = true;
          continue; // Don't emit the JSON as a token
        } catch {
          // JSON not yet complete
        }
      }

      if (!sentCitations) {
        sse({ type: "token", text: chunk });
      }
    }

    // Send citation events
    const docMap = Object.fromEntries(docs.map((d) => [d.id, d]));
    for (const cid of citationIds) {
      if (docMap[cid]) sse({ type: "citation", doc: docMap[cid] });
    }

    const confidence = citationIds.length > 0 ? 0.85 : 0.40;
    sse({ type: "done", confidence });
  } catch (err) {
    sse({ type: "error", message: String(err) });
  }

  res.end();
});

// ---------------------------------------------------------------------------
// Task 3 — POST /ask  (synchronous with confidence/failure states)
// ---------------------------------------------------------------------------

app.post("/ask", async (req: Request, res: Response) => {
  const { question = "" } = req.body as { question?: string };
  if (!question.trim()) {
    res.status(400).json({ error: "question is required" });
    return;
  }

  const provider = getProvider();
  const docs = retrieveContext(question);
  const messages: ChatMessage[] = [
    { role: "system", content: buildRagPrompt(question, docs) },
    { role: "user", content: question },
  ];

  try {
    const result = await provider.chat(messages);
    let answerText = result.text;
    const citationIds: string[] = [];

    if (answerText.includes('{"citations"')) {
      const idx = answerText.indexOf('{"citations"');
      const jsonPart = answerText.slice(idx);
      answerText = answerText.slice(0, idx).trim();
      try {
        citationIds.push(...(JSON.parse(jsonPart) as { citations: string[] }).citations);
      } catch { /* ignore */ }
    }

    const docMap = Object.fromEntries(docs.map((d) => [d.id, d]));
    const citedDocs = citationIds.filter((id) => docMap[id]).map((id) => docMap[id]);
    const confidence = citedDocs.length > 0 ? 0.85 : 0.35;

    res.json({ answer: answerText, citations: citedDocs, confidence, model: result.model });
  } catch (err) {
    // Structured error so the client can render the error state
    res.json({ error: String(err), confidence: 0.0 });
  }
});

// ---------------------------------------------------------------------------
// Task 4 — POST /feedback
// ---------------------------------------------------------------------------

app.post("/feedback", (req: Request, res: Response) => {
  const { question = "", answer = "", rating = "", note = "" } =
    req.body as { question?: string; answer?: string; rating?: string; note?: string };

  const entry = {
    id: randomUUID(),
    timestamp: new Date().toISOString(),
    question,
    answer,
    rating,
    note,
  };

  // TODO (task 4): implement the write to FEEDBACK_LOG
  const line = JSON.stringify(entry) + "\n";
  // Ensure parent dir exists
  mkdirSync(dirname(FEEDBACK_LOG), { recursive: true });
  const ws = createWriteStream(FEEDBACK_LOG, { flags: "a" });
  ws.write(line);
  ws.end();

  res.json({ status: "ok", id: entry.id });
});

// ---------------------------------------------------------------------------
// Task 5 — Approval flow
// ---------------------------------------------------------------------------

app.post("/actions/request", (req: Request, res: Response) => {
  const { action = "", payload = {} } =
    req.body as { action?: string; payload?: unknown };

  if (!action) {
    res.status(400).json({ error: "action is required" });
    return;
  }

  const token = randomBytes(18).toString("base64url");
  pendingApprovals.set(token, { action, payload, requestedAt: Date.now() });

  // Auto-expire after 120 s
  setTimeout(() => pendingApprovals.delete(token), 120_000);

  res.json({ token, expires_in_s: 120 });
});

app.post("/actions/approve", (req: Request, res: Response) => {
  const { token = "", approved = false } =
    req.body as { token?: string; approved?: boolean };

  const pending = pendingApprovals.get(token);
  if (!pending) {
    res.json({ status: "expired" });
    return;
  }

  if (Date.now() - pending.requestedAt > 120_000) {
    pendingApprovals.delete(token);
    res.json({ status: "expired" });
    return;
  }

  pendingApprovals.delete(token);

  const entry = {
    id: randomUUID(),
    timestamp: new Date().toISOString(),
    action: pending.action,
    payload: pending.payload,
    approved,
  };
  mkdirSync(dirname(ACTIONS_LOG), { recursive: true });
  const ws = createWriteStream(ACTIONS_LOG, { flags: "a" });
  ws.write(JSON.stringify(entry) + "\n");
  ws.end();

  if (approved) {
    res.json({ status: "executed", action: pending.action });
  } else {
    res.json({ status: "rejected" });
  }
});

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

app.listen(PORT, () => {
  console.log(`Module 22 backend running at http://localhost:${PORT}`);
  console.log(`Open modules/22-ai-product-ux/web/index.html to use the UI`);
});
