/**
 * Task 2 🟡 — OPTIMIZERS (SGD / momentum / Adam) and weight INITIALISATION (plain TS).
 *
 * What you'll learn:
 *   - How the same gradient produces very different steps under SGD / momentum / Adam.
 *   - Why Adam usually reaches a target loss in fewer epochs (adaptive per-param steps).
 *   - He vs Xavier initialisation and why the fan-in scale keeps activations sane.
 *   - The vanishing-gradient problem: sigmoid squashes gradients, ReLU doesn't.
 *
 * The math (README §2 explains each step in plain English):
 *
 *   SGD:       θ ← θ - lr·g
 *   Momentum:  v ← β·v + (1-β)·g ;              θ ← θ - lr·v            (β=0.9)
 *   Adam:      m ← β1·m + (1-β1)·g
 *              v ← β2·v + (1-β2)·g²
 *              m̂ = m/(1-β1^t) ;  v̂ = v/(1-β2^t)                        (t = step, 1-indexed)
 *              θ ← θ - lr·m̂/(sqrt(v̂)+ε)          (β1=0.9, β2=0.999, ε=1e-8)
 *
 *   He init (ReLU):        scale = sqrt(2 / fan_in)
 *   Xavier init (tanh):    scale = sqrt(2 / (fan_in + fan_out))
 *
 *   Vanishing gradients: sigmoid'(x)=σ(1-σ) ≤ 0.25, so a deep sigmoid net multiplies
 *   many small factors → tiny first-layer gradients. ReLU'(x)=1 for x>0 → gradients survive.
 *
 * Everything (dataset, forward, MANUAL backprop, training loop) is provided.
 * You implement the three optimizer update rules and the two init scale factors.
 *
 * How to run:
 *   pnpm tsx modules/01c-deep-learning/ts/02-optimizers.ts
 *
 * No math library — plain number[] / number[][] arrays.
 */

// ---------------------------------------------------------------------------
// Init scale factors — implement these
// ---------------------------------------------------------------------------

/**
 * He initialisation scale (std of the Normal), tuned for ReLU.
 * TODO: return the He scale factor (see the He-init formula in the file header) —
 *       it depends only on `fanIn`.
 */
function heInit(fanIn: number, _fanOut: number): number {
  throw new Error("TODO: implement heInit()");
}

/**
 * Xavier/Glorot initialisation scale (std of the Normal), tuned for tanh/sigmoid.
 * TODO: return the Xavier scale factor (see the Xavier-init formula in the file
 *       header) — it uses both `fanIn` and `fanOut`.
 */
function xavierInit(fanIn: number, fanOut: number): number {
  throw new Error("TODO: implement xavierInit()");
}

// ---------------------------------------------------------------------------
// Optimizer update rules — implement these
//   Params/grads/state are flat number[] (weight matrices are flattened by the
//   training loop). You mutate `param` IN PLACE.
// ---------------------------------------------------------------------------

interface OptState {
  v: number[]; // velocity / Adam 2nd moment lives in vAdam below; v is momentum velocity
  m: number[]; // Adam 1st moment
  vAdam: number[]; // Adam 2nd moment
  t: number; // Adam step count
}

/**
 * Plain SGD, IN PLACE:  param[i] -= lr * grad[i]
 * TODO: step every element of `param` down its gradient by `lr`, mutating the
 *       array in place (assign into `param[i]`, don't reassign `param`).
 */
function sgdUpdate(
  param: number[],
  grad: number[],
  _state: OptState,
  lr: number,
): void {
  throw new Error("TODO: implement sgdUpdate()");
}

/**
 * SGD with momentum, IN PLACE. state.v holds the running velocity (init 0).
 *   v[i] ← β·v[i] + (1-β)·g[i]
 *   param[i] ← param[i] - lr·v[i]
 * TODO: implement the two-line rule above (β = 0.9, already declared below). For
 *       each element: update the persistent velocity `state.v[i]` to the moving
 *       average of the gradient, then step `param[i]` down that velocity by `lr`.
 */
function momentumUpdate(
  param: number[],
  grad: number[],
  state: OptState,
  lr: number,
): void {
  const beta = 0.9;
  throw new Error("TODO: implement momentumUpdate()");
}

