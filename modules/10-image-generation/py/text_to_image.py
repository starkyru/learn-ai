"""text_to_image.py — Task 1 🟢: generate an image from a text prompt.

What it teaches:
    The simplest possible hosted image generation call: prompt → PNG file.
    Varying the seed demonstrates that diffusion is fully deterministic given
    the same seed, yet explores different regions of the learned image
    distribution with different seeds — all starting from the same noise
    distribution N(0, I).

How to run (from the repo root):
    uv run python modules/10-image-generation/py/text_to_image.py

Requires: REPLICATE_API_TOKEN in .env  (or IMAGE_PROVIDER + its key)
"""

from __future__ import annotations

from image_client import GenerateOptions, generate_image, save_image

# ---------------------------------------------------------------------------
# Exercise parameters — change these freely
# ---------------------------------------------------------------------------

# Change this prompt to explore what the model can generate.
PROMPT = (
    "A photorealistic red fox sitting in a snowy pine forest at golden hour, "
    "soft bokeh background, National Geographic style"
)

# Negative prompt — describe what you do NOT want in the image.
# Common boilerplate: blurry artifacts, watermarks, unrealistic anatomy.
NEGATIVE_PROMPT = "blurry, low quality, cartoon, watermark, text, logo, deformed"

# Two seeds to compare — same prompt, different random starting noise.
# Same seed + same prompt = identical output every run (reproducibility).
SEEDS = [42, 1337]


def main() -> None:
    print(f'Prompt: "{PROMPT}"\n')

    for seed in SEEDS:
        print(f"Generating with seed={seed} …")
        result = generate_image(
            GenerateOptions(
                prompt=PROMPT,
                negative_prompt=NEGATIVE_PROMPT,
                width=1024,
                height=1024,
                guidance_scale=7.5,
                num_inference_steps=25,
                seed=seed,
            )
        )
        save_image(result.image_bytes, f"output_seed_{seed}.png")
        print(f"  Provider: {result.provider}  Model: {result.model}\n")

    print("Done! Open the PNG files to compare outputs across seeds.")
    print(
        "The fox is in the same setting (same prompt) but the exact composition,\n"
        "pose, and lighting differ — because the noise starting point (seed) differs."
    )


if __name__ == "__main__":
    main()
