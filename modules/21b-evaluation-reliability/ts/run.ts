/**
 * run.ts — CLI for the Module 21b gold-evidence retrieval benchmark.
 *
 * Loads the versioned corpus + case fixtures, ranks every case with each
 * retrieval method, computes Recall@k / MRR / NDCG@k from scratch (before any
 * generator runs), prints a comparison table + failure report, and writes a
 * deterministic JSON report to an output directory.
 *
 * Run it:
 *   pnpm --filter @learn-ai/m21b-eval bench
 *   pnpm tsx modules/21b-evaluation-reliability/ts/run.ts --split heldout --k 5
 *   pnpm tsx modules/21b-evaluation-reliability/ts/run.ts --split both --out /tmp/21b
 *
 * Offline and deterministic: no provider, no network, no randomness.
 */

import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import {
  buildReport,
  type CasesFixture,
  type CorpusFixture,
  evaluateSplit,
  formatFailures,
  formatTable,
  type ReportManifest,
  type RubricFixture,
  serializeReport,
  validateFixtures,
} from "./benchmark.js";
import { configFromManifest, type Manifest, RetrievalIndex } from "./retrieval.js";

const FIXTURES_DIR = join(dirname(fileURLToPath(import.meta.url)), "..", "fixtures");

function loadJson<T>(name: string): T {
  return JSON.parse(readFileSync(join(FIXTURES_DIR, name), "utf-8")) as T;
}

type ManifestFile = Manifest & ReportManifest & { default_k: number };

interface Args {
  split: "dev" | "heldout" | "both";
  k?: number;
  out?: string;
}

function parseArgs(argv: readonly string[]): Args {
  const args: Args = { split: "dev" };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--split") {
      const value = argv[(i += 1)];
      if (value !== "dev" && value !== "heldout" && value !== "both") {
        throw new Error(`--split must be dev|heldout|both, got: ${value}`);
      }
      args.split = value;
    } else if (arg === "--k") {
      const raw = argv[(i += 1)];
      const value = Number.parseInt(raw, 10);
      if (Number.isNaN(value)) {
        throw new Error(`--k must be an integer, got: ${String(raw)}`);
      }
      args.k = value;
    } else if (arg === "--out") {
      args.out = argv[(i += 1)];
    } else {
      throw new Error(`unknown argument: ${arg}`);
    }
  }
  return args;
}

function main(): void {
  const args = parseArgs(process.argv.slice(2));
  const manifest = loadJson<ManifestFile>("manifest.json");
  const rubric = loadJson<RubricFixture>("rubrics.json");
  const corpus = loadJson<CorpusFixture>("corpus.json");
  const threshold = rubric.relevant_threshold ?? 1;
  const k = args.k ?? manifest.default_k;

  const splits: Array<"dev" | "heldout"> =
    args.split === "both" ? ["dev", "heldout"] : [args.split];

  // Gate: reject malformed fixtures before any evaluation runs. The map keys are
  // the EXPECTED split names, so a mislabeled cases file is caught.
  const casesBySplit = new Map<string, CasesFixture>(
    splits.map((s) => [s, loadJson<CasesFixture>(`cases_${s}.json`)]),
  );
  validateFixtures(corpus, manifest, rubric, casesBySplit);

  const index = new RetrievalIndex(corpus.chunks, configFromManifest(manifest));
  const outDir = args.out ?? mkdtempSync(join(tmpdir(), "m21b-retrieval-"));
  mkdirSync(outDir, { recursive: true });

  for (const split of splits) {
    const cases = casesBySplit.get(split)!.cases;
    const result = evaluateSplit(index, cases, k, threshold);
    const report = buildReport(split, k, manifest, result, cases.length, threshold);

    const reportPath = join(outDir, `report_${split}_k${k}.json`);
    writeFileSync(reportPath, serializeReport(report), "utf-8");

    process.stdout.write(
      `\n=== split: ${split}  (k=${k}, cases=${cases.length}) ===\n`,
    );
    process.stdout.write(`${formatTable(k, report.metrics)}\n\n`);
    process.stdout.write(`${formatFailures(report.failures)}\n`);
    process.stdout.write(`\nreport written to: ${reportPath}\n`);
  }
}

main();