/**
 * Adam, IN PLACE. state.m = 1st moment, state.vAdam = 2nd moment, state.t = step (init 0).
 *   t ← t + 1
 *   m ← β1·m + (1-β1)·g
 *   v ← β2·v + (1-β2)·g²
 *   m̂ = m / (1 - β1^t)
 *   v̂ = v / (1 - β2^t)
 *   param ← param - lr·m̂ / (sqrt(v̂) + ε)
 * TODO: implement the six-line rule above (β1/β2/ε already declared below).
 *   - Bump the step counter `state.t` and read it as `t` (needed for bias
 *     correction — this is why t must persist in state).
 *   - For each element: update the persistent 1st moment `state.m[i]` (moving avg
 *     of the gradient) and 2nd moment `state.vAdam[i]` (moving avg of the gradient
 *     SQUARED), each mixed with beta1/beta2.
 *   - Bias-correct each moment by dividing by (1 - beta^t) (use Math.pow).
 *   - Step `param[i]` in place: corrected 1st moment over sqrt(corrected 2nd
 *     moment) + eps, scaled by `lr`.
 */
function adamUpdate(
  param: number[],
  grad: number[],
  state: OptState,
  lr: number,
): void {
  const beta1 = 0.9,
    beta2 = 0.999,
    eps = 1e-8;
  throw new Error("TODO: implement adamUpdate()");
}

// ---------------------------------------------------------------------------
// Seeded RNG + Gaussian (deterministic)
// ---------------------------------------------------------------------------

function makeRng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function gaussianFactory(rng: () => number): (mean: number, std: number) => number {
  return (mean, std) => {
    const u1 = Math.max(rng(), 1e-12);
    const u2 = rng();
    return mean + std * Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  };
}

// ---------------------------------------------------------------------------
// Matrix helpers (number[][])
// ---------------------------------------------------------------------------

function matMul(A: number[][], B: number[][]): number[][] {
  const N = A.length,
    K = A[0].length,
    M = B[0].length;
  const C = Array.from({ length: N }, () => new Array(M).fill(0) as number[]);
  for (let i = 0; i < N; i++)
    for (let k = 0; k < K; k++) {
      const aik = A[i][k];
      for (let j = 0; j < M; j++) C[i][j] += aik * B[k][j];
    }
  return C;
}

function transpose(A: number[][]): number[][] {
  const N = A.length,
    M = A[0].length;
  const T = Array.from({ length: M }, () => new Array(N).fill(0) as number[]);
  for (let i = 0; i < N; i++) for (let j = 0; j < M; j++) T[j][i] = A[i][j];
  return T;
}

function addRowVec(Z: number[][], b: number[]): number[][] {
  return Z.map((row) => row.map((v, j) => v + b[j]));
}

function sigmoidScalar(z: number): number {
  return 1 / (1 + Math.exp(-z));
}

// ---------------------------------------------------------------------------
// Synthetic dataset (complete) — two nonlinear rings, binary labels
// ---------------------------------------------------------------------------

function makeDataset(n = 400, seed = 0): { X: number[][]; y: number[] } {
  const rng = makeRng(seed);
  const gauss = gaussianFactory(rng);
  const half = Math.floor(n / 2);
  const X: number[][] = [];
  const y: number[] = [];
  for (let i = 0; i < half; i++) {
    const theta = rng() * 2 * Math.PI;
    const r = 1.0 + gauss(0, 0.15);
    X.push([r * Math.cos(theta), r * Math.sin(theta)]);
    y.push(0);
  }
  for (let i = 0; i < half; i++) {
    const theta = rng() * 2 * Math.PI;
    const r = 2.5 + gauss(0, 0.15);
    X.push([r * Math.cos(theta), r * Math.sin(theta)]);
    y.push(1);
  }
  // Shuffle deterministically
  const idx = Array.from({ length: X.length }, (_, i) => i);
  for (let i = idx.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [idx[i], idx[j]] = [idx[j], idx[i]];
  }
  return { X: idx.map((i) => X[i]), y: idx.map((i) => y[i]) };
}

// ---------------------------------------------------------------------------
// Matrix-form 2-layer MLP with MANUAL backprop (complete — you don't edit this)
// ---------------------------------------------------------------------------

interface Cache {
  X: number[][];
  z1: number[][];
  a1: number[][];
  p: number[][];
}

class TwoLayerMLP {
  W1: number[][]; // (2, H)
  b1: number[]; // (H,)
  W2: number[][]; // (H, 1)
  b2: number[]; // (1,)

  constructor(
    nIn: number,
    private nHidden: number,
    private activation: "relu" | "sigmoid",
    init: "he" | "xavier",
    seed = 0,
  ) {
    const rng = makeRng(seed);
    const gauss = gaussianFactory(rng);
    const s1 = init === "he" ? heInit(nIn, nHidden) : xavierInit(nIn, nHidden);
    const s2 = init === "he" ? heInit(nHidden, 1) : xavierInit(nHidden, 1);
    this.W1 = Array.from({ length: nIn }, () =>
      Array.from({ length: nHidden }, () => gauss(0, s1)),
    );
    this.b1 = new Array(nHidden).fill(0);
    this.W2 = Array.from({ length: nHidden }, () => [gauss(0, s2)]);
    this.b2 = [0];
  }

