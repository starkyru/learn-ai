"""
Task 3 🟡 — LoRA / QLoRA locally (Python only, OPTIONAL).

What you'll learn:
  - How PEFT wraps a model and adds trainable LoRA adapters
  - Concrete parameter counts: how many params LoRA adds vs full fine-tuning
  - How the transformers Trainer API works at its simplest
  - Why rank r is a tunable hyperparameter (low rank = fewer params, faster, may underfit)

NOTE: This task is OPTIONAL and requires heavy dependencies.

To install:
  uv sync --extra finetune

This installs: torch, transformers, peft, datasets, accelerate (~3-5 GB download).

Model used: facebook/opt-125m (~250 MB weights download on first run).

TS note: LoRA training is Python/CUDA territory. TypeScript engineers should do
Task 2 (hosted SFT via the OpenAI API) as their practical equivalent.

How to run (after uv sync --extra finetune):
  uv run python modules/13-fine-tuning/py/03_lora_local.py
"""

from __future__ import annotations

try:
    import torch
    import transformers
    import peft
    import datasets as hf_datasets
    import accelerate  # noqa: F401 — needed by Trainer
except ImportError:
    raise SystemExit(
        "Missing dependencies. Run:\n"
        "  uv sync --extra finetune\n"
        "then re-run this script."
    )

from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer, DataCollatorForLanguageModeling
from peft import LoraConfig, get_peft_model, TaskType

MODEL_ID = "facebook/opt-125m"

# A tiny training corpus — enough to see loss drop in a few steps
TRAIN_PAIRS = [
    ("Rewrite formally: hey can u send me the report asap thx",
     "Dear colleague, could you please send me the report at your earliest convenience?"),
    ("Rewrite formally: gonna be late to the meeting srry",
     "I apologise for the inconvenience, but I will be arriving to the meeting slightly late."),
    ("Rewrite formally: yo the budget is way over can we fix this",
     "I wish to draw your attention to a budget overrun that requires prompt resolution."),
    ("Rewrite formally: pls approve the purchase order before friday",
     "I kindly request your approval of the purchase order prior to Friday."),
    ("Rewrite formally: thx for the help earlier means a lot",
     "Thank you for your assistance earlier; it was greatly appreciated."),
]


# ---------------------------------------------------------------------------
# Model and tokenizer
# ---------------------------------------------------------------------------


def load_model_and_tokenizer() -> tuple:
    """
    Load facebook/opt-125m and its tokenizer.

    Returns (model, tokenizer).

    TODO:
      1. Load the tokenizer with AutoTokenizer.from_pretrained(MODEL_ID). OPT
         models sometimes ship without a pad token — if tokenizer.pad_token is
         None, set it to the eos_token so batching/padding works.
      2. Load the model with AutoModelForCausalLM.from_pretrained(MODEL_ID, ...).
         Pass torch_dtype=torch.float32 (CPU-safe; add MPS/CUDA later).
      3. Print the total parameter count (sum of p.numel() over model.parameters()).
      4. Return (model, tokenizer).
    """
    # TODO: implement load_model_and_tokenizer
    raise NotImplementedError("TODO: implement load_model_and_tokenizer()")


# ---------------------------------------------------------------------------
# LoRA adapters
# ---------------------------------------------------------------------------


def add_lora_adapters(model, rank: int = 8) -> object:
    """
    Wrap `model` with LoRA adapters using PEFT.

    Returns the PEFT model.

    TODO:
      1. Build a LoraConfig(...). The parameters that matter:
           - task_type=TaskType.CAUSAL_LM
           - r=rank                     (the adapter rank passed in)
           - lora_alpha=...             (scaling factor, conventionally 2*r)
           - lora_dropout=...           (a small dropout, e.g. ~0.1)
           - target_modules=[...]       (which weights get adapters — for OPT
                                         attention, the q and v projections)
      2. Wrap the base model with get_peft_model(model, config).
      3. Call peft_model.print_trainable_parameters() to see the trainable/total
         split. For opt-125m at rank=8 expect ~0.3% trainable.
      4. Return the wrapped peft_model.
    """
    # TODO: implement add_lora_adapters
    raise NotImplementedError("TODO: implement add_lora_adapters()")


