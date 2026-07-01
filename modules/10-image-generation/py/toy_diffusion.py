"""toy_diffusion.py — Task 4 🔴: minimal DDPM in pure NumPy.

What it teaches:
    The forward noising process and the reverse denoising loop — the core
    math of diffusion models — without ANY framework hiding the details.
    No PyTorch, no diffusers, no CUDA. Just numpy and a tiny MLP.

    The "dataset" is a 2D spiral point cloud.  The model learns to denoise
    2D coordinates, not pixels — so training takes ~10 s on CPU and the
    maths stays legible.

    Architecture:
        - Forward process: T=300 steps, linear beta schedule β₁=1e-4→β_T=0.02
        - Denoiser: 3-layer MLP on 2D coordinates, conditioned on sinusoidal
          timestep embedding
        - Loss: mean squared error between predicted noise and actual noise
        - Sampler: DDPM ancestral sampling (the original Ho et al. reverse loop)

How to run (from the repo root):
    uv run python modules/10-image-generation/py/toy_diffusion.py

    With both TODOs implemented: takes ~30-60 s on CPU; prints progress and
    saves toy_samples.png (a scatter plot of generated 2D points).

TODOs for the learner:
    TODO A — train_denoiser():
        Implement the training loop. Sample random timesteps, add noise via
        the closed-form formula, run the MLP, compute MSE, gradient-descent.
        (NumPy manual backprop provided as a scaffold — or switch to PyTorch.)

    TODO B — ddpm_reverse_step():
        Implement the DDPM reverse step. Given x_t and ε_θ (the model's
        predicted noise), compute x_{t-1} using the reverse posterior.

Math reference:
    Forward:  q(x_t|x₀) = N(x_t; √ᾱₜ x₀, (1-ᾱₜ)I)
    => x_t = √ᾱₜ x₀ + √(1-ᾱₜ) ε,   ε ~ N(0,I)

    Reverse:
    x_{t-1} = 1/√αₜ · (x_t - βₜ/√(1-ᾱₜ) · ε_θ(x_t,t)) + σₜ z,  z~N(0,I)
    σₜ = √βₜ  (simplest choice; Ho et al. also use posterior variance)

    ᾱₜ = ∏_{s=1}^{t} αₛ,  αₜ = 1-βₜ
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# 0. Dataset — a 2D spiral
# ---------------------------------------------------------------------------

def make_spiral(n: int = 2000, seed: int = 0) -> np.ndarray:
    """Generate n 2D points arranged in a two-arm spiral.

    Returns array of shape (n, 2), values roughly in [-1, 1].
    """
    rng = np.random.default_rng(seed)
    n_half = n // 2
    theta = np.linspace(0, 4 * np.pi, n_half)
    r = theta / (4 * np.pi)

    # Arm 1
    x1 = r * np.cos(theta)
    y1 = r * np.sin(theta)

    # Arm 2 (rotated 180°)
    x2 = r * np.cos(theta + np.pi)
    y2 = r * np.sin(theta + np.pi)

    data = np.stack([
        np.concatenate([x1, x2]),
        np.concatenate([y1, y2]),
    ], axis=1)  # (n, 2)

    # Add tiny Gaussian jitter so points aren't perfectly on a curve
    data += rng.standard_normal(data.shape) * 0.02
    return data.astype(np.float32)


# ---------------------------------------------------------------------------
# 1. Noise schedule — linear beta schedule
# ---------------------------------------------------------------------------

def make_noise_schedule(T: int = 300) -> dict:
    """Build the linear beta schedule and pre-compute derived quantities.

    Returns a dict with:
        betas    (T,)  — noise added at each step
        alphas   (T,)  — 1 - beta_t
        alpha_bars (T,) — cumulative product ᾱₜ = ∏ αₛ
    """
    beta_start = 1e-4
    beta_end = 0.02
    betas = np.linspace(beta_start, beta_end, T, dtype=np.float32)  # (T,)
    alphas = 1.0 - betas                                              # αₜ = 1-βₜ
    alpha_bars = np.cumprod(alphas)                                   # ᾱₜ (cumulative product)
    return {"betas": betas, "alphas": alphas, "alpha_bars": alpha_bars, "T": T}


def q_sample(x0: np.ndarray, t: np.ndarray, schedule: dict, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Forward diffusion: add noise to x0 at timestep t (closed-form).

    Closed-form: x_t = √ᾱₜ · x₀ + √(1-ᾱₜ) · ε,   ε ~ N(0,I)

    Args:
        x0:   (batch, 2)   — clean data points
        t:    (batch,)     — integer timesteps in [0, T-1]
        schedule:          — output of make_noise_schedule()
        rng:               — NumPy random generator

    Returns:
        x_t:  (batch, 2)   — noised data
        eps:  (batch, 2)   — the actual noise added (training target)
    """
    alpha_bars = schedule["alpha_bars"]
    ab_t = alpha_bars[t][:, None]        # (batch, 1) — broadcast over 2D coords
    eps = rng.standard_normal(x0.shape).astype(np.float32)
    x_t = np.sqrt(ab_t) * x0 + np.sqrt(1.0 - ab_t) * eps
    return x_t, eps


