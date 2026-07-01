"""
Task 1 🔴 — Micro scalar AUTOGRAD engine + an MLP trained on XOR.

What you'll learn:
  - Backpropagation IS the chain rule run backwards over a computation graph.
  - Every value remembers how it was produced (its inputs + a local-gradient closure).
  - A topological sort lets us run those closures in the correct order.
  - Gradient checking: compare autograd against finite differences to prove it right.

The math (README §1 explains each step in plain English):

  For c = a + b :   ∂c/∂a = 1,      ∂c/∂b = 1
  For c = a * b :   ∂c/∂a = b,      ∂c/∂b = a
  For o = tanh(x):  do/dx = 1 - o²           (o = tanh(x))
  For o = relu(x):  do/dx = 1 if x>0 else 0

  backward(): seed the root grad = 1 (∂L/∂L = 1), then walk nodes in REVERSE
  topological order so each node's grad is fully accumulated before its
  _backward closure pushes gradient to its parents. Gradients ACCUMULATE (+=)
  because a node feeding two consumers gets contributions from both.

  Finite-difference check:  f'(x) ≈ (f(x+h) - f(x-h)) / (2h)

No numpy needed for the engine — it's pure scalar Python (that's the point).

How to run:
  uv run python modules/01c-deep-learning/py/01_autograd_mlp.py

The harness builds an MLP from Value nodes and trains it on the 4-point XOR
problem with MSE loss. You implement the local-gradient closures, backward(),
and the SGD update; everything else is provided.
"""

from __future__ import annotations

import math
import random

# ---------------------------------------------------------------------------
# The autograd Value — a scalar node in the computation graph
# ---------------------------------------------------------------------------


class Value:
    """
    A single scalar with a gradient and a link back to the nodes that produced it.

    Attributes:
      data       : float — the forward value
      grad       : float — ∂(final loss)/∂(this value), filled in by backward()
      _backward  : closure that pushes this node's grad to its parents' grads
      _prev      : set of parent Values this node was built from
      _op        : string tag (for debugging / graph viz)
    """

    def __init__(self, data: float, _children: tuple = (), _op: str = "") -> None:
        self.data = float(data)
        self.grad = 0.0
        self._backward = lambda: None
        self._prev = set(_children)
        self._op = _op

    def __add__(self, other: Value | float) -> Value:
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data + other.data, (self, other), "+")

        def _backward() -> None:
            # TODO: local grads of addition. c = a + b  →  ∂c/∂a = 1, ∂c/∂b = 1.
            # Push `out.grad` (scaled by each local derivative) onto self.grad and
            # other.grad. Use += so gradients ACCUMULATE when a node feeds multiple
            # consumers.
            raise NotImplementedError("TODO: implement __add__ backward")

        out._backward = _backward
        return out

    def __mul__(self, other: Value | float) -> Value:
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data * other.data, (self, other), "*")

        def _backward() -> None:
            # TODO: local grads of multiplication. c = a * b  →  ∂c/∂a = b, ∂c/∂b = a.
            # Each parent's grad gets `out.grad` times the OTHER factor's data.
            # Use += to accumulate.
            raise NotImplementedError("TODO: implement __mul__ backward")

        out._backward = _backward
        return out

    def tanh(self) -> Value:
        t = math.tanh(self.data)
        out = Value(t, (self,), "tanh")

        def _backward() -> None:
            # TODO: derivative of tanh. o = tanh(x)  →  do/dx = 1 - o².
            # Note `out.data` already holds tanh(x), so the local derivative is a
            # cheap expression in it. Accumulate onto self.grad with +=.
            raise NotImplementedError("TODO: implement tanh backward")

        out._backward = _backward
        return out

    def relu(self) -> Value:
        out = Value(self.data if self.data > 0 else 0.0, (self,), "relu")

        def _backward() -> None:
            # TODO: derivative of relu. o = max(0, x)  →  do/dx = 1 if x>0 else 0.
            # Gate `out.grad` by whether the unit was active (out.data > 0), then
            # accumulate onto self.grad with +=.
            raise NotImplementedError("TODO: implement relu backward")

        out._backward = _backward
        return out

    def backward(self) -> None:
        """
        Run backpropagation from THIS node (treated as the final scalar loss).

        TODO: implement.
          1. Build a topological ordering `topo` of the graph reachable from self
             (each node appears AFTER all nodes it depends on). Use a depth-first
             post-order visit: for an unvisited node, recurse into every child in
             `._prev` first, THEN append the node — with a `visited` set so shared
             nodes are added once.
          2. Seed the output gradient:  self.grad = 1.0   (∂L/∂L = 1)
          3. Walk `topo` in REVERSE and call each node's `_backward()` closure — the
             reverse post-order guarantees a node's grad is fully accumulated before
             it pushes to its parents.
        """
        raise NotImplementedError("TODO: implement backward()")

    # --- convenience operators (complete — no need to edit) -----------------
    def __neg__(self) -> Value:
        return self * -1.0

    def __sub__(self, other: Value | float) -> Value:
        return self + (-other if isinstance(other, Value) else Value(-other))

    def __radd__(self, other: Value | float) -> Value:
        return self + other

    def __rmul__(self, other: Value | float) -> Value:
        return self * other

    def __repr__(self) -> str:
        return f"Value(data={self.data:.4f}, grad={self.grad:.4f})"


