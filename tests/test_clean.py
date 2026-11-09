"""Tests for the trade-stats cleaning + validation layer."""
from __future__ import annotations

import pandas as pd

from commerce_trade_scraper.clean import _norm_hs, _to_number, clean
from commerce_trade_scraper.validate import validate


def test_norm_hs_keeps_leading_zeros():
    assert _norm_hs("09 - Coffee, tea") == "09"
    assert _norm_hs("8471") == "8471"
    assert _norm_hs("  ") is None


def test_to_number_handles_indian_grouping():
    assert _to_number("1,23,456.78") == 123456.78
    assert _to_number("US$ 2,500") == 2500.0
    assert _to_number("-") is None


def test_clean_dedupes_and_types():
    raw = [
        {"year": 2023, "direction": "export", "hs_code": "09", "commodity": "Coffee", "value_usd_mn": "1,200"},
        {"year": 2023, "direction": "export", "hs_code": "09", "commodity": "Coffee", "value_usd_mn": "1,200"},  # dup
        {"year": 2022, "direction": "export", "hs_code": "8471", "commodity": "Computers", "value_usd_mn": "3,400.5"},
    ]
    df = clean(raw)
    assert len(df) == 2
    assert df["year"].dtype == "Int64"
    assert df.loc[df["hs_code"] == "8471", "value_usd_mn"].iloc[0] == 3400.5


def test_cleaned_frame_passes_validation():
    raw = [
        {"year": 2021, "direction": "import", "hs_code": "27", "commodity": "Mineral fuels", "value_usd_mn": "150000"},
    ]
    out = validate(clean(raw))
    assert isinstance(out, pd.DataFrame) and len(out) == 1
