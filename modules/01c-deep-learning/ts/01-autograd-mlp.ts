/**
 * Task 1 🔴 — Micro scalar AUTOGRAD engine + an MLP trained on XOR (plain TS).
 *
 * What you'll learn:
 *   - Backpropagation IS the chain rule run backwards over a computation graph.
 *   - Every value remembers how it was produced (its inputs + a local-grad closure).
 *   - A topological sort lets us run those closures in the correct order.
 *   - Gradient checking: compare autograd against finite differences to prove it right.
 *
 * The math (README §1 explains each step in plain English):
 *
 *   For c = a + b :   ∂c/∂a = 1,      ∂c/∂b = 1
 *   For c = a * b :   ∂c/∂a = b,      ∂c/∂b = a
 *   For o = tanh(x):  do/dx = 1 - o²           (o = tanh(x))
 *   For o = relu(x):  do/dx = 1 if x>0 else 0
 *
 *   backward(): seed the root grad = 1 (∂L/∂L = 1), then walk nodes in REVERSE
 *   topological order so each node's grad is fully accumulated before its
 *   _backward closure pushes gradient to its parents. Gradients ACCUMULATE (+=)
 *   because a node feeding two consumers gets contributions from both.
 *
 *   Finite-difference check:  f'(x) ≈ (f(x+h) - f(x-h)) / (2h)
 *
 * No math library — pure scalar arithmetic (that's the point).
 *
 * How to run:
 *   pnpm tsx modules/01c-deep-learning/ts/01-autograd-mlp.ts
 *
 * The harness builds an MLP from Value nodes and trains it on the 4-point XOR
 * problem with MSE loss. You implement the local-gradient closures, backward(),
 * and the SGD update; everything else is provided.
 */

// ---------------------------------------------------------------------------
// Seeded RNG (deterministic across runs)
// ---------------------------------------------------------------------------

function makeRng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    // mulberry32
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ---------------------------------------------------------------------------
// The autograd Value — a scalar node in the computation graph
// ---------------------------------------------------------------------------

class Value {
  data: number;
  grad: number;
  _backward: () => void;
  _prev: Value[];
  _op: string;

  constructor(data: number, children: Value[] = [], op = "") {
    this.data = data;
    this.grad = 0;
    this._backward = () => {};
    this._prev = children;
    this._op = op;
  }

  add(other: Value | number): Value {
    const o = other instanceof Value ? other : new Value(other);
    const out = new Value(this.data + o.data, [this, o], "+");
    out._backward = () => {
      // TODO: local grads of addition. c = a + b  →  ∂c/∂a = 1, ∂c/∂b = 1.
      //   this.grad += 1.0 * out.grad
      //   o.grad    += 1.0 * out.grad
      // (use += so gradients accumulate when a node feeds multiple consumers)
      throw new Error("TODO: implement add() backward");
    };
    return out;
  }

  mul(other: Value | number): Value {
    const o = other instanceof Value ? other : new Value(other);
    const out = new Value(this.data * o.data, [this, o], "*");
    out._backward = () => {
      // TODO: local grads of multiplication. c = a * b  →  ∂c/∂a = b, ∂c/∂b = a.
      //   this.grad += o.data    * out.grad
      //   o.grad    += this.data * out.grad
      throw new Error("TODO: implement mul() backward");
    };
    return out;
  }

  tanh(): Value {
    const t = Math.tanh(this.data);
    const out = new Value(t, [this], "tanh");
    out._backward = () => {
      // TODO: derivative of tanh. o = tanh(x)  →  do/dx = 1 - o².
      //   this.grad += (1 - out.data ** 2) * out.grad
      throw new Error("TODO: implement tanh() backward");
    };
    return out;
  }

  relu(): Value {
    const out = new Value(this.data > 0 ? this.data : 0, [this], "relu");
    out._backward = () => {
      // TODO: derivative of relu. o = max(0, x)  →  do/dx = 1 if x>0 else 0.
      //   this.grad += (out.data > 0 ? 1 : 0) * out.grad
      throw new Error("TODO: implement relu() backward");
    };
    return out;
  }

