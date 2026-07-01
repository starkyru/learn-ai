"""task1_classify.py — image classification with a pretrained model.  🟢

What it teaches:
    How a pretrained vision model assigns a label (or ranked list of labels) to
    an image. We use the HuggingFace Inference API so no GPU or multi-GB model
    download is needed — the model lives in HF's cloud.

How to run (from the repo root):
    uv run python modules/09-computer-vision/py/task1_classify.py

Environment variables (in .env):
    HF_TOKEN   — HuggingFace token (get one free at huggingface.co/settings/tokens)

Optional local path (skip the API, run model on your machine):
    uv sync --extra vision         # installs torch, torchvision, transformers, pillow
    Then uncomment the LOCAL block below and comment out the HOSTED block.
    Warning: first run downloads ~350 MB of model weights; slow on Mac MPS.

Acceptance:
    - Prints a ranked list of label/score pairs for the sample image.
    - You can swap IMAGE_PATH to any local JPEG/PNG and it still works.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Path to a sample image — uses the bundled one or any local file you provide.
SAMPLE_IMAGE = Path(__file__).parent.parent / "assets" / "cat.jpg"

# HuggingFace model for image classification (ImageNet-1k, 1000 classes).
# See: https://huggingface.co/google/vit-base-patch16-224
HF_MODEL = "google/vit-base-patch16-224"


# ---------------------------------------------------------------------------
# HOSTED path — HuggingFace Inference API (default, no local GPU needed)
# ---------------------------------------------------------------------------

def classify_hosted(image_path: Path) -> list[dict]:
    """Call HF Inference API to classify the image. Returns list of
    {'label': str, 'score': float} dicts sorted by score descending."""
    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        raise ImportError(
            "huggingface_hub is not installed. Run: uv sync --extra vision\n"
            "Or install manually: pip install huggingface-hub"
        )

    token = os.getenv("HF_TOKEN")
    if not token:
        raise RuntimeError(
            "Missing HF_TOKEN. Get a free token at huggingface.co/settings/tokens "
            "and add HF_TOKEN=... to your .env file."
        )

    client = InferenceClient(token=token)

    # The InferenceClient accepts a file path, URL, or raw bytes.
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # TODO (exercise): classify the image via the client.
    #   - Call `client.image_classification(...)`, passing the raw `image_bytes`
    #     and telling it which `model` to use (HF_MODEL).
    #   - The return value is a list of ClassificationOutput objects, each with
    #     `.label` and `.score` attributes.
    results = None  # replace with the API call

    raise NotImplementedError(
        "Complete the TODO above: call client.image_classification() "
        "and assign the result to `results`."
    )

    # TODO (exercise): return `results` as a plain list of `{"label": ..., "score": ...}`
    # dicts (read the .label / .score off each item) so they print cleanly.
    return results  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# LOCAL path (optional) — transformers + PIL, runs entirely offline
# ---------------------------------------------------------------------------

def classify_local(image_path: Path) -> list[dict]:
    """Classify using a locally-downloaded ViT model via transformers.
    Uncomment and call this instead of classify_hosted() to run offline.
    First run will download ~350 MB of model weights.
    """
    # TODO (optional exercise): implement the offline path.
    #   - From `transformers`, build an "image-classification" `pipeline(...)`
    #     pointed at HF_MODEL; open the file with PIL's `Image.open(...)` and
    #     convert it to "RGB".
    #   - Run the pipeline on the image (it returns a list of
    #     `{"label": ..., "score": ...}` dicts) and return them sorted by score,
    #     highest first.

    raise NotImplementedError("Local path is not implemented yet — see the TODO above.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    image_path = SAMPLE_IMAGE
    if not image_path.exists():
        # Fallback: download the sample image automatically on first run.
        image_path = _download_sample_image()

    print(f"Image    : {image_path.name}")
    print(f"Model    : {HF_MODEL} (via HF Inference API)")
    print()

    results = classify_hosted(image_path)

    print("Top predictions:")
    for i, item in enumerate(results[:5], 1):
        label = item["label"] if isinstance(item, dict) else item.label
        score = item["score"] if isinstance(item, dict) else item.score
        print(f"  {i}. {label:<40} {score:.3f}")


def _download_sample_image() -> Path:
    """Download a royalty-free sample image on first run."""
    import urllib.request

    assets_dir = Path(__file__).parent.parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    dest = assets_dir / "cat.jpg"

    # Wikimedia Commons — public domain cat photo.
    url = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Cat_November_2010-1a.jpg/320px-Cat_November_2010-1a.jpg"
    print(f"Downloading sample image from Wikimedia Commons → {dest}")
    urllib.request.urlretrieve(url, dest)  # noqa: S310
    return dest


if __name__ == "__main__":
    main()
