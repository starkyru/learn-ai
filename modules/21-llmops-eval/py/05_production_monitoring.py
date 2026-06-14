"""
Task 5 — Production monitoring  🟢

What this teaches:
  - In production, every LLM call writes a JSONL log entry (module 07 task 2
    shows how). This script aggregates those logs into a rolling report.
  - Key metrics to watch: latency (p50/p95), token usage, cost, error rate.
  - Alert thresholds: if a metric crosses a threshold, print a warning so an
    on-call engineer (or a Slack webhook) can act.
  - Rolling windows (last N minutes or last N entries) prevent stale averages
    from masking recent spikes.

How to run:
  # Point at the log file from module 07:
  uv run python modules/21-llmops-eval/py/05_production_monitoring.py \\
      --log-file modules/07-advanced-production/llm-calls.jsonl

  # Or generate a synthetic log for demo purposes:
  uv run python modules/21-llmops-eval/py/05_production_monitoring.py --demo

  # Watch mode (re-read the log every N seconds):
  uv run python modules/21-llmops-eval/py/05_production_monitoring.py \\
      --log-file modules/07-advanced-production/llm-calls.jsonl \\
      --watch --interval 10
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------------------
# Alert thresholds (override via CLI)
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLDS = {
    "p95_latency_ms": 5000,     # alert if p95 latency > 5 s
    "error_rate": 0.05,          # alert if error rate > 5 %
    "avg_cost_usd": 0.01,        # alert if avg cost per call > $0.01
    "total_cost_usd": 1.00,      # alert if session total > $1.00
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class LogEntry:
    id: str
    timestamp: str
    provider: str
    model: str
    latency_ms: float
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: float | None
    error: str | None


@dataclass
class MonitorReport:
    window_size: int                    # number of entries analysed
    start_time: str
    end_time: str
    error_rate: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    total_tokens: int
    total_cost_usd: float
    avg_cost_usd: float
    alerts: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Step 1 — Parse the JSONL log
# ---------------------------------------------------------------------------

def parse_log(path: Path, last_n: int | None = None) -> list[LogEntry]:
    """Read a JSONL log file and return a list of LogEntry objects.

    This file is written by module 07 task 2 (02_observability.py).
    Each line is a JSON object with at least: id, timestamp, latency_ms.

    TODO 1a: Open path; read line-by-line; parse each as JSON.
    TODO 1b: Map fields to LogEntry. Missing fields default to None/0.
    TODO 1c: If last_n is set, return only the last N entries.
    Handle missing files gracefully (return []).
    """
    raise NotImplementedError("TODO: implement parse_log")


# ---------------------------------------------------------------------------
# Step 2 — Compute percentile
# ---------------------------------------------------------------------------

def percentile(values: list[float], p: float) -> float:
    """Return the p-th percentile of values (0 < p <= 100).

    TODO 2: Sort values; compute index = (p/100) * (len-1) using linear
    interpolation between floor and ceil indices.
    Return 0.0 for empty input.
    """
    raise NotImplementedError("TODO: implement percentile")


# ---------------------------------------------------------------------------
# Step 3 — Build the report
# ---------------------------------------------------------------------------

def build_report(entries: list[LogEntry]) -> MonitorReport:
    """Aggregate entries into a MonitorReport.

    TODO 3a: Compute error_rate = errors / total (entries where error is not None).
    TODO 3b: Compute latency stats (avg, p50, p95) from latency_ms values.
    TODO 3c: Sum input_tokens + output_tokens for total_tokens.
    TODO 3d: Sum estimated_cost_usd for total_cost_usd; avg per call.
    TODO 3e: Set start_time/end_time from first/last entry timestamps.
    Return MonitorReport (alerts list starts empty).
    """
    raise NotImplementedError("TODO: implement build_report")


# ---------------------------------------------------------------------------
# Step 4 — Alert checking
# ---------------------------------------------------------------------------

def check_alerts(report: MonitorReport, thresholds: dict[str, float]) -> None:
    """Populate report.alerts based on threshold violations.

    TODO 4a: For each threshold key, compare report field:
             p95_latency_ms → report.p95_latency_ms
             error_rate     → report.error_rate
             avg_cost_usd   → report.avg_cost_usd
             total_cost_usd → report.total_cost_usd
    TODO 4b: If a threshold is exceeded, append a message to report.alerts:
             "[ALERT] p95_latency_ms=6234 exceeds threshold=5000"
    Modifies report in place.
    """
    raise NotImplementedError("TODO: implement check_alerts")


# ---------------------------------------------------------------------------
# Step 5 — Print the report
# ---------------------------------------------------------------------------

def print_report(report: MonitorReport) -> None:
    """Format and print the monitoring report to stdout.

    TODO 5: Print a section-based report:
            --- Production Monitoring Report ---
            Window: N entries (start → end)
            Latency:  avg=X  p50=Y  p95=Z ms
            Errors:   rate=X%
            Tokens:   total=X
            Cost:     avg=$X  total=$X
            Alerts (if any): [ALERT] ...
    """
    raise NotImplementedError("TODO: implement print_report")


# ---------------------------------------------------------------------------
# Demo — generate a synthetic JSONL log
# ---------------------------------------------------------------------------

def generate_demo_log(path: Path, n: int = 50) -> None:
    """Write N synthetic log entries to path for demo purposes.

    TODO 6: Generate N random entries with realistic latency (100–3000 ms),
    token counts (50–500), cost estimates, and occasional errors (5 %).
    Write as JSONL.
    """
    raise NotImplementedError("TODO: implement generate_demo_log")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="LLM production monitor")
    parser.add_argument("--log-file", type=Path, default=None,
                        help="Path to JSONL log file (module 07 output)")
    parser.add_argument("--demo", action="store_true",
                        help="Generate a synthetic log and analyse it")
    parser.add_argument("--last-n", type=int, default=None,
                        help="Analyse only the last N entries")
    parser.add_argument("--watch", action="store_true",
                        help="Re-read and report every --interval seconds")
    parser.add_argument("--interval", type=int, default=10,
                        help="Watch interval in seconds (default 10)")
    args = parser.parse_args()

    if args.demo:
        demo_path = REPO_ROOT / "modules" / "21-llmops-eval" / "data" / "demo-calls.jsonl"
        print(f"Generating synthetic log: {demo_path}")
        generate_demo_log(demo_path, n=50)
        log_path = demo_path
    elif args.log_file:
        log_path = args.log_file
    else:
        parser.error("Provide --log-file <path> or --demo.")

    def run_once() -> None:
        entries = parse_log(log_path, last_n=args.last_n)
        if not entries:
            print(f"No entries found in {log_path}")
            return
        report = build_report(entries)
        check_alerts(report, DEFAULT_THRESHOLDS)
        print_report(report)

    if args.watch:
        print(f"Watching {log_path} every {args.interval}s. Ctrl-C to stop.\n")
        try:
            while True:
                run_once()
                print()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        run_once()


if __name__ == "__main__":
    main()
