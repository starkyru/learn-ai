"""
Task 2 🟢 — Hosted SFT via the OpenAI fine-tuning API.

What you'll learn:
  - The JSONL chat format required for OpenAI fine-tuning
  - How to upload a training file, start a job, poll for completion
  - How to call a fine-tuned model and compare it to the base
  - Real cost and latency implications of hosted fine-tuning

This task uses the `openai` SDK directly (not llm-core) because fine-tuning
API endpoints are provider-specific and not part of the shared abstraction.

COST WARNING:
  Fine-tuning gpt-4o-mini costs ~$0.008 per 1K training tokens (check current
  pricing at https://platform.openai.com/docs/guides/fine-tuning/pricing).
  The 30-example dataset here is ~3K tokens, so expect $0.02–$0.05.
  You can run build_dataset() and upload_and_finetune() up to the job submission
  and then CANCEL the job from the OpenAI dashboard to save cost.

Requires: OPENAI_API_KEY in .env

How to run:
  uv run python modules/13-fine-tuning/py/02_hosted_sft.py
"""

from __future__ import annotations

import json
import os
import pathlib
import time

from dotenv import load_dotenv

load_dotenv()

# The openai SDK is used directly here — fine-tuning is not in llm-core.
# It is installed as part of the course's base dependencies.
import openai

DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
TRAIN_FILE = DATA_DIR / "emails_train.jsonl"

BASE_MODEL = "gpt-4o-mini"

# ---------------------------------------------------------------------------
# Dataset builder
# ---------------------------------------------------------------------------

# 30 training examples: (informal_email, formal_rewrite)
TRAINING_PAIRS: list[tuple[str, str]] = [
    ("hey can u send me the report asap thx", "Dear colleague, could you please send me the report at your earliest convenience? Thank you."),
    ("gonna be late to the meeting srry", "I apologise for the inconvenience, but I will be arriving to the meeting slightly late."),
    ("wtf is going on with the server its been down for hours", "I am writing to flag a critical issue: the server has been unavailable for several hours and requires immediate attention."),
    ("can we reschedule tmrw? something came up", "I would like to request rescheduling tomorrow's appointment, as an unforeseen commitment has arisen."),
    ("the numbers look good lmk if u need anything else", "The figures appear satisfactory. Please do not hesitate to reach out should you require any further information."),
    ("hey wanna grab coffee and talk about the project", "I would welcome the opportunity to meet for coffee to discuss the project at your convenience."),
    ("yo the budget is way over can we fix this", "I wish to draw your attention to a budget overrun that requires prompt resolution."),
    ("just fyi we missed the deadline again", "I am writing to inform you that we have again not met the agreed deadline."),
    ("could u review my slides b4 the presentation", "I would appreciate it if you could review my presentation slides before the scheduled meeting."),
    ("hi got ur email ill get back to u soon", "Thank you for your message. I will respond to you in due course."),
    ("the client wants changes asap its urgent!!", "The client has requested revisions urgently; I would appreciate your immediate attention to this matter."),
    ("can u cover for me tmrw i have a family thing", "I am writing to request coverage for tomorrow, as I have a prior family commitment."),
    ("pls approve the purchase order before friday", "I kindly request your approval of the purchase order prior to Friday."),
    ("the meeting got cancelled btw", "Please note that the meeting has been cancelled."),
    ("good job on the launch everyone!!", "I would like to extend my congratulations to the entire team for the successful launch."),
    ("hey we need more headcount this quarter", "I wish to raise the need for additional headcount in the current quarter."),
    ("can u ping me when the data is ready", "Please notify me when the data becomes available."),
    ("fyi the demo is pushed to next week", "For your information, the demonstration has been rescheduled to next week."),
    ("thx for the help earlier means a lot", "Thank you for your assistance earlier; it was greatly appreciated."),
    ("can we hop on a quick call tmrw morning", "I would like to propose a brief call tomorrow morning at your convenience."),
    ("the report has typos pls fix before sending", "I have noticed typographical errors in the report; please correct them before distribution."),
    ("heads up: new policy kicks in monday", "Please be advised that the new policy will take effect on Monday."),
    ("r u free this afternoon to review the contract", "I would like to enquire whether you are available this afternoon to review the contract."),
    ("we r behind schedule need to talk", "I would like to arrange a discussion, as we are currently behind schedule."),
    ("awesome work on the deck!!", "Excellent work on the presentation — it was very well received."),
    ("pls dont forget the meeting @ 3pm", "A reminder that the meeting is scheduled for 3:00 PM today."),
    ("can someone help me with the excel file", "I would appreciate assistance with the Excel file at someone's earliest convenience."),
    ("just checking if everyone got the invite", "I am writing to confirm that all relevant parties have received the calendar invitation."),
    ("the vendor hasnt responded in 2 weeks smh", "I wish to note that the vendor has not responded in two weeks; further follow-up may be required."),
    ("great chatting c u at the conf next month!", "It was a pleasure speaking with you. I look forward to seeing you at the conference next month."),
]

