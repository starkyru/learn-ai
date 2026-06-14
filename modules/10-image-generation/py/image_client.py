"""image_client.py — provider-agnostic hosted image generation client.

What it teaches:
    The same abstraction pattern as llm_core — a single ``generate_image()``
    function that hides provider-specific HTTP details. Change
    IMAGE_PROVIDER (or the env var) and every exercise script just works.

Supported providers (set IMAGE_PROVIDER in .env or override per-call):
    "replicate"   REPLICATE_API_TOKEN   default; poll-based, ~$0.004/image
    "hf"          HF_TOKEN              HuggingFace Inference API, free tier
    "stability"   STABILITY_API_KEY     Stability AI REST API

How to add another provider:
    1. Write a function _generate_<name>(opts) -> bytes.
    2. Add a case in generate_image().
    Done.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

Provider = Literal["replicate", "hf", "stability"]


@dataclass
class GenerateOptions:
    """All parameters that control image generation."""

    prompt: str
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    guidance_scale: float = 7.0
    num_inference_steps: int = 25
    seed: int | None = None


@dataclass
class GenerateResult:
    """Return value from generate_image()."""

    image_bytes: bytes
    provider: str
    model: str


# ---------------------------------------------------------------------------
# Replicate
# ---------------------------------------------------------------------------

_REPLICATE_MODEL_VERSION = "39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
_REPLICATE_MODEL = "stability-ai/sdxl"


def _generate_replicate(opts: GenerateOptions) -> GenerateResult:
    """Text-to-image via Replicate's polling REST API.

    Replicate works asynchronously: you POST to create a prediction,
    then poll /v1/predictions/{id} until status == "succeeded".
    Docs: https://replicate.com/docs/reference/http
    """
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError("Missing REPLICATE_API_TOKEN in .env")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload: dict = {
        "version": _REPLICATE_MODEL_VERSION,
        "input": {
            "prompt": opts.prompt,
            "negative_prompt": opts.negative_prompt,
            "width": opts.width,
            "height": opts.height,
            "guidance_scale": opts.guidance_scale,
            "num_inference_steps": opts.num_inference_steps,
        },
    }
    if opts.seed is not None:
        payload["input"]["seed"] = opts.seed

    with httpx.Client(timeout=30) as client:
        # 1. Create prediction
        res = client.post("https://api.replicate.com/v1/predictions", headers=headers, json=payload)
        res.raise_for_status()
        prediction = res.json()
        poll_url: str = prediction["urls"]["get"]

        # 2. Poll until done (usually 10-30 s)
        for _ in range(60):
            time.sleep(2)
            poll = client.get(poll_url, headers=headers)
            poll.raise_for_status()
            data = poll.json()

            if data["status"] == "succeeded":
                image_url: str = data["output"][0]
                break
            if data["status"] == "failed":
                raise RuntimeError(f"Replicate prediction failed: {data.get('error')}")
        else:
            raise TimeoutError("Replicate prediction timed out after 120 s")

        # 3. Download PNG bytes
        img_res = client.get(image_url, timeout=60)
        img_res.raise_for_status()
        return GenerateResult(
            image_bytes=img_res.content,
            provider="replicate",
            model=_REPLICATE_MODEL,
        )


# ---------------------------------------------------------------------------
# HuggingFace Inference API
# ---------------------------------------------------------------------------

_HF_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"


def _generate_hf(opts: GenerateOptions) -> GenerateResult:
    """Text-to-image via HuggingFace Inference API.

    The response body IS the image bytes (PNG), unlike Replicate's URL indirection.
    Docs: https://huggingface.co/docs/api-inference/tasks/text-to-image
    Free tier has rate limits; upgrade to Inference Endpoints for production.
    """
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("Missing HF_TOKEN in .env")

    url = f"https://api-inference.huggingface.co/models/{_HF_MODEL}"
    payload = {
        "inputs": opts.prompt,
        "parameters": {
            "negative_prompt": opts.negative_prompt or None,
            "width": opts.width,
            "height": opts.height,
            "guidance_scale": opts.guidance_scale,
            "num_inference_steps": opts.num_inference_steps,
            "seed": opts.seed,
        },
    }

    with httpx.Client(timeout=120) as client:
        res = client.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        # HF returns 503 while the model is loading — retry once
        if res.status_code == 503:
            print("  (HF model loading, waiting 20 s …)")
            time.sleep(20)
            res = client.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload)
        res.raise_for_status()
        return GenerateResult(image_bytes=res.content, provider="huggingface", model=_HF_MODEL)


# ---------------------------------------------------------------------------
# Stability AI
# ---------------------------------------------------------------------------

_STABILITY_MODEL = "stability-ai/stable-image-core"


def _generate_stability(opts: GenerateOptions) -> GenerateResult:
    """Text-to-image via Stability AI platform API.

    Uses multipart/form-data. Response is direct PNG bytes when Accept: image/*.
    Docs: https://platform.stability.ai/docs/api-reference#tag/Generate
    """
    api_key = os.environ.get("STABILITY_API_KEY")
    if not api_key:
        raise RuntimeError("Missing STABILITY_API_KEY in .env")

    data: dict[str, str] = {
        "prompt": opts.prompt,
        "aspect_ratio": "1:1",
        "output_format": "png",
    }
    if opts.negative_prompt:
        data["negative_prompt"] = opts.negative_prompt
    if opts.seed is not None:
        data["seed"] = str(opts.seed)

    with httpx.Client(timeout=60) as client:
        res = client.post(
            "https://api.stability.ai/v2beta/stable-image/generate/core",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "image/*",
            },
            data=data,
        )
        res.raise_for_status()
        return GenerateResult(image_bytes=res.content, provider="stability", model=_STABILITY_MODEL)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_DEFAULT_PROVIDER: Provider = "replicate"


def generate_image(opts: GenerateOptions, provider: str | None = None) -> GenerateResult:
    """Generate an image from a text prompt using the configured hosted provider.

    The provider is resolved in this order:
    1. The ``provider`` argument if passed.
    2. The IMAGE_PROVIDER environment variable.
    3. "replicate" (the default).

    Example::

        result = generate_image(GenerateOptions(prompt="a red fox in snow", seed=42))
        Path("fox.png").write_bytes(result.image_bytes)
    """
    p = provider or os.environ.get("IMAGE_PROVIDER", _DEFAULT_PROVIDER)
    if p == "replicate":
        return _generate_replicate(opts)
    if p in ("hf", "huggingface"):
        return _generate_hf(opts)
    if p == "stability":
        return _generate_stability(opts)
    raise ValueError(f"Unknown IMAGE_PROVIDER={p!r}. Choose: replicate | hf | stability")


def save_image(image_bytes: bytes, path: str | Path) -> Path:
    """Write image bytes to disk and print a confirmation line."""
    p = Path(path)
    p.write_bytes(image_bytes)
    print(f"Saved → {p}  ({len(image_bytes) / 1024:.1f} KB)")
    return p
