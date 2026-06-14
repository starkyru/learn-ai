"""task3_vision_llm.py — image understanding via a multimodal LLM.  🟡

What it teaches:
    Modern LLMs (GPT-4o, Claude 3.x+) accept images alongside text. Under the
    hood they use a vision encoder (often a ViT) to convert the image into a
    sequence of "image tokens", which are then interleaved with text tokens and
    fed into the language model. The LLM can then answer questions, describe
    content, extract text (OCR-style), or classify — all in natural language.

    Going beyond the abstraction:
        llm_core's LLMProvider is TEXT-ONLY. Image inputs require the raw vendor
        SDKs (openai, anthropic) because the multimodal message format differs
        from the plain-string content that llm_core abstracts. This module uses
        those SDKs directly so you see the real request shape — a core lesson
        about where abstractions leak.

    Comparison to tasks 1 & 2:
        - Task 1: fast, deterministic label from a single-purpose classifier.
        - Task 2: ranked similarity scores without any fine-tuning (CLIP).
        - Task 3: rich, flexible natural-language answer — but slower and priced
          per token. Use a multimodal LLM when you need *understanding*, not just
          a label.

How to run (from the repo root):
    # With OpenAI (gpt-4o-mini is cheap):
    LLM_PROVIDER=openai uv run python modules/09-computer-vision/py/task3_vision_llm.py

    # With Anthropic (Claude):
    LLM_PROVIDER=anthropic uv run python modules/09-computer-vision/py/task3_vision_llm.py

Environment variables (in .env):
    OPENAI_API_KEY     — for the OpenAI path
    ANTHROPIC_API_KEY  — for the Anthropic path
    LLM_PROVIDER       — "openai" or "anthropic" (controls which path runs)

Acceptance:
    - Prints a natural-language description of the sample image.
    - Prints a one-word classification (what kind of animal/object is in it).
    - Works with at least one of OpenAI or Anthropic.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SAMPLE_IMAGE = Path(__file__).parent.parent / "assets" / "cat.jpg"

DESCRIBE_PROMPT = (
    "Describe this image in 2-3 sentences. "
    "Then on a new line starting with 'Label:', give a single word that best "
    "classifies the main subject (e.g. 'cat', 'car', 'mountain')."
)


# ---------------------------------------------------------------------------
# Helper — encode an image file as base64 for the API request bodies
# ---------------------------------------------------------------------------

def image_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


# ---------------------------------------------------------------------------
# OpenAI path  (gpt-4o / gpt-4o-mini)
# ---------------------------------------------------------------------------

def describe_with_openai(image_path: Path, prompt: str) -> str:
    """Send an image + text prompt to GPT-4o-mini and return the reply text.

    The multimodal message format wraps content as a list of 'content parts':
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
    This is the raw OpenAI SDK shape — llm_core does not expose it.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("Run: pip install openai")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in .env")

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")

    b64 = image_to_base64(image_path)
    mime = "image/jpeg" if image_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"

    # TODO (exercise): build the messages list with a multimodal user message:
    #
    # messages = [
    #     {
    #         "role": "user",
    #         "content": [
    #             {"type": "text", "text": prompt},
    #             {
    #                 "type": "image_url",
    #                 "image_url": {"url": f"data:{mime};base64,{b64}"},
    #             },
    #         ],
    #     }
    # ]
    #
    # Then call client.chat.completions.create(model=model, messages=messages)
    # and return response.choices[0].message.content

    raise NotImplementedError(
        "Complete the TODO: build the multimodal messages list and call the API."
    )


# ---------------------------------------------------------------------------
# Anthropic path  (claude-3-haiku / claude-3-5-sonnet)
# ---------------------------------------------------------------------------

def describe_with_anthropic(image_path: Path, prompt: str) -> str:
    """Send an image + text prompt to Claude and return the reply text.

    Anthropic's multimodal format uses a 'source' block of type 'base64':
        {"type": "image", "source": {"type": "base64", "media_type": ..., "data": ...}}
    Again, this is the raw SDK shape — not exposed by llm_core.
    """
    try:
        import anthropic
    except ImportError:
        raise ImportError("Run: pip install anthropic")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ANTHROPIC_API_KEY in .env")

    client = anthropic.Anthropic(api_key=api_key)
    model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

    b64 = image_to_base64(image_path)
    mime = "image/jpeg" if image_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"

    # TODO (exercise): build the Anthropic multimodal message and call the API:
    #
    # message = client.messages.create(
    #     model=model,
    #     max_tokens=512,
    #     messages=[
    #         {
    #             "role": "user",
    #             "content": [
    #                 {
    #                     "type": "image",
    #                     "source": {
    #                         "type": "base64",
    #                         "media_type": mime,
    #                         "data": b64,
    #                     },
    #                 },
    #                 {"type": "text", "text": prompt},
    #             ],
    #         }
    #     ],
    # )
    # return message.content[0].text

    raise NotImplementedError(
        "Complete the TODO: build the Anthropic multimodal message and call the API."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    image_path = SAMPLE_IMAGE
    if not image_path.exists():
        image_path = _download_sample_image()

    provider = os.getenv("LLM_PROVIDER", "openai")
    print(f"Image    : {image_path.name}")
    print(f"Provider : {provider}")
    print(f"Prompt   : {DESCRIBE_PROMPT}")
    print()

    if provider == "openai":
        reply = describe_with_openai(image_path, DESCRIBE_PROMPT)
    elif provider == "anthropic":
        reply = describe_with_anthropic(image_path, DESCRIBE_PROMPT)
    else:
        raise RuntimeError(
            f"Provider '{provider}' does not support vision. "
            "Set LLM_PROVIDER=openai or LLM_PROVIDER=anthropic."
        )

    print("Model reply:")
    print(reply)


def _download_sample_image() -> Path:
    import urllib.request
    assets_dir = Path(__file__).parent.parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    dest = assets_dir / "cat.jpg"
    url = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Cat_November_2010-1a.jpg/320px-Cat_November_2010-1a.jpg"
    print(f"Downloading sample image → {dest}")
    urllib.request.urlretrieve(url, dest)  # noqa: S310
    return dest


if __name__ == "__main__":
    main()
