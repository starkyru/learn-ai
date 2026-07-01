/**
 * Task 2 🟢 — Hosted SFT via the OpenAI fine-tuning API (TypeScript mirror).
 *
 * What you'll learn:
 *   - The JSONL chat format required for OpenAI fine-tuning
 *   - Uploading a training file and starting a job via the openai npm package
 *   - Polling for completion and calling the resulting model
 *   - Cost and latency implications of hosted fine-tuning
 *
 * This uses the `openai` npm package directly (not @learn-ai/llm-core) because
 * fine-tuning APIs are provider-specific and not in the shared abstraction.
 *
 * COST WARNING:
 *   Fine-tuning gpt-4o-mini costs ~$0.008 per 1K training tokens.
 *   The 30-example dataset is ~3K tokens → expect $0.02–$0.05.
 *   You can cancel the job at https://platform.openai.com/finetune after submitting.
 *
 * Requires: OPENAI_API_KEY in .env
 *
 * How to run:
 *   pnpm tsx modules/13-fine-tuning/ts/02-hosted-sft.ts
 */

import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import "dotenv/config";
import OpenAI from "openai";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, "../data");
const TRAIN_FILE = path.join(DATA_DIR, "emails_train.jsonl");
const BASE_MODEL = "gpt-4o-mini";

// ---------------------------------------------------------------------------
// Dataset
// ---------------------------------------------------------------------------

const TRAINING_PAIRS: [string, string][] = [
  ["hey can u send me the report asap thx", "Dear colleague, could you please send me the report at your earliest convenience? Thank you."],
  ["gonna be late to the meeting srry", "I apologise for the inconvenience, but I will be arriving to the meeting slightly late."],
  ["wtf is going on with the server its been down for hours", "I am writing to flag a critical issue: the server has been unavailable for several hours and requires immediate attention."],
  ["can we reschedule tmrw? something came up", "I would like to request rescheduling tomorrow's appointment, as an unforeseen commitment has arisen."],
  ["the numbers look good lmk if u need anything else", "The figures appear satisfactory. Please do not hesitate to reach out should you require any further information."],
  ["hey wanna grab coffee and talk about the project", "I would welcome the opportunity to meet for coffee to discuss the project at your convenience."],
  ["yo the budget is way over can we fix this", "I wish to draw your attention to a budget overrun that requires prompt resolution."],
  ["just fyi we missed the deadline again", "I am writing to inform you that we have again not met the agreed deadline."],
  ["could u review my slides b4 the presentation", "I would appreciate it if you could review my presentation slides before the scheduled meeting."],
  ["hi got ur email ill get back to u soon", "Thank you for your message. I will respond to you in due course."],
  ["the client wants changes asap its urgent!!", "The client has requested revisions urgently; I would appreciate your immediate attention to this matter."],
  ["can u cover for me tmrw i have a family thing", "I am writing to request coverage for tomorrow, as I have a prior family commitment."],
  ["pls approve the purchase order before friday", "I kindly request your approval of the purchase order prior to Friday."],
  ["the meeting got cancelled btw", "Please note that the meeting has been cancelled."],
  ["good job on the launch everyone!!", "I would like to extend my congratulations to the entire team for the successful launch."],
  ["hey we need more headcount this quarter", "I wish to raise the need for additional headcount in the current quarter."],
  ["can u ping me when the data is ready", "Please notify me when the data becomes available."],
  ["fyi the demo is pushed to next week", "For your information, the demonstration has been rescheduled to next week."],
  ["thx for the help earlier means a lot", "Thank you for your assistance earlier; it was greatly appreciated."],
  ["can we hop on a quick call tmrw morning", "I would like to propose a brief call tomorrow morning at your convenience."],
  ["the report has typos pls fix before sending", "I have noticed typographical errors in the report; please correct them before distribution."],
  ["heads up: new policy kicks in monday", "Please be advised that the new policy will take effect on Monday."],
  ["r u free this afternoon to review the contract", "I would like to enquire whether you are available this afternoon to review the contract."],
  ["we r behind schedule need to talk", "I would like to arrange a discussion, as we are currently behind schedule."],
  ["awesome work on the deck!!", "Excellent work on the presentation — it was very well received."],
  ["pls dont forget the meeting @ 3pm", "A reminder that the meeting is scheduled for 3:00 PM today."],
  ["can someone help me with the excel file", "I would appreciate assistance with the Excel file at someone's earliest convenience."],
  ["just checking if everyone got the invite", "I am writing to confirm that all relevant parties have received the calendar invitation."],
  ["the vendor hasnt responded in 2 weeks smh", "I wish to note that the vendor has not responded in two weeks; further follow-up may be required."],
  ["great chatting c u at the conf next month!", "It was a pleasure speaking with you. I look forward to seeing you at the conference next month."],
];

