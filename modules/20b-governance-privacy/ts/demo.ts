/**
 * Proof-of-redaction demo (Module 20b, Task 1).
 *
 * Pipeline: redact a synthetic subject record -> build a prompt from ONLY the
 * survivors -> structured-log the request -> "send" it to a provider. The
 * provider is the shared `@learn-ai/llm-core` interface; a deterministic
 * `RecordingProvider` is injected so the run is offline and a test can inspect
 * what crossed the boundary.
 *
 * Run it:
 *   pnpm tsx modules/20b-governance-privacy/ts/demo.ts
 *
 * Not legal advice — see the module README.
 */

import type { ChatMessage, LLMProvider } from "@learn-ai/llm-core";
import { RecordingProvider } from "./fakes.js";
import {
  DEFAULT_POLICY,
  isRedactedRecord,
  RedactionPolicy,
  SYNTHETIC_SUBJECT,
  type RedactedRecord,
} from "./redaction.js";

export const LOGGER_NAME = "m20b.redaction";

export const SYSTEM_PROMPT =
  "You are a customer-support assistant. Use only the fields provided between " +
  "the <subject_fields> tags. Do not ask for or infer any identifier that is " +
  "not present.";

/** A structured-log sink — the injectable logging boundary. */
export type LogSink = (record: Record<string, unknown>) => void;

export interface DemoResult {
  redacted: RedactedRecord;
  prompt: string;
  messages: ChatMessage[];
  reply: string;
  dropped: string[];
}

/**
 * Assemble a prompt from an already-redacted record.
 *
 * Values live inside a labelled, delimited block. With real (non-synthetic)
 * input you would additionally escape/validate values so a field cannot forge
 * the closing delimiter — a small prompt-injection safeguard.
 */
function renderValue(value: unknown): string {
  // Non-scalars are JSON-encoded so a surviving nested field is visible rather
  // than rendered as an opaque "[object Object]".
  if (value !== null && typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function buildPrompt(redacted: RedactedRecord): string {
  // Refuse un-redacted input at runtime too (a caller may have cast past the
  // type). Authenticity is WeakSet-registry membership from redact(), which a
  // symbol-copy or Object.create() forgery cannot obtain. Honest scope: an
  // in-process adversary can call the provider directly — this catches
  // ACCIDENTAL misuse and mutation, not a malicious co-process.
  if (!isRedactedRecord(redacted)) {
    throw new TypeError(
      "buildPrompt requires a RedactedRecord from RedactionPolicy.redact(); " +
        "refusing un-redacted input.",
    );
  }
  const body = Object.entries(redacted)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => `- ${key}: ${renderValue(value)}`)
    .join("\n");
  return (
    "<subject_fields>\n" +
    `${body}\n` +
    "</subject_fields>\n" +
    "Answer the subject's support_topic in one short paragraph."
  );
}

/**
 * Redact `record`, log the request, and send it through `provider`.
 *
 * `provider` must satisfy the shared `LLMProvider` interface (a real client
 * from `getProvider()` or an injected fake). Nothing above the allowed
 * sensitivity is placed in the prompt, the log, or the provider call.
 */
export async function runRedactionDemo(
  record: Record<string, unknown>,
  provider: LLMProvider,
  opts: { policy?: RedactionPolicy; log?: LogSink } = {},
): Promise<DemoResult> {
  const policy = opts.policy ?? DEFAULT_POLICY;
  const log: LogSink = opts.log ?? ((r) => console.log(JSON.stringify(r)));

  const redacted = policy.redact(record);
  const prompt = buildPrompt(redacted);
  const messages: ChatMessage[] = [
    { role: "system", content: SYSTEM_PROMPT },
    { role: "user", content: prompt },
  ];

  // Audit only KNOWN (schema) field names — a user-supplied key may itself be
  // PII, so unknown keys are summarised as a count + non-reversible codes and
  // never written raw. `dropped` lists only known dropped fields.
  const knownActions = policy.knownFieldActions(record);
  const dropped = Object.keys(knownActions)
    .filter((name) => knownActions[name] === "drop")
    .sort();

  // Structured request log: known field names + actions, the unknown-field
  // digest, and the already-redacted record (masked/kept values only; dropped
  // and restricted values are, by construction, absent).
  log({
    event: "llm_request",
    provider: provider.name,
    model: provider.chatModel,
    field_actions: knownActions,
    dropped_fields: dropped,
    unknown_fields: policy.unknownFieldDigest(record),
    redacted,
    prompt_chars: prompt.length,
  });

  const result = await provider.chat(messages, {
    temperature: 0,
    maxTokens: 256,
  });
  return { redacted, prompt, messages, reply: result.text, dropped };
}

async function main(): Promise<void> {
  const provider = new RecordingProvider();
  const result = await runRedactionDemo(SYNTHETIC_SUBJECT, provider);

  console.log("\n--- dropped (never left the boundary) ---");
  console.log(result.dropped.join(", "));
  console.log("\n--- prompt actually sent ---");
  console.log(result.prompt);
  console.log("\n--- provider reply ---");
  console.log(result.reply);
}

// Run only when invoked directly (tsx/node), never when imported by a test.
// Avoids `import.meta` so this module also loads cleanly under jest (CJS).
const invokedPath = process.argv[1] ?? "";
if (invokedPath.endsWith("demo.ts") || invokedPath.endsWith("demo.js")) {
  void main();
}