# ---------------------------------------------------------------------------
# A tiny MLP built from Value nodes (complete — you don't edit this)
# ---------------------------------------------------------------------------


class Neuron:
    """A single neuron: tanh(Σ wᵢ·xᵢ + b)."""

    def __init__(self, n_in: int, rng: random.Random) -> None:
        self.w = [Value(rng.uniform(-1, 1)) for _ in range(n_in)]
        self.b = Value(0.0)

    def __call__(self, x: list[Value]) -> Value:
        act = sum((wi * xi for wi, xi in zip(self.w, x, strict=True)), self.b)
        return act.tanh()

    def parameters(self) -> list[Value]:
        return self.w + [self.b]


class Layer:
    """A fully-connected layer: n_out neurons, each seeing all n_in inputs."""

    def __init__(self, n_in: int, n_out: int, rng: random.Random) -> None:
        self.neurons = [Neuron(n_in, rng) for _ in range(n_out)]

    def __call__(self, x: list[Value]) -> list[Value]:
        return [n(x) for n in self.neurons]

    def parameters(self) -> list[Value]:
        return [p for n in self.neurons for p in n.parameters()]


class MLP:
    """A stack of layers. Output layer has one neuron (scalar prediction)."""

    def __init__(self, n_in: int, hidden: list[int], rng: random.Random) -> None:
        sizes = [n_in] + hidden
        self.layers = [Layer(sizes[i], sizes[i + 1], rng) for i in range(len(hidden))]

    def __call__(self, x: list[float] | list[Value]) -> Value:
        vx = [xi if isinstance(xi, Value) else Value(xi) for xi in x]
        out: list[Value] = vx
        for layer in self.layers:
            out = layer(out)
        return out[0]

    def parameters(self) -> list[Value]:
        return [p for layer in self.layers for p in layer.parameters()]


# ---------------------------------------------------------------------------
# Gradient check (complete — proves your engine matches finite differences)
# ---------------------------------------------------------------------------


def grad_check() -> float:
    """
    Verify autograd against numerical finite differences on a sample expression:

        f(a, b, c) = tanh(a*b + c) * (a + c)

    Returns the maximum absolute difference between the autograd gradient and the
    central finite-difference gradient over the three inputs. Should be < 1e-4.
    """

    def f_values(a: Value, b: Value, c: Value) -> Value:
        return (a * b + c).tanh() * (a + c)

    def f_scalar(av: float, bv: float, cv: float) -> float:
        return math.tanh(av * bv + cv) * (av + cv)

    a0, b0, c0 = 0.7, -1.3, 0.4

    # Autograd gradients
    a, b, c = Value(a0), Value(b0), Value(c0)
    out = f_values(a, b, c)
    out.backward()
    auto = {"a": a.grad, "b": b.grad, "c": c.grad}

    # Numerical gradients (central differences)
    h = 1e-5
    num = {
        "a": (f_scalar(a0 + h, b0, c0) - f_scalar(a0 - h, b0, c0)) / (2 * h),
        "b": (f_scalar(a0, b0 + h, c0) - f_scalar(a0, b0 - h, c0)) / (2 * h),
        "c": (f_scalar(a0, b0, c0 + h) - f_scalar(a0, b0, c0 - h)) / (2 * h),
    }

    max_diff = max(abs(auto[k] - num[k]) for k in auto)
    print("  Gradient check (autograd vs finite differences):")
    for k in ("a", "b", "c"):
        print(f"    d/d{k}: autograd={auto[k]:+.6f}  numeric={num[k]:+.6f}")
    print(f"    max abs diff = {max_diff:.2e}  (want < 1e-4)")
    return max_diff


