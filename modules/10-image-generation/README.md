# Module 10 — Generative Images & Diffusion Models

Stable Diffusion, DALL-E, and friends are not magic filters — they are
probabilistic models that learn to _reverse a noise process_. By the end of
this module you will have generated images from text via a hosted API (Application Programming Interface),
explored every major generation knob, and built a minimal diffusion sampler
from scratch in NumPy so the maths clicks.

---

## Concepts

### 1. What is a diffusion model?

A diffusion model learns to undo Gaussian noise. Training has two phases:

**Forward process (fixed, no learning):**  
Take a real image x₀. Repeatedly add small amounts of Gaussian noise over T
steps, producing x₁, x₂, …, x_T. At step T the image is pure noise — you
cannot tell what the original was.

```
x₀  ──noise──▶  x₁  ──noise──▶  x₂  ──noise──▶  …  ──noise──▶  x_T ~ N(0,I)
```

The noise schedule (the βₜ values) controls how much noise is added each
step. A common choice is a linear schedule: β₁ = 0.0001, β_T = 0.02.
Because the noise compounds, a closed-form exists:

```
x_t = √ᾱₜ · x₀  +  √(1−ᾱₜ) · ε,   ε ~ N(0,I)
```

where ᾱₜ = ∏\_{s=1}^{t} (1−βₛ). This lets you jump to _any_ noise level
without simulating each step individually.

**Reverse process (learned):**  
A neural network ε*θ(x_t, t) is trained to *predict the noise* that was
added to get x_t from x₀. Given the prediction, you can recover x*{t−1} via
the DDPM (Denoising Diffusion Probabilistic Model) update rule (Ho et al. 2020):

```
x_{t−1} = 1/√αₜ · (x_t − β_t/√(1−ᾱₜ) · ε_θ(x_t,t))  +  σₜ·z,  z~N(0,I)
```

Starting from pure noise x_T ~ N(0,I) and running this backwards for T steps
yields a new sample that looks like the training data.

### 2. Latent diffusion (why Stable Diffusion is fast)

Running diffusion on raw pixels (512×512×3 = 786 432 numbers) is slow. Stable
Diffusion runs diffusion in a _compressed latent space_ produced by a VAE
(Variational Autoencoder):

```
image (512×512×3)  ──VAE encoder──▶  latent (64×64×4)   ← diffusion lives here
                   ──VAE decoder──▶  image (512×512×3)
```

The latent is ~48× smaller than the pixel space. The VAE is frozen during
diffusion training; only the denoiser (a U-Net) trains. At inference, you
sample a noisy latent, denoise it, then decode to pixels.

### 3. The U-Net denoiser

The denoiser ε_θ is a U-Net: a convolutional encoder-decoder with skip
connections. It takes (x_t, t, c) — the noisy latent, the timestep, and a
conditioning vector c — and outputs the predicted noise.

The timestep t is embedded (sinusoidal, like transformer positional
encodings) and injected at every residual block so the network knows "how
noisy" its input is. The conditioning vector c comes from the text encoder.

### 4. CLIP text conditioning

Stable Diffusion uses a frozen CLIP (Contrastive Language–Image Pretraining)
text encoder to convert your prompt into a sequence of token embeddings c.
The U-Net attends to these embeddings via cross-attention at every scale,
so each part of the image can "look at" the full prompt.

CLIP was trained to align images and captions in a joint embedding space, so
it understands that "a red ball" and an image of a red ball should be close.
The text encoder part is reused as a semantic compressor for the denoiser.

### 5. Classifier-free guidance (CFG / guidance scale)

To make the model follow the prompt more strongly, the denoiser is run
_twice_ per step: once conditioned on the prompt, once on an empty prompt:

```
ε_guided = ε_uncond  +  guidance_scale · (ε_cond − ε_uncond)
```

`guidance_scale = 1` → no guidance (the model ignores the text); `= 7–8` →
balanced quality/diversity; `≥ 15` → strong adherence to the prompt but
oversaturated, less varied. This is the most important generation parameter.

### 6. Samplers and steps

