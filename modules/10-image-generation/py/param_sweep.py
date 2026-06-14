"""param_sweep.py — Task 2 🟡: explore guidance scale, steps, and negative prompts.

What it teaches:
    Every "knob" on an image generation request has a concrete effect rooted
    in the math. This script sends ~6 API calls across two parameter axes and
    assembles the results into a PNG grid so you can see the differences
    side-by-side.

    Parameters explored:
        guidance_scale  — how strongly the denoiser follows the text prompt
                          (classifier-free guidance weight, see README Concept 5)
        num_inference_steps — how many denoising steps to run
                          (more ≈ more detail, diminishing returns past ~40)

    The negative_prompt is kept constant and its effect explained below.

How to run (from the repo root):
    uv run python modules/10-image-generation/py/param_sweep.py

    Sends ~6 API requests. Each takes a few seconds. Total ~30-60 s.

Requires: REPLICATE_API_TOKEN (or IMAGE_PROVIDER + its key)
Requires: pip install pillow  (for grid assembly; part of --extra imagegen)

Note on negative prompts:
    Classifier-free guidance (CFG) runs the U-Net TWICE per step:
        ε_guided = ε_uncond + scale * (ε_cond - ε_uncond)
    The negative prompt is encoded by CLIP and used as ε_uncond, making the
    model steer AWAY from those features. An empty negative prompt uses a zero
    embedding instead. Common values: "blurry, low quality, watermark, deformed".
"""

from __future__ import annotations

import io
import sys
from itertools import product

from image_client import GenerateOptions, generate_image

# ---------------------------------------------------------------------------
# Sweep configuration — change these to explore
# ---------------------------------------------------------------------------

PROMPT = (
    "A majestic snow leopard on a mountain ridge at dusk, cinematic lighting, "
    "ultra-detailed fur, professional wildlife photography"
)

# Try: ""  vs  "blurry, low quality, watermark, cartoon, distorted"
NEGATIVE_PROMPT = "blurry, low quality, watermark, cartoon, deformed"

# Axis 1: guidance_scale (columns)
GUIDANCE_SCALES = [3.0, 7.5, 15.0]

# Axis 2: num_inference_steps (rows)
STEPS_LIST = [10, 30]

# Fixed seed so all images share the same noise starting point —
# differences come only from the parameter being swept.
SEED = 42

OUTPUT_PATH = "sweep_grid.png"


def _assemble_grid(images: list[bytes], cols: int, rows: int) -> bytes:
    """Stitch PIL images into a (cols × rows) grid. Returns PNG bytes."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print(
            "\nPillow is not installed. Run `uv sync --extra imagegen` to get it,\n"
            "or install manually: pip install pillow\n"
            "Saving individual images instead."
        )
        for idx, img_bytes in enumerate(images):
            path = f"sweep_img_{idx}.png"
            with open(path, "wb") as f:
                f.write(img_bytes)
            print(f"  Saved {path}")
        sys.exit(0)

    pil_images = [Image.open(io.BytesIO(b)) for b in images]
    w, h = pil_images[0].size
    label_h = 30  # px for axis labels

    grid_w = cols * w
    grid_h = rows * h + label_h
    grid = Image.new("RGB", (grid_w, grid_h), (240, 240, 240))

    # Try to get a font; fall back gracefully
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except Exception:
        font = ImageFont.load_default()

    draw = ImageDraw.Draw(grid)

    for idx, pil_img in enumerate(pil_images):
        col = idx % cols
        row = idx // cols
        x = col * w
        y = row * h + label_h
        grid.paste(pil_img, (x, y))

    # Column labels (guidance scale)
    for col, gs in enumerate(GUIDANCE_SCALES):
        draw.text((col * w + 5, 5), f"CFG={gs}", fill=(30, 30, 30), font=font)

    buf = io.BytesIO()
    grid.save(buf, format="PNG")
    return buf.getvalue()


def main() -> None:
    print(f'Prompt: "{PROMPT}"')
    print(f"Negative: {NEGATIVE_PROMPT!r}")
    print(f"Grid: {len(GUIDANCE_SCALES)} guidance scales × {len(STEPS_LIST)} step counts\n")

    combinations = list(product(STEPS_LIST, GUIDANCE_SCALES))
    images: list[bytes] = []

    for steps, gs in combinations:
        label = f"steps={steps}, cfg={gs}"
        print(f"  Generating {label} …")
        result = generate_image(
            GenerateOptions(
                prompt=PROMPT,
                negative_prompt=NEGATIVE_PROMPT,
                width=512,  # smaller for speed in a sweep
                height=512,
                guidance_scale=gs,
                num_inference_steps=steps,
                seed=SEED,
            )
        )
        images.append(result.image_bytes)
        print(f"  Done ({result.provider})")

    print(f"\nAssembling {len(GUIDANCE_SCALES)}×{len(STEPS_LIST)} grid …")
    grid_bytes = _assemble_grid(
        images, cols=len(GUIDANCE_SCALES), rows=len(STEPS_LIST)
    )
    with open(OUTPUT_PATH, "wb") as f:
        f.write(grid_bytes)
    print(f"Grid saved → {OUTPUT_PATH}")
    print()
    print("What to look for:")
    print("  CFG  3.0 (left col) : loosely follows the prompt; painterly, creative.")
    print("  CFG  7.5 (mid col)  : balanced — the default for most use cases.")
    print("  CFG 15.0 (right col): strong prompt adherence; may oversaturate/over-sharpen.")
    print("  10 steps (top row)  : faster but coarser; some coherence issues visible.")
    print("  30 steps (bot row)  : more detail and cleaner edges; diminishing returns above ~40.")


if __name__ == "__main__":
    main()
