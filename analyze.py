"""Sanity-check analysis for the agricultural-commodity dataset.

Loads the per-category CSVs, computes global totals per marketing year, and
saves a chart of world production vs. consumption. This doubles as the
environment "hello world": running it end to end exercises pandas, numpy and
matplotlib against the repository data.

Usage:
    python analyze.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless-safe backend
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
YEAR_COLUMNS = ["2018/19", "2019/20", "2020/21", "2021/22", "2022/23", "May2023/24"]
CATEGORIES = ["production", "consumption", "import", "export", "ending"]


def load_category(name: str) -> pd.DataFrame:
    """Load one category CSV and coerce the year columns to numbers."""
    df = pd.read_csv(ROOT / f"{name}_df.csv", thousands=",")
    for col in YEAR_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def main() -> None:
    frames = {name: load_category(name) for name in CATEGORIES}

    print("Rows loaded per category:")
    for name, df in frames.items():
        print(f"  {name:<12} {len(df):>3} countries")

    totals = pd.DataFrame(
        {name: df[YEAR_COLUMNS].sum() for name, df in frames.items()}
    )
    totals.index.name = "marketing_year"

    print("\nGlobal totals per marketing year (thousand metric tons):")
    print(totals.to_string())

    balance = totals["production"] - totals["consumption"]
    print("\nWorld production minus consumption:")
    print(balance.to_string())

    OUTPUT_DIR.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    totals["production"].plot(ax=ax, marker="o", label="Production")
    totals["consumption"].plot(ax=ax, marker="o", label="Consumption")
    ax.set_title("World Production vs. Consumption")
    ax.set_ylabel("Thousand metric tons")
    ax.set_xlabel("Marketing year")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    chart_path = OUTPUT_DIR / "production_vs_consumption.png"
    fig.savefig(chart_path, dpi=120)
    print(f"\nSaved chart to {chart_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