const SYSTEM_PROMPT =
  "You are an assistant that rewrites informal or casual email text into " +
  "polished, formal business English. Preserve the meaning exactly. " +
  "Do not add extra information. Reply with only the rewritten text.";

// ---------------------------------------------------------------------------
// Dataset builder
// ---------------------------------------------------------------------------

/**
 * Convert TRAINING_PAIRS into OpenAI fine-tuning JSONL format and write to disk.
 *
 * Each line is a JSON object with a single "messages" key holding three chat
 * messages: a system message (use SYSTEM_PROMPT), a user message (the informal
 * email), and an assistant message (the formal rewrite).
 *
 * TODO:
 *   1. Ensure DATA_DIR exists (fs.mkdirSync with recursive: true).
 *   2. For each [informal, formal] pair, assemble the three-message array above.
 *   3. Write TRAIN_FILE as JSONL — one JSON.stringify'd object per line.
 *   4. Print how many examples were written and the path.
 *   5. Return TRAIN_FILE.
 */
function buildDataset(): string {
  // TODO: implement buildDataset
  throw new Error("TODO: implement buildDataset()");
}

// ---------------------------------------------------------------------------
// Fine-tuning job management
// ---------------------------------------------------------------------------

/**
 * Upload the JSONL file to OpenAI and start a fine-tune job.
 *
 * Returns the job id.
 *
 * TODO:
 *   1. Create an OpenAI client (reads OPENAI_API_KEY from process.env).
 *   2. Upload the training file with client.files.create(...), passing a read
 *      stream of trainPath and purpose: "fine-tune". Keep the returned file id.
 *   3. Start a fine-tune job with client.fineTuning.jobs.create(...), passing
 *      that file id as training_file and BASE_MODEL as model.
 *   4. Print the job id and return it.
 */
async function uploadAndFinetune(trainPath: string): Promise<string> {
  // TODO: implement uploadAndFinetune
  throw new Error("TODO: implement uploadAndFinetune()");
}

/**
 * Poll the fine-tune job until it succeeds, fails, or is cancelled.
 *
 * Returns the fine-tuned model id on success, null otherwise.
 *
 * TODO:
 *   1. Create an OpenAI client.
 *   2. Loop: retrieve the job, print its status and recent events.
 *      Break when status is "succeeded" | "failed" | "cancelled".
 *   3. Sleep pollIntervalMs between checks (use setTimeout in a Promise).
 *   4. On success return job.fine_tuned_model, else return null.
 */
async function waitForJob(
  jobId: string,
  pollIntervalMs: number = 30_000,
): Promise<string | null> {
  // TODO: implement waitForJob
  throw new Error("TODO: implement waitForJob()");
}

// ---------------------------------------------------------------------------
// Comparison
// ---------------------------------------------------------------------------

/**
 * Run both gpt-4o-mini (base) and the fine-tuned model on test prompts.
 *
 * TODO:
 *   1. Create an OpenAI client.
 *   2. For each test input, call chat.completions.create() twice:
 *        once with BASE_MODEL, once with fineTunedModelId.
 *   3. Print a formatted table: input | base output | fine-tuned output.
 */
async function compareModels(fineTunedModelId: string): Promise<void> {
  const testInputs = [
    "yo where is my invoice?? i need it now",
    "fyi the client is kinda unhappy with our progress",
    "can u double check the contract before we sign",
  ];
  // TODO: implement compareModels
  throw new Error("TODO: implement compareModels()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    console.error("ERROR: OPENAI_API_KEY is not set. Add it to .env and re-run.");
    process.exit(1);
  }

  console.log("Step 1: Building training dataset...");
  const trainPath = buildDataset();

  console.log("\nStep 2: Uploading and submitting fine-tune job...");
  const jobId = await uploadAndFinetune(trainPath);
  console.log(`  Job ID: ${jobId}`);
  console.log(
    "\n  NOTE: Fine-tuning takes 10–30 minutes. You can cancel the job at",
    "\n  https://platform.openai.com/finetune to avoid charges.",
    "\n  To continue, call waitForJob() with the job id above.",
  );

  // Uncomment to wait (takes 10-30 min):
  // console.log("\nStep 3: Waiting for fine-tune to complete...");
  // const ftModel = await waitForJob(jobId);
  // if (ftModel) {
  //   console.log(`\nStep 4: Comparing base vs fine-tuned model (${ftModel})...`);
  //   await compareModels(ftModel);
  // }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
