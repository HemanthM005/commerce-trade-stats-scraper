"""Normalise raw trade-stats rows into a tidy, typed DataFrame."""
from __future__ import annotations

import re
from typing import Any

import pandas as pd

_WS = re.compile(r"\s+")


def _tidy(val: Any) -> str | None:
    if val is None:
        return None
    s = _WS.sub(" ", str(val)).strip()
    return s or None


def _to_number(raw: Any) -> float | None:
    """'1,23,456.78' / '₹12,345' / '-' -> float|None (Indian grouping safe)."""
    if raw is None:
        return None
    s = re.sub(r"[^\d.\-]", "", str(raw))
    if s in ("", "-", "."):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _norm_hs(raw: Any) -> str | None:
    """HS codes are digit strings; keep leading zeros, drop stray text."""
    s = _tidy(raw)
    if not s:
        return None
    digits = re.sub(r"\D", "", s)
    return digits or None


def clean(raw_rows: list[dict[str, Any]]) -> pd.DataFrame:
    records = []
    for row in raw_rows:
        hs = _norm_hs(row.get("hs_code"))
        val = _to_number(row.get("value_usd_mn"))
        if hs is None and val is None:
            continue
        records.append(
            {
                "year": int(row["year"]) if str(row.get("year", "")).isdigit() else None,
                "direction": _tidy(row.get("direction")),
                "hs_code": hs,
                "commodity": _tidy(row.get("commodity")),
                "value_usd_mn": val,
            }
        )

    df = pd.DataFrame(
        records, columns=["year", "direction", "hs_code", "commodity", "value_usd_mn"]
    )
    df = df.dropna(subset=["year", "hs_code"])
    df = df.drop_duplicates(subset=["year", "direction", "hs_code"])
    df = df.sort_values(["year", "direction", "hs_code"]).reset_index(drop=True)
    df["year"] = df["year"].astype("Int64")
    return df
