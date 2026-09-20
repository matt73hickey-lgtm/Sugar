#!/usr/bin/env python3
"""Sanity checks for the sugar balance CSVs and generated infographic."""

from __future__ import annotations

import csv
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import build_infographic as builder  # noqa: E402

YEARS = ["2018/19", "2019/20", "2020/21", "2021/22", "2022/23", "May2023/24"]
ACTIONS = {"production", "consumption", "export", "import", "ending"}


class CombinedDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = builder.load_combined()

    def test_combined_has_expected_shape(self) -> None:
        self.assertGreaterEqual(len(self.rows), 100)
        self.assertTrue(ACTIONS.issubset({row["Action"] for row in self.rows}))
        names = {row["Name"] for row in self.rows}
        self.assertIn("Total", names)
        self.assertIn("Brazil", names)
        self.assertIn("India", names)

    def test_world_totals_match_known_2023_24(self) -> None:
        totals = builder.totals_by_year(self.rows)
        self.assertEqual(totals["production"]["May2023/24"], 187881)
        self.assertEqual(totals["consumption"]["May2023/24"], 180045)
        self.assertEqual(totals["ending"]["May2023/24"], 33455)
        self.assertEqual(totals["export"]["May2023/24"], 72104)
        self.assertEqual(totals["import"]["May2023/24"], 59012)

    def test_stocks_drew_down_over_sample(self) -> None:
        totals = builder.totals_by_year(self.rows)
        self.assertLess(totals["ending"]["May2023/24"], totals["ending"]["2018/19"])

    def test_action_files_are_ranked_slices(self) -> None:
        for action, filename in builder.ACTION_FILES.items():
            path = ROOT / filename
            with path.open(newline="", encoding="utf-8") as handle:
                slice_rows = list(csv.DictReader(handle))
            self.assertTrue(slice_rows)
            self.assertEqual({row["Action"] for row in slice_rows}, {action})
            self.assertEqual(slice_rows[-1]["Name"], "Total")
            combined_action = [row for row in self.rows if row["Action"] == action]
            self.assertEqual(len(slice_rows), len(combined_action))

    def test_only_four_markets_report_every_flow(self) -> None:
        by_name = builder.coverage(self.rows)
        complete = {name for name, actions in by_name.items() if actions == ACTIONS}
        self.assertEqual(complete, {"China", "European_Union", "India", "Indonesia"})


class InfographicBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.check_call(
            [sys.executable, str(ROOT / "scripts" / "build_infographic.py")],
            cwd=ROOT,
        )
        cls.html = (ROOT / "infographic.html").read_text(encoding="utf-8")

    def test_infographic_contains_headline_figures(self) -> None:
        for snippet in (
            "187.9",
            "180.0",
            "33.5",
            "combined_df.csv",
            "production_df.csv",
            "The cupboard is emptying",
            "China, European Union, India, Indonesia",
        ):
            self.assertIn(snippet, self.html)

    def test_infographic_is_self_contained(self) -> None:
        self.assertIn("<!DOCTYPE html>", self.html)
        self.assertIn('id="infographic-data"', self.html)
        self.assertNotIn("assets/", self.html)


if __name__ == "__main__":
    unittest.main()
