/**
 * Task 4 🟡 — Dataset prep and overfitting evaluation.
 *
 * What you'll learn:
 *   - What "clean" training data means and how to enforce it programmatically
 *   - Proper train / val / test splits to avoid data leakage
 *   - LLM-as-judge scoring on held-out data
 *   - Detecting overfitting: train score rising while val score stalls
 *
 * Key insight: the most common fine-tuning failure mode is bad data quality.
 * Inconsistent formatting, duplicates, or near-duplicate train/val examples
 * make your eval metrics unreliable and your fine-tuned model unpredictable.
 *
 * How to run:
 *   pnpm tsx modules/13-fine-tuning/ts/04-dataset-eval.ts
 */

import { getProvider } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Example {
  informal: string;
  formal: string;
}

interface EvalResult {
  train_score: number;
  val_score: number;
}

// ---------------------------------------------------------------------------
// Raw dataset
// ---------------------------------------------------------------------------

const RAW_EXAMPLES: Example[] = [
  { informal: "hey can u send me the report asap thx", formal: "Dear colleague, could you please send me the report at your earliest convenience? Thank you." },
  { informal: "gonna be late to the meeting srry", formal: "I apologise for the inconvenience, but I will be arriving to the meeting slightly late." },
  { informal: "wtf is going on with the server its been down for hours", formal: "I am writing to flag a critical issue: the server has been unavailable for several hours." },
  { informal: "can we reschedule tmrw? something came up", formal: "I would like to request rescheduling tomorrow's appointment, as an unforeseen commitment has arisen." },
  { informal: "the numbers look good lmk if u need anything else", formal: "The figures appear satisfactory. Please do not hesitate to reach out should you require further information." },
  { informal: "yo the budget is way over can we fix this", formal: "I wish to draw your attention to a budget overrun that requires prompt resolution." },
  { informal: "just fyi we missed the deadline again", formal: "I am writing to inform you that we have again not met the agreed deadline." },
  { informal: "could u review my slides b4 the presentation", formal: "I would appreciate it if you could review my presentation slides before the scheduled meeting." },
  { informal: "hi got ur email ill get back to u soon", formal: "Thank you for your message. I will respond to you in due course." },
  { informal: "the client wants changes asap its urgent!!", formal: "The client has requested revisions urgently; I would appreciate your immediate attention to this matter." },
  { informal: "can u cover for me tmrw i have a family thing", formal: "I am writing to request coverage for tomorrow, as I have a prior family commitment." },
  { informal: "pls approve the purchase order before friday", formal: "I kindly request your approval of the purchase order prior to Friday." },
  { informal: "the meeting got cancelled btw", formal: "Please note that the meeting has been cancelled." },
  { informal: "good job on the launch everyone!!", formal: "I would like to extend my congratulations to the entire team for the successful launch." },
  { informal: "hey we need more headcount this quarter", formal: "I wish to raise the need for additional headcount in the current quarter." },
  { informal: "can u ping me when the data is ready", formal: "Please notify me when the data becomes available." },
  { informal: "fyi the demo is pushed to next week", formal: "For your information, the demonstration has been rescheduled to next week." },
  { informal: "thx for the help earlier means a lot", formal: "Thank you for your assistance earlier; it was greatly appreciated." },
  { informal: "can we hop on a quick call tmrw morning", formal: "I would like to propose a brief call tomorrow morning at your convenience." },
  { informal: "the report has typos pls fix before sending", formal: "I have noticed typographical errors in the report; please correct them before distribution." },
  { informal: "heads up: new policy kicks in monday", formal: "Please be advised that the new policy will take effect on Monday." },
  { informal: "r u free this afternoon to review the contract", formal: "I would like to enquire whether you are available this afternoon to review the contract." },
  { informal: "we r behind schedule need to talk", formal: "I would like to arrange a discussion, as we are currently behind schedule." },
  { informal: "awesome work on the deck!!", formal: "Excellent work on the presentation — it was very well received." },
  { informal: "pls dont forget the meeting @ 3pm", formal: "A reminder that the meeting is scheduled for 3:00 PM today." },
  { informal: "can someone help me with the excel file", formal: "I would appreciate assistance with the Excel file at someone's earliest convenience." },
  { informal: "just checking if everyone got the invite", formal: "I am writing to confirm that all relevant parties have received the calendar invitation." },
  { informal: "the vendor hasnt responded in 2 weeks smh", formal: "I wish to note that the vendor has not responded in two weeks; further follow-up may be required." },
  { informal: "great chatting c u at the conf next month!", formal: "It was a pleasure speaking with you. I look forward to seeing you at the conference next month." },
  { informal: "yo where is my invoice?? i need it now", formal: "I am writing to enquire about the outstanding invoice, which I require promptly." },
];

// ---------------------------------------------------------------------------
// Data cleaning
// ---------------------------------------------------------------------------

