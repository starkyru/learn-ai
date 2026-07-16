"""Tests for the route-hours calculator and CI check.

These drive the REAL functions in check_route_hours.py. Expected route totals
are HAND-DERIVED from a tiny synthetic fixture (written out by hand below), not
recomputed via the function under test, so the assertions catch a regression in
the summation logic. The failure tests corrupt the VISIBLE published table (the
same numbers a learner reads) and drive the real check to prove the gate fails —
a stale visible number cannot pass.

Run:
    uv run pytest scripts/curriculum/test_route_hours.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_route_hours as crh  # noqa: E402

# A tiny module_times-shaped fixture. Kept deliberately small so the expected
# route sums can be added up by hand.
SYNTHETIC = {
    "modules": {
        "a": {
            "exercise_only": [1, 2],
            "setup_debug": [0.5, 1],
            "provider_cloud": [0, 0],
            "capstone": [0, 0],
        },
        "b": {
            "exercise_only": [3, 4],
            "setup_debug": [1, 2],
            "provider_cloud": [0.25, 0.5],
            "capstone": [0, 0],
        },
        "c": {
            "exercise_only": [0, 0],
            "setup_debug": [0, 0],
            "provider_cloud": [1, 2],
            "capstone": [10, 20],
        },
    },
    "routes": {
        "r1": {"label": "R1", "modules": ["a", "b"]},
        "r2": {"label": "R2", "modules": ["a", "b", "c"]},
    },
}


def test_compute_route_totals_matches_hand_derived_sums():
    # r1 = a + b, added up by hand:
    #   exercise_only  1+3 .. 2+4   = 4 .. 6
    #   setup_debug    0.5+1 .. 1+2 = 1.5 .. 3
    #   provider_cloud 0+0.25 .. 0+0.5 = 0.25 .. 0.5
    #   capstone       0 .. 0
    assert crh.compute_route_totals(SYNTHETIC, "r1") == {
        "exercise_only": (4, 6),
        "setup_debug": (1.5, 3),
        "provider_cloud": (0.25, 0.5),
        "capstone": (0, 0),
    }
    # r2 = a + b + c; only provider_cloud and capstone change vs r1.
    assert crh.compute_route_totals(SYNTHETIC, "r2") == {
        "exercise_only": (4, 6),
        "setup_debug": (1.5, 3),
        "provider_cloud": (1.25, 2.5),
        "capstone": (10, 20),
    }


def test_compute_route_totals_rejects_unknown_route():
    with pytest.raises(KeyError):
        crh.compute_route_totals(SYNTHETIC, "does-not-exist")


def test_fmt_range_trims_trailing_zeros():
    assert crh.fmt_range(4, 6) == "4-6"
    assert crh.fmt_range(8.5, 16.0) == "8.5-16"
    assert crh.fmt_range(14.5, 25.5) == "14.5-25.5"
    assert crh.fmt_range(0, 0) == "0-0"
    assert crh.fmt_range(4.75, 9.5) == "4.75-9.5"


def test_normalise_range_accepts_dashes_and_bare_numbers():
    assert crh.normalise_range("114–153") == "114-153"  # en dash
    assert crh.normalise_range("114—153") == "114-153"  # em dash
    assert crh.normalise_range("28-52.5") == "28-52.5"  # ascii hyphen
    assert crh.normalise_range(" **0** ") == "0-0"  # bare number, bold, padded
    assert crh.normalise_range("abc") is None  # unparseable


def test_parse_published_table_reads_rows_and_lessons():
    text = (
        "intro\n\n"
        "| Route            | Lessons | Exercise-only | Setup/debug | Provider/cloud | Capstone |\n"
        "| ---------------- | ------- | ------------- | ----------- | -------------- | -------- |\n"
        "| **Core**         | 27      | 114–153       | 28–52.5     | 11–22          | 10–20    |\n"
        "| **Mini**         | 2       | 4–6           | 1–2         | 0              | 0        |\n"
        "\ntrailing prose\n"
    )
    table = crh.parse_published_table(text)
    assert table == {
        "Core": {
            "exercise_only": "114-153",
            "setup_debug": "28-52.5",
            "provider_cloud": "11-22",
            "capstone": "10-20",
            "lessons": 27,
        },
        "Mini": {
            "exercise_only": "4-6",
            "setup_debug": "1-2",
            "provider_cloud": "0-0",
            "capstone": "0-0",
            "lessons": 2,
        },
    }


def test_real_source_covers_every_lesson_and_is_valid():
    data = crh.load_data()  # raises DataError if a lesson is missing/malformed
    assert set(data["modules"]) == set(crh.EXPECTED_MODULE_IDS)
    assert set(data["routes"]) == {
        "core-app-builder",
        "ml-foundations",
        "agent-systems",
        "model-training",
    }


def test_real_repo_published_table_matches_source():
    data = crh.load_data()
    assert crh.check_published(data) == []


def test_cli_main_passes_on_real_repo():
    assert crh.main([]) == 0
    assert crh.main(["--report"]) == 0


def _write_docs_from_real(tmp_path: Path, mutate) -> tuple[Path, ...]:
    """Copy the real published docs into tmp_path, applying `mutate` to each."""
    out = []
    for src in crh.PUBLISHED_DOCS:
        text = src.read_text(encoding="utf-8")
        dst = tmp_path / src.name
        dst.write_text(mutate(text), encoding="utf-8")
        out.append(dst)
    return tuple(out)


def test_check_fails_when_a_visible_total_is_wrong(tmp_path):
    # The false-green guard: corrupt the VISIBLE table cell a learner reads (not
    # a hidden marker). The checker must catch it.
    docs = _write_docs_from_real(tmp_path, lambda t: t.replace("114–153", "999–153"))
    # Sanity: the substitution actually happened in the copies.
    assert any("999–153" in d.read_text(encoding="utf-8") for d in docs)

    errors = crh.check_published(crh.load_data(), docs)
    assert errors, "checker must report an error when a published total is wrong"
    assert any(
        "Core app-builder" in e and "exercise_only" in e and "999-153" in e for e in errors
    ), errors


def test_check_fails_when_lessons_count_is_wrong(tmp_path):
    docs = _write_docs_from_real(
        tmp_path, lambda t: t.replace("| **Core app-builder** | 27", "| **Core app-builder** | 99")
    )
    errors = crh.check_published(crh.load_data(), docs)
    assert any(
        "Core app-builder" in e and "Lessons published 99" in e and "source has 27" in e
        for e in errors
    ), errors


def test_cli_main_fails_when_table_wrong(tmp_path, monkeypatch):
    docs = _write_docs_from_real(tmp_path, lambda t: t.replace("11–22", "11–999"))
    monkeypatch.setattr(crh, "PUBLISHED_DOCS", docs)
    assert crh.main([]) == 1


def test_check_fails_when_a_route_row_is_missing(tmp_path):
    # Drop the whole ML foundations table row from the copies.
    def drop(text: str) -> str:
        return "\n".join(line for line in text.splitlines() if "| **ML foundations**" not in line)

    docs = _write_docs_from_real(tmp_path, drop)
    errors = crh.check_published(crh.load_data(), docs)
    assert any("missing table row for route 'ML foundations'" in e for e in errors), errors
