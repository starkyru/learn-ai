"""task2_clip.py — zero-shot image classification with CLIP.  🟢

What it teaches:
    CLIP (Contrastive Language–Image Pretraining, OpenAI 2021) learns a *shared
    embedding space* for images and text. A photo of a cat and the sentence
    "a photo of a cat" end up near each other in that space — without ever being
    trained on a labelled dataset in the traditional sense.

    Zero-shot classification: given an image and a list of candidate text labels,
    compute the cosine similarity between the image embedding and each label
    embedding and rank by score. No fine-tuning needed.

    This is fundamentally different from the task-1 classifier: there the model
    can only predict the 1000 ImageNet classes it was trained on. With CLIP you
    supply any labels you like at inference time — the "vocabulary" is open.

How to run (from the repo root):
    uv run python modules/09-computer-vision/py/task2_clip.py

Environment variables (in .env):
    HF_TOKEN   — HuggingFace token (free at huggingface.co/settings/tokens)

Optional local path (no API, runs offline):
    uv sync --extra vision     # torch + transformers + pillow
    Uncomment the LOCAL block at the bottom.

Acceptance:
    - Prints each candidate label with its CLIP similarity score.
    - The correct label (or the closest one to the image content) ranks highest.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SAMPLE_IMAGE = Path(__file__).parent.parent / "assets" / "cat.jpg"

# CLIP model on HuggingFace
HF_CLIP_MODEL = "openai/clip-vit-base-patch32"

# Candidate labels for zero-shot classification — try changing these!
CANDIDATE_LABELS = [
    "a photo of a cat",
    "a photo of a dog",
    "a photo of a bird",
    "a photo of a car",
    "a photo of a landscape",
]


# ---------------------------------------------------------------------------
# HOSTED path — HuggingFace zero-shot-image-classification pipeline via API
# ---------------------------------------------------------------------------

def clip_classify_hosted(image_path: Path, labels: list[str]) -> list[dict]:
    """Use HF Inference API's zero-shot-image-classification endpoint.
    Returns list of {'label': str, 'score': float} sorted by score descending.
    """
    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        raise ImportError("Run: pip install huggingface-hub")

    token = os.getenv("HF_TOKEN")
    if not token:
        raise RuntimeError(
            "Missing HF_TOKEN. Get one free at huggingface.co/settings/tokens."
        )

    client = InferenceClient(token=token)

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # TODO (exercise): run zero-shot classification via the client.
    #   - Call `client.zero_shot_image_classification(...)`, passing the raw
    #     `image_bytes`, the `candidate_labels` (the `labels` argument), and which
    #     `model` to use (HF_CLIP_MODEL).
    #   - The return type is a list[ClassificationOutput] with `.label` / `.score`.
    results = None  # replace with the API call

    raise NotImplementedError(
        "Complete the TODO: call client.zero_shot_image_classification() "
        "and assign results. Then remove the raise."
    )

    # TODO (exercise): return `results` as plain `{"label": ..., "score": ...}`
    # dicts, sorted by score descending.
    return results  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# LOCAL path (optional) — transformers + PIL, fully offline
# ---------------------------------------------------------------------------

def clip_classify_local(image_path: Path, labels: list[str]) -> list[dict]:
    """Classify using a local CLIP model. Downloads ~600 MB on first run."""
    # TODO (optional exercise): implement the offline path.
    #   - From `transformers`, build a "zero-shot-image-classification"
    #     `pipeline(...)` pointed at HF_CLIP_MODEL; open the file with PIL's
    #     `Image.open(...)` and convert it to "RGB".
    #   - Run the pipeline on the image, passing `candidate_labels=labels`. It
    #     returns a list already sorted by score descending; reshape each entry
    #     into a `{"label": ..., "score": ...}` dict and return them.

    raise NotImplementedError("Local path not yet implemented — see the TODO above.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    image_path = SAMPLE_IMAGE
    if not image_path.exists():
        image_path = _download_sample_image()

    print(f"Image    : {image_path.name}")
    print(f"Model    : {HF_CLIP_MODEL} (CLIP via HF Inference API)")
    print(f"Labels   : {CANDIDATE_LABELS}")
    print()

    results = clip_classify_hosted(image_path, CANDIDATE_LABELS)

    print("CLIP similarity scores (higher = more similar):")
    for item in results:
        label = item["label"] if isinstance(item, dict) else item.label
        score = item["score"] if isinstance(item, dict) else item.score
        bar = "#" * int(score * 30)
        print(f"  {label:<35} {score:.4f}  {bar}")

    winner = results[0]
    label = winner["label"] if isinstance(winner, dict) else winner.label
    print(f"\nBest match: {label}")


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
