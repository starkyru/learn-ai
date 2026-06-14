/**
 * Task 2 — Streaming 🟢
 *
 * What this teaches:
 *   - Streaming returns tokens as they're generated, so the UI feels
 *     responsive even for long outputs. Under the hood the provider
 *     sends Server-Sent Events (SSE); the SDK turns them into an async
 *     iterable you consume with `for await`.
 *   - Time-to-first-token (TTFT) is the latency the user *feels*. Total
 *     generation time matters too, but TTFT is usually more noticeable.
 *   - Streaming changes error handling: you may get a partial response
 *     before an error mid-stream.
 *
 * How to run:
 *   pnpm tsx modules/02-llm-integration/ts/02-streaming.ts
 */

import { getProvider } from "@learn-ai/llm-core";

const PROMPT =
  "Explain how transformer attention works in exactly 5 bullet points, each 1-2 sentences.";

async function main() {
  const llm = getProvider();
  console.log(`Provider: ${llm.name} / ${llm.chatModel}\n`);
  console.log(`Prompt: ${PROMPT}\n`);
  console.log("--- streaming response ---");

  // ---------------------------------------------------------------------------
  // TODO 1: Record the wall-clock time before the first call so you can
  //         compute TTFT and total time. Use `performance.now()`.
  // ---------------------------------------------------------------------------
  const startTime = 0; // TODO: replace with performance.now()

  let firstTokenTime: number | null = null;
  let fullText = "";

  // ---------------------------------------------------------------------------
  // TODO 2: Call llm.chatStream() with a single user message containing PROMPT.
  //         Iterate over the async iterable. For each chunk:
  //           a) If it's the first chunk, record `firstTokenTime`.
  //           b) Write the chunk to stdout WITHOUT a newline so tokens appear
  //              inline: process.stdout.write(chunk)
  //           c) Append the chunk to `fullText`.
  // ---------------------------------------------------------------------------

  // const stream = llm.chatStream([{ role: "user", content: PROMPT }]);
  // for await (const chunk of stream) {
  //   if (firstTokenTime === null) firstTokenTime = performance.now();
  //   process.stdout.write(chunk);
  //   fullText += chunk;
  // }

  console.log("\nTODO: implement streaming above.");

  // ---------------------------------------------------------------------------
  // TODO 3: After the loop, print timing stats:
  //   - Time to first token  = firstTokenTime - startTime  (ms)
  //   - Total time           = performance.now() - startTime  (ms)
  //   - Tokens in output     = rough estimate: fullText.split(" ").length
  //   - Tokens/second        = tokens / (totalTime / 1000)
  // ---------------------------------------------------------------------------

  // const totalTime = performance.now() - startTime;
  // const ttft = firstTokenTime !== null ? firstTokenTime - startTime : null;
  // const words = fullText.split(/\s+/).filter(Boolean).length;
  // console.log("\n--- stats ---");
  // console.log(`TTFT:        ${ttft?.toFixed(0) ?? "N/A"} ms`);
  // console.log(`Total time:  ${totalTime.toFixed(0)} ms`);
  // console.log(`~Words out:  ${words}  (~${(words / (totalTime / 1000)).toFixed(1)} words/s)`);

  // ---------------------------------------------------------------------------
  // TODO 4 (stretch): Try the same prompt with llm.chat() (non-streaming) and
  //         compare the wall-clock time. They should be similar in total, but
  //         the non-streaming version shows nothing until fully done.
  // ---------------------------------------------------------------------------
}

main().catch(console.error);
