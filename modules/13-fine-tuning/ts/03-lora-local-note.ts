/**
 * Task 3 🟡 — LoRA / QLoRA locally (TypeScript note).
 *
 * LoRA training is Python/CUDA territory. The required libraries (PEFT,
 * transformers, accelerate) are Python-only — there is no equivalent
 * TypeScript ecosystem for local model training.
 *
 * WHAT TO DO AS A TYPESCRIPT LEARNER:
 *
 * 1. Read the Python stub at ../py/03_lora_local.py for the concepts and
 *    the PEFT API. Understanding what PEFT does is the goal, not running it.
 *
 * 2. Your practical equivalent for fine-tuning from TypeScript is Task 2
 *    (02-hosted-sft.ts) — the OpenAI fine-tuning API does the heavy lifting
 *    on their infrastructure. You get a fine-tuned model without managing
 *    GPU memory, quantization, or training loops.
 *
 * 3. If you want to understand LoRA math without Python, Task 5
 *    (05-lora-scratch.ts) implements the low-rank update from scratch in
 *    plain TypeScript arrays — no ML framework needed.
 *
 * KEY CONCEPTS TO UNDERSTAND (no code needed):
 *
 *   - PEFT wraps the base model and adds two small matrices (A and B) to
 *     each targeted weight. Only A and B are updated during training.
 *
 *   - The `target_modules` list in LoraConfig controls which weight matrices
 *     get adapters. For attention: typically q_proj and v_proj.
 *
 *   - `peft_model.print_trainable_parameters()` prints the ratio of trainable
 *     to total params. For a 125M-param model at rank=8 expect ~0.3%.
 *
 *   - After training, you can merge the adapter back into the base model
 *     (`peft_model.merge_and_unload()`) to get a single model file.
 *
 * How to run:
 *   There is nothing to run in this file. Proceed to 04-dataset-eval.ts.
 */

console.log(
  "Task 3 (LoRA locally) is Python-only. See ../py/03_lora_local.py for the stub.",
);
console.log(
  "TypeScript equivalent: Task 2 (02-hosted-sft.ts) — OpenAI hosted fine-tuning.",
);
console.log(
  "LoRA math from scratch: Task 5 (05-lora-scratch.ts) — no ML framework needed.",
);
