# India Trade Statistics Scraper (Ministry of Commerce)

Pulls India's **import / export statistics** from the Ministry of Commerce
[Trade Statistics portal](https://tradestat.commerce.gov.in) — commodity-wise
(HS code) values across multiple financial years — into a single tidy,
validated CSV.

The portal is **query-only**: pick a year, a direction and a commodity level,
submit an ASP form carrying hidden state, and read a results table. No bulk
download. This scraper drives that form year-by-year and assembles a clean
time series.

```
year,direction,hs_code,commodity,value_usd_mn
2023,export,8471,Automatic data processing machines,3765.2
2023,import,27,"Mineral fuels, oils, waxes",162044.8
...
```

## The hard parts (and how it handles them)

| Challenge | Approach |
|-----------|----------|
| **ASP form state** (`__VIEWSTATE` etc.) | Seeds a GET, harvests all hidden inputs, replays them in the POST so the server accepts the query |
| **Query-only portal** | Iterates `(year × direction)` programmatically — turns a one-query-at-a-time UI into a full dataset |
| **Slow / flaky govt server** | Long timeouts + exponential backoff + polite delays |
| **Messy values** (Indian grouping, `US$`, `-`) | Robust number parsing; HS codes normalised while preserving leading zeros |
| **Trust** | **pandera** schema: valid HS pattern, known direction, unique `(year, direction, hs_code)` |

## Architecture

```
scrape()  ─ (year × direction) loop ─┐
  ├─ fetch_via_requests (form replay) │
  └─ fetch_via_browser  (fallback)    ├─► clean() ─► validate() ─► CSV
       raw rows                       │   parse $/HS    pandera
                                      │   + de-dup      schema
```

## Install

```bash
git clone https://github.com/HemanthM005/commerce-trade-stats-scraper
cd commerce-trade-stats-scraper
pip install -r requirements.txt
playwright install chromium   # optional, for the browser fallback
```

## Usage

```bash
# exports, 2018-2024
python -m commerce_trade_scraper --direction export --from-year 2018 --to-year 2024 --out data/exports.csv

# imports, single year, requests only
python -m commerce_trade_scraper --direction import --from-year 2023 --to-year 2023 --no-browser
```

```python
from commerce_trade_scraper import scrape, clean, validate
from commerce_trade_scraper.config import ScraperConfig

df = validate(clean(scrape(ScraperConfig(years=(2023,), direction="import"))))
```

## Output schema

| column | description |
|--------|-------------|
| `year` | financial year |
| `direction` | `export` or `import` |
| `hs_code` | HS commodity code (leading zeros preserved) |
| `commodity` | commodity description |
| `value_usd_mn` | trade value, US$ million |

> `data/sample_output/trade_SAMPLE.csv` is an **illustrative** sample of the
> output schema. Run the scraper to pull the live figures.

## Tests

```bash
pip install pytest
PYTHONPATH=src pytest -q
```

## Tech
Python · requests · BeautifulSoup · Playwright · pandas · pandera

## Responsible scraping
Targets only **public** aggregate trade statistics, identifies itself with a
descriptive User-Agent, and rate-limits/backs off to stay gentle on a public
government server.

## License
MIT © 2026 Manikala Hemanth
