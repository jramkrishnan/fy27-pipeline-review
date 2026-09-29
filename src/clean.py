"""Clean the raw divisional pipeline submission.

Every rule here mirrors a step in the original Excel / Power Query workflow and
maps to an entry in docs/data_quality_log.md. Rows are never silently dropped:
the only rows removed are exact duplicates, and those are written out
separately so the removal can be audited.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

RAW_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "pipeline_raw.csv"

ORIGINAL_COLUMNS = [
    "Division", "Customer", "Project", "Segment", "Under Contract",
    "Month", "Quarter", "Year", "Revenue",
]

MONTH_TO_QUARTER = {
    "Jan": "Q1", "Feb": "Q1", "Mar": "Q1",
    "Apr": "Q2", "May": "Q2", "Jun": "Q2",
    "Jul": "Q3", "Aug": "Q3", "Sep": "Q3",
    "Oct": "Q4", "Nov": "Q4", "Dec": "Q4",
}

# Stage labels as received -> canonical stage from the case prompt.
# "Contracted" on its own does not match any of the five defined stages, so it
# is kept as its own bucket instead of being guessed into one.
STAGE_MAP = {
    "executable": "Executable",
    "contracted backlog": "Contracted Backlog",
    "forecasted": "Forecasted",
    "contracted pipeline": "Contracted Pipeline",
    "go get": "Go-Get",
    "go-get": "Go-Get",
    "contracted": "Contracted (unclassified)",
    "ytd": "YTD",
}

LARGE_OPPORTUNITY_THRESHOLD = 10_000_000
ROUND_AMOUNT = 150_000


def load_raw(path: Path = RAW_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])
    df.insert(0, "Src_RowID", range(1, len(df) + 1))
    return df


def _strip(s: pd.Series) -> pd.Series:
    return s.str.replace(r"\s+", " ", regex=True).str.strip()


def _canonical_customer(value: str) -> str:
    # "customer 2", "Customer  2", "Customer 02" -> "Customer 2"
    m = re.fullmatch(r"customer\s*0*(\d+)", value.strip(), flags=re.IGNORECASE)
    return f"Customer {int(m.group(1))}" if m else value


def _canonical_stage(value: str) -> str:
    if re.fullmatch(r"\d{4}", value):
        return value  # FY24 / FY25 actuals carry the year in this column
    return STAGE_MAP.get(value.lower(), value)


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (clean, duplicates_removed)."""
    df = raw.copy()

    # DQ-02, DQ-03: trailing and double spaces in text labels
    for col in ["Division", "Customer", "Project", "Segment", "Under Contract", "Month", "Quarter"]:
        df[col] = _strip(df[col])

    # DQ-04: rows with no division are kept under an explicit bucket
    df["Division"] = df["Division"].fillna("Unknown")

    # DQ-05: three spellings of Customer 2
    df["Customer"] = df["Customer"].map(_canonical_customer)

    # DQ-01: missing project identifiers
    df["Project_Issue"] = df["Project"].isna()
    df["Project"] = df["Project"].fillna("Not provided")

    # DQ-06: missing / N/A segment
    df["Segment"] = df["Segment"].replace({"N/A": None}).fillna("Unknown")

    # DQ-07, DQ-08: stage label variants, plus the unmapped "Contracted" label
    df["Under Contract"] = df["Under Contract"].map(_canonical_stage)

    # DQ-09: revenue stored as text with thousands separators
    df["Revenue"] = pd.to_numeric(df["Revenue"].str.replace(",", "", regex=False))
    df["Year"] = df["Year"].astype(int)

    # DQ-10: quarter label disagrees with month. Keep the original, add a clean one.
    df["Quarter_Clean"] = df["Month"].map(MONTH_TO_QUARTER).fillna(df["Quarter"])
    df["Quarter_Mismatch"] = df["Month"].isin(MONTH_TO_QUARTER) & (df["Quarter"] != df["Quarter_Clean"])

    # DQ-11: FY27 rows labelled YTD although the analysis date is Sept 2026
    df["Future_YTD_Issue"] = (df["Under Contract"] == "YTD") & (df["Year"] > 2026)

    # DQ-12: negative actuals
    df["Negative_Revenue_Issue"] = df["Revenue"] < 0

    # DQ-13, DQ-14: review flags, amounts retained. The large-opportunity flag
    # only looks at forward rows; FY24/FY25 actuals are annual totals and are
    # naturally large.
    df["Large_Opportunity_Review"] = (df["Revenue"] >= LARGE_OPPORTUNITY_THRESHOLD) & (df["Year"] >= 2026) & (
        df["Under Contract"] != "YTD"
    )
    df["Round_Amount_Review"] = df["Revenue"] == ROUND_AMOUNT

    # DQ-15: exact duplicates across every original column, checked after
    # normalisation so that formatting differences cannot hide a duplicate
    dup_mask = df.duplicated(subset=ORIGINAL_COLUMNS, keep="first")
    duplicates = df[dup_mask].copy()
    df = df[~dup_mask].copy()

    df["Analysis_Class"] = classify(df)
    duplicates["Analysis_Class"] = classify(duplicates)
    return df.reset_index(drop=True), duplicates.reset_index(drop=True)


def classify(df: pd.DataFrame) -> pd.Series:
    """Split every row into exactly one analysis bucket."""
    out = pd.Series("Forward pipeline", index=df.index)
    out[df["Year"] <= 2025] = "Historical actual"
    out[(df["Under Contract"] == "YTD") & (df["Year"] == 2026)] = "FY26 YTD actual"
    out[df["Future_YTD_Issue"]] = "Future YTD exception"
    return out


if __name__ == "__main__":
    c, d = clean(load_raw())
    print(f"{len(c)} clean rows, {len(d)} duplicates removed")
