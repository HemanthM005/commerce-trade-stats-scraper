"""Configuration for the Ministry of Commerce trade-statistics scraper.

tradestat.commerce.gov.in publishes India's import/export figures as a
query-driven portal: pick a year, a trade direction (export/import) and a
commodity/country grouping, submit the form, and it renders a results table.
This scraper drives that form programmatically across a range of years.
"""
from __future__ import annotations

from dataclasses import dataclass, field

BASE_URL = "https://tradestat.commerce.gov.in"
# The results form posts to a commodity/country query handler. The exact path
# shifts between portal versions, so the scraper tries candidates in order.
QUERY_PATH_CANDIDATES = (
    "/eidb/icomq.asp",     # commodity-wise imports
    "/eidb/ecomq.asp",     # commodity-wise exports
)


@dataclass(frozen=True)
class ScraperConfig:
    base_url: str = BASE_URL
    query_paths: tuple[str, ...] = QUERY_PATH_CANDIDATES

    # Query space
    years: tuple[int, ...] = tuple(range(2018, 2025))   # financial years to pull
    direction: str = "export"                            # "export" | "import"
    hs_digit_level: int = 2                              # 2/4/8-digit HS commodity

    # Politeness / resilience
    user_agent: str = (
        "commerce-trade-stats-scraper/1.0 "
        "(+https://github.com/HemanthM005/commerce-trade-stats-scraper)"
    )
    request_timeout: int = 45           # govt portal can be slow
    max_retries: int = 4
    backoff_factor: float = 2.0
    min_delay_seconds: float = 2.0
    retry_statuses: tuple[int, ...] = (429, 500, 502, 503, 504)

    use_browser_fallback: bool = True
    headless: bool = False
    browser_wait_ms: int = 30_000

    expected_columns: tuple[str, ...] = field(
        default=("year", "direction", "hs_code", "commodity", "value_usd_mn")
    )
