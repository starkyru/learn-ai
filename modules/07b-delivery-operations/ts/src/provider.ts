/**
 * The `@learn-ai/llm-core` seam.
 *
 * Every model call goes through the provider-agnostic client — we never import a
 * vendor SDK directly. Tests inject a fake provider implementing the same
 * `LLMProvider` interface, so the request path runs deterministically offline.
 */

import type { Config } from "./config.js";
import type { LLMProvider, ProviderName } from "@learn-ai/llm-core";

/**
 * Construct the real provider selected by configuration.
 *
 * `@learn-ai/llm-core` is imported *dynamically* (not at module top level) on
 * purpose: it is an ESM-only package that resolves env/credentials at import
 * time. Loading it lazily keeps it out of the synchronous module graph, so tests
 * that inject a fake provider never load the real client, and credential
 * resolution is deferred to the first real model call.
 */
export async function buildDefaultProvider(config: Config): Promise<LLMProvider> {
  const { getProvider } = await import("@learn-ai/llm-core");
  // `getProvider` reads the provider-specific credentials from the environment;
  // we only pass the validated provider name.
  return getProvider(config.provider as ProviderName);
}
