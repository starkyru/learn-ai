/**
 * Task 4 — Output parsing & guardrails 🟢
 *
 * What this teaches:
 *   - Forcing a constrained output format (e.g. "one word only") is harder
 *     than it sounds. Models add punctuation, explanations, or extra words.
 *   - Guardrails = validate the output, and if it fails, retry with feedback.
 *   - The repair loop: prompt → parse → fail → tell the model what's wrong
 *     → try again. This is more robust than hoping the first call is perfect.
 *   - After 2-3 failed retries you should give up and surface the error —
 *     infinite retry loops are a production anti-pattern.
 *
 * How to run:
 *   pnpm tsx modules/03-prompting/ts/04-guardrails.ts
 */

import { getProvider, ChatMessage } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Constraint: the model must respond with exactly one of three labels.
//             No punctuation. No explanation. One word.
// ---------------------------------------------------------------------------
const VALID_LABELS = ["positive", "negative", "neutral"] as const;
type SentimentLabel = typeof VALID_LABELS[number];

const SYSTEM_PROMPT = `You are a sentiment classifier.
Respond with EXACTLY one word — no punctuation, no explanation, no extra text.
The word must be one of: positive, negative, neutral.`;

// ---------------------------------------------------------------------------
// TODO 1: Implement parseLabel.
//         Take the raw model output string, clean it, and return the matching
//         SentimentLabel. Throw a descriptive error if the output doesn't
//         match any valid label (after cleaning).
//         Cleaning steps (in order):
//           1. Trim whitespace.
//           2. Lowercase.
//           3. Remove punctuation: .replace(/[^a-z]/g, "")
// ---------------------------------------------------------------------------
function parseLabel(raw: string): SentimentLabel {
  // TODO: implement
  const cleaned = raw.trim().toLowerCase().replace(/[^a-z]/g, "");
  if (VALID_LABELS.includes(cleaned as SentimentLabel)) {
    return cleaned as SentimentLabel;
  }
  throw new Error(`Invalid label: "${raw}" → cleaned: "${cleaned}". Expected one of: ${VALID_LABELS.join(", ")}`);
}

// ---------------------------------------------------------------------------
// TODO 2: Implement classifyWithGuardrails.
//         Try up to maxRetries times to get a valid label.
//         On parse failure: add a user message explaining what went wrong and
//         asking the model to try again (repair in the conversation history).
//         Return the valid label on success, throw after exhausting retries.
// ---------------------------------------------------------------------------
async function classifyWithGuardrails(
  text: string,
  maxRetries = 3,
): Promise<SentimentLabel> {
  const llm = getProvider();

  const messages: ChatMessage[] = [
    { role: "system", content: SYSTEM_PROMPT },
    { role: "user", content: text },
  ];

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    // TODO: call llm.chat(messages), try parseLabel on result.text
    //       On ParseError:
    //         - append { role: "assistant", content: result.text } to messages
    //         - append { role: "user", content: `Invalid output: "${result.text}". Respond with exactly one of: positive, negative, neutral.` }
    //         - continue the loop
    //       On success: return the label

    // const result = await llm.chat(messages);
    // try {
    //   return parseLabel(result.text);
    // } catch (err) {
    //   console.warn(`Attempt ${attempt + 1}: parse failed (${(err as Error).message})`);
    //   messages.push({ role: "assistant", content: result.text });
    //   messages.push({
    //     role: "user",
    //     content: `Invalid output: "${result.text}". Respond with EXACTLY one of: positive, negative, neutral.`,
    //   });
    // }

    console.log(`Attempt ${attempt + 1}: TODO — implement the retry loop above.`);
    break; // remove once implemented
  }

  throw new Error(`Failed to get a valid label after ${maxRetries} attempts.`);
}

// ---------------------------------------------------------------------------
// Demo inputs — some chosen to provoke edge-case outputs from the model.
// ---------------------------------------------------------------------------
const INPUTS = [
  "This is the best product I've ever used!",
  "Totally broken. Avoid at all costs.",
  "Meh. It's fine I guess.",
  "Not bad, not great — somewhere in the middle.",
  "I'm genuinely impressed. Five stars!", // model might respond "Five stars!" → should retry
];

async function main() {
  const llm = getProvider();
  console.log(`Provider: ${llm.name} / ${llm.chatModel}\n`);
  console.log("Classifying with guardrails (retry on invalid output):\n");

  for (const input of INPUTS) {
    try {
      const label = await classifyWithGuardrails(input);
      console.log(`"${input}"\n  → ${label}\n`);
    } catch (err) {
      console.error(`"${input}"\n  → FAILED: ${(err as Error).message}\n`);
    }
  }

  // -------------------------------------------------------------------------
  // TODO 3 (stretch): Add a second constraint — the model must also return a
  //         confidence score as a float between 0.0 and 1.0 in the format:
  //         "positive 0.92". Update parseLabel to return { label, confidence }
  //         and add validation for the confidence range.
  // -------------------------------------------------------------------------
}

main().catch(console.error);
