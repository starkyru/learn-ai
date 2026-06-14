/**
 * Task 5 — Production monitoring  🟢
 *
 * What this teaches:
 *   - Aggregate JSONL logs from module 07 into a rolling report.
 *   - Key metrics: latency (p50/p95), token usage, cost, error rate.
 *   - Alert thresholds: if a metric exceeds a threshold, flag it.
 *   - Rolling windows (last N entries) prevent stale averages.
 *
 * How to run:
 *   pnpm tsx modules/21-llmops-eval/ts/05-production-monitoring.ts \
 *       --log-file modules/07-advanced-production/llm-calls.jsonl
 *
 *   pnpm tsx modules/21-llmops-eval/ts/05-production-monitoring.ts --demo
 *
 *   pnpm tsx modules/21-llmops-eval/ts/05-production-monitoring.ts \
 *       --log-file modules/07-advanced-production/llm-calls.jsonl \
 *       --watch --interval 10
 */

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../../");

const DEFAULT_THRESHOLDS = {
  p95_latency_ms: 5000,
  error_rate: 0.05,
  avg_cost_usd: 0.01,
  total_cost_usd: 1.0,
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LogEntry {
  id: string;
  timestamp: string;
  provider: string;
  model: string;
  latency_ms: number;
  input_tokens: number | null;
  output_tokens: number | null;
  estimated_cost_usd: number | null;
  error: string | null;
}

interface MonitorReport {
  window_size: number;
  start_time: string;
  end_time: string;
  error_rate: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_cost_usd: number;
  alerts: string[];
}

// ---------------------------------------------------------------------------
// Step 1 — Parse the JSONL log
// ---------------------------------------------------------------------------

/**
 * Read a JSONL file and return LogEntry[].
 *
 * TODO 1a: readFileSync if exists; split on '\n'; filter blanks.
 * TODO 1b: JSON.parse each line; map to LogEntry.
 * TODO 1c: If lastN set, return last N entries.
 * Return [] for missing files.
 */
function parseLog(path: string, lastN?: number): LogEntry[] {
  // TODO: implement parseLog
  throw new Error("TODO: implement parseLog");
}

// ---------------------------------------------------------------------------
// Step 2 — Percentile
// ---------------------------------------------------------------------------

/**
 * Return the p-th percentile of values (0 < p <= 100).
 *
 * TODO 2: Sort values; linear interpolation between floor/ceil indices.
 * Return 0 for empty input.
 */
function percentile(values: number[], p: number): number {
  // TODO: implement percentile
  throw new Error("TODO: implement percentile");
}

// ---------------------------------------------------------------------------
// Step 3 — Build report
// ---------------------------------------------------------------------------

/**
 * Aggregate entries into a MonitorReport.
 *
 * TODO 3a: error_rate = entries with error / total.
 * TODO 3b: Latency stats from latency_ms.
 * TODO 3c: total_tokens = sum(input + output).
 * TODO 3d: total_cost_usd, avg_cost_usd.
 * TODO 3e: start_time, end_time from first/last entries.
 * Return MonitorReport with alerts: [].
 */
function buildReport(entries: LogEntry[]): MonitorReport {
  // TODO: implement buildReport
  throw new Error("TODO: implement buildReport");
}

// ---------------------------------------------------------------------------
// Step 4 — Alert checking
// ---------------------------------------------------------------------------

/**
 * Populate report.alerts based on threshold violations.
 *
 * TODO 4: For each threshold key, compare the matching report field.
 *         Push "[ALERT] <metric>=<value> exceeds threshold=<t>" strings.
 * Modifies report in place.
 */
function checkAlerts(
  report: MonitorReport,
  thresholds: typeof DEFAULT_THRESHOLDS,
): void {
  // TODO: implement checkAlerts
  throw new Error("TODO: implement checkAlerts");
}

// ---------------------------------------------------------------------------
// Step 5 — Print report
// ---------------------------------------------------------------------------

/**
 * Print a formatted monitoring report.
 *
 * TODO 5: Print sections: window, latency, errors, tokens, cost, alerts.
 */
function printReport(report: MonitorReport): void {
  // TODO: implement printReport
  throw new Error("TODO: implement printReport");
}

// ---------------------------------------------------------------------------
// Demo — generate synthetic log
// ---------------------------------------------------------------------------

/**
 * Write N synthetic JSONL log entries to path.
 *
 * TODO 6: Random latency 100–3000 ms, token counts 50–500,
 *         ~5% error rate, cost estimates. Write as JSONL.
 */
function generateDemoLog(path: string, n = 50): void {
  // TODO: implement generateDemoLog
  throw new Error("TODO: implement generateDemoLog");
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

function parseArgs(): {
  logFile: string | null;
  demo: boolean;
  lastN: number | undefined;
  watch: boolean;
  interval: number;
} {
  const argv = process.argv.slice(2);
  let logFile: string | null = null;
  let demo = false;
  let lastN: number | undefined;
  let watch = false;
  let interval = 10;

  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--log-file" && argv[i + 1]) logFile = argv[++i];
    if (argv[i] === "--demo") demo = true;
    if (argv[i] === "--last-n" && argv[i + 1]) lastN = parseInt(argv[++i], 10);
    if (argv[i] === "--watch") watch = true;
    if (argv[i] === "--interval" && argv[i + 1]) interval = parseInt(argv[++i], 10);
  }
  return { logFile, demo, lastN, watch, interval };
}

async function main(): Promise<void> {
  const { logFile, demo, lastN, watch, interval } = parseArgs();

  let logPath: string;

  if (demo) {
    logPath = resolve(REPO_ROOT, "modules/21-llmops-eval/data/demo-calls.jsonl");
    console.log(`Generating synthetic log: ${logPath}`);
    generateDemoLog(logPath, 50);
  } else if (logFile) {
    logPath = logFile;
  } else {
    console.error("Provide --log-file <path> or --demo.");
    process.exit(1);
  }

  const runOnce = () => {
    const entries = parseLog(logPath, lastN);
    if (!entries.length) {
      console.log(`No entries found in ${logPath}`);
      return;
    }
    const report = buildReport(entries);
    checkAlerts(report, DEFAULT_THRESHOLDS);
    printReport(report);
  };

  if (watch) {
    console.log(`Watching ${logPath} every ${interval}s. Ctrl-C to stop.\n`);
    runOnce();
    setInterval(runOnce, interval * 1000);
  } else {
    runOnce();
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
