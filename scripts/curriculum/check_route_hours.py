"""Route-hours calculator and CI check.

Reads the single machine-readable module-time source
(`scripts/curriculum/module_times.json`), sums each learning route's time
budget per category (exercise_only, setup_debug, provider_cloud, capstone),
and verifies that the totals **a learner actually sees** — the visible
route-hours table published in `CURRICULUM.md` and `README.md` — match what the
source computes. There is no hidden machine-readable marker: the checked
artifact is the same table the learner reads, so a stale visible number cannot
pass the gate while an invisible marker silently stays correct.

Usage:
    uv run python scripts/curriculum/check_route_hours.py            # check, exit 0/1
    uv run python scripts/curriculum/check_route_hours.py --report   # print the table to embed

The published table is a normal markdown table, keyed by each route's label,
e.g.:

    | Route                | Lessons | Exercise-only | Setup/debug | Provider/cloud | Capstone |
    | -------------------- | ------- | ------------- | ----------- | -------------- | -------- |
    | **Core app-builder** | 27      | 114-153       | 28-52.5     | 11-22          | 10-20    |

Cells may use an en/em dash or a bare single number (`0` == `0-0`); the checker
normalises both before comparing. The Lessons column is checked against the
route's module count too.

This file is a runnable script, not a pytest suite (pytest's testpaths cover
modules/ and packages/, so scripts/ is never auto-collected).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "scripts" / "curriculum" / "module_times.json"
PUBLISHED_DOCS = (ROOT / "CURRICULUM.md", ROOT / "README.md")

CATEGORIES = ("exercise_only", "setup_debug", "provider_cloud", "capstone")

# Every lesson in the course map (24 numbered modules + 13 companions/deep
# dives). The source must cover all of them so no lesson is silently dropped.
EXPECTED_MODULE_IDS = frozenset(
    [f"{n:02d}" for n in range(24)]
    + ["01b", "01c", "01d", "01e", "01f", "05b", "06b", "06c", "06d", "07b", "13b", "20b", "21b"]
)

# Visible table header cell (lowercased) -> category key. The table is located by
# requiring a header row that carries the first and last of these.
COLUMN_TO_CATEGORY = {
    "exercise-only": "exercise_only",
    "setup/debug": "setup_debug",
    "provider/cloud": "provider_cloud",
    "capstone": "capstone",
}

_RANGE_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)?-[0-9]+(?:\.[0-9]+)?$")


class DataError(Exception):
    """Raised when module_times.json is structurally invalid."""


def load_data(path: str | Path = DATA_PATH) -> dict:
    """Load and structurally validate the module-time source."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate_data(data)
    if errors:
        raise DataError("; ".join(errors))
    return data


def validate_data(data: dict) -> list[str]:
    """Return a list of structural problems (empty means valid)."""
    errors: list[str] = []
    modules = data.get("modules")
    routes = data.get("routes")
    if not isinstance(modules, dict) or not isinstance(routes, dict):
        return ["module_times.json must have object 'modules' and 'routes'"]

    ids = set(modules)
    missing = EXPECTED_MODULE_IDS - ids
    extra = ids - EXPECTED_MODULE_IDS
    if missing:
        errors.append(f"modules missing from source: {sorted(missing)}")
    if extra:
        errors.append(f"unknown module ids in source: {sorted(extra)}")

    for mid, entry in modules.items():
        for cat in CATEGORIES:
            rng = entry.get(cat)
            if (
                not isinstance(rng, list)
                or len(rng) != 2
                or not all(isinstance(x, (int, float)) for x in rng)
            ):
                errors.append(f"module {mid}: {cat} must be a [min, max] number pair")
                continue
            lo, hi = rng
            if lo < 0 or hi < 0 or lo > hi:
                errors.append(f"module {mid}: {cat} range {rng} must satisfy 0 <= min <= max")

    labels: dict[str, str] = {}
    for route, spec in routes.items():
        route_modules = spec.get("modules") if isinstance(spec, dict) else None
        if not isinstance(route_modules, list) or not route_modules:
            errors.append(f"route {route}: 'modules' must be a non-empty list")
            continue
        unknown = [m for m in route_modules if m not in modules]
        if unknown:
            errors.append(f"route {route}: references unknown modules {unknown}")
        if len(set(route_modules)) != len(route_modules):
            errors.append(f"route {route}: contains duplicate modules")
        label = spec.get("label")
        if not isinstance(label, str) or not label.strip():
            errors.append(f"route {route}: 'label' must be a non-empty string")
        elif label in labels:
            errors.append(f"route {route}: label {label!r} collides with route {labels[label]!r}")
        else:
            labels[label] = route

    return errors


def compute_route_totals(data: dict, route: str) -> dict[str, tuple[float, float]]:
    """Sum a route's per-category [min, max] budgets across its modules.

    Returns a mapping of category -> (min_total, max_total) in hours.
    """
    routes = data["routes"]
    if route not in routes:
        raise KeyError(f"unknown route: {route}")
    modules = data["modules"]
    totals = {cat: [0.0, 0.0] for cat in CATEGORIES}
    for mid in routes[route]["modules"]:
        entry = modules[mid]
        for cat in CATEGORIES:
            lo, hi = entry[cat]
            totals[cat][0] += lo
            totals[cat][1] += hi
    return {cat: (round(v[0], 2), round(v[1], 2)) for cat, v in totals.items()}


def fmt_num(x: float) -> str:
    """Format an hour value: drop trailing zeros (8.50 -> '8.5', 8.00 -> '8')."""
    return f"{x:.2f}".rstrip("0").rstrip(".")


def fmt_range(lo: float, hi: float) -> str:
    """Canonical 'min-max' string for a range."""
    return f"{fmt_num(lo)}-{fmt_num(hi)}"


