/**
 * Task 4 🔴 — A vanilla RNN trained with BACKPROP THROUGH TIME (BPTT), plain TS.
 *
 * What you'll learn:
 *   - How an RNN carries a hidden state (memory) across timesteps with shared weights.
 *   - The forward unroll: run the same cell over a sequence, storing every state.
 *   - BPTT: ordinary backprop over the unrolled graph — with two twists:
 *       * the tanh local gradient (1 - h²) reappears at every timestep;
 *       * because Wxh/Whh/Why are SHARED, their gradients are SUMMED over time.
 *   - Why `dhNext = Whhᵀ·da` carries error *backwards in time*.
 *
 * The math (README §4 explains each step in plain English):
 *
 *   Forward (per timestep t):
 *     h_t    = tanh(Wxh·x_t + Whh·h_{t-1} + bh)      hidden state (H, 1)
 *     logits = Why·h_t + by                          scores       (V, 1)
 *     p_t    = softmax(logits)                       next-char probs
 *
 *   Backward (t = T-1 … 0), accumulating shared-weight grads:
 *     dy       = p_t - oneHot(target_t)              softmax+CE gradient (module 08)
 *     dWhy    += dy · h_tᵀ ;   dby += dy
 *     dh       = Whyᵀ · dy + dhNext                  output path + gradient-from-future
 *     da       = (1 - h_t²) · dh                     backprop through tanh
 *     dbh     += da
 *     dWxh    += da · x_tᵀ
 *     dWhh    += da · h_{t-1}ᵀ
 *     dhNext   = Whhᵀ · da                           pass memory-grad to previous step
 *
 * The corpus, vocab, one-hot, parameter init, softmax+CE, the Adam update, gradient
 * clipping, and the sampling/evaluation harness are all provided. You implement
 * rnnStep, forward (the unroll), and the BPTT accumulation in backward.
 *
 * How to run:
 *   pnpm tsx modules/01c-deep-learning/ts/04-rnn-bptt.ts
 *
 * No math library — plain number[] (vectors) / number[][] (matrices).
 * Convention: hidden state and logits are COLUMN vectors stored as number[].
 */

// ---------------------------------------------------------------------------
// Tiny deterministic char-level corpus
// ---------------------------------------------------------------------------

const CORPUS = "hello world ".repeat(12); // a short repeating pattern
const CHARS = Array.from(new Set(CORPUS)).sort();
const VOCAB = CHARS.length;
const STOI: Record<string, number> = Object.fromEntries(CHARS.map((c, i) => [c, i]));
const ITOS: Record<number, string> = Object.fromEntries(CHARS.map((c, i) => [i, c]));

const HIDDEN = 32; // hidden-state size
const SEQ_LEN = 24; // BPTT window length

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
// Linear-algebra helpers on column vectors / matrices (complete)
//   matrix M is number[][] (rows × cols); vector v is number[] (length = rows).
// ---------------------------------------------------------------------------

/** Matrix (R×C) times column vector (length C) → column vector (length R). */
function matVec(M: number[][], v: number[]): number[] {
  const R = M.length,
    C = M[0].length;
  const out = new Array(R).fill(0) as number[];
  for (let i = 0; i < R; i++) {
    let s = 0;
    for (let j = 0; j < C; j++) s += M[i][j] * v[j];
    out[i] = s;
  }
  return out;
}
/** Mᵀ (C×R) times column vector (length R) → column vector (length C). */
function matTVec(M: number[][], v: number[]): number[] {
  const R = M.length,
    C = M[0].length;
  const out = new Array(C).fill(0) as number[];
  for (let i = 0; i < R; i++) {
    const vi = v[i];
    for (let j = 0; j < C; j++) out[j] += M[i][j] * vi;
  }
  return out;
}
/** Add several equal-length vectors. */
function addVec(...vs: number[][]): number[] {
  const out = vs[0].slice();
  for (let k = 1; k < vs.length; k++)
    for (let i = 0; i < out.length; i++) out[i] += vs[k][i];
  return out;
}
/** Outer product a·bᵀ → matrix (len(a) × len(b)). */
function outer(a: number[], b: number[]): number[][] {
  return a.map((ai) => b.map((bj) => ai * bj));
}
/** In-place M += G (same shape). */
function addMatInto(M: number[][], G: number[][]): void {
  for (let i = 0; i < M.length; i++)
    for (let j = 0; j < M[i].length; j++) M[i][j] += G[i][j];
}
/** In-place v += g (same length). */
function addVecInto(v: number[], g: number[]): void {
  for (let i = 0; i < v.length; i++) v[i] += g[i];
}

