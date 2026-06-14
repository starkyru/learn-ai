/**
 * hello.ts — your first LLM call.
 *
 * What it teaches:
 *   The minimal shape of every exercise in this course — get a provider, send
 *   one message, read the answer plus the model id and token usage off the
 *   result. There is no magic beyond this.
 *
 * How to run (from the repo root):
 *   pnpm tsx modules/00-setup/ts/hello.ts
 *
 *   By default this uses LLM_PROVIDER from your .env (ollama unless changed).
 *   To try a different provider without editing .env, pass a name to
 *   getProvider(), e.g. getProvider("nvidia").
 */

import { getProvider } from "@learn-ai/llm-core";

const PROMPT = "Explain what a large language model is, in 2 sentences.";

async function main(): Promise<void> {
  // No argument -> use the provider named in LLM_PROVIDER (default: ollama).
  // Swap to getProvider("anthropic") / ("openai") / ("nvidia") to force one.
  const llm = getProvider();

  // A conversation is an array of messages. Here, a single user turn.
  const result = await llm.chat([{ role: "user", content: PROMPT }]);

  console.log(`Provider : ${llm.name}`);
  console.log(`Model    : ${result.model}`);
  console.log(`Prompt   : ${PROMPT}\n`);
  console.log(result.text.trim());

  // Token usage is what paid providers bill on — keep it visible.
  console.log(
    `\nTokens   : input=${result.usage?.inputTokens} output=${result.usage?.outputTokens}`,
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
