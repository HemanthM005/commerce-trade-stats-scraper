"""CLI: scrape -> clean -> validate -> CSV.

    python -m commerce_trade_scraper --direction export --out data/exports.csv
"""
from __future__ import annotations

import argparse
import logging
import sys

from .clean import clean
from .config import ScraperConfig
from .scraper import scrape
from .validate import validate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scrape MoC import/export statistics.")
    parser.add_argument("--out", default="data/trade.csv", help="output CSV path")
    parser.add_argument("--direction", choices=["export", "import"], default="export")
    parser.add_argument("--from-year", type=int, default=2018)
    parser.add_argument("--to-year", type=int, default=2024)
    parser.add_argument("--no-browser", action="store_true", help="disable browser fallback")
    parser.add_argument("--headless", action="store_true", help="run browser headless")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )

    cfg = ScraperConfig(
        years=tuple(range(args.from_year, args.to_year + 1)),
        direction=args.direction,
        use_browser_fallback=not args.no_browser,
        headless=args.headless,
    )

    logging.info("Scraping MoC %s statistics %d-%d...", args.direction, args.from_year, args.to_year)
    raw = scrape(cfg)
    if not raw:
        logging.error("No data scraped. Exiting.")
        return 1

    df = clean(raw)
    logging.info("Cleaned %d rows across %d years.", len(df), df["year"].nunique())

    try:
        validate(df)
    except Exception as exc:
        logging.error("Validation FAILED - not writing output.\n%s", exc)
        return 2

    df.to_csv(args.out, index=False)
    logging.info("Validated & wrote %d rows -> %s", len(df), args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
