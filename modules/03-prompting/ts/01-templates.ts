/**
 * Task 1 — Templates & roles 🟢
 *
 * What this teaches:
 *   - Raw string concatenation for prompts doesn't scale: typos in variable
 *     names are silent, escaping is error-prone, and the "shape" of the prompt
 *     is invisible. A tiny template helper solves all three.
 *   - The system role is the highest-trust part of the conversation. It sets
 *     persona, constraints, and output format. Users can't (easily) override it.
 *   - The user role is the request; the assistant role is the model's reply.
 *     Few-shot examples are also expressed as user/assistant pairs.
 *
 * How to run:
 *   pnpm tsx modules/03-prompting/ts/01-templates.ts
 */

import { getProvider, ChatMessage } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// TODO 1: Implement renderTemplate.
//         Replace every {{variable}} placeholder in `template` with the
//         corresponding value from `variables`. Throw an error if a placeholder
//         is referenced but not provided in `variables`.
//         Example:
//           renderTemplate("Hello, {{name}}! You are {{age}} years old.", { name: "Alice", age: "30" })
//           → "Hello, Alice! You are 30 years old."
// ---------------------------------------------------------------------------
export function renderTemplate(
  template: string,
  variables: Record<string, string>,
): string {
  // TODO: implement
  // Hint: use template.replace(/\{\{(\w+)\}\}/g, (_, key) => { ... })
  return template; // placeholder — remove and implement
}

// ---------------------------------------------------------------------------
// TODO 2: Define a library of reusable prompt templates.
//         Each template is just a string with {{...}} placeholders.
//         Add at least two: one for a task (e.g. summarisation) and one
//         for structured output (e.g. extraction).
// ---------------------------------------------------------------------------
export const TEMPLATES = {
  summarise: `Summarise the following text in {{max_sentences}} sentences or fewer.
Be concise and capture only the key points.

Text:
{{text}}`,

  classify: `Classify the sentiment of the following text as exactly one of:
positive, negative, or neutral.
Respond with only the label — no punctuation, no explanation.

Text: {{text}}`,

  // TODO: add your own template here
  custom: `TODO: define your own template with at least one {{placeholder}}`,
};

// ---------------------------------------------------------------------------
// TODO 3: Build a reusable "chat caller" that accepts a system prompt string
//         and a filled user message, sends them to the LLM, and returns the
//         reply text.
//         This is the pattern you'll use in every subsequent task — a tiny
//         helper that separates prompt construction from the API call.
// ---------------------------------------------------------------------------
async function callWithSystem(systemPrompt: string, userMessage: string): Promise<string> {
  const llm = getProvider();
  const messages: ChatMessage[] = [
    { role: "system", content: systemPrompt },
    { role: "user", content: userMessage },
  ];
  // TODO: call llm.chat(messages) and return result.text
  return "TODO: implement callWithSystem";
}

// ---------------------------------------------------------------------------
// Demo
// ---------------------------------------------------------------------------
async function main() {
  const llm = getProvider();
  console.log(`Provider: ${llm.name} / ${llm.chatModel}\n`);

  // -------------------------------------------------------------------------
  // TODO 4: Use renderTemplate + TEMPLATES.summarise to summarise the sample
  //         text below in at most 2 sentences. Print the result.
  // -------------------------------------------------------------------------
  const sampleText = `Transformer models revolutionized natural language processing by replacing
recurrent architectures with a mechanism called self-attention. Instead of processing
tokens sequentially, transformers consider all tokens simultaneously, learning which
parts of the input are relevant to each other. This parallel processing makes them
much faster to train on modern GPUs and allows them to capture long-range dependencies
that were difficult for RNNs to model.`;

  const summaryPrompt = renderTemplate(TEMPLATES.summarise, {
    max_sentences: "2",
    text: sampleText,
  });
  console.log("--- summarisation ---");
  console.log("Filled prompt:\n", summaryPrompt, "\n");
  // const summary = await callWithSystem("You are a precise summariser.", summaryPrompt);
  // console.log("Summary:", summary, "\n");

  // -------------------------------------------------------------------------
  // TODO 5: Use TEMPLATES.classify to classify three short texts and print the
  //         label for each. The output should be ONLY the label word.
  //         If the model returns extra text, note it — you'll fix this in task 4.
  // -------------------------------------------------------------------------
  const samples = [
    "This is the best product I've ever bought!",
    "Arrived broken. Terrible packaging.",
    "It does the job. Nothing special.",
  ];
  console.log("--- classification ---");
  for (const text of samples) {
    const prompt = renderTemplate(TEMPLATES.classify, { text });
    // const label = await callWithSystem("You are a sentiment classifier.", prompt);
    // console.log(`"${text}" → ${label.trim()}`);
    console.log(`TODO: classify: "${text}"`);
  }

  // -------------------------------------------------------------------------
  // TODO 6 (stretch): Add a template for your own task (code review, tone
  //         rewriting, question generation, etc.) and test it.
  //         Does the system prompt or the user message have more influence
  //         on the output style? Experiment by swapping the same instructions
  //         between system and user role.
  // -------------------------------------------------------------------------
}

main().catch(console.error);
