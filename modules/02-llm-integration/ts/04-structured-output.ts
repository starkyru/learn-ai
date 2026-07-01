/**
 * Task 4 — Structured output 🟢
 *
 * What this teaches:
 *   - LLMs output text. Getting structured data (JSON, typed objects) out
 *     of them requires either JSON mode, schema-constrained decoding, or a
 *     careful prompt + parser — and validation to catch hallucinated fields.
 *   - zod lets you declare a schema and parse/validate in one step. If the
 *     model's JSON doesn't match, you get a clear error to retry from.
 *   - Why schemas matter: without them you're doing `JSON.parse` and
 *     hoping for the best. Type-safe parsing catches errors at the seam
 *     between the model and your application code.
 *
 * Note: zod is added to this module's package.json dependencies.
 *
 * How to run:
 *   pnpm tsx modules/02-llm-integration/ts/04-structured-output.ts
 */

import { getProvider } from "@learn-ai/llm-core";
import { z } from "zod";

// ---------------------------------------------------------------------------
// TODO 1: Define a Zod schema for the data you want to extract.
//         Start with this recipe schema, then try your own.
// ---------------------------------------------------------------------------
const RecipeSchema = z.object({
  name: z.string().describe("Name of the dish"),
  ingredients: z.array(
    z.object({
      item: z.string(),
      amount: z.string(),
    }),
  ).describe("List of ingredients with amounts"),
  steps: z.array(z.string()).describe("Ordered cooking steps"),
  prepTimeMinutes: z.number().int().positive().describe("Prep time in minutes"),
  servings: z.number().int().positive(),
});

type Recipe = z.infer<typeof RecipeSchema>;

// ---------------------------------------------------------------------------
// TODO 2: Build a prompt that instructs the model to respond in JSON matching
//         the schema above. Embedding the schema (or its description) directly
//         in the prompt is the most portable approach.
//         Tip: JSON.stringify(zodToJsonSchema(...)) or just describe fields
//         manually in the system message.
// ---------------------------------------------------------------------------
function buildPrompt(request: string): string {
  // A system message that explains the required output format.
  return `You are a recipe assistant. When asked for a recipe, respond ONLY with
valid JSON matching this exact structure — no markdown, no prose, just JSON:
{
  "name": "string",
  "ingredients": [{"item": "string", "amount": "string"}],
  "steps": ["string"],
  "prepTimeMinutes": number,
  "servings": number
}

User request: ${request}`;
}

// ---------------------------------------------------------------------------
// TODO 3: Implement parseRecipe.
//         a) The model often wraps JSON in ```json ... ``` fences or adds prose —
//            strip any code-fence markers off `rawText` first (a regex replace works).
//         b) JSON.parse the cleaned text inside a try/catch.
//         c) Hand the parsed object to RecipeSchema.parse() so zod validates the
//            shape and coerces to the typed Recipe.
//         d) Return that typed object; throw a descriptive Error if either the
//            JSON parse or the schema validation fails.
// ---------------------------------------------------------------------------
function parseRecipe(rawText: string): Recipe {
  // TODO: implement
  throw new Error("parseRecipe not implemented yet");
}

async function main() {
  const llm = getProvider();
  console.log(`Provider: ${llm.name} / ${llm.chatModel}\n`);

  const request = "a simple pasta carbonara for 2 people";
  console.log(`Requesting recipe for: "${request}"\n`);

  // ---------------------------------------------------------------------------
  // TODO 4: Call llm.chat() with a single user message (buildPrompt(request))
  //         and lower temperature (use ChatOptions with temperature: 0.1) to
  //         make the output more deterministic and JSON-like.
  //         Then call parseRecipe on result.text and pretty-print the result.
  //         Pass the options as a second arg to llm.chat(); keep temperature low
  //         (~0.1) so the model sticks to the requested JSON shape.
  // ---------------------------------------------------------------------------

  console.log("TODO: implement the chat call and parsing above.");

  // ---------------------------------------------------------------------------
  // TODO 5: Add a retry loop — if parseRecipe throws, append an error message
  //         to the history and ask the model to fix its output. Try up to 3
  //         times before giving up. This is the "repair on parse failure"
  //         pattern you'll use again in module 03.
  // ---------------------------------------------------------------------------

  // ---------------------------------------------------------------------------
  // TODO 6 (stretch): Try a different schema — e.g., extract structured data
  //         from unstructured text. Paste a news article snippet and extract:
  //         { headline, date, people: string[], summary }.
  //         Notice how zod validation reveals when the model misses a field.
  // ---------------------------------------------------------------------------
}

main().catch(console.error);