  backward(): void {
    // TODO: implement.
    //   1. Build a topological ordering `topo` of the graph reachable from `this`
    //      (each node appears AFTER all nodes it depends on). DFS post-order:
    //
    //        const topo: Value[] = [];
    //        const visited = new Set<Value>();
    //        const build = (v: Value) => {
    //          if (!visited.has(v)) {
    //            visited.add(v);
    //            for (const child of v._prev) build(child);
    //            topo.push(v);
    //          }
    //        };
    //        build(this);
    //
    //   2. Seed the output gradient:  this.grad = 1.0   (∂L/∂L = 1)
    //   3. Walk topo in REVERSE and call each node's closure:
    //        for (let i = topo.length - 1; i >= 0; i--) topo[i]._backward();
    throw new Error("TODO: implement backward()");
  }

  // --- convenience helpers (complete — no need to edit) --------------------
  neg(): Value {
    return this.mul(-1);
  }
  sub(other: Value | number): Value {
    const o = other instanceof Value ? other : new Value(other);
    return this.add(o.neg());
  }
}

// ---------------------------------------------------------------------------
// A tiny MLP built from Value nodes (complete — you don't edit this)
// ---------------------------------------------------------------------------

class Neuron {
  w: Value[];
  b: Value;
  constructor(nIn: number, rng: () => number) {
    this.w = Array.from({ length: nIn }, () => new Value(rng() * 2 - 1));
    this.b = new Value(0);
  }
  call(x: Value[]): Value {
    let act = this.b;
    for (let i = 0; i < this.w.length; i++) act = act.add(this.w[i].mul(x[i]));
    return act.tanh();
  }
  parameters(): Value[] {
    return [...this.w, this.b];
  }
}

class Layer {
  neurons: Neuron[];
  constructor(nIn: number, nOut: number, rng: () => number) {
    this.neurons = Array.from({ length: nOut }, () => new Neuron(nIn, rng));
  }
  call(x: Value[]): Value[] {
    return this.neurons.map((n) => n.call(x));
  }
  parameters(): Value[] {
    return this.neurons.flatMap((n) => n.parameters());
  }
}

class MLP {
  layers: Layer[];
  constructor(nIn: number, hidden: number[], rng: () => number) {
    const sizes = [nIn, ...hidden];
    this.layers = hidden.map((_, i) => new Layer(sizes[i], sizes[i + 1], rng));
  }
  call(x: number[] | Value[]): Value {
    let out: Value[] = x.map((xi) => (xi instanceof Value ? xi : new Value(xi)));
    for (const layer of this.layers) out = layer.call(out);
    return out[0];
  }
  parameters(): Value[] {
    return this.layers.flatMap((l) => l.parameters());
  }
}

// ---------------------------------------------------------------------------
// Gradient check (complete — proves your engine matches finite differences)
// ---------------------------------------------------------------------------

function gradCheck(): number {
  // f(a, b, c) = tanh(a*b + c) * (a + c)
  const fValues = (a: Value, b: Value, c: Value): Value =>
    a.mul(b).add(c).tanh().mul(a.add(c));
  const fScalar = (av: number, bv: number, cv: number): number =>
    Math.tanh(av * bv + cv) * (av + cv);

  const a0 = 0.7,
    b0 = -1.3,
    c0 = 0.4;

  const a = new Value(a0),
    b = new Value(b0),
    c = new Value(c0);
  const out = fValues(a, b, c);
  out.backward();
  const auto = { a: a.grad, b: b.grad, c: c.grad };

  const h = 1e-5;
  const num = {
    a: (fScalar(a0 + h, b0, c0) - fScalar(a0 - h, b0, c0)) / (2 * h),
    b: (fScalar(a0, b0 + h, c0) - fScalar(a0, b0 - h, c0)) / (2 * h),
    c: (fScalar(a0, b0, c0 + h) - fScalar(a0, b0, c0 - h)) / (2 * h),
  };

  const keys: (keyof typeof auto)[] = ["a", "b", "c"];
  const maxDiff = Math.max(...keys.map((k) => Math.abs(auto[k] - num[k])));
  console.log("  Gradient check (autograd vs finite differences):");
  for (const k of keys) {
    console.log(
      `    d/d${k}: autograd=${auto[k].toFixed(6)}  numeric=${num[k].toFixed(6)}`,
    );
  }
  console.log(`    max abs diff = ${maxDiff.toExponential(2)}  (want < 1e-4)`);
  return maxDiff;
}

