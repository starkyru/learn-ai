"""
Task 4 🔴 — A vanilla RNN trained with BACKPROP THROUGH TIME (BPTT).

What you'll learn:
  - How an RNN carries a hidden state (memory) across timesteps with shared weights.
  - The forward unroll: run the same cell over a sequence, storing every state.
  - BPTT: ordinary backprop over the unrolled graph — with two twists:
      * the tanh local gradient (1 - h²) reappears at every timestep;
      * because Wxh/Whh/Why are SHARED, their gradients are SUMMED over time.
  - Why `dh_next = Whhᵀ·da` carries error *backwards in time*.

The math (README §4 explains each step in plain English):

  Forward (per timestep t):
    h_t    = tanh(Wxh·x_t + Whh·h_{t-1} + bh)      hidden state (H, 1)
    logits = Why·h_t + by                          scores       (V, 1)
    p_t    = softmax(logits)                       next-char probs

  Loss: cross-entropy over the sequence, summed over t.

  Backward (t = T-1 … 0), accumulating shared-weight grads:
    dy       = p_t - one_hot(target_t)             softmax+CE gradient (module 08)
    dWhy    += dy · h_tᵀ ;   dby += dy
    dh       = Whyᵀ · dy + dh_next                 output path + gradient-from-future
    da       = (1 - h_t²) · dh                     backprop through tanh
    dbh     += da
    dWxh    += da · x_tᵀ
    dWhh    += da · h_{t-1}ᵀ
    dh_next  = Whhᵀ · da                           pass memory-grad to previous step

The corpus, vocab, one-hot, parameter init, softmax+CE, the Adam update, gradient
clipping, and the sampling/evaluation harness are all provided. You implement
rnn_step, forward (the unroll), and the BPTT accumulation in backward.

How to run:
  uv run python modules/01c-deep-learning/py/04_rnn_bptt.py

Only numpy is used.
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# Tiny deterministic char-level corpus
# ---------------------------------------------------------------------------

CORPUS = "hello world " * 12  # a short repeating pattern
CHARS = sorted(set(CORPUS))
VOCAB = len(CHARS)
STOI = {c: i for i, c in enumerate(CHARS)}
ITOS = {i: c for c, i in STOI.items()}

HIDDEN = 32  # hidden-state size
SEQ_LEN = 24  # BPTT window length


# ---------------------------------------------------------------------------
# Helpers (complete)
# ---------------------------------------------------------------------------


def one_hot(idx: int) -> np.ndarray:
    """Column vector (VOCAB, 1) with a 1 at position idx."""
    v = np.zeros((VOCAB, 1))
    v[idx] = 1.0
    return v


def softmax(z: np.ndarray) -> np.ndarray:
    """Numerically stable softmax over a column vector."""
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()


def init_params(seed: int = 1) -> dict[str, np.ndarray]:
    """Small random weights (0.01·N) keep the initial dynamics stable."""
    rng = np.random.default_rng(seed)
    return {
        "Wxh": rng.normal(0, 0.01, (HIDDEN, VOCAB)),  # input → hidden
        "Whh": rng.normal(0, 0.01, (HIDDEN, HIDDEN)),  # hidden → hidden (memory)
        "Why": rng.normal(0, 0.01, (VOCAB, HIDDEN)),  # hidden → output
        "bh": np.zeros((HIDDEN, 1)),
        "by": np.zeros((VOCAB, 1)),
    }


# ---------------------------------------------------------------------------
# The RNN cell and unroll — implement these
# ---------------------------------------------------------------------------


def rnn_step(x: np.ndarray, h_prev: np.ndarray, P: dict) -> tuple[np.ndarray, np.ndarray]:
    """
    One RNN timestep.

      h      = tanh(Wxh·x + Whh·h_prev + bh)     (HIDDEN, 1)
      logits = Why·h + by                        (VOCAB, 1)

    Returns (h, logits). x is a one-hot column (VOCAB, 1); h_prev is (HIDDEN, 1).

    TODO: implement.
      h = np.tanh(P["Wxh"] @ x + P["Whh"] @ h_prev + P["bh"])
      logits = P["Why"] @ h + P["by"]
      return h, logits
    """
    raise NotImplementedError("TODO: implement rnn_step()")


def forward(
    inputs: list[int], targets: list[int], h_prev: np.ndarray, P: dict
) -> tuple[float, dict, dict, dict]:
    """
    Unroll the RNN over the sequence, computing loss and STORING everything BPTT
    will need.

    Returns (loss, xs, hs, ps) where:
      xs[t] : the one-hot input at step t           (VOCAB, 1)
      hs[t] : the hidden state after step t          (HIDDEN, 1); hs[-1] = h_prev
      ps[t] : the softmax probabilities at step t    (VOCAB, 1)
      loss  : summed cross-entropy over the sequence (scalar)

    TODO: implement.
      1. xs, hs, ps = {}, {}, {} ;  hs[-1] = h_prev.copy() ;  loss = 0.0
      2. for t in range(len(inputs)):
           xs[t] = one_hot(inputs[t])
           hs[t], logits = rnn_step(xs[t], hs[t - 1], P)
           ps[t] = softmax(logits)
           loss += -np.log(ps[t][targets[t], 0] + 1e-12)   # CE for the true char
      3. return loss, xs, hs, ps
    """
    raise NotImplementedError("TODO: implement forward()")


def backward(inputs: list[int], targets: list[int], xs: dict, hs: dict, ps: dict, P: dict) -> dict:
    """
    Backprop through time. Returns a dict of gradients matching P's keys.

    The output-layer gradient (softmax + cross-entropy) is given to you as `dy`.
    You fill in the tanh local gradient and the through-time accumulation.

    TODO: implement the marked lines inside the loop.

    Scaffold:
      grads = {k: np.zeros_like(v) for k, v in P.items()}
      dh_next = np.zeros((HIDDEN, 1))
      for t in reversed(range(len(inputs))):
          # softmax + cross-entropy gradient at the output (GIVEN):
          dy = ps[t].copy()
          dy[targets[t]] -= 1.0

          # (a) output-layer grads (shared Why/by → accumulate with +=):
          grads["Why"] += dy @ hs[t].T
          grads["by"]  += dy

          # (b) gradient flowing into the hidden state: output path + future:
          dh = P["Why"].T @ dy + dh_next

          # (c) TODO: backprop through tanh.  h = tanh(a) → da = (1 - h²)·dh
          da = (1 - hs[t] ** 2) * dh

          # (d) TODO: accumulate the shared hidden-layer grads (use +=):
          grads["bh"]  += da
          grads["Wxh"] += da @ xs[t].T
          grads["Whh"] += da @ hs[t - 1].T

          # (e) TODO: pass the memory-gradient to the previous timestep:
          dh_next = P["Whh"].T @ da

      # Clip to fight exploding gradients (GIVEN):
      for k in grads:
          np.clip(grads[k], -5.0, 5.0, out=grads[k])
      return grads
    """
    raise NotImplementedError("TODO: implement backward() (BPTT)")


# ---------------------------------------------------------------------------
# Adam optimizer state + step (complete — you don't edit this)
# ---------------------------------------------------------------------------


def make_adam_state(P: dict) -> dict:
    return {k: {"m": np.zeros_like(v), "v": np.zeros_like(v)} for k, v in P.items()}


def adam_step(P: dict, grads: dict, state: dict, t: int, lr: float = 0.01) -> None:
    b1, b2, eps = 0.9, 0.999, 1e-8
    for k in P:
        st = state[k]
        st["m"] = b1 * st["m"] + (1 - b1) * grads[k]
        st["v"] = b2 * st["v"] + (1 - b2) * (grads[k] ** 2)
        m_hat = st["m"] / (1 - b1**t)
        v_hat = st["v"] / (1 - b2**t)
        P[k] -= lr * m_hat / (np.sqrt(v_hat) + eps)


# ---------------------------------------------------------------------------
# Evaluation (complete): teacher-forced next-char accuracy over the whole corpus
# ---------------------------------------------------------------------------


def evaluate(data: list[int], P: dict) -> float:
    h = np.zeros((HIDDEN, 1))
    correct = 0
    for t in range(len(data) - 1):
        h, logits = rnn_step(one_hot(data[t]), h, P)
        pred = int(np.argmax(softmax(logits)))
        correct += int(pred == data[t + 1])
    return correct / (len(data) - 1)


def sample(P: dict, seed_char: str, length: int) -> str:
    """Greedy generation, for a human-readable sanity check."""
    h = np.zeros((HIDDEN, 1))
    idx = STOI[seed_char]
    out = [seed_char]
    for _ in range(length):
        h, logits = rnn_step(one_hot(idx), h, P)
        idx = int(np.argmax(softmax(logits)))
        out.append(ITOS[idx])
    return "".join(out)


# ---------------------------------------------------------------------------
# Training loop (complete)
# ---------------------------------------------------------------------------


def train(P: dict, data: list[int], n_iters: int = 2000, lr: float = 0.01) -> tuple[float, float]:
    """
    Slide a SEQ_LEN window across the corpus, carrying the hidden state between
    windows (min-char-rnn style). Returns (initial_loss_per_char, final_loss_per_char).
    """
    state = make_adam_state(P)
    h = np.zeros((HIDDEN, 1))
    ptr = 0
    step = 0
    init_loss = None
    last_loss = 0.0

    for it in range(n_iters):
        # Reset to the start (and clear memory) when we run out of corpus.
        if ptr + SEQ_LEN + 1 >= len(data):
            ptr = 0
            h = np.zeros((HIDDEN, 1))

        inputs = data[ptr : ptr + SEQ_LEN]
        targets = data[ptr + 1 : ptr + SEQ_LEN + 1]

        loss, xs, hs, ps = forward(inputs, targets, h, P)
        grads = backward(inputs, targets, xs, hs, ps, P)

        h = hs[SEQ_LEN - 1]  # carry the final hidden state forward
        step += 1
        adam_step(P, grads, state, step, lr)

        last_loss = loss / SEQ_LEN
        if init_loss is None:
            init_loss = last_loss
        ptr += SEQ_LEN

        if (it + 1) % 500 == 0 or it == 0:
            print(f"  Iter {it + 1:>5}/{n_iters}  loss/char={last_loss:.4f}")

    return init_loss, last_loss


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    print("\n=== Task 4: vanilla RNN + backprop through time ===\n")
    print(f"Corpus ({len(CORPUS)} chars): {CORPUS[:36]!r}...")
    print(f"Vocab ({VOCAB} chars): {CHARS}")
    print(f"Chance accuracy (1/vocab): {1 / VOCAB:.3f}")

    data = [STOI[c] for c in CORPUS]
    P = init_params(seed=1)

    print("\nTraining...")
    init_loss, final_loss = train(P, data, n_iters=2000, lr=0.01)

    acc = evaluate(data, P)
    print(f"\n  Initial loss/char: {init_loss:.4f}")
    print(f"  Final   loss/char: {final_loss:.4f}   ({final_loss / init_loss:.1%} of initial)")
    print(f"  Next-char accuracy: {acc:.2%}   (want ≥ 90%, chance = {1 / VOCAB:.1%})")

    print(f"\n  Sample generation from 'h': {sample(P, 'h', 24)!r}")

    loss_dropped = final_loss < 0.4 * init_loss
    beats_chance = acc >= 0.90
    print(f"\n  Loss dropped substantially (<40% of initial): {loss_dropped}")
    print(f"  Accuracy ≥ 90%: {beats_chance}")


if __name__ == "__main__":
    main()