The DDPM (Denoising Diffusion Probabilistic Models) reverse loop is slow —
1000 steps is typical for training. Faster samplers (DDIM, DPM++ 2M, UniPC,
LCM) can produce good images in 20–50 steps by taking bigger, smarter steps.
More steps = more detail but diminishing returns past ~40 for DPM++.

| Sampler    | Steps needed | Speed     | Notes                                                 |
| ---------- | ------------ | --------- | ----------------------------------------------------- |
| DDPM       | 1000         | slow      | training sampler; rarely used at inference            |
| DDIM       | 50           | medium    | deterministic if eta=0; good for img2img              |
| DPM++ 2M   | 20–30        | fast      | strong default for SD 1.5 / SDXL                      |
| LCM        | 4–8          | very fast | distilled consistency model; slight quality trade-off |
| SDXL-Turbo | 1–4          | instant   | adversarial distillation; best local fast option      |

### 7. img2img and inpainting

**img2img:** Start from a _real image_ noised to a partial timestep (not all
the way to T). The denoiser reverse-processes from there, guided by the
prompt. The `strength` parameter controls how noisy the starting point is:
`strength = 1` ≈ text-to-image; `strength = 0.3` keeps most of the original.

**Inpainting:** Provide a binary mask. Only the masked region is noised and
denoised; the rest is preserved. Some models (SD-inpainting, SDXL-inpainting)
were fine-tuned specifically for this and blend edges better.

### 8. ControlNet

ControlNet (Zhang et al. 2023) adds an extra input to the U-Net: a spatial
conditioning map — an edge map (Canny), a depth map, a human pose skeleton,
a scribble drawing, etc. The denoiser copies its encoder weights into a
trainable "control" branch that processes the spatial input, injecting
feature maps at each U-Net scale. This lets you control the _composition_ of
the image precisely while still following a text prompt.

### 9. LoRA and DreamBooth fine-tuning

**LoRA (Low-Rank Adaptation):** Instead of fine-tuning all 900M+ parameters
of SD, you add small rank-decomposed matrices (W = W₀ + AB, rank ≈ 4–64)
to the attention and feed-forward layers. Training LoRA for a new style or
concept takes minutes on a consumer GPU (Graphics Processing Unit). At inference you "merge" the LoRA
weights at a specified strength.

**DreamBooth:** A fine-tuning technique (Ruiz et al. 2022) that binds a new
concept to a rare token (e.g. `sks dog`) using just 3–30 reference images,
with a class-preservation loss to prevent catastrophic forgetting. Often
combined with LoRA for efficiency.

### 10. Image-to-video

Models like Stable Video Diffusion (SVD), AnimateDiff, and Runway Gen-3 extend
the spatial U-Net with temporal attention layers. The forward/reverse process
is the same conceptually, but applied to a sequence of latents that must be
temporally consistent. Inference costs scale with frame count.

### 11. Safety and watermarking

Generated images are subject to misuse risks (deepfakes, CSAM, deceptive
content). Practical safeguards include:

