#!/usr/bin/env python3
"""Static checks that the dashboard files are present and wired together."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class DashboardFileTests(unittest.TestCase):
    def test_index_loads_local_assets(self) -> None:
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        for asset in (
            "assets/styles.css",
            "assets/chart.umd.min.js",
            "assets/data.js",
            "assets/dashboard.js",
            "balance-chart",
            "rank-chart",
            "trade-chart",
            "stocks-chart",
            "country-chart",
        ):
            self.assertIn(asset, html)

    def test_generated_payload_is_valid_json(self) -> None:
        payload = json.loads((ROOT / "assets" / "data.json").read_text(encoding="utf-8"))
        self.assertEqual(len(payload["years"]), 6)
        self.assertIn("Brazil", payload["series"])
        js = (ROOT / "assets" / "data.js").read_text(encoding="utf-8")
        self.assertTrue(js.startswith("window.SUGAR_DATA = "))

    def test_chart_library_is_vendored(self) -> None:
        chart = (ROOT / "assets" / "chart.umd.min.js").read_text(encoding="utf-8")
        self.assertIn("Chart.js v4", chart)
        self.assertGreater((ROOT / "assets" / "chart.umd.min.js").stat().st_size, 50_000)


if __name__ == "__main__":
    unittest.main()