# ---------------------------------------------------------------------------
# Dataset preparation
# ---------------------------------------------------------------------------


def tokenize_dataset(tokenizer, pairs: list[tuple[str, str]], max_length: int = 128):
    """
    Tokenize (prompt, completion) pairs for causal language model training.

    The standard approach: concatenate prompt + completion into one sequence.
    The model is trained to predict all tokens; the loss on prompt tokens is
    typically masked (labels=-100) so the model learns to predict completions.

    Returns a HuggingFace Dataset ready for Trainer.

    TODO:
      1. For each (prompt, completion) pair, join them into one training string:
         the prompt, a space, the completion, then tokenizer.eos_token appended.
      2. Tokenize that string with the tokenizer, passing truncation=True,
         max_length=max_length, and padding="max_length" so every row is the
         same length.
      3. For causal LM the labels are just a copy of input_ids.
      4. Collect the per-example input_ids / attention_mask / labels into a dict
         of lists (one key per field).
      5. Return a HF dataset built from that dict (hf_datasets.Dataset.from_dict).
    """
    # TODO: implement tokenize_dataset
    raise NotImplementedError("TODO: implement tokenize_dataset()")


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train(peft_model, tokenized_dataset, tokenizer, output_dir: str = "/tmp/lora-opt") -> None:
    """
    Fine-tune the PEFT model for a small number of steps.

    TODO:
      1. Build TrainingArguments(output_dir=output_dir, ...). Settings that
         matter for a quick CPU run: a few epochs (num_train_epochs), a tiny
         per_device_train_batch_size, logging_steps=1 so you see loss every step,
         save_strategy="no", report_to="none" (no wandb/tensorboard), fp16=False.
      2. Create a Trainer wrapping peft_model, the args, the tokenized_dataset,
         and a data_collator. For causal LM use DataCollatorForLanguageModeling
         with mlm=False (we predict the next token, not a masked one).
      3. Kick off training with trainer.train().
      4. Print the final training loss.
    """
    # TODO: implement train
    raise NotImplementedError("TODO: implement train()")


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def compare_outputs(base_model, peft_model, tokenizer, prompt: str) -> None:
    """
    Generate text from both the base model and the LoRA-adapted model.

    Prints side-by-side so you can see if fine-tuning changed the output.

    TODO:
      1. Tokenize the prompt.
      2. Generate from base_model with max_new_tokens=60, do_sample=False.
      3. Generate from peft_model with the same settings.
      4. Decode and print both outputs.

    Tip: use model.generate() with attention_mask to suppress warnings.
    """
    # TODO: implement compare_outputs
    raise NotImplementedError("TODO: implement compare_outputs()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    print(f"Loading {MODEL_ID}...")
    model, tokenizer = load_model_and_tokenizer()

    # Keep a reference to the base model before wrapping with LoRA
    # (so we can compare outputs later)
    import copy
    base_model = copy.deepcopy(model)
    base_model.eval()

    print("\nAdding LoRA adapters (rank=8)...")
    peft_model = add_lora_adapters(model, rank=8)

    print("\nTokenising training data...")
    dataset = tokenize_dataset(tokenizer, TRAIN_PAIRS)
    print(f"  {len(dataset)} examples")

    print("\nTraining for 3 epochs...")
    train(peft_model, dataset, tokenizer)

    print("\nComparing base vs LoRA-adapted outputs:")
    compare_outputs(
        base_model,
        peft_model,
        tokenizer,
        prompt="Rewrite formally: hey where is my invoice i need it now",
    )


if __name__ == "__main__":
    main()
