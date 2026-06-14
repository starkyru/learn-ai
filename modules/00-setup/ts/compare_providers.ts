/**
 * compare_providers.ts — same prompt, all four providers, side by side.
 *
 * What it teaches:
 *   The provider abstraction in action: the exact same call works against four
 *   different backends. And a real-world habit — gracefully SKIP a provider
 *   whose key or server is missing (catch the error) instead of crashing.
 *
 * How to run (from the repo root):
 *   pnpm tsx modules/00-setup/ts/compare_providers.ts
 *
 *   You only need ONE provider configured for this to be useful; the rest are
 *   reported as skipped with a friendly reason.
 */

import { getProvider, type ProviderName } from "@learn-ai/llm-core";

const PROMPT = "Explain what a large language model is, in 2 sentences.";

const PROVIDERS: ProviderName[] = ["openai", "anthropic", "ollama", "nvidia"];

async function tryProvider(name: ProviderName): Promise<void> {
  console.log(`\n=== ${name} ${"=".repeat(Math.max(0, 40 - name.length))}`);

  // Two things can go wrong and BOTH should be non-fatal:
  //   * getProvider() throws if a required API key env var is missing.
  //   * chat() rejects if the server is unreachable or the key is rejected.
  let llm;
  try {
    llm = getProvider(name);
  } catch (err) {
    console.log(`  [skipped] ${(err as Error).message}`);
    return;
  }

  try {
    const result = await llm.chat([{ role: "user", content: PROMPT }]);
    console.log(`  model : ${result.model}`);
    console.log(
      `  tokens: input=${result.usage?.inputTokens} output=${result.usage?.outputTokens}`,
    );
    console.log(`  answer: ${result.text.trim()}`);
  } catch (err) {
    console.log(`  [skipped] call failed: ${(err as Error).message}`);
  }
}

async function main(): Promise<void> {
  console.log(`Prompt: ${PROMPT}`);
  // Sequential on purpose so the side-by-side output stays readable.
  for (const name of PROVIDERS) {
    await tryProvider(name);
  }
  console.log("\nDone. Providers without a key/server were skipped, not fatal.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
