#!/usr/bin/env python3
"""Parse sugar balance CSVs into a dashboard payload (assets/data.js)."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMBINED = ROOT / "combined_df.csv"
OUT_JS = ROOT / "assets" / "data.js"
OUT_JSON = ROOT / "assets" / "data.json"

YEARS = ["2018/19", "2019/20", "2020/21", "2021/22", "2022/23", "May2023/24"]
YEAR_LABELS = {
    "2018/19": "2018/19",
    "2019/20": "2019/20",
    "2020/21": "2020/21",
    "2021/22": "2021/22",
    "2022/23": "2022/23",
    "May2023/24": "2023/24",
}
ACTIONS = ("production", "consumption", "export", "import", "ending")
DISPLAY_NAMES = {
    "Korea_South": "South Korea",
    "United_Arab_Emirates": "United Arab Emirates",
    "United_Kingdom": "United Kingdom",
    "United_States": "United States",
    "Costa_Rica": "Costa Rica",
    "El_Salvador": "El Salvador",
    "South_Africa": "South Africa",
    "Saudi_Arabia": "Saudi Arabia",
    "European_Union": "European Union",
}


def parse_number(raw: str) -> int:
    text = (raw or "").strip().replace(",", "").replace('"', "")
    if text == "":
        raise ValueError("empty numeric cell")
    return int(text)


def display_name(name: str) -> str:
    if name in DISPLAY_NAMES:
        return DISPLAY_NAMES[name]
    return name.replace("_", " ")


def load_combined(path: Path = COMBINED) -> dict:
    series: dict[str, dict[str, list[int | None]]] = defaultdict(
        lambda: {action: [None] * len(YEARS) for action in ACTIONS}
    )
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV is missing a header row")
        missing = [year for year in YEARS if year not in reader.fieldnames]
        if missing:
            raise ValueError(f"CSV is missing year columns: {missing}")
        for row in reader:
            name = (row.get("Name") or "").strip()
            action = (row.get("Action") or "").strip()
            if not name or action not in ACTIONS:
                raise ValueError(f"Unexpected row: {row}")
            for index, year in enumerate(YEARS):
                series[name][action][index] = parse_number(row[year])
    if "Total" not in series:
        raise ValueError("Combined CSV does not include a Total row")
    return dict(series)


def countries_for(series: dict) -> list[str]:
    names = [name for name in series if name not in {"Total"}]
    names.sort(key=lambda name: (name == "Other", display_name(name).lower()))
    return names


def value_at(series: dict, name: str, action: str, year_index: int) -> int | None:
    values = series.get(name, {}).get(action)
    if not values:
        return None
    return values[year_index]


def ranking(series: dict, action: str, year_index: int, limit: int | None = None) -> list[dict]:
    rows = []
    for name in countries_for(series):
        if name == "Other":
            continue
        amount = value_at(series, name, action, year_index)
        if amount is None:
            continue
        rows.append(
            {
                "id": name,
                "name": display_name(name),
                "value": amount,
            }
        )
    rows.sort(key=lambda row: (-row["value"], row["name"]))
    if limit is not None:
        return rows[:limit]
    return rows


def net_trade(series: dict, year_index: int) -> list[dict]:
    rows = []
    for name in countries_for(series):
        exports = value_at(series, name, "export", year_index)
        imports = value_at(series, name, "import", year_index)
        if exports is None and imports is None:
            continue
        export_value = exports or 0
        import_value = imports or 0
        rows.append(
            {
                "id": name,
                "name": display_name(name),
                "export": export_value,
                "import": import_value,
                "net": export_value - import_value,
            }
        )
    rows.sort(key=lambda row: (row["net"], row["name"]))
    return rows


def stock_changes(series: dict) -> list[dict]:
    start, end = 0, len(YEARS) - 1
    rows = []
    for name in countries_for(series):
        first = value_at(series, name, "ending", start)
        last = value_at(series, name, "ending", end)
        if first is None or last is None:
            continue
        rows.append(
            {
                "id": name,
                "name": display_name(name),
                "start": first,
                "end": last,
                "delta": last - first,
                "pct": None if first == 0 else (last - first) / first,
            }
        )
    rows.sort(key=lambda row: (row["delta"], row["name"]))
    return rows


def kpis_for_year(series: dict, year_index: int) -> dict:
    totals = series["Total"]
    production = totals["production"][year_index]
    consumption = totals["consumption"][year_index]
    exports = totals["export"][year_index]
    imports = totals["import"][year_index]
    ending = totals["ending"][year_index]
    prior = year_index - 1

    def delta(action: str) -> int | None:
        if prior < 0:
            return None
        return totals[action][year_index] - totals[action][prior]

    surplus = production - consumption
    stock_to_use = ending / consumption if consumption else None
    return {
        "year": YEARS[year_index],
        "label": YEAR_LABELS[YEARS[year_index]],
        "production": production,
        "consumption": consumption,
        "export": exports,
        "import": imports,
        "ending": ending,
        "surplus": surplus,
        "stockToUse": stock_to_use,
        "delta": {
            "production": delta("production"),
            "consumption": delta("consumption"),
            "export": delta("export"),
            "import": delta("import"),
            "ending": delta("ending"),
            "surplus": None if prior < 0 else surplus - (totals["production"][prior] - totals["consumption"][prior]),
            "stockToUse": None
            if prior < 0 or not totals["consumption"][prior]
            else stock_to_use - (totals["ending"][prior] / totals["consumption"][prior]),
        },
    }


def insights(series: dict, year_index: int) -> list[dict]:
    totals = series["Total"]
    production = totals["production"][year_index]
    consumption = totals["consumption"][year_index]
    ending = totals["ending"][year_index]
    exports = totals["export"][year_index]
    brazil_export = value_at(series, "Brazil", "export", year_index) or 0
    india_stocks = value_at(series, "India", "ending", year_index)
    india_start = value_at(series, "India", "ending", 0)
    top_producer = ranking(series, "production", year_index, 1)[0]
    return [
        {
            "id": "tightness",
            "title": "Stocks are drawing down",
            "body": (
                f"Ending stocks are {ending / 1000:.1f} million tonnes, "
                f"{(ending / totals['ending'][0] - 1) * 100:.0f}% versus 2018/19, "
                f"while consumption is at a series high."
            ),
        },
        {
            "id": "balance",
            "title": "Supply still covers use",
            "body": (
                f"World production of {production / 1000:.1f} Mt exceeds consumption "
                f"by {(production - consumption) / 1000:.1f} Mt in {YEAR_LABELS[YEARS[year_index]]}."
            ),
        },
        {
            "id": "brazil",
            "title": "Brazil dominates trade",
            "body": (
                f"Brazil ships {brazil_export / 1000:.1f} Mt, "
                f"{(brazil_export / exports) * 100:.0f}% of recorded world exports."
            ),
        },
        {
            "id": "india",
            "title": "India's buffer is shrinking",
            "body": (
                f"Indian ending stocks fall from {india_start / 1000:.1f} Mt to "
                f"{india_stocks / 1000:.1f} Mt across the window."
            ),
        },
        {
            "id": "leader",
            "title": f"{top_producer['name']} leads output",
            "body": (
                f"{top_producer['name']} produces {top_producer['value'] / 1000:.1f} Mt, "
                f"{(top_producer['value'] / production) * 100:.0f}% of the world total."
            ),
        },
    ]


def country_payload(series: dict, name: str) -> dict:
    row = series[name]
    latest = len(YEARS) - 1
    production = row["production"][latest]
    consumption = row["consumption"][latest]
    exports = row["export"][latest]
    imports = row["import"][latest]
    return {
        "id": name,
        "name": display_name(name),
        "series": row,
        "latest": {
            "production": production,
            "consumption": consumption,
            "export": exports,
            "import": imports,
            "ending": row["ending"][latest],
            "net": (exports or 0) - (imports or 0),
            "surplus": None
            if production is None or consumption is None
            else production - consumption,
        },
    }


def build_payload(series: dict) -> dict:
    country_ids = countries_for(series)
    kpis = [kpis_for_year(series, index) for index in range(len(YEARS))]
    return {
        "units": "1,000 metric tons",
        "unitShort": "kt",
        "sourceNote": (
            "Country-level sugar balance sheet, marketing years 2018/19 to 2023/24 "
            "(May estimate). Values are thousand metric tons."
        ),
        "years": YEARS,
        "yearLabels": [YEAR_LABELS[year] for year in YEARS],
        "actions": list(ACTIONS),
        "countries": [
            {"id": name, "name": display_name(name)} for name in country_ids
        ],
        "totals": series["Total"],
        "series": {name: series[name] for name in country_ids},
        "kpis": kpis,
        "insights": insights(series, len(YEARS) - 1),
        "stockChanges": stock_changes(series),
        "latestRankings": {
            action: ranking(series, action, len(YEARS) - 1, 12) for action in ACTIONS
        },
        "profiles": {name: country_payload(series, name) for name in country_ids},
        "netTradeLatest": net_trade(series, len(YEARS) - 1),
    }


def write_payload(payload: dict) -> None:
    OUT_JS.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2)
    OUT_JSON.write_text(encoded + "\n", encoding="utf-8")
    OUT_JS.write_text(
        "window.SUGAR_DATA = " + encoded + ";\n",
        encoding="utf-8",
    )


def main() -> None:
    series = load_combined()
    payload = build_payload(series)
    write_payload(payload)
    latest = payload["kpis"][-1]
    print(
        f"Wrote {OUT_JS.relative_to(ROOT)} and {OUT_JSON.relative_to(ROOT)} "
        f"({len(payload['countries'])} countries, {len(YEARS)} years)."
    )
    print(
        f"Latest {latest['label']}: production {latest['production']:,} kt, "
        f"consumption {latest['consumption']:,} kt, ending stocks {latest['ending']:,} kt."
    )


if __name__ == "__main__":
    main()