// ---------------------------------------------------------------------------
// Training on XOR
// ---------------------------------------------------------------------------

// XOR: not linearly separable — needs a hidden layer. Targets are ±1 (tanh range).
const XOR_X = [
  [0, 0],
  [0, 1],
  [1, 0],
  [1, 1],
];
const XOR_Y = [-1, 1, 1, -1];

function trainXor(model: MLP, epochs = 200, lr = 0.1, printEvery = 20): number {
  const params = model.parameters();
  let finalLoss = 0;

  for (let epoch = 0; epoch < epochs; epoch++) {
    // Forward + MSE loss over all 4 points
    let loss = new Value(0);
    for (let i = 0; i < XOR_X.length; i++) {
      const pred = model.call(XOR_X[i]);
      const diff = pred.sub(XOR_Y[i]);
      loss = loss.add(diff.mul(diff));
    }
    loss = loss.mul(1 / XOR_X.length);

    // Backward
    for (const p of params) p.grad = 0;
    loss.backward();

    // ── SGD update (TODO) ────────────────────────────────────────────────────
    // TODO: for each parameter p in `params`:
    //         p.data -= lr * p.grad
    //   (grads were already zeroed above and refilled by loss.backward();
    //    we zero again at the top of the next epoch.)
    throw new Error("TODO: implement the SGD parameter update");

    finalLoss = loss.data;
    if ((epoch + 1) % printEvery === 0 || epoch === 0) {
      console.log(
        `  Epoch ${String(epoch + 1).padStart(4)}/${epochs}  loss=${loss.data.toFixed(5)}`,
      );
    }
  }

  return finalLoss;
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

function main() {
  console.log("\n=== Task 1: scalar autograd + MLP on XOR ===\n");

  // ── Gradient check first: proves the engine before we trust training ──────
  console.log("[1/2] Verifying the autograd engine...");
  const maxDiff = gradCheck();
  const ok = maxDiff < 1e-4;
  console.log(`  → gradient check ${ok ? "PASSED" : "FAILED"}\n`);

  // ── Train XOR ─────────────────────────────────────────────────────────────
  console.log("[2/2] Training a 2-4-4-1 MLP on XOR (MSE loss)...");
  const rng = makeRng(1337);
  const model = new MLP(2, [4, 4, 1], rng);
  const finalLoss = trainXor(model, 200, 0.1, 40);

  console.log("\n  Predictions:");
  let allSignsOk = true;
  for (let i = 0; i < XOR_X.length; i++) {
    const pred = model.call(XOR_X[i]).data;
    const signOk = pred > 0 === XOR_Y[i] > 0;
    allSignsOk = allSignsOk && signOk;
    const mark = signOk ? "ok " : "BAD";
    console.log(
      `    x=[${XOR_X[i].join(", ")}]  target=${XOR_Y[i] >= 0 ? "+" : ""}${XOR_Y[i]}  pred=${pred >= 0 ? "+" : ""}${pred.toFixed(3)}  [${mark}]`,
    );
  }

  console.log(`\n  Final loss: ${finalLoss.toFixed(5)}   (want < 0.05)`);
  console.log(`  All 4 signs correct: ${allSignsOk}`);
  console.log(`  Gradient check within 1e-4: ${ok}`);
}

main();

export {};