- **NSFW (Not Safe For Work) classifier:** a post-generation image classifier blacks out unsafe
  outputs (used in SD's default pipeline).
- **Invisible watermarking:** C2PA/SynthID embed invisible signals in pixel or
  DCT (Discrete Cosine Transform) domain so downstream detectors can flag AI-generated images.
- **Prompt filtering:** a text classifier blocks harmful prompts before inference.

---

## Environment variables

Add these to your `.env` (all optional — you only need one provider):

```
# Primary recommended provider (Replicate):
REPLICATE_API_TOKEN=r8_...

# Alternatives:
HF_TOKEN=hf_...                # HuggingFace Inference API
STABILITY_API_KEY=sk-...       # Stability AI REST API
NVIDIA_API_KEY=...             # NVIDIA NIM (also used for LLMs in earlier modules)
```

Do **not** edit `.env.example` — document your keys only in `.env`.

---

## Tasks

### Task 1 — Text-to-image 🟢

Generate an image from a text prompt via the hosted API; save it as a PNG (Portable Network Graphics);
vary the seed to see how stochasticity works.

**Python:** `py/text_to_image.py`  
**TypeScript:** `ts/text_to_image.ts`

Steps:

1. Set `REPLICATE_API_TOKEN` in `.env` (or pick another provider — see the
   "Hosted provider options" section below).
2. Run the script:
   ```bash
   uv run python modules/10-image-generation/py/text_to_image.py
   pnpm tsx modules/10-image-generation/ts/text_to_image.ts
   ```
3. Open the saved `output_seed_*.png` files. Change `PROMPT` and re-run.
4. Change the seed to any integer; same prompt + seed = same image (fully
   deterministic). Different seed = different composition with the same subject.

Acceptance: at least two PNG files on disk, from two different seeds.

### Task 2 — Prompt craft & parameter sweep 🟡

Sweep `guidance_scale` and `num_inference_steps`; save a small image grid;
understand the effect of negative prompts.

**Python:** `py/param_sweep.py`

Steps:

1. Run the sweep (sends ~6 API calls — each takes a few seconds):
   ```bash
   uv run python modules/10-image-generation/py/param_sweep.py
   ```
2. Open `sweep_grid.png`. Notice how guidance_scale affects sharpness/adherence
   and how steps affect detail.
3. Modify `NEGATIVE_PROMPT` — try `"blurry, ugly, watermark"` vs. `""`.

Acceptance: a `sweep_grid.png` with a visible difference across columns.

What each knob does:

- **guidance_scale (CFG):** controls how strongly the model follows the text
  prompt (see Concept 5 above). ~7 is a balanced default.
- **num_inference_steps:** more steps = more detail and coherence, but slower
  and with diminishing returns past 40 for DPM++ samplers.
- **negative_prompt:** runs the same CFG steering but _away from_ the
  described features. Effectively a second CLIP encoding subtracted during
  guidance. "blurry, low quality, watermark" is a common boilerplate.
- **seed:** controls the random noise starting point. Same seed = same image.

### Task 3 — img2img & inpainting 🟡

Transform an input image with img2img; edit a masked region with inpainting.

**Python:** `py/img2img.py`

Steps:

1. The script downloads a sample input image automatically on first run.
2. Run:
   ```bash
   uv run python modules/10-image-generation/py/img2img.py
   ```
3. Compare `img2img_output.png` with the original — similar composition, new
   style/details. Adjust `STRENGTH` (0.3–0.9) and observe.
4. Look at `inpaint_output.png` — the unmasked region is unchanged; the white
   mask area was regenerated from the prompt.

Acceptance: both `img2img_output.png` and `inpaint_output.png` saved.

**Local diffusers variant (optional):**  
Install the extra first: `uv sync --extra imagegen`  
Then run: `uv run python modules/10-image-generation/py/local_diffusers.py`  
Warning: downloads ~6 GB on first run; MPS (Apple Silicon) is supported but
is 5–15× slower than a CUDA GPU. SDXL-Turbo is recommended for local use
(4-step generation).

### Task 4 — Toy diffusion from scratch 🔴

A minimal DDPM implementation in NumPy — no Torch, no diffusers. Teaches
the math before any framework hides it.

**Python:** `py/toy_diffusion.py`

Steps:

1. Run the skeleton as-is to see the forward noising process and the reverse
   sampler structure:
   ```bash
   uv run python modules/10-image-generation/py/toy_diffusion.py
   ```
   The script will run the forward process (visualisable) and attempt the
   reverse loop — but the denoiser MLP (Multi-Layer Perceptron) is a stub. Fill in the TODOs.
2. **TODO A — Training loop:** implement `train_denoiser()`. Sample random
   timesteps, add noise via the closed-form formula, run the MLP, compute
   MSE (Mean Squared Error) loss, backprop with tiny NumPy autograd (or switch to PyTorch — the
   MLP class is compatible).
3. **TODO B — Reverse sampler:** implement `ddpm_reverse_step()`. Given
   x*t and the model's noise prediction, compute x*{t−1} using the DDPM
   formula from Concept 1.
4. After both TODOs are filled, a 2D spiral point-cloud should emerge from
   random noise in under a minute on CPU.

Math to keep in mind:

```
Forward:  q(x_t | x₀) = N(x_t; √ᾱₜ x₀, (1−ᾱₜ)I)
Reverse:  x_{t-1} = 1/√αₜ · (x_t − βₜ/√(1−ᾱₜ) · ε_θ(x_t,t)) + σₜ z
σₜ = √βₜ   (or √((1−ᾱ_{t-1})/(1−ᾱₜ)·βₜ) for the posterior variance)
```

Acceptance: after filling the TODOs, generated 2D points that form a spiral
(or two-moon) shape rather than white noise.

---

## Hosted provider options

The exercises default to **Replicate** (reliable, cheap, simple REST (Representational State Transfer) API).
All functions are isolated so swapping is one line:

| Provider                                        | Token env var         | Model used                                 | Notes                                          |
| ----------------------------------------------- | --------------------- | ------------------------------------------ | ---------------------------------------------- |
| **Replicate** ✓ default                         | `REPLICATE_API_TOKEN` | `stability-ai/sdxl`                        | Poll-based API; ~$0.004/image                  |
| **HuggingFace Inference API**                   | `HF_TOKEN`            | `stabilityai/stable-diffusion-xl-base-1.0` | POST image directly; free tier limited         |
| **Stability AI**                                | `STABILITY_API_KEY`   | SDXL via `stable-image/generate/core`      | Direct PNG return                              |
| **NVIDIA NIM (NVIDIA Inference Microservices)** | `NVIDIA_API_KEY`      | `stability/stable-diffusion-xl`            | Same key as LLM (Large Language Model) modules |

To switch, edit `IMAGE_PROVIDER` at the top of any script or set the env var.

---

## Done when

- [ ] Generated at least two PNGs from different seeds (Task 1).
- [ ] Ran the parameter sweep and can explain what guidance_scale does (Task 2).
- [ ] Have `img2img_output.png` and `inpaint_output.png` saved (Task 3).
- [ ] The toy diffusion script runs end-to-end and generates points that
      look like the training distribution (Task 4, after filling TODOs).
- [ ] Can explain in a sentence: what the U-Net predicts, and what
      classifier-free guidance actually does to the noise prediction.

---

## Going deeper

**Papers:**

- [DDPM — Ho et al. 2020](https://arxiv.org/abs/2006.11239) — the original
  denoising diffusion probabilistic models paper.
- [Latent Diffusion / Stable Diffusion — Rombach et al. 2022](https://arxiv.org/abs/2112.10752)
  — LDM: why moving to latent space is the key insight.
- [DDIM — Song et al. 2020](https://arxiv.org/abs/2010.02502) — deterministic
  fast sampling; the basis of most modern samplers.
- [Classifier-Free Guidance — Ho & Salimans 2022](https://arxiv.org/abs/2207.12598)
- [ControlNet — Zhang et al. 2023](https://arxiv.org/abs/2302.05543)
- [DreamBooth — Ruiz et al. 2022](https://arxiv.org/abs/2208.12242)

**Courses and tutorials:**

- [Lilian Weng — "What are Diffusion Models?"](https://lilianweng.github.io/posts/2021-07-11-diffusion-models/)
  — the best single blog post on the math, clearly written.
- [HuggingFace Diffusers Course](https://huggingface.co/learn/diffusers-course/)
  — hands-on, goes from basics to fine-tuning.
- [fast.ai — Practical Deep Learning, Stable Diffusion chapters](https://course.fast.ai/)
  — intuition-first, code-second; great for visual thinkers.
- [Andrej Karpathy — "Building makemore"](https://www.youtube.com/playlist?list=PLAqhIrjkxbuWI23v9cThsA9GvCAUhRvKZ)
  — not diffusion-specific, but the mindset of building from scratch applies.

**Code:**

- [HuggingFace diffusers](https://github.com/huggingface/diffusers) — the
  reference library; read `StableDiffusionPipeline.__call__` to see the
  full inference loop.
- [AUTOMATIC1111 WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
  — the most popular local SD interface; good for manual experimentation.
