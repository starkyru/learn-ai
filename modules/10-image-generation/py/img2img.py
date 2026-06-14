"""img2img.py — Task 3 🟡: image-to-image and inpainting via hosted API.

What it teaches:
    Standard text-to-image always starts from pure Gaussian noise (x_T).
    img2img starts from a PARTIALLY noised version of a real image, so the
    denoiser can build on the existing composition while still following the
    text prompt. The ``strength`` parameter controls how noisy the start is:

        strength = 1.0  → fully noised  ≈ text-to-image (ignores the input)
        strength = 0.5  → half-noised   → keeps rough layout, changes details
        strength = 0.2  → lightly noised → very close to the original

    Inpainting is img2img with a binary mask. The masked region is noised and
    denoised from scratch (guided by the prompt); the unmasked region is
    preserved by blending at each step. Some models (SD-inpainting, SDXL-inpainting)
    were fine-tuned for better edge blending — but any img2img model works.

How to run (from the repo root):
    uv run python modules/10-image-generation/py/img2img.py

    This downloads a small sample image (~80 KB) on first run.
    Sends 2 API requests (img2img + inpainting). Each ~10-30 s.

Requires: REPLICATE_API_TOKEN (or IMAGE_PROVIDER + its key)
Requires: pip install pillow httpx  (for image prep; part of --extra imagegen)

Local diffusers alternative:
    See local_diffusers.py for the same operations using HuggingFace diffusers
    running locally on MPS (Apple Silicon). Download size: ~6 GB.
"""

from __future__ import annotations

import base64
import io
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# A freely licensed landscape photo (Unsplash — CC0)
SAMPLE_IMAGE_URL = (
    "https://images.unsplash.com/photo-1506905925346-21bda4d32df4"
    "?w=512&h=512&fit=crop&auto=format"
)
SAMPLE_IMAGE_PATH = Path("sample_input.png")

IMG2IMG_PROMPT = (
    "The same mountain landscape in the style of a Japanese woodblock print, "
    "ukiyo-e, bold outlines, muted ink colours"
)
IMG2IMG_STRENGTH = 0.65   # 0 = keep everything; 1 = full text-to-image
IMG2IMG_OUTPUT = "img2img_output.png"

INPAINT_PROMPT = "A dramatic stormy sky with lightning bolts, photorealistic"
INPAINT_OUTPUT = "inpaint_output.png"

SEED = 42


# ---------------------------------------------------------------------------
# Image utilities
# ---------------------------------------------------------------------------

def download_sample_image() -> bytes:
    """Download the sample image if not already cached."""
    if SAMPLE_IMAGE_PATH.exists():
        print(f"Using cached {SAMPLE_IMAGE_PATH}")
        return SAMPLE_IMAGE_PATH.read_bytes()

    print(f"Downloading sample image from Unsplash …")
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        res = client.get(SAMPLE_IMAGE_URL)
        res.raise_for_status()
    SAMPLE_IMAGE_PATH.write_bytes(res.content)
    print(f"  Saved → {SAMPLE_IMAGE_PATH}")
    return res.content


def make_top_mask(width: int = 512, height: int = 512) -> bytes:
    """Create a white-on-black mask covering the top 40% of the image (the sky).

    White = region to regenerate; black = region to preserve.
    """
    try:
        from PIL import Image
    except ImportError:
        raise ImportError(
            "Pillow required for mask creation. Run: uv sync --extra imagegen"
        )

    mask = Image.new("L", (width, height), 0)  # all black
    sky_rows = int(height * 0.4)
    for y in range(sky_rows):
        for x in range(width):
            mask.putpixel((x, y), 255)  # white = regenerate

    buf = io.BytesIO()
    mask.save(buf, format="PNG")
    return buf.getvalue()


def to_data_uri(image_bytes: bytes, mime: str = "image/png") -> str:
    """Encode image bytes as a base64 data URI for APIs that require it."""
    b64 = base64.b64encode(image_bytes).decode()
    return f"data:{mime};base64,{b64}"


# ---------------------------------------------------------------------------
# Replicate img2img
# ---------------------------------------------------------------------------

