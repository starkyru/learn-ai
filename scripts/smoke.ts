/**
 * TypeScript smoke test — verifies your provider is reachable and returns a response.
 *
 * Run with:
 *   pnpm smoke
 *
 * (Defined in root package.json as: "smoke": "tsx scripts/smoke.ts")
 */

import { getProvider } from "@learn-ai/llm-core";

async function main(): Promise<void> {
  let llm;
  try {
    llm = getProvider();
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error("Could not initialise provider:", message);
    console.error(
      'Tip: copy .env.example to .env, set LLM_PROVIDER and the matching API key (or start Ollama for the free path).',
    );
    process.exit(1);
  }

  console.log(`Provider : ${llm.name}`);
  console.log(`Model    : ${llm.chatModel}`);

  try {
    const result = await llm.chat([
      { role: "user", content: "Reply with exactly: ok" },
    ]);

    console.log(`Reply    : ${result.text.trim()}`);

    if (result.usage) {
      const { inputTokens, outputTokens } = result.usage;
      if (inputTokens != null || outputTokens != null) {
        console.log(`Tokens   : ${inputTokens ?? "?"} in / ${outputTokens ?? "?"} out`);
      }
    }

    console.log("\nSmoke test passed.");
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error("\nRequest failed:", message);
    console.error(
      "Check that your API key is valid and the provider is reachable (Ollama: is the server running?).",
    );
    process.exit(1);
  }
}

main();