  private act(Z: number[][]): number[][] {
    return Z.map((row) =>
      row.map((z) => (this.activation === "relu" ? Math.max(0, z) : sigmoidScalar(z))),
    );
  }

  private actGrad(Z: number[][], A: number[][]): number[][] {
    return Z.map((row, i) =>
      row.map((z, j) =>
        this.activation === "relu" ? (z > 0 ? 1 : 0) : A[i][j] * (1 - A[i][j]),
      ),
    );
  }

  forward(X: number[][]): Cache {
    const z1 = addRowVec(matMul(X, this.W1), this.b1);
    const a1 = this.act(z1);
    const z2 = addRowVec(matMul(a1, this.W2), this.b2);
    const p = z2.map((row) => [sigmoidScalar(row[0])]);
    return { X, z1, a1, p };
  }

  loss(X: number[][], y: number[]): number {
    const p = this.forward(X).p;
    let s = 0;
    for (let i = 0; i < y.length; i++) {
      const pi = Math.min(Math.max(p[i][0], 1e-12), 1 - 1e-12);
      s += -(y[i] * Math.log(pi) + (1 - y[i]) * Math.log(1 - pi));
    }
    return s / y.length;
  }

  backward(
    cache: Cache,
    y: number[],
  ): { W1: number[][]; b1: number[]; W2: number[][]; b2: number[] } {
    const { X, z1, a1, p } = cache;
    const N = X.length;
    // dL/dz2 = (p - y) / N  (BCE + sigmoid)
    const dz2 = p.map((row, i) => [(row[0] - y[i]) / N]); // (N,1)
    const dW2 = matMul(transpose(a1), dz2); // (H,1)
    const db2 = [dz2.reduce((acc, r) => acc + r[0], 0)]; // (1,)
    const da1 = matMul(dz2, transpose(this.W2)); // (N,H)
    const ag = this.actGrad(z1, a1); // (N,H)
    const dz1 = da1.map((row, i) => row.map((v, j) => v * ag[i][j])); // (N,H)
    const dW1 = matMul(transpose(X), dz1); // (2,H)
    const db1 = new Array(this.nHidden).fill(0) as number[];
    for (let i = 0; i < N; i++)
      for (let j = 0; j < this.nHidden; j++) db1[j] += dz1[i][j];
    return { W1: dW1, b1: db1, W2: dW2, b2: db2 };
  }
}

// ---------------------------------------------------------------------------
// Flatten helpers so optimizers see plain number[] (complete)
// ---------------------------------------------------------------------------

function flatten(M: number[][]): number[] {
  return M.reduce((acc, row) => acc.concat(row), [] as number[]);
}
function unflattenInto(M: number[][], flat: number[]): void {
  let k = 0;
  for (let i = 0; i < M.length; i++)
    for (let j = 0; j < M[i].length; j++) M[i][j] = flat[k++];
}

// ---------------------------------------------------------------------------
// Generic training loop that plugs in any optimizer (complete)
// ---------------------------------------------------------------------------

type UpdateFn = (param: number[], grad: number[], state: OptState, lr: number) => void;
const OPTIMIZERS: Record<string, UpdateFn> = {
  sgd: sgdUpdate,
  momentum: momentumUpdate,
  adam: adamUpdate,
};

function newState(len: number): OptState {
  return {
    v: new Array(len).fill(0),
    m: new Array(len).fill(0),
    vAdam: new Array(len).fill(0),
    t: 0,
  };
}

function trainUntil(
  model: TwoLayerMLP,
  X: number[][],
  y: number[],
  optimizer: string,
  lr: number,
  targetLoss: number,
  maxEpochs = 5000,
): { epochs: number; loss: number } {
  const update = OPTIMIZERS[optimizer];
  // Parameter names → the 2-D array and a matching bias 1-D array
  const paramMats: Record<string, number[][]> = { W1: model.W1, W2: model.W2 };
  const paramVecs: Record<string, number[]> = { b1: model.b1, b2: model.b2 };
  const states: Record<string, OptState> = {
    W1: newState(flatten(model.W1).length),
    W2: newState(flatten(model.W2).length),
    b1: newState(model.b1.length),
    b2: newState(model.b2.length),
  };

  for (let epoch = 1; epoch <= maxEpochs; epoch++) {
    const cache = model.forward(X);
    const grads = model.backward(cache, y);
    // Matrix params
    for (const name of ["W1", "W2"] as const) {
      const flat = flatten(paramMats[name]);
      update(flat, flatten(grads[name]), states[name], lr);
      unflattenInto(paramMats[name], flat);
    }
    // Bias vectors
    for (const name of ["b1", "b2"] as const) {
      update(paramVecs[name], grads[name], states[name], lr);
    }
    const loss = model.loss(X, y);
    if (loss <= targetLoss) return { epochs: epoch, loss };
  }
  return { epochs: maxEpochs, loss: model.loss(X, y) };
}