# ---------------------------------------------------------------------------
# 2. Sinusoidal timestep embedding
# ---------------------------------------------------------------------------

def sinusoidal_embedding(t: np.ndarray, dim: int = 32) -> np.ndarray:
    """Encode integer timesteps t as sinusoidal embeddings.

    The same idea as transformer positional encodings: half the dimensions use
    sin, half use cos, with geometrically-spaced frequencies.

    Args:
        t:    (batch,) int timesteps
        dim:  embedding dimension (must be even)

    Returns:
        emb:  (batch, dim)
    """
    assert dim % 2 == 0
    half = dim // 2
    freqs = np.exp(
        -np.log(10000) * np.arange(half, dtype=np.float32) / half
    )  # (half,)
    args = t[:, None].astype(np.float32) * freqs[None, :]  # (batch, half)
    emb = np.concatenate([np.sin(args), np.cos(args)], axis=-1)  # (batch, dim)
    return emb


# ---------------------------------------------------------------------------
# 3. Tiny MLP — NumPy manual forward/backward
# ---------------------------------------------------------------------------

class TinyMLP:
    """3-layer MLP with ReLU activations.

    Input:  2 (x_t coords) + timestep_embed_dim
    Hidden: h
    Output: 2 (predicted noise for each coordinate)

    Implements manual forward and backward so no autograd framework is needed.
    Alternatively, you can replace this with a PyTorch nn.Module and use
    torch.optim.Adam — the interface is the same.
    """

    def __init__(
        self,
        input_dim: int,   # 2 + timestep_embed_dim
        hidden_dim: int = 256,
        seed: int = 1,
    ) -> None:
        rng = np.random.default_rng(seed)
        # He initialization for ReLU networks
        scale1 = np.sqrt(2.0 / input_dim)
        scale2 = np.sqrt(2.0 / hidden_dim)
        self.W1 = rng.standard_normal((input_dim, hidden_dim)).astype(np.float32) * scale1
        self.b1 = np.zeros(hidden_dim, dtype=np.float32)
        self.W2 = rng.standard_normal((hidden_dim, hidden_dim)).astype(np.float32) * scale2
        self.b2 = np.zeros(hidden_dim, dtype=np.float32)
        self.W3 = rng.standard_normal((hidden_dim, 2)).astype(np.float32) * 0.01
        self.b3 = np.zeros(2, dtype=np.float32)

        # Cache for backward pass
        self._cache: dict = {}

    def params(self) -> list[np.ndarray]:
        return [self.W1, self.b1, self.W2, self.b2, self.W3, self.b3]

    def forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass. Caches activations for backward.

        Args:
            x: (batch, input_dim)
        Returns:
            out: (batch, 2)  — predicted noise
        """
        h1 = x @ self.W1 + self.b1             # (batch, hidden)
        a1 = np.maximum(0, h1)                  # ReLU
        h2 = a1 @ self.W2 + self.b2            # (batch, hidden)
        a2 = np.maximum(0, h2)                  # ReLU
        out = a2 @ self.W3 + self.b3            # (batch, 2)
        self._cache = {"x": x, "h1": h1, "a1": a1, "h2": h2, "a2": a2}
        return out

    def backward(self, d_out: np.ndarray) -> None:
        """Backpropagation. Stores gradients in self.grads.

        Args:
            d_out: (batch, 2)  — gradient of loss w.r.t. output
        """
        batch = d_out.shape[0]
        c = self._cache

        # Layer 3
        dW3 = c["a2"].T @ d_out / batch
        db3 = d_out.mean(axis=0)
        d_a2 = d_out @ self.W3.T

        # ReLU 2
        d_h2 = d_a2 * (c["h2"] > 0)

        # Layer 2
        dW2 = c["a1"].T @ d_h2 / batch
        db2 = d_h2.mean(axis=0)
        d_a1 = d_h2 @ self.W2.T

        # ReLU 1
        d_h1 = d_a1 * (c["h1"] > 0)

        # Layer 1
        dW1 = c["x"].T @ d_h1 / batch
        db1 = d_h1.mean(axis=0)

        self.grads = [dW1, db1, dW2, db2, dW3, db3]

    def step(self, lr: float = 1e-3) -> None:
        """SGD update with gradient clipping."""
        for param, grad in zip(self.params(), self.grads):
            # Clip to prevent exploding gradients in early training
            grad_clipped = np.clip(grad, -1.0, 1.0)
            param -= lr * grad_clipped


# ---------------------------------------------------------------------------
# 4. Training loop (TODO A)
# ---------------------------------------------------------------------------

def train_denoiser(
    data: np.ndarray,
    model: TinyMLP,
    schedule: dict,
    n_epochs: int = 500,
    batch_size: int = 512,
    lr: float = 1e-3,
    seed: int = 2,
) -> list[float]:
    """Train the denoiser MLP to predict the noise added by q_sample.

    Training objective: minimise E_{t,x₀,ε}[ ||ε_θ(x_t, t) − ε||² ]

    This is the "simple" DDPM loss (Ho et al. Eq. 14): instead of predicting
    x₀ or x_{t-1} directly, predict the noise ε. At inference the DDPM
    reverse formula converts this back to x_{t-1}.

    TODO A — implement the body of this function:

        Loop for `n_epochs`. Each iteration is one mini-batch step:
        1. Draw a random mini-batch of `batch_size` rows from `data` (index
           with `rng.integers`).
        2. Sample integer timesteps `t` of shape (batch,), uniform over the
           valid range [1, T-1] (t=0 is the clean sample — skip it).
        3. Get the noised batch and its target noise from `q_sample(x0, t,
           schedule, rng)` — it returns `(x_t, eps)`.
        4. Build the MLP input by concatenating `x_t` with
           `sinusoidal_embedding(t)` along the feature axis → shape
           (batch, 2 + embed_dim).
        5. Run `model.forward(inp)` to get the predicted noise `eps_pred`.
        6. Compute the scalar MSE between `eps_pred` and the target `eps`.
        7. Backprop: the gradient of MSE w.r.t. the output is
           2·(eps_pred − eps) / (number of elements). Pass that to
           `model.backward(...)`, then apply `model.step(lr)`.
        8. Append the loss and print progress every ~50 epochs.

    Returns:
        losses: list of per-epoch mean losses.

    Once implemented, the loss should fall from ~1.0 to ~0.05 in 500 epochs
    for the spiral dataset with the default hyperparameters.
    """
    raise NotImplementedError(
        "TODO A: implement the training loop — see the docstring above.\n"
        "Steps: sample batch → q_sample → forward → MSE loss → backward → step."
    )


# ---------------------------------------------------------------------------
# 5. Reverse sampler (TODO B)
# ---------------------------------------------------------------------------

def ddpm_reverse_step(
    x_t: np.ndarray,
    t: int,
    eps_pred: np.ndarray,
    schedule: dict,
    rng: np.random.Generator,
) -> np.ndarray:
    """One step of the DDPM reverse process.

    Given x_t and the model's predicted noise ε_θ(x_t, t), compute x_{t-1}.

    The DDPM reverse formula (Ho et al. Eq. 11):
        x_{t-1} = 1/√αₜ · (x_t - βₜ/√(1-ᾱₜ) · ε_θ) + σₜ · z
        where σₜ = √βₜ   and   z ~ N(0,I)  (set z=0 for the last step, t=1)

    Args:
        x_t:       (batch, 2) — current noisy samples at timestep t
        t:         int        — current timestep (1-indexed; 0 = clean)
        eps_pred:  (batch, 2) — noise predicted by the MLP
        schedule:  dict       — from make_noise_schedule()
        rng:       np rng     — for the stochastic term z

    Returns:
        x_{t-1}:  (batch, 2)

    TODO B — implement this function:
        1. Pull the scalars βₜ, αₜ, and ᾱₜ for this `t` out of `schedule`.
        2. Apply the reverse formula in the docstring above to turn `x_t` and
           `eps_pred` into the mean of x_{t-1} (a deterministic combination of
           the two, scaled by 1/√αₜ).
        3. Add the stochastic term σₜ·z (with σₜ = √βₜ and z drawn from
           `rng.standard_normal`) only when t > 1; on the final step (t == 1)
           return the mean with no added noise.
    """
    raise NotImplementedError(
        "TODO B: implement the DDPM reverse step — see the docstring above.\n"
        "Formula: x_{t-1} = 1/√αₜ · (x_t - βₜ/√(1-ᾱₜ) · ε_θ) + σₜ · z"
    )


def sample(
    model: TinyMLP,
    schedule: dict,
    n_samples: int = 500,
    timestep_embed_dim: int = 32,
    seed: int = 99,
) -> np.ndarray:
    """Run the full DDPM reverse loop to generate samples from noise.

    Starts from x_T ~ N(0, I) and iterates from t=T down to t=1.

    Args:
        model:   trained TinyMLP
        schedule: from make_noise_schedule()

    Returns:
        x_0: (n_samples, 2) — generated 2D points
    """
    rng = np.random.default_rng(seed)
    T = schedule["T"]

    # Start from pure Gaussian noise — this is x_T
    x = rng.standard_normal((n_samples, 2)).astype(np.float32)

    for t in range(T - 1, 0, -1):
        t_batch = np.full(n_samples, t, dtype=np.int32)
        t_emb = sinusoidal_embedding(t_batch, dim=timestep_embed_dim)  # (n, D)
        inp = np.concatenate([x, t_emb], axis=-1)                      # (n, 2+D)
        eps_pred = model.forward(inp)                                   # (n, 2)
        x = ddpm_reverse_step(x, t, eps_pred, schedule, rng)           # (n, 2)

    return x


# ---------------------------------------------------------------------------
# 6. Visualisation
# ---------------------------------------------------------------------------

def visualize(
    original: np.ndarray,
    generated: np.ndarray,
    output_path: str = "toy_samples.png",
) -> None:
    """Plot original vs generated 2D points and save to PNG."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print(
            "matplotlib not installed; skipping plot.\n"
            "Install with: pip install matplotlib"
        )
        print("Generated points (first 5):", generated[:5])
        return

    fig, axes = plt.subplots(1, 2, figsize=(10, 5))

    axes[0].scatter(original[:, 0], original[:, 1], s=2, alpha=0.4, color="steelblue")
    axes[0].set_title("Training data (spiral)")
    axes[0].set_aspect("equal")
    axes[0].set_xlim(-1.2, 1.2)
    axes[0].set_ylim(-1.2, 1.2)

    axes[1].scatter(generated[:, 0], generated[:, 1], s=2, alpha=0.4, color="tomato")
    axes[1].set_title("DDPM samples (after training)")
    axes[1].set_aspect("equal")
    axes[1].set_xlim(-1.2, 1.2)
    axes[1].set_ylim(-1.2, 1.2)

    plt.tight_layout()
    plt.savefig(output_path, dpi=120)
    print(f"Plot saved → {output_path}")