SYSTEM_PROMPT = (
    "You are an assistant that rewrites informal or casual email text into "
    "polished, formal business English. Preserve the meaning exactly. "
    "Do not add extra information. Reply with only the rewritten text."
)


def build_dataset() -> pathlib.Path:
    """
    Convert TRAINING_PAIRS into OpenAI fine-tuning JSONL format and write to disk.

    Each line must be a JSON object with a "messages" key:
      {"messages": [
        {"role": "system", "content": "<system_prompt>"},
        {"role": "user",   "content": "<informal_email>"},
        {"role": "assistant", "content": "<formal_rewrite>"}
      ]}

    TODO:
      1. Create DATA_DIR if it doesn't exist.
      2. For each (informal, formal) pair in TRAINING_PAIRS, build the messages list.
      3. Write each example as a JSON line to TRAIN_FILE.
      4. Print how many examples were written and the file path.
      5. Return TRAIN_FILE.
    """
    # TODO: implement build_dataset
    raise NotImplementedError("TODO: implement build_dataset()")


# ---------------------------------------------------------------------------
# Fine-tuning job management
# ---------------------------------------------------------------------------


def upload_and_finetune(train_path: pathlib.Path) -> str:
    """
    Upload the JSONL file to OpenAI and start a fine-tune job.

    Returns the fine-tune job id.

    TODO:
      1. Create an openai.OpenAI() client (reads OPENAI_API_KEY from env).
      2. Upload the file:
           response = client.files.create(
               file=open(train_path, "rb"),
               purpose="fine-tune",
           )
         Store response.id as file_id.
      3. Start the job:
           job = client.fine_tuning.jobs.create(
               training_file=file_id,
               model=BASE_MODEL,
           )
         Print the job id and status.
      4. Return job.id.

    Tip: you can cancel the job from https://platform.openai.com/finetune
    to avoid charges while still seeing the submission work.
    """
    # TODO: implement upload_and_finetune
    raise NotImplementedError("TODO: implement upload_and_finetune()")


def wait_for_job(job_id: str, poll_interval: int = 30) -> str | None:
    """
    Poll the fine-tune job until it succeeds or fails.

    Returns the fine-tuned model id on success, or None on failure.

    TODO:
      1. Create an openai.OpenAI() client.
      2. Loop: retrieve the job, print its status and any new events.
         Use: client.fine_tuning.jobs.retrieve(job_id)
         And: client.fine_tuning.jobs.list_events(job_id, limit=5)
      3. Break when job.status in ("succeeded", "failed", "cancelled").
      4. On success, return job.fine_tuned_model.
      5. On failure/cancellation, print the reason and return None.
      6. Sleep poll_interval seconds between checks.
    """
    # TODO: implement wait_for_job
    raise NotImplementedError("TODO: implement wait_for_job()")


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def compare_models(fine_tuned_model_id: str) -> None:
    """
    Run both gpt-4o-mini (base) and the fine-tuned model on test prompts.

    Prints side-by-side responses so you can see if fine-tuning changed the style.

    TODO:
      1. Create an openai.OpenAI() client.
      2. For each test_input in TEST_INPUTS below, call chat.completions.create()
         twice: once with BASE_MODEL, once with fine_tuned_model_id.
         Use the same SYSTEM_PROMPT.
      3. Print a table: input | base response | fine-tuned response.
    """
    TEST_INPUTS = [
        "yo where is my invoice?? i need it now",
        "fyi the client is kinda unhappy with our progress",
        "can u double check the contract before we sign",
    ]
    # TODO: implement compare_models
    raise NotImplementedError("TODO: implement compare_models()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY is not set. Add it to .env and re-run.")
        return

    print("Step 1: Building training dataset...")
    train_path = build_dataset()

    print("\nStep 2: Uploading and submitting fine-tune job...")
    job_id = upload_and_finetune(train_path)
    print(f"  Job ID: {job_id}")
    print(
        "\n  NOTE: Fine-tuning takes 10–30 minutes. You can cancel the job at"
        "\n  https://platform.openai.com/finetune to avoid charges."
        "\n  To continue, call wait_for_job() with the job id above."
    )

    # Uncomment to wait for completion (takes 10-30 min):
    # print("\nStep 3: Waiting for fine-tune to complete...")
    # ft_model = wait_for_job(job_id)
    # if ft_model:
    #     print(f"\nStep 4: Comparing base vs fine-tuned model ({ft_model})...")
    #     compare_models(ft_model)


if __name__ == "__main__":
    main()