def _img2img_replicate(
    image_bytes: bytes,
    prompt: str,
    strength: float,
    seed: int,
) -> bytes:
    """img2img via Replicate using SDXL img2img version."""
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError("Missing REPLICATE_API_TOKEN")

    # SDXL img2img model on Replicate
    version = "7762fd07cf82c948538e41f63f77d685e02b063e37e496e96eefd46c929f9bdc"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "version": version,
        "input": {
            "prompt": prompt,
            "image": to_data_uri(image_bytes),
            "prompt_strength": strength,  # replicate uses "prompt_strength"
            "num_inference_steps": 30,
            "guidance_scale": 7.5,
            "seed": seed,
        },
    }

    with httpx.Client(timeout=30) as client:
        res = client.post("https://api.replicate.com/v1/predictions", headers=headers, json=payload)
        res.raise_for_status()
        prediction = res.json()
        poll_url: str = prediction["urls"]["get"]

        for _ in range(60):
            time.sleep(2)
            poll = client.get(poll_url, headers=headers)
            poll.raise_for_status()
            data = poll.json()
            if data["status"] == "succeeded":
                output_url: str = data["output"][0]
                img_res = client.get(output_url, timeout=60)
                img_res.raise_for_status()
                return img_res.content
            if data["status"] == "failed":
                raise RuntimeError(f"Replicate img2img failed: {data.get('error')}")

    raise TimeoutError("Replicate img2img timed out")


def _inpaint_replicate(
    image_bytes: bytes,
    mask_bytes: bytes,
    prompt: str,
    seed: int,
) -> bytes:
    """Inpainting via Replicate (SDXL inpainting model)."""
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError("Missing REPLICATE_API_TOKEN")

    # SDXL inpainting model on Replicate
    version = "ca1f5e306e5721e19c473e0d094e6603f0456fe759c10715fcd6c1b79242d4a5"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "version": version,
        "input": {
            "prompt": prompt,
            "image": to_data_uri(image_bytes),
            "mask": to_data_uri(mask_bytes),
            "num_inference_steps": 30,
            "guidance_scale": 8.0,
            "seed": seed,
        },
    }

    with httpx.Client(timeout=30) as client:
        res = client.post("https://api.replicate.com/v1/predictions", headers=headers, json=payload)
        res.raise_for_status()
        prediction = res.json()
        poll_url: str = prediction["urls"]["get"]

        for _ in range(60):
            time.sleep(2)
            poll = client.get(poll_url, headers=headers)
            poll.raise_for_status()
            data = poll.json()
            if data["status"] == "succeeded":
                output_url: str = data["output"][0]
                img_res = client.get(output_url, timeout=60)
                img_res.raise_for_status()
                return img_res.content
            if data["status"] == "failed":
                raise RuntimeError(f"Replicate inpainting failed: {data.get('error')}")

    raise TimeoutError("Replicate inpainting timed out")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # 1. Get the input image
    input_bytes = download_sample_image()
    print()

    # 2. img2img — transform the landscape into a ukiyo-e woodblock style
    print("Running img2img …")
    print(f"  Prompt   : {IMG2IMG_PROMPT}")
    print(f"  Strength : {IMG2IMG_STRENGTH}  (0=keep original, 1=full text2img)")
    result_bytes = _img2img_replicate(
        image_bytes=input_bytes,
        prompt=IMG2IMG_PROMPT,
        strength=IMG2IMG_STRENGTH,
        seed=SEED,
    )
    Path(IMG2IMG_OUTPUT).write_bytes(result_bytes)
    print(f"  Saved → {IMG2IMG_OUTPUT}")
    print()

    # 3. Inpainting — replace the sky with a storm
    print("Creating inpaint mask (top 40% of image = sky) …")
    mask_bytes = make_top_mask(512, 512)
    Path("inpaint_mask.png").write_bytes(mask_bytes)
    print("  mask saved → inpaint_mask.png")

    print("Running inpainting …")
    print(f"  Prompt : {INPAINT_PROMPT}")
    inpaint_bytes = _inpaint_replicate(
        image_bytes=input_bytes,
        mask_bytes=mask_bytes,
        prompt=INPAINT_PROMPT,
        seed=SEED,
    )
    Path(INPAINT_OUTPUT).write_bytes(inpaint_bytes)
    print(f"  Saved → {INPAINT_OUTPUT}")
    print()
    print("Compare:")
    print("  sample_input.png   — original photo")
    print("  img2img_output.png — same composition, ukiyo-e style")
    print("  inpaint_output.png — same mountains, stormy AI-generated sky")
    print()
    print("Key insight: in img2img the model starts from x_t (partially noised),")
    print("not x_T (pure noise). The denoiser has less work to undo, so the")
    print("spatial structure of the input is preserved. Strength controls x_t's t.")


if __name__ == "__main__":
    main()