function zerosVec(n: number): number[] {
  return new Array(n).fill(0);
}
function zerosMat(r: number, c: number): number[][] {
  return Array.from({ length: r }, () => new Array(c).fill(0) as number[]);
}

// ---------------------------------------------------------------------------
// Helpers (complete)
// ---------------------------------------------------------------------------

function oneHot(idx: number): number[] {
  const v = zerosVec(VOCAB);
  v[idx] = 1;
  return v;
}

function softmax(z: number[]): number[] {
  const m = Math.max(...z);
  const e = z.map((v) => Math.exp(v - m));
  const s = e.reduce((a, b) => a + b, 0);
  return e.map((v) => v / s);
}

interface Params {
  Wxh: number[][]; // (H, V)
  Whh: number[][]; // (H, H)
  Why: number[][]; // (V, H)
  bh: number[]; // (H,)
  by: number[]; // (V,)
}

function initParams(seed = 1): Params {
  const rng = makeRng(seed);
  const g = gaussianFactory(rng);
  return {
    Wxh: Array.from({ length: HIDDEN }, () =>
      Array.from({ length: VOCAB }, () => g(0, 0.01)),
    ),
    Whh: Array.from({ length: HIDDEN }, () =>
      Array.from({ length: HIDDEN }, () => g(0, 0.01)),
    ),
    Why: Array.from({ length: VOCAB }, () =>
      Array.from({ length: HIDDEN }, () => g(0, 0.01)),
    ),
    bh: zerosVec(HIDDEN),
    by: zerosVec(VOCAB),
  };
}

// ---------------------------------------------------------------------------
// The RNN cell and unroll — implement these
// ---------------------------------------------------------------------------

/**
 * One RNN timestep.
 *   h      = tanh(Wxh·x + Whh·hPrev + bh)     (length HIDDEN)
 *   logits = Why·h + by                       (length VOCAB)
 * Returns [h, logits]. x is a one-hot vector (length VOCAB); hPrev length HIDDEN.
 *
 * TODO: implement.
 *   const pre = addVec(matVec(P.Wxh, x), matVec(P.Whh, hPrev), P.bh);
 *   const h = pre.map(Math.tanh);
 *   const logits = addVec(matVec(P.Why, h), P.by);
 *   return [h, logits];
 */
function rnnStep(x: number[], hPrev: number[], P: Params): [number[], number[]] {
  throw new Error("TODO: implement rnnStep()");
}

interface Cache {
  xs: number[][]; // xs[t] one-hot input
  hs: number[][]; // hs[t] hidden state; hs[0] is the seed h_{-1}, hs[t+1] is state after step t
  ps: number[][]; // ps[t] softmax probs
}

/**
 * Unroll the RNN over the sequence, computing loss and STORING everything BPTT
 * needs. To keep indices simple we store hidden states with a +1 offset:
 *   hsStore[0]   = hPrev            (the state BEFORE step 0)
 *   hsStore[t+1] = state AFTER step t
 * so "h_{t-1}" is hsStore[t] and "h_t" is hsStore[t+1].
 *
 * Returns [loss, cache].
 *
 * TODO: implement.
 *   const xs: number[][] = [], ps: number[][] = [];
 *   const hs: number[][] = [hPrev.slice()];    // hs[0] = hPrev
 *   let loss = 0;
 *   for (let t = 0; t < inputs.length; t++) {
 *     const x = oneHot(inputs[t]);
 *     const [h, logits] = rnnStep(x, hs[t], P);   // hs[t] is h_{t-1}
 *     const p = softmax(logits);
 *     xs.push(x); hs.push(h); ps.push(p);
 *     loss += -Math.log(p[targets[t]] + 1e-12);
 *   }
 *   return [loss, { xs, hs, ps }];
 */
function forward(
  inputs: number[],
  targets: number[],
  hPrev: number[],
  P: Params,
): [number, Cache] {
  throw new Error("TODO: implement forward()");
}

