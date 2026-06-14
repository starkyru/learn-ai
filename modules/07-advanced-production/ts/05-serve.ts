/**
 * Task 5 — Serve it 🟢
 *
 * What this teaches:
 *   - Wrapping an LLM pipeline in an HTTP server is the final step to making
 *     it accessible to other services, UIs, and scripts.
 *   - A minimal Node.js HTTP server (no framework needed) shows the low-level
 *     mechanics: parse the request body, call the pipeline, write the response.
 *   - Streaming responses (chunked transfer) dramatically improve perceived
 *     latency for long outputs — the client sees tokens as they arrive.
 *   - Health check endpoints are essential for load balancers and uptime monitors.
 *
 * How to run:
 *   pnpm tsx modules/07-advanced-production/ts/05-serve.ts
 *
 * Then test it:
 *   curl http://localhost:3000/health
 *   curl -X POST http://localhost:3000/chat \
 *        -H "Content-Type: application/json" \
 *        -d '{"message": "What is the capital of France?"}'
 *   curl -X POST http://localhost:3000/chat/stream \
 *        -H "Content-Type: application/json" \
 *        -d '{"message": "Explain recursion in 3 sentences."}'
 */

import * as http from "node:http";
import { getProvider } from "@learn-ai/llm-core";

const PORT = Number(process.env.PORT ?? 3000);

// ---------------------------------------------------------------------------
// Request body parser
// ---------------------------------------------------------------------------

// TODO 1: Implement readBody(req).
//         Read the IncomingMessage body as a Buffer, concatenate chunks, then
//         JSON.parse the result. Return the parsed object.
//         If parsing fails, throw a descriptive error.

async function readBody(req: http.IncomingMessage): Promise<unknown> {
  throw new Error("TODO: implement readBody");
}

// ---------------------------------------------------------------------------
// Route handlers
// ---------------------------------------------------------------------------

// GET /health — liveness probe
function handleHealth(res: http.ServerResponse): void {
  // TODO 2: Write a 200 response with Content-Type: application/json.
  //         Body: { "status": "ok", "timestamp": <ISO string> }
  throw new Error("TODO: implement handleHealth");
}

// POST /chat — synchronous (waits for full response)
async function handleChat(
  req: http.IncomingMessage,
  res: http.ServerResponse
): Promise<void> {
  // TODO 3: Parse the body. Expect { message: string }.
  //         Validate that message is a non-empty string.
  //         Call getProvider().chat([{ role: "user", content: message }]).
  //         Write a 200 JSON response:
  //           { "text": <result.text>, "model": <result.model>,
  //             "inputTokens": ..., "outputTokens": ... }
  //         On error, write a 500 JSON response: { "error": <message> }

  throw new Error("TODO: implement handleChat");
}

// POST /chat/stream — streaming (tokens arrive as they're generated)
async function handleChatStream(
  req: http.IncomingMessage,
  res: http.ServerResponse
): Promise<void> {
  // TODO 4: Parse the body and validate the message field (same as above).
  //         Set response headers:
  //           Content-Type: text/event-stream
  //           Cache-Control: no-cache
  //           Connection: keep-alive
  //         Call getProvider().chatStream([{ role: "user", content: message }]).
  //         For each chunk in the async iterable, write it to res with res.write().
  //         End the response with res.end() after the loop.

  throw new Error("TODO: implement handleChatStream");
}

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------

async function router(
  req: http.IncomingMessage,
  res: http.ServerResponse
): Promise<void> {
  const { method, url } = req;

  // TODO 5: Route requests to the right handler:
  //   GET  /health      -> handleHealth
  //   POST /chat        -> handleChat
  //   POST /chat/stream -> handleChatStream
  //   anything else     -> 404 JSON { error: "Not found" }

  try {
    if (method === "GET" && url === "/health") {
      handleHealth(res);
    } else if (method === "POST" && url === "/chat") {
      await handleChat(req, res);
    } else if (method === "POST" && url === "/chat/stream") {
      await handleChatStream(req, res);
    } else {
      res.writeHead(404, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "Not found" }));
    }
  } catch (err) {
    console.error("Unhandled error:", err);
    if (!res.headersSent) {
      res.writeHead(500, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "Internal server error" }));
    }
  }
}

// ---------------------------------------------------------------------------
// Start server
// ---------------------------------------------------------------------------

const server = http.createServer(router);

server.listen(PORT, () => {
  const provider = getProvider();
  console.log(`LLM server running on http://localhost:${PORT}`);
  console.log(`Provider: ${provider.name} / ${provider.chatModel}`);
  console.log("\nEndpoints:");
  console.log(`  GET  http://localhost:${PORT}/health`);
  console.log(`  POST http://localhost:${PORT}/chat`);
  console.log(`  POST http://localhost:${PORT}/chat/stream`);
  console.log("\nExample:");
  console.log(
    `  curl -X POST http://localhost:${PORT}/chat \\`
  );
  console.log(
    `       -H "Content-Type: application/json" \\`
  );
  console.log(
    `       -d '{"message": "What is the capital of France?"}'`
  );

  // TODO 6 (stretch): Add a POST /rag endpoint that runs a mini RAG pipeline:
  //   - Embed the query (provider.embed)
  //   - Retrieve the top-k chunks from an in-memory vector store
  //     (re-use your code from module 04/05)
  //   - Generate an answer grounded in those chunks
  //   This combines everything from the course into one deployable service.
});

server.on("error", (err) => {
  console.error("Server error:", err);
  process.exit(1);
});
