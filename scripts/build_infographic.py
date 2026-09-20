#!/usr/bin/env python3
"""Build a self-contained HTML infographic from the sugar balance CSVs."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMBINED = ROOT / "combined_df.csv"
OUTPUT = ROOT / "infographic.html"

YEARS = ["2018/19", "2019/20", "2020/21", "2021/22", "2022/23", "May2023/24"]
YEAR_LABELS = ["2018/19", "2019/20", "2020/21", "2021/22", "2022/23", "2023/24"]
ACTIONS = ("production", "consumption", "export", "import", "ending")
ACTION_FILES = {
    "production": "production_df.csv",
    "consumption": "consumption_df.csv",
    "export": "export_df.csv",
    "import": "import_df.csv",
    "ending": "ending_df.csv",
}
COLORS = {
    "production": "#8fce72",
    "consumption": "#7eb8d4",
    "export": "#3fc1b0",
    "import": "#e07a5f",
    "ending": "#e0c36a",
}


def parse_num(value: str) -> int:
    return int(str(value).replace(",", "").replace('"', "").strip())


def pretty_name(name: str) -> str:
    return name.replace("_", " ")


def fmt_int(n: int) -> str:
    return f"{n:,}"


def fmt_mt(thousand_mt: int, digits: int = 1) -> str:
    return f"{thousand_mt / 1000:.{digits}f}"


def load_combined() -> list[dict[str, str]]:
    with COMBINED.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def totals_by_year(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for row in rows:
        if row["Name"] != "Total":
            continue
        out[row["Action"]] = {year: parse_num(row[year]) for year in YEARS}
    return out


def coverage(rows: list[dict[str, str]]) -> dict[str, set[str]]:
    by_name: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row["Name"] in {"Total", "Other"}:
            continue
        by_name[row["Name"]].add(row["Action"])
    return dict(by_name)


def ranked(rows: list[dict[str, str]], action: str, year: str, n: int = 5) -> list[tuple[str, int]]:
    subset = [
        (pretty_name(row["Name"]), parse_num(row[year]))
        for row in rows
        if row["Action"] == action and row["Name"] not in {"Total", "Other"}
    ]
    subset.sort(key=lambda item: item[1], reverse=True)
    return subset[:n]


def bar_rows(items: list[tuple[str, int]], color: str) -> str:
    maximum = max(value for _, value in items) if items else 1
    html = []
    for name, value in items:
        width = max(8, round(100 * value / maximum))
        html.append(
            f"""
            <div class="hbar">
              <span class="hbar-name">{name}</span>
              <span class="hbar-track"><span class="hbar-fill" style="width:{width}%;background:{color}"></span></span>
              <span class="hbar-val">{fmt_mt(value)}</span>
            </div>"""
        )
    return "".join(html)


def stock_chart(ending: dict[str, int]) -> str:
    values = [ending[year] for year in YEARS]
    maximum = max(values)
    width, height = 640, 168
    pad_l, pad_r, pad_t, pad_b = 8, 8, 18, 28
    inner_w = width - pad_l - pad_r
    inner_h = height - pad_t - pad_b
    step = inner_w / (len(values) - 1)
    points = []
    for i, value in enumerate(values):
        x = pad_l + i * step
        y = pad_t + inner_h * (1 - value / maximum)
        points.append((x, y, value))
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
    area = f"{pad_l:.1f},{pad_t + inner_h:.1f} " + polyline + f" {pad_l + inner_w:.1f},{pad_t + inner_h:.1f}"
    circles = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="#e0c36a" />'
        f'<text x="{x:.1f}" y="{y - 10:.1f}" text-anchor="middle" class="chart-num">{fmt_mt(value)}</text>'
        for x, y, value in points
    )
    labels = "".join(
        f'<text x="{x:.1f}" y="{height - 6}" text-anchor="middle" class="chart-axis">{label}</text>'
        for (x, _, _), label in zip(points, YEAR_LABELS)
    )
    return f"""
    <svg class="spark" viewBox="0 0 {width} {height}" role="img" aria-label="Ending stocks falling from 52.8 to 33.5 million tonnes">
      <polygon points="{area}" fill="rgba(224,195,106,0.16)" />
      <polyline points="{polyline}" fill="none" stroke="#e0c36a" stroke-width="3" />
      {circles}
      {labels}
    </svg>"""


def balance_chart(totals: dict[str, dict[str, int]]) -> str:
    prod = [totals["production"][year] for year in YEARS]
    cons = [totals["consumption"][year] for year in YEARS]
    maximum = max(prod + cons)
    group_w = 84
    width = 36 + group_w * len(YEARS)
    height = 210
    pad_t, pad_b = 16, 36
    inner_h = height - pad_t - pad_b
    bars = []
    labels = []
    for i, label in enumerate(YEAR_LABELS):
        x0 = 24 + i * group_w
        ph = inner_h * prod[i] / maximum
        ch = inner_h * cons[i] / maximum
        bars.append(
            f'<rect x="{x0}" y="{pad_t + inner_h - ph:.1f}" width="28" height="{ph:.1f}" rx="4" fill="#8fce72" />'
            f'<rect x="{x0 + 32}" y="{pad_t + inner_h - ch:.1f}" width="28" height="{ch:.1f}" rx="4" fill="#7eb8d4" />'
        )
        labels.append(
            f'<text x="{x0 + 30}" y="{height - 10}" text-anchor="middle" class="chart-axis">{label}</text>'
        )
    return f"""
    <svg class="spark" viewBox="0 0 {width} {height}" role="img" aria-label="World production versus consumption">
      {''.join(bars)}
      {''.join(labels)}
    </svg>"""


def coverage_pills(by_name: dict[str, set[str]]) -> str:
    buckets = {1: [], 2: [], 3: [], 4: [], 5: []}
    for name, actions in by_name.items():
        buckets[len(actions)].append(pretty_name(name))
    for names in buckets.values():
        names.sort()
    complete = ", ".join(buckets[5])
    specialists = ", ".join(buckets[1])
    return buckets, complete, specialists


def build_html(rows: list[dict[str, str]]) -> str:
    totals = totals_by_year(rows)
    by_name = coverage(rows)
    latest = YEARS[-1]
    first = YEARS[0]
    prod = totals["production"][latest]
    cons = totals["consumption"][latest]
    exp = totals["export"][latest]
    imp = totals["import"][latest]
    end = totals["ending"][latest]
    end0 = totals["ending"][first]
    surplus = prod - cons
    stu = 100 * end / cons
    stu0 = 100 * end0 / totals["consumption"][first]
    stock_drop = 100 * (end - end0) / end0
    named = len(by_name)
    buckets, complete, specialists = coverage_pills(by_name)
    file_rows = {
        "combined_df.csv": len(rows),
        **{
            filename: sum(1 for row in rows if row["Action"] == action)
            for action, filename in ACTION_FILES.items()
        },
    }
    brazil_share = 100 * next(v for n, v in ranked(rows, "production", latest, 1)) / prod
    india_cons_share = 100 * next(v for n, v in ranked(rows, "consumption", latest, 1)) / cons
    brazil_export_share = 100 * next(v for n, v in ranked(rows, "export", latest, 1)) / exp

    payload = {
        "years": YEAR_LABELS,
        "production": [totals["production"][y] for y in YEARS],
        "consumption": [totals["consumption"][y] for y in YEARS],
        "ending": [totals["ending"][y] for y in YEARS],
    }

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Sugar — codebase infographic</title>
  <meta name="description" content="Visual map of the Sugar repository: six CSV files, five balance-sheet flows, and the 2018/19–2023/24 world sugar story." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,650&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet" />
  <style>
    :root {{
      --bg: #0c100e;
      --card: #17201b;
      --card-2: #1d2822;
      --line: rgba(224, 195, 106, 0.16);
      --gold: #e0c36a;
      --cream: #f4ecd8;
      --muted: #9aa392;
      --prod: #8fce72;
      --cons: #7eb8d4;
      --export: #3fc1b0;
      --import: #e07a5f;
      --stocks: #e0c36a;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      background:
        radial-gradient(1100px 480px at 8% -8%, rgba(224,195,106,0.14), transparent 55%),
        radial-gradient(900px 400px at 100% 0%, rgba(63,193,176,0.08), transparent 50%),
        var(--bg);
      color: var(--cream);
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
    }}
    body {{ line-height: 1.45; }}
    .page {{ width: min(1180px, calc(100% - 28px)); margin: 0 auto; padding: 32px 0 72px; }}
    .eyebrow {{ margin: 0 0 8px; letter-spacing: 0.2em; text-transform: uppercase; font-size: 11px; color: var(--gold); }}
    h1, h2, .kpi-value, .poster-stat {{ font-family: "Fraunces", Georgia, serif; font-weight: 550; }}
    h1 {{ margin: 0; font-size: clamp(48px, 8vw, 84px); letter-spacing: -0.04em; line-height: 0.9; }}
    h2 {{ margin: 0 0 6px; font-size: 26px; letter-spacing: -0.03em; }}
    .lede {{ margin: 12px 0 0; max-width: 46rem; color: #cfc6ae; font-size: 17px; }}
    .hero {{ display: grid; grid-template-columns: 1.4fr 0.8fr; gap: 28px; align-items: end; margin-bottom: 28px; }}
    .hero-aside {{
      border: 1px solid var(--line); background: var(--card); border-radius: 22px; padding: 18px 20px;
    }}
    .hero-aside strong {{ display: block; font-size: 28px; font-family: "Fraunces", Georgia, serif; color: var(--gold); }}
    .kpis {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 16px; }}
    .kpi {{
      background: var(--card); border: 1px solid var(--line); border-radius: 20px; padding: 16px 16px 14px;
    }}
    .kpi-label {{ margin: 0; color: var(--muted); font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; }}
    .kpi-value {{ margin: 6px 0 0; font-size: 30px; }}
    .kpi-note {{ margin: 4px 0 0; color: var(--muted); font-size: 12px; }}
    .grid {{ display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 14px; margin-bottom: 14px; }}
    .grid-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 14px; }}
    .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }}
    .card {{
      background: var(--card); border: 1px solid var(--line); border-radius: 22px; padding: 20px 22px 18px;
    }}
    .muted {{ color: var(--muted); margin: 0 0 14px; }}
    .files {{ display: grid; gap: 8px; }}
    .file {{
      display: grid; grid-template-columns: 18px 1fr auto; gap: 10px; align-items: center;
      background: var(--card-2); border-radius: 14px; padding: 10px 12px;
    }}
    .dot {{ width: 10px; height: 10px; border-radius: 50%; }}
    .file code {{ font-size: 13px; color: var(--cream); }}
    .count {{ color: var(--gold); font-size: 12px; }}
    .identity {{
      display: flex; flex-wrap: wrap; gap: 8px; align-items: center; font-size: 15px; margin-top: 8px;
    }}
    .chip {{
      border-radius: 999px; padding: 6px 12px; font-weight: 600; background: var(--card-2);
    }}
    .hbar {{ display: grid; grid-template-columns: 118px 1fr 54px; gap: 8px; align-items: center; margin: 8px 0; }}
    .hbar-name {{ font-size: 13px; }}
    .hbar-track {{ height: 10px; background: #24312a; border-radius: 99px; overflow: hidden; }}
    .hbar-fill {{ display: block; height: 100%; border-radius: 99px; }}
    .hbar-val {{ text-align: right; font-size: 13px; color: var(--gold); }}
    .spark {{ width: 100%; height: auto; display: block; }}
    .chart-axis {{ fill: #9aa392; font-size: 11px; font-family: "IBM Plex Sans", sans-serif; }}
    .chart-num {{ fill: #f4ecd8; font-size: 11px; font-family: "IBM Plex Sans", sans-serif; }}
    .legend {{ display: flex; gap: 16px; margin: 8px 0 0; color: var(--muted); font-size: 13px; }}
    .swatch {{ display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; }}
    .story {{
      display: grid; grid-template-columns: 88px 1fr; gap: 14px; padding: 12px 0; border-top: 1px solid var(--line);
    }}
    .story:first-of-type {{ border-top: 0; padding-top: 0; }}
    .story-year {{ color: var(--gold); font-weight: 600; }}
    .coverage-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }}
    .cov {{
      background: var(--card-2); border-radius: 16px; padding: 12px; text-align: center;
    }}
    .cov strong {{ display: block; font-size: 28px; font-family: "Fraunces", Georgia, serif; color: var(--gold); }}
    .footer {{
      margin-top: 8px; color: var(--muted); font-size: 13px; display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap;
    }}
    @media (max-width: 900px) {{
      .hero, .grid, .grid-3, .grid-2, .kpis, .coverage-grid {{ grid-template-columns: 1fr; }}
      .hbar {{ grid-template-columns: 1fr; }}
    }}
    @media print {{
      body {{ background: #0c100e; }}
      .page {{ width: 100%; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <header class="hero">
      <div>
        <p class="eyebrow">Repository infographic</p>
        <h1>Sugar</h1>
        <p class="lede">
          This repo is a country-level sugar balance sheet: production, consumption,
          trade, and ending stocks for marketing years 2018/19–2023/24 (May estimate).
          Values are thousand metric tons. The infographic is generated from the CSVs.
        </p>
      </div>
      <aside class="hero-aside">
        <span class="eyebrow">Headline</span>
        <strong>{stock_drop:.0f}%</strong>
        <p class="muted" style="margin:6px 0 0">
          World ending stocks fell from {fmt_mt(end0)} Mt in 2018/19 to {fmt_mt(end)} Mt
          in 2023/24. Stock-to-use dropped from {stu0:.1f}% to {stu:.1f}%.
        </p>
      </aside>
    </header>

    <section class="kpis" aria-label="World totals 2023/24">
      <article class="kpi">
        <p class="kpi-label">Production</p>
        <p class="kpi-value" style="color:var(--prod)">{fmt_mt(prod)}</p>
        <p class="kpi-note">Mt · 2023/24 May</p>
      </article>
      <article class="kpi">
        <p class="kpi-label">Consumption</p>
        <p class="kpi-value" style="color:var(--cons)">{fmt_mt(cons)}</p>
        <p class="kpi-note">Mt · +{fmt_mt(cons - totals["consumption"][first])} vs 2018/19</p>
      </article>
      <article class="kpi">
        <p class="kpi-label">Surplus</p>
        <p class="kpi-value">{fmt_mt(surplus)}</p>
        <p class="kpi-note">Production minus use</p>
      </article>
      <article class="kpi">
        <p class="kpi-label">Exports</p>
        <p class="kpi-value" style="color:var(--export)">{fmt_mt(exp)}</p>
        <p class="kpi-note">Brazil {brazil_export_share:.0f}% of world</p>
      </article>
      <article class="kpi">
        <p class="kpi-label">Ending stocks</p>
        <p class="kpi-value" style="color:var(--stocks)">{fmt_mt(end)}</p>
        <p class="kpi-note">{stu:.1f}% stock-to-use</p>
      </article>
    </section>

    <section class="grid">
      <article class="card">
        <h2>The cupboard is emptying</h2>
        <p class="muted">World ending stocks, million tonnes. Drawdown is the main tightness signal in this dataset.</p>
        {stock_chart(totals["ending"])}
      </article>
      <article class="card">
        <h2>How the files fit</h2>
        <p class="muted">Six CSVs, one balance sheet. Combined is long-form; the five action files are ranked slices of the same facts.</p>
        <div class="files">
          <div class="file"><span class="dot" style="background:#e0c36a"></span><code>combined_df.csv</code><span class="count">{file_rows["combined_df.csv"]} rows · Name, Action, years</span></div>
          <div class="file"><span class="dot" style="background:var(--prod)"></span><code>production_df.csv</code><span class="count">{file_rows["production_df.csv"]} rows · growers</span></div>
          <div class="file"><span class="dot" style="background:var(--cons)"></span><code>consumption_df.csv</code><span class="count">{file_rows["consumption_df.csv"]} rows · users</span></div>
          <div class="file"><span class="dot" style="background:var(--export)"></span><code>export_df.csv</code><span class="count">{file_rows["export_df.csv"]} rows · shippers</span></div>
          <div class="file"><span class="dot" style="background:var(--import)"></span><code>import_df.csv</code><span class="count">{file_rows["import_df.csv"]} rows · buyers</span></div>
          <div class="file"><span class="dot" style="background:#cfc6ae"></span><code>ending_df.csv</code><span class="count">{file_rows["ending_df.csv"]} rows · inventories</span></div>
        </div>
      </article>
    </section>

    <section class="grid">
      <article class="card">
        <h2>Production vs consumption</h2>
        <p class="muted">2019/20 was the only deficit year. 2023/24 production rebounded to a six-year high while stocks kept falling.</p>
        {balance_chart(totals)}
        <p class="legend">
          <span><i class="swatch" style="background:var(--prod)"></i>Production</span>
          <span><i class="swatch" style="background:var(--cons)"></i>Consumption</span>
        </p>
      </article>
      <article class="card">
        <h2>Balance identity</h2>
        <p class="muted">Each named market is a sparse row in a five-flow ledger. World totals do not fully reconcile because export and import coverage differ.</p>
        <div class="identity">
          <span class="chip" style="color:var(--prod)">Production</span>
          <span>+</span>
          <span class="chip" style="color:var(--import)">Imports</span>
          <span>≈</span>
          <span class="chip" style="color:var(--cons)">Consumption</span>
          <span>+</span>
          <span class="chip" style="color:var(--export)">Exports</span>
          <span>+</span>
          <span class="chip" style="color:var(--stocks)">Δ stocks</span>
        </div>
        <div class="story">
          <div class="story-year">47</div>
          <div>Named countries or blocs, plus an <code>Other</code> residual and a <code>Total</code> world row.</div>
        </div>
        <div class="story">
          <div class="story-year">4</div>
          <div>Markets with every flow reported: {complete}.</div>
        </div>
        <div class="story">
          <div class="story-year">{fmt_mt(exp - imp)}</div>
          <div>Mt gap between world exports ({fmt_mt(exp)}) and imports ({fmt_mt(imp)}) in 2023/24 — a statistical residual, not a physical surplus.</div>
        </div>
      </article>
    </section>

    <section class="grid-3">
      <article class="card">
        <h2>Growers</h2>
        <p class="muted">Top production, 2023/24 Mt. Brazil is {brazil_share:.0f}% of the world crop.</p>
        {bar_rows(ranked(rows, "production", latest), COLORS["production"])}
      </article>
      <article class="card">
        <h2>Users</h2>
        <p class="muted">Top consumption. India is {india_cons_share:.0f}% of world use and still drawing stocks.</p>
        {bar_rows(ranked(rows, "consumption", latest), COLORS["consumption"])}
      </article>
      <article class="card">
        <h2>Shippers</h2>
        <p class="muted">Top exports. Thailand is the second engine after Brazil.</p>
        {bar_rows(ranked(rows, "export", latest), COLORS["export"])}
      </article>
    </section>

    <section class="grid-2">
      <article class="card">
        <h2>Buyers</h2>
        <p class="muted">Top imports, 2023/24 Mt. Indonesia and China lead the deficit markets.</p>
        {bar_rows(ranked(rows, "import", latest), COLORS["import"])}
      </article>
      <article class="card">
        <h2>Inventories</h2>
        <p class="muted">Largest ending stocks. India and Thailand both ran down warehouses over the sample.</p>
        {bar_rows(ranked(rows, "ending", latest), COLORS["ending"])}
      </article>
    </section>

    <section class="card" style="margin-bottom:14px">
      <h2>Coverage is sparse on purpose</h2>
      <p class="muted">
        Not every country appears in every file. Each action slice keeps the top reporters plus Other and Total.
        Single-flow specialists include {specialists}.
      </p>
      <div class="coverage-grid">
        <div class="cov"><strong>{len(buckets[5])}</strong>all 5 flows</div>
        <div class="cov"><strong>{len(buckets[4])}</strong>4 flows</div>
        <div class="cov"><strong>{len(buckets[3])}</strong>3 flows</div>
        <div class="cov"><strong>{len(buckets[2])}</strong>2 flows</div>
        <div class="cov"><strong>{len(buckets[1])}</strong>1 flow only</div>
      </div>
    </section>

    <footer class="footer">
      <span>Generated from combined_df.csv · {named} markets · 6 marketing years · thousand metric tons shown here as Mt</span>
      <span>Rebuild: <code>python3 scripts/build_infographic.py</code></span>
    </footer>
  </main>
  <script type="application/json" id="infographic-data">{json.dumps(payload)}</script>
</body>
</html>
"""


def main() -> None:
    rows = load_combined()
    OUTPUT.write_text(build_html(rows), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
