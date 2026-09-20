#!/usr/bin/env python3
"""Data integrity tests for the sugar dashboard payload."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_data as prep  # noqa: E402


class ParseNumberTests(unittest.TestCase):
    def test_strips_commas(self) -> None:
        self.assertEqual(prep.parse_number("187,881"), 187881)

    def test_plain_integer(self) -> None:
        self.assertEqual(prep.parse_number("760"), 760)

    def test_rejects_empty(self) -> None:
        with self.assertRaises(ValueError):
            prep.parse_number("  ")


class CombinedDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.series = prep.load_combined()
        cls.payload = prep.build_payload(cls.series)

    def test_expected_year_columns(self) -> None:
        self.assertEqual(self.payload["years"], prep.YEARS)

    def test_world_totals_match_source_latest_year(self) -> None:
        totals = self.series["Total"]
        self.assertEqual(totals["production"][-1], 187881)
        self.assertEqual(totals["consumption"][-1], 180045)
        self.assertEqual(totals["export"][-1], 72104)
        self.assertEqual(totals["import"][-1], 59012)
        self.assertEqual(totals["ending"][-1], 33455)

    def test_brazil_is_top_exporter_in_latest_year(self) -> None:
        ranking = self.payload["latestRankings"]["export"]
        self.assertEqual(ranking[0]["id"], "Brazil")
        self.assertEqual(ranking[0]["value"], 32398)

    def test_india_is_top_consumer_in_latest_year(self) -> None:
        ranking = self.payload["latestRankings"]["consumption"]
        self.assertEqual(ranking[0]["id"], "India")
        self.assertEqual(ranking[0]["value"], 31000)
        self.assertNotIn("Other", [row["id"] for row in ranking])

    def test_stock_to_use_is_consumption_share(self) -> None:
        latest = self.payload["kpis"][-1]
        self.assertAlmostEqual(latest["stockToUse"], 33455 / 180045, places=6)

    def test_surplus_is_production_minus_consumption(self) -> None:
        latest = self.payload["kpis"][-1]
        self.assertEqual(latest["surplus"], 187881 - 180045)

    def test_country_list_excludes_world_total(self) -> None:
        ids = [row["id"] for row in self.payload["countries"]]
        self.assertNotIn("Total", ids)
        self.assertIn("Brazil", ids)
        self.assertIn("Other", ids)
        self.assertGreaterEqual(len(ids), 40)

    def test_display_names(self) -> None:
        self.assertEqual(prep.display_name("Korea_South"), "South Korea")
        self.assertEqual(prep.display_name("European_Union"), "European Union")

    def test_ending_stocks_declined_over_the_window(self) -> None:
        start = self.series["Total"]["ending"][0]
        end = self.series["Total"]["ending"][-1]
        self.assertLess(end, start)
        india = next(row for row in self.payload["stockChanges"] if row["id"] == "India")
        self.assertEqual(india["start"], 17614)
        self.assertEqual(india["end"], 5506)

    def test_net_trade_brazil_is_largest_exporter(self) -> None:
        net = self.payload["netTradeLatest"]
        brazil = next(row for row in net if row["id"] == "Brazil")
        self.assertEqual(brazil["net"], 32398)
        self.assertEqual(max(row["net"] for row in net), brazil["net"])

    def test_country_counts_match_component_files(self) -> None:
        actions = {
            "production": ROOT / "production_df.csv",
            "consumption": ROOT / "consumption_df.csv",
            "import": ROOT / "import_df.csv",
            "export": ROOT / "export_df.csv",
            "ending": ROOT / "ending_df.csv",
        }
        for action, path in actions.items():
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(handle)[1:]
            named = [line.split(",", 1)[0] for line in rows if line.strip()]
            named = [name for name in named if name not in {"Total"}]
            present = [
                country
                for country in self.payload["countries"]
                if self.series[country["id"]][action][-1] is not None
                or any(value is not None for value in self.series[country["id"]][action])
            ]
            self.assertEqual(len(named), len(present), msg=action)


if __name__ == "__main__":
    unittest.main()