/**
 * Backprop through time. Returns gradients matching Params.
 * The softmax+cross-entropy output gradient `dy` is given; you fill the tanh
 * local gradient and the through-time accumulation.
 *
 * Remember the +1 offset from forward(): with cache.hs indexed so hs[t] = h_{t-1}
 * and hs[t+1] = h_t, at step t the "current" hidden state is hs[t+1] and the
 * "previous" one is hs[t].
 *
 * TODO: fill the marked (c)/(d)/(e) lines.
 *
 * Scaffold:
 *   const { xs, hs, ps } = cache;
 *   const g = {
 *     Wxh: zerosMat(HIDDEN, VOCAB), Whh: zerosMat(HIDDEN, HIDDEN),
 *     Why: zerosMat(VOCAB, HIDDEN), bh: zerosVec(HIDDEN), by: zerosVec(VOCAB),
 *   };
 *   let dhNext = zerosVec(HIDDEN);
 *   for (let t = inputs.length - 1; t >= 0; t--) {
 *     const hCur = hs[t + 1];   // h_t
 *     const hPrev = hs[t];      // h_{t-1}
 *     // softmax + cross-entropy gradient at the output (GIVEN):
 *     const dy = ps[t].slice();
 *     dy[targets[t]] -= 1;
 *     // (a) output-layer grads (shared → accumulate):
 *     addMatInto(g.Why, outer(dy, hCur));
 *     addVecInto(g.by, dy);
 *     // (b) gradient into the hidden state: output path + future:
 *     const dh = addVec(matTVec(P.Why, dy), dhNext);
 *     // (c) TODO: backprop through tanh.  h = tanh(a) → da = (1 - h²)·dh
 *     const da = dh.map((v, i) => (1 - hCur[i] * hCur[i]) * v);
 *     // (d) TODO: accumulate shared hidden-layer grads:
 *     addVecInto(g.bh, da);
 *     addMatInto(g.Wxh, outer(da, xs[t]));
 *     addMatInto(g.Whh, outer(da, hPrev));
 *     // (e) TODO: pass memory-gradient to the previous timestep:
 *     dhNext = matTVec(P.Whh, da);
 *   }
 *   return g;   // (the training loop clips these grads for you via clipGrads)
 */
function backward(
  inputs: number[],
  targets: number[],
  cache: Cache,
  P: Params,
): Params {
  throw new Error("TODO: implement backward() (BPTT)");
}

// ---------------------------------------------------------------------------
// Gradient clipping (complete)
// ---------------------------------------------------------------------------

function clipGrads(g: Params): void {
  const clip = (x: number) => Math.max(-5, Math.min(5, x));
  for (const M of [g.Wxh, g.Whh, g.Why])
    for (const row of M) for (let j = 0; j < row.length; j++) row[j] = clip(row[j]);
  for (const v of [g.bh, g.by]) for (let i = 0; i < v.length; i++) v[i] = clip(v[i]);
}

// ---------------------------------------------------------------------------
// Adam optimizer (complete — you don't edit this)
// ---------------------------------------------------------------------------

interface AdamState {
  mMat: Record<string, number[][]>;
  vMat: Record<string, number[][]>;
  mVec: Record<string, number[]>;
  vVec: Record<string, number[]>;
  t: number;
}

function makeAdamState(): AdamState {
  return {
    mMat: {
      Wxh: zerosMat(HIDDEN, VOCAB),
      Whh: zerosMat(HIDDEN, HIDDEN),
      Why: zerosMat(VOCAB, HIDDEN),
    },
    vMat: {
      Wxh: zerosMat(HIDDEN, VOCAB),
      Whh: zerosMat(HIDDEN, HIDDEN),
      Why: zerosMat(VOCAB, HIDDEN),
    },
    mVec: { bh: zerosVec(HIDDEN), by: zerosVec(VOCAB) },
    vVec: { bh: zerosVec(HIDDEN), by: zerosVec(VOCAB) },
    t: 0,
  };
}

function adamStep(P: Params, g: Params, st: AdamState, lr = 0.01): void {
  const b1 = 0.9,
    b2 = 0.999,
    eps = 1e-8;
  st.t += 1;
  const bc1 = 1 - Math.pow(b1, st.t);
  const bc2 = 1 - Math.pow(b2, st.t);
  const stepMat = (name: "Wxh" | "Whh" | "Why") => {
    const M = P[name],
      G = g[name],
      m = st.mMat[name],
      v = st.vMat[name];
    for (let i = 0; i < M.length; i++)
      for (let j = 0; j < M[i].length; j++) {
        m[i][j] = b1 * m[i][j] + (1 - b1) * G[i][j];
        v[i][j] = b2 * v[i][j] + (1 - b2) * G[i][j] * G[i][j];
        M[i][j] -= (lr * (m[i][j] / bc1)) / (Math.sqrt(v[i][j] / bc2) + eps);
      }
  };
  const stepVec = (name: "bh" | "by") => {
    const V = P[name],
      G = g[name],
      m = st.mVec[name],
      v = st.vVec[name];
    for (let i = 0; i < V.length; i++) {
      m[i] = b1 * m[i] + (1 - b1) * G[i];
      v[i] = b2 * v[i] + (1 - b2) * G[i] * G[i];
      V[i] -= (lr * (m[i] / bc1)) / (Math.sqrt(v[i] / bc2) + eps);
    }
  };
  stepMat("Wxh");
  stepMat("Whh");
  stepMat("Why");
  stepVec("bh");
  stepVec("by");
}