/**
 * Normalise and validate a single training example.
 *
 * Rules:
 *   - Return null if the input is null/undefined or either field is empty after cleaning.
 *   - Strip HTML tags (e.g. "<b>hello</b>" → "hello").
 *   - Unescape common HTML entities (&amp; &lt; &gt; &quot;).
 *   - Collapse multiple whitespace into single spaces; strip leading/trailing.
 *   - Truncate both fields to maxChars characters.
 *   - Ensure the formal rewrite ends with . ? or ! — if not, append ".".
 *
 * TODO: implement cleanExample following the rules above.
 */
function cleanExample(example: Example | null | undefined, maxChars = 512): Example | null {
  // TODO: implement cleanExample
  throw new Error("TODO: implement cleanExample()");
}

// ---------------------------------------------------------------------------
// Train / val / test split
// ---------------------------------------------------------------------------

/**
 * Shuffle and split examples into train / val / test.
 *
 * test fraction = 1 - trainFrac - valFrac.
 *
 * TODO:
 *   1. Shuffle a COPY of examples deterministically. Drive a Fisher-Yates
 *      shuffle from a seeded PRNG so the same seed always gives the same order —
 *      a tiny LCG (a linear-congruential generator: rng = rng * a + c, kept in
 *      uint32 range) is enough to produce the random() values you need.
 *   2. Compute the split sizes from trainFrac / valFrac; the remainder is test.
 *   3. Slice into three non-overlapping parts and return [train, val, test].
 */
function splitDataset(
  examples: Example[],
  trainFrac = 0.70,
  valFrac = 0.15,
  seed = 42,
): [Example[], Example[], Example[]] {
  // TODO: implement splitDataset
  throw new Error("TODO: implement splitDataset()");
}

// ---------------------------------------------------------------------------
// LLM-based evaluation
// ---------------------------------------------------------------------------

/**
 * Evaluate a zero-shot rewriting prompt on a sample from `examples`.
 *
 * For each sampled example:
 *   1. Call the LLM to rewrite the informal email.
 *   2. Ask a judge LLM to score it 1–5 vs the reference formal rewrite.
 * Return the mean score.
 *
 * TODO:
 *   1. Sample min(nSamples, examples.length) random examples (deterministic, index 0..n).
 *   2. For each: call provider.chat() with a system message, then call again
 *      to judge the output. Parse the digit (fallback 3).
 *   3. Return mean.
 */
async function evalOnSplit(
  examples: Example[],
  provider: ReturnType<typeof getProvider>,
  nSamples = 5,
): Promise<number> {
  // TODO: implement evalOnSplit
  throw new Error("TODO: implement evalOnSplit()");
}

// ---------------------------------------------------------------------------
// Overfitting check
// ---------------------------------------------------------------------------

/**
 * Print a table of train vs val scores and flag overfitting.
 *
 * Flag "OVERFIT?" when val_score[i] <= val_score[i-1] and
 * train_score[i] > train_score[i-1].
 *
 * TODO: implement the table and overfitting detection.
 */
function overfittingCheck(measurements: EvalResult[]): void {
  // TODO: implement overfittingCheck
  throw new Error("TODO: implement overfittingCheck()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  const provider = getProvider();
  console.log(`\nUsing provider: ${provider.name} (model: ${provider.chatModel})`);

  // Step 1: clean
  console.log("\nStep 1: Cleaning dataset...");
  const cleaned: Example[] = [];
  for (const ex of RAW_EXAMPLES) {
    const result = cleanExample(ex);
    if (result !== null) cleaned.push(result);
  }
  console.log(`  ${RAW_EXAMPLES.length} raw → ${cleaned.length} clean examples`);

  // Step 2: split
  console.log("\nStep 2: Splitting dataset (70/15/15)...");
  const [train, val, test] = splitDataset(cleaned);
  console.log(`  Train: ${train.length} | Val: ${val.length} | Test: ${test.length}`);

  // Step 3: evaluate
  console.log("\nStep 3: Evaluating on train and val splits (3 samples each)...");
  const trainScore = await evalOnSplit(train, provider, 3);
  const valScore = await evalOnSplit(val, provider, 3);
  console.log(`  Train score: ${trainScore.toFixed(2)} | Val score: ${valScore.toFixed(2)}`);

  // Step 4: overfitting check with mocked measurements
  console.log("\nStep 4: Overfitting check (mocked multi-epoch measurements):");
  overfittingCheck([
    { train_score: 3.1, val_score: 3.0 },
    { train_score: 3.6, val_score: 3.4 },
    { train_score: 4.1, val_score: 3.5 },
    { train_score: 4.5, val_score: 3.4 },
    { train_score: 4.8, val_score: 3.3 },
  ]);

  console.log("\nDone. In a real fine-tune, you'd plot these curves and stop early.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
