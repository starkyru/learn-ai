"""
Task 2 — Streaming 🟢

What this teaches:
  - Streaming returns tokens as they're generated, so the UI feels
    responsive even for long outputs. Under the hood the provider
    sends Server-Sent Events (SSE); the SDK turns them into an iterator.
  - Time-to-first-token (TTFT) is the latency the user *feels*. Total
    generation time matters too, but TTFT is usually more noticeable.
  - Streaming changes error handling: you may get a partial response
    before an error mid-stream.

How to run:
  uv run python modules/02-llm-integration/py/02_streaming.py
"""

import time

from llm_core import get_provider

PROMPT = (
    "Explain how transformer attention works in exactly 5 bullet points, "
    "each 1-2 sentences."
)


def main() -> None:
    llm = get_provider()
    print(f"Provider: {llm.name} / {llm.chat_model}\n")
    print(f"Prompt: {PROMPT}\n")
    print("--- streaming response ---")

    # -------------------------------------------------------------------------
    # TODO 1: Record the wall-clock time before the first call so you can
    #         compute TTFT and total time. Use time.perf_counter().
    # -------------------------------------------------------------------------
    start_time = 0.0  # TODO: replace with time.perf_counter()

    first_token_time: float | None = None
    full_text = ""

    # -------------------------------------------------------------------------
    # TODO 2: Call llm.chat_stream() with a single user message containing PROMPT.
    #         Iterate over the iterator. For each chunk:
    #           a) If it's the first chunk, record first_token_time.
    #           b) Print the chunk without a newline: print(chunk, end="", flush=True)
    #           c) Append the chunk to full_text.
    # -------------------------------------------------------------------------

    # for chunk in llm.chat_stream([{"role": "user", "content": PROMPT}]):
    #     if first_token_time is None:
    #         first_token_time = time.perf_counter()
    #     print(chunk, end="", flush=True)
    #     full_text += chunk

    print("\nTODO: implement streaming above.")

    # -------------------------------------------------------------------------
    # TODO 3: After the loop, print timing stats:
    #   - Time to first token  = first_token_time - start_time  (ms)
    #   - Total time           = time.perf_counter() - start_time  (ms)
    #   - Words in output      = rough estimate: len(full_text.split())
    #   - Words/second         = words / total_time_seconds
    # -------------------------------------------------------------------------

    # total_time = time.perf_counter() - start_time
    # ttft = (first_token_time - start_time) * 1000 if first_token_time else None
    # words = len(full_text.split())
    # print("\n--- stats ---")
    # print(f"TTFT:        {ttft:.0f} ms" if ttft else "TTFT: N/A")
    # print(f"Total time:  {total_time * 1000:.0f} ms")
    # print(f"~Words out:  {words}  (~{words / total_time:.1f} words/s)")

    # -------------------------------------------------------------------------
    # TODO 4 (stretch): Try the same prompt with llm.chat() (non-streaming) and
    #         compare the wall-clock time. They should be similar in total, but
    #         the non-streaming version shows nothing until fully done.
    # -------------------------------------------------------------------------


if __name__ == "__main__":
    main()
