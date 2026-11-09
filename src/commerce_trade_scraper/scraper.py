"""Scrape India's import/export statistics from the Ministry of Commerce portal.

The portal is a classic ASP form: it carries hidden state fields and returns an
HTML results table per (year, direction) query. This scraper submits the form
year-by-year, parses the table, and tags every row with its query context so
the output is fully self-describing.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import ScraperConfig

logger = logging.getLogger(__name__)
RawRow = dict[str, Any]


def _build_session(cfg: ScraperConfig) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=cfg.max_retries,
        backoff_factor=cfg.backoff_factor,
        status_forcelist=cfg.retry_statuses,
        allowed_methods=frozenset(["GET", "POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": cfg.user_agent})
    return session


def _hidden_form_state(html: str) -> dict[str, str]:
    """Extract ASP hidden fields (__VIEWSTATE etc.) so POSTs are accepted."""
    soup = BeautifulSoup(html, "html.parser")
    state = {}
    for inp in soup.select("input[type=hidden]"):
        name = inp.get("name")
        if name:
            state[name] = inp.get("value", "")
    return state


def parse_results_table(html: str, year: int, direction: str) -> list[RawRow]:
    """Parse one results table; tag each row with year + direction."""
    soup = BeautifulSoup(html, "html.parser")
    rows: list[RawRow] = []
    table = soup.find("table")
    if not table:
        return rows
    for tr in table.find_all("tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        # Expect: HS code | commodity | value. Skip header/summary rows.
        if len(cells) >= 3 and any(c.replace(".", "").isdigit() for c in cells):
            rows.append(
                {
                    "year": year,
                    "direction": direction,
                    "hs_code": cells[0],
                    "commodity": cells[1],
                    "value_usd_mn": cells[-1],
                }
            )
    return rows


def _query_year(session: requests.Session, cfg: ScraperConfig, year: int) -> list[RawRow]:
    for path in cfg.query_paths:
        url = f"{cfg.base_url}{path}"
        time.sleep(cfg.min_delay_seconds)
        try:
            seed = session.get(url, timeout=cfg.request_timeout)
            form = _hidden_form_state(seed.text)
            form.update(
                {
                    "year": str(year),
                    "radio": cfg.direction,
                    "hslevel": str(cfg.hs_digit_level),
                }
            )
            resp = session.post(url, data=form, timeout=cfg.request_timeout)
        except requests.RequestException as exc:
            logger.warning("Query failed (%s %d): %s", path, year, exc)
            continue
        if resp.status_code != 200:
            continue
        rows = parse_results_table(resp.text, year, cfg.direction)
        if rows:
            return rows
    return []


def fetch_via_requests(cfg: ScraperConfig) -> list[RawRow]:
    session = _build_session(cfg)
    out: list[RawRow] = []
    for year in cfg.years:
        logger.info("Querying %s %d...", cfg.direction, year)
        rows = _query_year(session, cfg, year)
        logger.info("  -> %d rows", len(rows))
        out.extend(rows)
    return out


def fetch_via_browser(cfg: ScraperConfig) -> list[RawRow]:
    """Browser fallback for when the portal's form state defeats plain POSTs."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Browser fallback needs Playwright: "
            "pip install playwright && playwright install chromium"
        ) from exc

    out: list[RawRow] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=cfg.headless)
        page = browser.new_page(user_agent=cfg.user_agent)
        for path in cfg.query_paths:
            page.goto(f"{cfg.base_url}{path}", timeout=cfg.browser_wait_ms)
            for year in cfg.years:
                try:
                    page.select_option("select[name=year]", str(year))
                    page.click("input[type=submit]")
                    page.wait_for_selector("table tr td", timeout=cfg.browser_wait_ms)
                except Exception:
                    continue
                out.extend(parse_results_table(page.content(), year, cfg.direction))
            if out:
                break
        browser.close()
    return out


def scrape(cfg: ScraperConfig | None = None) -> list[RawRow]:
    cfg = cfg or ScraperConfig()
    rows = fetch_via_requests(cfg)
    if rows:
        return rows
    if cfg.use_browser_fallback:
        logger.info("Falling back to browser...")
        return fetch_via_browser(cfg)
    raise RuntimeError("No rows via requests and browser fallback disabled.")
