"""local_diffusers.py — OPTIONAL local Stable Diffusion via HuggingFace diffusers.

What it teaches:
    The same operations as img2img.py (text-to-image, img2img, inpainting) but
    running the actual SD model locally on your Mac via MPS (Metal Performance
    Shaders). This reveals the full pipeline internals: VAE encoding, U-Net
    denoising loop, and VAE decoding — all in Python.

WARNING:
    - First run downloads ~6 GB of model weights.
    - MPS (Apple Silicon) runs at roughly 5–15 it/s; a 25-step generation
      takes 30-90 s depending on image size and your GPU.
    - If you have no GPU, diffusers will fall back to CPU (very slow).

Why SDXL-Turbo?
    SDXL-Turbo (Adversarial Diffusion Distillation) is a distilled model that
    achieves good quality in just 1–4 steps — the fastest local option.
    Normal SDXL needs 25–50 steps. The trade-off: slightly less detail and
    less prompt adherence compared to full SDXL at high step counts.

How to run (from the repo root):
    uv sync --extra imagegen          # installs diffusers, torch, pillow, etc.
    uv run python modules/10-image-generation/py/local_diffusers.py

No API key required — the model runs entirely on your machine.
"""

from __future__ import annotations

# Guard — fail early with a clear message if diffusers is not installed
try:
    import torch
    from diffusers import AutoPipelineForText2Image, AutoPipelineForImage2Image
    from PIL import Image
except ImportError as exc:
    raise ImportError(
        f"Missing dependency: {exc}\n"
        "Install with: uv sync --extra imagegen\n"
        "This pulls in: diffusers, transformers, accelerate, torch, pillow"
    ) from exc

import io
from pathlib import Path

# ---------------------------------------------------------------------------
# Device selection
# ---------------------------------------------------------------------------

def _get_device() -> str:
    """Return the best available device for diffusers on this machine."""
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    print("WARNING: No GPU found. Falling back to CPU — this will be VERY slow.")
    return "cpu"


# ---------------------------------------------------------------------------
# Task A — Text-to-image with SDXL-Turbo (local)
# ---------------------------------------------------------------------------

def run_text_to_image(prompt: str, num_steps: int = 4, seed: int = 42) -> Image.Image:
    """Generate an image from a text prompt using SDXL-Turbo locally.

    SDXL-Turbo uses adversarial distillation to generate in 1-4 steps.
    Note: guidance_scale must be 0.0 for SDXL-Turbo (it's baked into distillation).
    """
    device = _get_device()
    dtype = torch.float16 if device != "cpu" else torch.float32

    print(f"Loading SDXL-Turbo on {device} (first run downloads ~3 GB) …")
    pipe = AutoPipelineForText2Image.from_pretrained(
        "stabilityai/sdxl-turbo",
        torch_dtype=dtype,
        variant="fp16" if device != "cpu" else None,
    )
    pipe = pipe.to(device)

    generator = torch.Generator(device=device).manual_seed(seed)
    print(f"Generating ({num_steps} steps) …")
    result = pipe(
        prompt=prompt,
        num_inference_steps=num_steps,
        guidance_scale=0.0,  # required for SDXL-Turbo
        generator=generator,
    )
    return result.images[0]


# ---------------------------------------------------------------------------
# Task B — img2img with SDXL-Turbo (local)
# ---------------------------------------------------------------------------

def run_img2img(
    input_image: Image.Image,
    prompt: str,
    strength: float = 0.6,
    num_steps: int = 4,
    seed: int = 42,
) -> Image.Image:
    """Transform an input image using SDXL-Turbo img2img locally.

    The 'strength' parameter controls how much noise is added before denoising:
        0.0 → return the input unchanged
        1.0 → full text-to-image (ignores input)
        0.5 → balanced; keeps composition, changes style

    Note: effective_steps = int(strength * num_steps). With num_steps=4 and
    strength=0.5, only 2 reverse steps are run.
    """
    device = _get_device()
    dtype = torch.float16 if device != "cpu" else torch.float32

    print(f"Loading SDXL-Turbo img2img pipeline on {device} …")
    pipe = AutoPipelineForImage2Image.from_pretrained(
        "stabilityai/sdxl-turbo",
        torch_dtype=dtype,
        variant="fp16" if device != "cpu" else None,
    )
    pipe = pipe.to(device)

    # Resize input to SD-friendly dimensions
    input_image = input_image.resize((512, 512))

    generator = torch.Generator(device=device).manual_seed(seed)
    print(f"Running img2img (strength={strength}, steps={num_steps}) …")
    result = pipe(
        prompt=prompt,
        image=input_image,
        num_inference_steps=num_steps,
        strength=strength,
        guidance_scale=0.0,  # SDXL-Turbo only
        generator=generator,
    )
    return result.images[0]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Text-to-image
    t2i_image = run_text_to_image(
        prompt="A red fox in a snowy forest at golden hour, photorealistic",
        num_steps=4,
        seed=42,
    )
    t2i_path = Path("local_t2i_output.png")
    t2i_image.save(t2i_path)
    print(f"Saved → {t2i_path}\n")

    # img2img using the generated image as input
    print("Running img2img on generated image …")
    i2i_image = run_img2img(
        input_image=t2i_image,
        prompt="The same fox, in the style of a watercolour painting, soft washes",
        strength=0.65,
        num_steps=4,
        seed=7,
    )
    i2i_path = Path("local_i2i_output.png")
    i2i_image.save(i2i_path)
    print(f"Saved → {i2i_path}\n")

    print("Done!")
    print()
    print("What you just ran (the hidden pipeline steps):")
    print("  1. VAE encoder: input image → 64×64×4 latent tensor")
    print("  2. CLIP text encoder: prompt → 77×1024 token embeddings")
    print("  3. Forward noising: add noise to latent for `strength` fraction of T steps")
    print("  4. U-Net reverse loop: ε_θ(x_t, t, c) predicts noise; DDPM/DDIM step removes it")
    print("  5. VAE decoder: final latent → 512×512×3 pixel image")


if __name__ == "__main__":
    main()