// ---------------------------------------------------------------------------
// Evaluation + sampling (complete)
// ---------------------------------------------------------------------------

function evaluate(data: number[], P: Params): number {
  let h = zerosVec(HIDDEN);
  let correct = 0;
  for (let t = 0; t < data.length - 1; t++) {
    const [hNew, logits] = rnnStep(oneHot(data[t]), h, P);
    h = hNew;
    const p = softmax(logits);
    let best = 0;
    for (let i = 1; i < p.length; i++) if (p[i] > p[best]) best = i;
    if (best === data[t + 1]) correct++;
  }
  return correct / (data.length - 1);
}

function sample(P: Params, seedChar: string, length: number): string {
  let h = zerosVec(HIDDEN);
  let idx = STOI[seedChar];
  const out = [seedChar];
  for (let k = 0; k < length; k++) {
    const [hNew, logits] = rnnStep(oneHot(idx), h, P);
    h = hNew;
    const p = softmax(logits);
    let best = 0;
    for (let i = 1; i < p.length; i++) if (p[i] > p[best]) best = i;
    idx = best;
    out.push(ITOS[idx]);
  }
  return out.join("");
}

// ---------------------------------------------------------------------------
// Training loop (complete)
// ---------------------------------------------------------------------------

function train(
  P: Params,
  data: number[],
  nIters = 2000,
  lr = 0.01,
): { initLoss: number; finalLoss: number } {
  const st = makeAdamState();
  let h = zerosVec(HIDDEN);
  let ptr = 0;
  let initLoss = NaN;
  let lastLoss = 0;

  for (let it = 0; it < nIters; it++) {
    if (ptr + SEQ_LEN + 1 >= data.length) {
      ptr = 0;
      h = zerosVec(HIDDEN);
    }
    const inputs = data.slice(ptr, ptr + SEQ_LEN);
    const targets = data.slice(ptr + 1, ptr + SEQ_LEN + 1);

    const [loss, cache] = forward(inputs, targets, h, P);
    const grads = backward(inputs, targets, cache, P);
    clipGrads(grads);

    h = cache.hs[SEQ_LEN]; // final hidden state (offset +1: hs[SEQ_LEN] = h_{SEQ_LEN-1})
    adamStep(P, grads, st, lr);

    lastLoss = loss / SEQ_LEN;
    if (Number.isNaN(initLoss)) initLoss = lastLoss;
    ptr += SEQ_LEN;

    if ((it + 1) % 500 === 0 || it === 0) {
      console.log(
        `  Iter ${String(it + 1).padStart(5)}/${nIters}  loss/char=${lastLoss.toFixed(4)}`,
      );
    }
  }
  return { initLoss, finalLoss: lastLoss };
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

function main() {
  console.log("\n=== Task 4: vanilla RNN + backprop through time ===\n");
  console.log(
    `Corpus (${CORPUS.length} chars): ${JSON.stringify(CORPUS.slice(0, 36))}...`,
  );
  console.log(`Vocab (${VOCAB} chars): ${JSON.stringify(CHARS)}`);
  console.log(`Chance accuracy (1/vocab): ${(1 / VOCAB).toFixed(3)}`);

  const data = Array.from(CORPUS).map((c) => STOI[c]);
  const P = initParams(1);

  console.log("\nTraining...");
  const { initLoss, finalLoss } = train(P, data, 2000, 0.01);

  const acc = evaluate(data, P);
  console.log(`\n  Initial loss/char: ${initLoss.toFixed(4)}`);
  console.log(
    `  Final   loss/char: ${finalLoss.toFixed(4)}   (${((finalLoss / initLoss) * 100).toFixed(1)}% of initial)`,
  );
  console.log(
    `  Next-char accuracy: ${(acc * 100).toFixed(2)}%   (want ≥ 90%, chance = ${((1 / VOCAB) * 100).toFixed(1)}%)`,
  );

  console.log(`\n  Sample generation from 'h': ${JSON.stringify(sample(P, "h", 24))}`);

  const lossDropped = finalLoss < 0.4 * initLoss;
  const beatsChance = acc >= 0.9;
  console.log(`\n  Loss dropped substantially (<40% of initial): ${lossDropped}`);
  console.log(`  Accuracy ≥ 90%: ${beatsChance}`);
}

main();

export {};
