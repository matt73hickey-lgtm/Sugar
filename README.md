# World sugar dashboard

Interactive visualisation of the country-level sugar balance sheet in this repository: production, consumption, exports, imports, and ending stocks across marketing years 2018/19 to 2023/24 (May estimate). Values are thousand metric tons.

## Open the dashboard

The visualisation is a static page. From the repository root:

```bash
python3 -m http.server 8000
```

Then open [http://localhost:8000](http://localhost:8000). You can also open `index.html` directly in a browser.

## Refresh the data payload

If the CSV files change, regenerate `assets/data.js` and `assets/data.json`:

```bash
python3 scripts/prepare_data.py
python3 -m unittest discover -s tests -v
```

No third-party Python packages are required.

## What to look at

- **World totals** for the selected marketing year, including surplus and stock-to-use.
- **Global balance** of production, consumption, and ending stocks.
- **Country rankings** for each flow, plus net trade (exports minus imports).
- **Stock drawdown** from 2018/19 to 2023/24, which is the main tightness signal in this dataset.
- **Country profile** for any named producer, consumer, or trader, including the residual `Other` bucket.
