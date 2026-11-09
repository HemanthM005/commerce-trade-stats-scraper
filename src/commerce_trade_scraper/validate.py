"""Schema + quality checks for cleaned trade statistics."""
from __future__ import annotations

from pandera.pandas import Check, Column, DataFrameSchema

trade_schema = DataFrameSchema(
    {
        "year": Column("Int64", checks=Check.in_range(1990, 2100), nullable=False),
        "direction": Column(str, checks=Check.isin(["export", "import"]), nullable=False),
        "hs_code": Column(str, checks=Check.str_matches(r"^\d{2,8}$"), nullable=False),
        "commodity": Column(str, nullable=True),
        "value_usd_mn": Column(float, checks=Check.greater_than_or_equal_to(0), nullable=True),
    },
    strict=True,
    coerce=True,
    # No two rows should share (year, direction, hs_code).
    unique=["year", "direction", "hs_code"],
)


def validate(df):
    """Validate; raises pandera SchemaErrors on any violation."""
    return trade_schema.validate(df, lazy=True)