# ---------------------------------------------------------------------------
# 7. Demonstrate the forward process (always runs — no TODOs needed)
# ---------------------------------------------------------------------------

def demo_forward_process(data: np.ndarray, schedule: dict) -> None:
    """Show how data gets progressively noisier over the forward process.

    This part runs without any TODOs. It illustrates q(x_t | x_0) for
    t = 0, 50, 150, 250, 299 so you can see the noise schedule in action.
    """
    rng = np.random.default_rng(0)
    T = schedule["T"]
    timesteps_to_show = [0, 50, 150, 250, T - 1]
    batch = data[:200]  # just 200 points for clarity

    print("Forward process — Signal-to-noise ratio at each timestep:")
    print(f"  {'Timestep t':>12}  {'ᾱₜ (signal)':>14}  {'1-ᾱₜ (noise)':>14}")
    for t in timesteps_to_show:
        ab = schedule["alpha_bars"][t]
        print(f"  {t:>12}  {ab:>14.4f}  {1 - ab:>14.4f}")

    print()
    print("At t=0 the data is clean; at t=T-1 it is pure Gaussian noise.")
    print("The model learns to reverse this, one step at a time.\n")

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("(matplotlib not installed; skipping forward process plot)\n")
        return

    fig, axes = plt.subplots(1, len(timesteps_to_show), figsize=(15, 3))
    for ax, t in zip(axes, timesteps_to_show):
        t_arr = np.full(len(batch), t, dtype=np.int32)
        x_t, _ = q_sample(batch, t_arr, schedule, rng)
        ax.scatter(x_t[:, 0], x_t[:, 1], s=3, alpha=0.5)
        ax.set_title(f"t={t}")
        ax.set_aspect("equal")
        ax.set_xlim(-3, 3)
        ax.set_ylim(-3, 3)
        ax.axis("off")

    plt.suptitle("Forward noising process: spiral → Gaussian noise")
    plt.tight_layout()
    plt.savefig("toy_forward_process.png", dpi=100)
    print("Forward process plot → toy_forward_process.png\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

TIMESTEP_EMBED_DIM = 32


def main() -> None:
    T = 300
    schedule = make_noise_schedule(T=T)
    data = make_spiral(n=2000)

    print(f"Dataset: {data.shape[0]} 2D spiral points")
    print(f"Schedule: T={T}, β₁={schedule['betas'][0]:.4f} → β_T={schedule['betas'][-1]:.4f}\n")

    # Always-working demo of the forward process
    demo_forward_process(data, schedule)

    # Build model — input is (x_t coords=2) + (timestep embedding=TIMESTEP_EMBED_DIM)
    model = TinyMLP(input_dim=2 + TIMESTEP_EMBED_DIM, hidden_dim=256)

    print("=" * 60)
    print("Training the denoiser MLP …")
    print("(Fill in TODO A in train_denoiser() to make this work)")
    print("=" * 60)

    try:
        losses = train_denoiser(
            data=data,
            model=model,
            schedule=schedule,
            n_epochs=500,
            batch_size=512,
            lr=1e-3,
            seed=2,
        )
        print(f"Training done. Final loss: {losses[-1]:.4f}\n")
    except NotImplementedError as e:
        print(f"\n{e}\n")
        print("Skipping sampling (cannot sample without a trained model).")
        sys.exit(0)

    print("=" * 60)
    print("Sampling from the trained model …")
    print("(Fill in TODO B in ddpm_reverse_step() to make this work)")
    print("=" * 60)

    try:
        generated = sample(
            model=model,
            schedule=schedule,
            n_samples=500,
            timestep_embed_dim=TIMESTEP_EMBED_DIM,
        )
        print(f"Generated {len(generated)} points.")
        visualize(data, generated)
    except NotImplementedError as e:
        print(f"\n{e}\n")
        print("Implement TODO B in ddpm_reverse_step() then re-run.")

    print()
    print("Key insight: the MLP never saw the spiral directly.")
    print("It only learned to predict noise. Yet by running the reverse loop")
    print("from pure Gaussian noise, spiral-shaped points emerge — because")
    print("the training distribution is embedded in the noise predictions.")


if __name__ == "__main__":
    main()
