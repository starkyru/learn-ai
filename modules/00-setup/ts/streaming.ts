/**
 * streaming.ts — print tokens as they arrive.
 *
 * What it teaches:
 *   Streaming. Instead of waiting for the full answer, chatStream() yields text
 *   chunks as the model generates them. This is what makes chat UIs feel fast —
 *   the user reads token 1 while token 50 is still being computed.
 *
 * How to run (from the repo root):
 *   pnpm tsx modules/00-setup/ts/streaming.ts
 *
 *   Uses your default provider (LLM_PROVIDER). All four support streaming.
 */

import { getProvider } from "@learn-ai/llm-core";

const PROMPT =
  "In 3 short sentences, explain why streaming output feels faster to a user.";

async function main(): Promise<void> {
  const llm = getProvider();
  console.log(`Provider: ${llm.name} (${llm.chatModel})\n`);

  // chatStream() is an async iterable of string chunks. process.stdout.write
  // (not console.log) avoids inserting a newline after every chunk.
  for await (const chunk of llm.chatStream([{ role: "user", content: PROMPT }])) {
    process.stdout.write(chunk);
  }

  process.stdout.write("\n"); // final newline once the stream is exhausted
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
