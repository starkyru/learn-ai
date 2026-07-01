"""task4_convolution.py — 2-D convolution from scratch.  🔴

What it teaches:
    Convolutional Neural Networks (CNNs) dominated computer vision from 2012
    (AlexNet) until Vision Transformers (ViT, 2020) took over. Understanding
    convolution is still essential because:
      - It's the operation inside every CNN layer.
      - ViT patches are a spatial structure too (just processed differently).
      - Edge detection by hand shows *exactly* what feature maps are.

    A 2-D convolution slides a small matrix (the **kernel** or **filter**) over
    an image, computing a dot product at each position. The output (a **feature
    map**) highlights whatever pattern the kernel encodes:
      - A horizontal-edge kernel lights up where brightness changes top→bottom.
      - A Gaussian-blur kernel smooths the image.
      - Learned CNN kernels detect curved edges, textures, eyes, wheels, etc.

    In a real CNN:
      - There are many kernels per layer (64, 256, …), each learning a different
        feature.
      - Multiple layers stack, so later kernels see combinations of earlier
        features (edges → shapes → parts → objects).

Kernels used here:
    EDGE_HORIZONTAL  — Sobel filter, detects horizontal edges
    EDGE_VERTICAL    — Sobel filter, detects vertical edges
    BLUR             — 3×3 box blur (averaging kernel)

How to run (from the repo root):
    uv sync --extra vision          # numpy + pillow (already present for task 1)
    uv run python modules/09-computer-vision/py/task4_convolution.py

    Output: saves edge_h.png / edge_v.png / blur.png next to the sample image.
    Open them to visualise what each kernel does.

Acceptance:
    - conv2d() passes the small sanity-check test at the bottom.
    - Output images are written and visually make sense (edges lit up, blur
      smoothed).

Note: numpy's own vectorised ops could do this faster; we use explicit Python
loops on purpose so the inner operation is completely transparent.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

SAMPLE_IMAGE = Path(__file__).parent.parent / "assets" / "cat.jpg"
OUTPUT_DIR = Path(__file__).parent.parent / "assets"

# ---------------------------------------------------------------------------
# Kernels
# ---------------------------------------------------------------------------

# Sobel horizontal-edge kernel: bright where intensity changes top→bottom.
EDGE_HORIZONTAL = np.array([
    [-1, -2, -1],
    [ 0,  0,  0],
    [ 1,  2,  1],
], dtype=np.float32)

# Sobel vertical-edge kernel: bright where intensity changes left→right.
EDGE_VERTICAL = np.array([
    [-1, 0, 1],
    [-2, 0, 2],
    [-1, 0, 1],
], dtype=np.float32)

# Simple 3×3 box blur: each output pixel is the average of its 3×3 neighbourhood.
BLUR = np.ones((3, 3), dtype=np.float32) / 9.0


# ---------------------------------------------------------------------------
# Task: implement 2-D convolution
# ---------------------------------------------------------------------------

def conv2d(image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """Apply a 2-D convolution kernel to a single-channel (grayscale) image.

    Args:
        image:  H × W float32 array, values in [0, 255].
        kernel: K × K float32 array (we only support odd-sized square kernels).

    Returns:
        H × W float32 array — the feature map. Edges use zero-padding so the
        output has the same spatial size as the input.

    Implementation notes:
        - k_half = kernel.shape[0] // 2 gives the padding on each side.
        - Pad `image` with zeros of width k_half on all four sides.
        - For each output position (i, j) extract the K×K patch from the padded
          image, element-wise multiply with the kernel, and sum the result.
        - That sum is output[i, j].

    Convolution vs correlation:
        Strictly, convolution flips the kernel 180° before sliding it; in deep
        learning the kernel is learned anyway so the flip is absorbed into the
        weights. Here we implement correlation (no flip), which is what PyTorch
        nn.Conv2d actually does.
    """
    H, W = image.shape
    K = kernel.shape[0]
    k_half = K // 2

    # Zero-pad the image so output is same size as input.
    padded = np.pad(image, k_half, mode="constant", constant_values=0)

    output = np.zeros((H, W), dtype=np.float32)

    # TODO (exercise): implement the convolution inner loop.
    #   - Loop over every output position (i, j) for i in range(H), j in range(W).
    #   - At each position, slice the K×K `patch` out of `padded` whose top-left
    #     corner is (i, j) — because `padded` is already offset by k_half, this
    #     patch is the neighbourhood centred on input pixel (i, j).
    #   - Element-wise multiply the patch by `kernel` and sum it (np.sum) into
    #     `output[i, j]`.

    raise NotImplementedError(
        "Implement the double for-loop that fills `output`. "
        "See the TODO comment above for guidance."
    )

    return output


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def load_grayscale(path: Path) -> np.ndarray:
    """Load an image and convert to float32 grayscale [0, 255]."""
    try:
        from PIL import Image
    except ImportError:
        raise ImportError(
            "Pillow is not installed. Run: uv sync --extra vision\n"
            "or: pip install pillow"
        )
    img = Image.open(path).convert("L")  # "L" = 8-bit grayscale
    return np.array(img, dtype=np.float32)


def save_feature_map(feature_map: np.ndarray, path: Path) -> None:
    """Normalise a feature map to [0, 255] and save as a PNG."""
    from PIL import Image

    # Clip and normalise to [0, 255] so the image is viewable.
    fm = np.abs(feature_map)
    if fm.max() > 0:
        fm = fm / fm.max() * 255.0
    Image.fromarray(fm.astype(np.uint8)).save(path)
    print(f"Saved: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    image_path = SAMPLE_IMAGE
    if not image_path.exists():
        image_path = _download_sample_image()

    print(f"Loading  : {image_path}")
    gray = load_grayscale(image_path)
    print(f"Shape    : {gray.shape}  (H × W, grayscale)")
    print()

    kernels = {
        "edge_h": (EDGE_HORIZONTAL, "Sobel horizontal edges"),
        "edge_v": (EDGE_VERTICAL,   "Sobel vertical edges"),
        "blur":   (BLUR,             "3×3 box blur"),
    }

    for name, (kernel, desc) in kernels.items():
        print(f"Applying : {desc}")
        feature_map = conv2d(gray, kernel)
        out_path = OUTPUT_DIR / f"{name}.png"
        save_feature_map(feature_map, out_path)

    print()
    print("Open the PNG files in assets/ to see the feature maps.")
    print("Notice: edge kernels light up boundaries; blur removes high-frequency detail.")


def _download_sample_image() -> Path:
    import urllib.request
    assets_dir = Path(__file__).parent.parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    dest = assets_dir / "cat.jpg"
    url = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Cat_November_2010-1a.jpg/320px-Cat_November_2010-1a.jpg"
    print(f"Downloading sample image → {dest}")
    urllib.request.urlretrieve(url, dest)  # noqa: S310
    return dest


# ---------------------------------------------------------------------------
# Sanity check (run automatically when you execute this file)
# ---------------------------------------------------------------------------

def _sanity_check() -> None:
    """Quick test: convolving a 5×5 image with the identity kernel (centre=1,
    rest=0) should return the image unchanged."""
    identity = np.array([[0, 0, 0], [0, 1, 0], [0, 0, 0]], dtype=np.float32)
    img = np.arange(25, dtype=np.float32).reshape(5, 5)
    result = conv2d(img, identity)
    assert np.allclose(result, img), (
        f"Identity convolution failed!\nExpected:\n{img}\nGot:\n{result}"
    )
    print("Sanity check passed: identity convolution is correct.")


if __name__ == "__main__":
    _sanity_check()
    print()
    main()