def _split_row(line: str) -> list[str]:
    """Split a markdown table row '| a | b |' into ['a', 'b'] (trimmed)."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    """True for a '| --- | :--: |' separator row (only dashes/colons/spaces)."""
    nonempty = [c for c in cells if c]
    return bool(nonempty) and all(re.fullmatch(r"[-: ]+", c) for c in nonempty)


def normalise_range(cell: str) -> str | None:
    """Normalise a visible cell to canonical 'min-max', or None if unparseable.

    Accepts an en/em dash as the range separator and a bare single number
    (`0` -> `0-0`), so the human-facing table can use typographic dashes.
    """
    s = cell.strip().strip("*").strip()
    s = s.replace("–", "-").replace("—", "-")  # en dash, em dash
    s = s.replace(" ", "")
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", s):
        s = f"{s}-{s}"
    return s if _RANGE_RE.fullmatch(s) else None


def parse_published_table(text: str) -> dict[str, dict[str, object]]:
    """Parse the visible route-hours table.

    Returns {label: {"lessons": int|None, category: 'min-max'|None, ...}}. Only
    the first table whose header carries the route-hours columns is read.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        lowered = line.lower()
        if not (
            line.lstrip().startswith("|") and "exercise-only" in lowered and "capstone" in lowered
        ):
            continue
        header = [c.lower() for c in _split_row(line)]
        col_cat = {
            idx: COLUMN_TO_CATEGORY[name]
            for idx, name in enumerate(header)
            if name in COLUMN_TO_CATEGORY
        }
        label_idx = header.index("route") if "route" in header else 0
        lessons_idx = header.index("lessons") if "lessons" in header else None

        rows: dict[str, dict[str, object]] = {}
        for row_line in lines[i + 1 :]:
            if not row_line.lstrip().startswith("|"):
                break  # table ended
            cells = _split_row(row_line)
            if _is_separator_row(cells):
                continue
            if label_idx >= len(cells):
                continue
            label = cells[label_idx].strip().strip("*").strip()
            if not label:
                continue
            entry: dict[str, object] = {
                cat: (normalise_range(cells[idx]) if idx < len(cells) else None)
                for idx, cat in col_cat.items()
            }
            if lessons_idx is not None and lessons_idx < len(cells):
                raw = cells[lessons_idx].strip().strip("*").strip()
                entry["lessons"] = int(raw) if raw.isdigit() else None
            rows[label] = entry
        return rows
    return {}


def check_published(data: dict, docs: tuple[Path, ...] | None = None) -> list[str]:
    """Compare the visible published table against computed totals.

    Verifies, per route and per doc: the Lessons count matches the route's module
    count, and every category range matches the source-computed total. Also flags
    a missing table, a missing route row, or a row for an unknown route.
    """
    if docs is None:
        docs = PUBLISHED_DOCS
    errors: list[str] = []
    label_to_route = {spec["label"]: route for route, spec in data["routes"].items()}
    expected: dict[str, dict[str, str]] = {}
    for route in data["routes"]:
        totals = compute_route_totals(data, route)
        expected[route] = {cat: fmt_range(*totals[cat]) for cat in CATEGORIES}

    for doc in docs:
        if not doc.exists():
            errors.append(f"{doc.name}: file not found")
            continue
        table = parse_published_table(doc.read_text(encoding="utf-8"))
        if not table:
            errors.append(f"{doc.name}: no route-hours table found")
            continue
        for label, route in label_to_route.items():
            if label not in table:
                errors.append(f"{doc.name}: missing table row for route '{label}'")
                continue
            published = table[label]
            want_lessons = len(data["routes"][route]["modules"])
            got_lessons = published.get("lessons")
            if got_lessons is None:
                errors.append(f"{doc.name}: route '{label}' has a missing/invalid Lessons count")
            elif got_lessons != want_lessons:
                errors.append(
                    f"{doc.name}: route '{label}' Lessons published {got_lessons}, "
                    f"source has {want_lessons}"
                )
            for cat in CATEGORIES:
                want = expected[route][cat]
                got = published.get(cat)
                if got is None:
                    errors.append(
                        f"{doc.name}: route '{label}' table cell for '{cat}' is missing/unparseable"
                    )
                elif got != want:
                    errors.append(
                        f"{doc.name}: route '{label}' {cat} published {got}, source says {want}"
                    )
        for label in table:
            if label not in label_to_route:
                errors.append(f"{doc.name}: table row for unknown route '{label}'")
    return errors


def build_report(data: dict) -> str:
    """Emit the exact visible table (rows generated from the source) to embed."""
    header = "| Route | Lessons | Exercise-only | Setup/debug | Provider/cloud | Capstone |"
    sep = "| --- | --- | --- | --- | --- | --- |"
    lines: list[str] = ["Route hours (computed from module_times.json):", "", header, sep]
    for route, spec in data["routes"].items():
        totals = compute_route_totals(data, route)
        cats = " | ".join(fmt_range(*totals[cat]) for cat in CATEGORIES)
        lines.append(f"| **{spec['label']}** | {len(spec['modules'])} | {cats} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(DATA_PATH), help="path to module_times.json")
    parser.add_argument(
        "--report",
        action="store_true",
        help="print the route-hours table generated from the source, then exit 0",
    )
    args = parser.parse_args(argv)

    try:
        data = load_data(args.json)
    except (OSError, json.JSONDecodeError, DataError) as exc:
        print(f"error loading {args.json}: {exc}", file=sys.stderr)
        return 2

    if args.report:
        print(build_report(data))
        return 0

    errors = check_published(data)
    if errors:
        print("Route-hours check FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("Route-hours check passed: the published table matches module_times.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