// ---------------------------------------------------------------------------
// Vanishing-gradient demo (complete)
// ---------------------------------------------------------------------------

function firstLayerGradNorm(
  activation: "relu" | "sigmoid",
  depth = 8,
  width = 16,
  seed = 3,
): number {
  const rng = makeRng(seed);
  const gauss = gaussianFactory(rng);
  const N = 64;
  const X: number[][] = Array.from({ length: N }, () =>
    Array.from({ length: width }, () => gauss(0, 1)),
  );
  const y: number[] = Array.from({ length: N }, () => (rng() < 0.5 ? 0 : 1));

  const scale = xavierInit(width, width);
  const Ws: number[][][] = Array.from({ length: depth }, () =>
    Array.from({ length: width }, () =>
      Array.from({ length: width }, () => gauss(0, scale)),
    ),
  );
  const Wout: number[][] = Array.from({ length: width }, () => [gauss(0, scale)]);

  const act = (Z: number[][]) =>
    Z.map((row) =>
      row.map((z) => (activation === "relu" ? Math.max(0, z) : sigmoidScalar(z))),
    );
  const actGrad = (Z: number[][], A: number[][]) =>
    Z.map((row, i) =>
      row.map((z, j) =>
        activation === "relu" ? (z > 0 ? 1 : 0) : A[i][j] * (1 - A[i][j]),
      ),
    );

  // Forward
  const zs: number[][][] = [];
  const as_: number[][][] = [X];
  let h = X;
  for (const W of Ws) {
    const z = matMul(h, W);
    h = act(z);
    zs.push(z);
    as_.push(h);
  }
  const pRaw = matMul(h, Wout);
  const p = pRaw.map((row) => [sigmoidScalar(row[0])]);

  // Backward
  const dz = p.map((row, i) => [(row[0] - y[i]) / N]);
  let dh = matMul(dz, transpose(Wout)); // (N, width)
  let firstGrad: number[][] = [];
  for (let i = depth - 1; i >= 0; i--) {
    const ag = actGrad(zs[i], as_[i + 1]);
    const dzI = dh.map((row, r) => row.map((v, c) => v * ag[r][c]));
    const gradI = matMul(transpose(as_[i]), dzI);
    if (i === 0) firstGrad = gradI;
    dh = matMul(dzI, transpose(Ws[i]));
  }
  let sumSq = 0;
  for (const row of firstGrad) for (const v of row) sumSq += v * v;
  return Math.sqrt(sumSq);
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

function main() {
  console.log("\n=== Task 2: optimizers + initialisation ===\n");

  const { X, y } = makeDataset(400, 0);
  console.log(`Dataset: ${X.length} points, 2 nonlinear classes (rings).`);

  // ── Optimizer race ─────────────────────────────────────────────────────────
  console.log("\n[1/2] Epochs to reach target loss (lower = faster convergence):");
  const target = 0.2;
  const lrs: Record<string, number> = { sgd: 0.5, momentum: 0.5, adam: 0.05 };
  const results: Record<string, { epochs: number; loss: number }> = {};
  for (const opt of ["sgd", "momentum", "adam"]) {
    const model = new TwoLayerMLP(2, 16, "relu", "he", 7);
    const res = trainUntil(model, X, y, opt, lrs[opt], target, 5000);
    results[opt] = res;
    console.log(
      `    ${opt.padEnd(9)}: ${String(res.epochs).padStart(5)} epochs  (final loss ${res.loss.toFixed(4)}, lr=${lrs[opt]})`,
    );
  }
  const adamFaster = results.adam.epochs < results.sgd.epochs;
  console.log(`\n  Adam reached target in fewer epochs than SGD: ${adamFaster}`);

  // ── Vanishing-gradient demo ────────────────────────────────────────────────
  console.log("\n[2/2] Vanishing gradients — first-layer grad norm in an 8-layer net:");
  const gSigmoid = firstLayerGradNorm("sigmoid");
  const gRelu = firstLayerGradNorm("relu");
  const ratio = gSigmoid > 0 ? gRelu / gSigmoid : Infinity;
  console.log(`    sigmoid first-layer |grad| = ${gSigmoid.toExponential(3)}`);
  console.log(`    relu    first-layer |grad| = ${gRelu.toExponential(3)}`);
  console.log(`    ratio (relu / sigmoid)     = ${ratio.toFixed(1)}x   (want > 5x)`);
  console.log(`\n  ReLU grad clearly larger than sigmoid: ${ratio > 5}`);
}

main();

export {};
