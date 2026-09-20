# Sugar

Country-level world sugar balance sheet for marketing years **2018/19–2023/24** (May estimate). Values are thousand metric tons.

## Infographic

A generated poster of this repository — file layout, coverage, and the six-year market story — lives in [`infographic.html`](infographic.html).

```bash
python3 scripts/build_infographic.py
python3 -m unittest discover -s tests -v
python3 -m http.server 8000
```

Then open [http://localhost:8000/infographic.html](http://localhost:8000/infographic.html). You can also open the HTML file directly in a browser.

## Data files

| File | Shape | Role |
| --- | --- | --- |
| `combined_df.csv` | long: `Name`, `Action`, six years | Canonical ledger |
| `production_df.csv` | ranked slice | Growers |
| `consumption_df.csv` | ranked slice | Users |
| `export_df.csv` | ranked slice | Shippers |
| `import_df.csv` | ranked slice | Buyers |
| `ending_df.csv` | ranked slice | Inventories |

Each action file is the same facts as `combined_df.csv` filtered to one flow, sorted by the latest year, with an `Other` residual and a `Total` world row.

Rebuild the infographic whenever the CSVs change.