# ---------------------------------------------------------------------------
# Training on XOR
# ---------------------------------------------------------------------------

# XOR: not linearly separable — needs a hidden layer. Targets are ±1 (tanh range).
XOR_X = [[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]]
XOR_Y = [-1.0, 1.0, 1.0, -1.0]


def train_xor(model: MLP, epochs: int = 200, lr: float = 0.1, print_every: int = 20) -> float:
    """
    Full-batch gradient descent on the 4-point XOR set with MSE loss.

    Each epoch:
      1. Forward every sample, accumulate squared-error loss.
      2. loss.backward() — fills .grad on every parameter (your engine).
      3. SGD update (YOU implement): step each param, then zero its grad.

    Returns the final loss.
    """
    params = model.parameters()
    final_loss = 0.0

    for epoch in range(epochs):
        # Forward + MSE loss over all 4 points
        loss = Value(0.0)
        for xrow, ytarget in zip(XOR_X, XOR_Y, strict=True):
            pred = model(xrow)
            diff = pred - Value(ytarget)
            loss = loss + diff * diff
        loss = loss * (1.0 / len(XOR_X))

        # Backward
        for p in params:
            p.grad = 0.0
        loss.backward()

        # ── SGD update (TODO) ────────────────────────────────────────────────
        # TODO: nudge every parameter in `params` a small step DOWN its gradient —
        #   i.e. subtract `lr` times each param's `.grad` from its `.data`, in place.
        #   (grads were already zeroed above and refilled by loss.backward();
        #    we zero again at the top of the next epoch.)
        raise NotImplementedError("TODO: implement the SGD parameter update")

        final_loss = loss.data
        if (epoch + 1) % print_every == 0 or epoch == 0:
            print(f"  Epoch {epoch + 1:>4}/{epochs}  loss={loss.data:.5f}")

    return final_loss


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    print("\n=== Task 1: scalar autograd + MLP on XOR ===\n")

    # ── Gradient check first: proves the engine before we trust training ──────
    print("[1/2] Verifying the autograd engine...")
    max_diff = grad_check()
    ok = max_diff < 1e-4
    print(f"  → gradient check {'PASSED' if ok else 'FAILED'}\n")

    # ── Train XOR ─────────────────────────────────────────────────────────────
    print("[2/2] Training a 2-4-4-1 MLP on XOR (MSE loss)...")
    rng = random.Random(1337)
    model = MLP(n_in=2, hidden=[4, 4, 1], rng=rng)
    final_loss = train_xor(model, epochs=200, lr=0.1, print_every=40)

    print("\n  Predictions:")
    all_signs_ok = True
    for xrow, ytarget in zip(XOR_X, XOR_Y, strict=True):
        pred = model(xrow).data
        sign_ok = (pred > 0) == (ytarget > 0)
        all_signs_ok = all_signs_ok and sign_ok
        mark = "ok " if sign_ok else "BAD"
        print(f"    x={xrow}  target={ytarget:+.0f}  pred={pred:+.3f}  [{mark}]")

    print(f"\n  Final loss: {final_loss:.5f}   (want < 0.05)")
    print(f"  All 4 signs correct: {all_signs_ok}")
    print(f"  Gradient check within 1e-4: {ok}")


if __name__ == "__main__":
    main()
