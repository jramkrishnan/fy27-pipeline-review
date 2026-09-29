"""Headline numbers for the FY27 pipeline review.

Run from the repo root:  python -m src.analysis
Writes CSV tables to outputs/ and prints the headline figures.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.clean import clean, load_raw

OUT = Path(__file__).resolve().parents[1] / "outputs"

# Judgement-based realisation weights, read off the stage definitions in the
# prompt. These are planning assumptions, NOT measured conversion rates: the
# dataset has no snapshots or outcomes to measure conversion from.
STAGE_WEIGHTS = pd.DataFrame(
    {
        "Stage": ["Executable", "Contracted Backlog", "Forecasted", "Contracted Pipeline", "Go-Get", "Contracted (unclassified)"],
        "Conservative": [0.90, 0.70, 0.55, 0.35, 0.10, 0.55],
        "Base": [0.95, 0.80, 0.70, 0.50, 0.20, 0.70],
        "Upside": [1.00, 0.90, 0.85, 0.65, 0.30, 0.85],
    }
).set_index("Stage")


def reconciliation(raw_total: float, clean_df: pd.DataFrame, dups: pd.DataFrame) -> pd.DataFrame:
    by_class = clean_df.groupby("Analysis_Class")["Revenue"].sum()
    fy27 = clean_df.query("Analysis_Class == 'Forward pipeline' and Year == 2027")["Revenue"].sum()
    rows = [
        ("A", "Revenue as submitted by four divisions", raw_total),
        ("B", "Less: duplicate submissions", -dups["Revenue"].sum()),
        ("C", "Revenue after cleaning", clean_df["Revenue"].sum()),
        ("D", "Less: FY24 and FY25 actuals", -by_class["Historical actual"]),
        ("E", "Less: FY26 actuals to date (Jan to Jun)", -by_class["FY26 YTD actual"]),
        ("F", "Less: FY27 records labelled YTD", -by_class["Future YTD exception"]),
        ("G", "Forward pipeline, FY26 and FY27", by_class["Forward pipeline"]),
        ("H", "of which FY27", fy27),
        ("I", "of which FY26 (Jul to Dec)", by_class["Forward pipeline"] - fy27),
    ]
    rec = pd.DataFrame(rows, columns=["Line", "Description", "Amount"])
    # The waterfall has to tie out; fail loudly if it does not.
    assert abs(rec.Amount[0] + rec.Amount[1] - rec.Amount[2]) < 1
    assert abs(rec.Amount[2] + rec.Amount[3] + rec.Amount[4] + rec.Amount[5] - rec.Amount[6]) < 1
    return rec


def fy27_forward(clean_df: pd.DataFrame) -> pd.DataFrame:
    return clean_df.query("Analysis_Class == 'Forward pipeline' and Year == 2027")


def weighted_scenarios(fy27: pd.DataFrame) -> pd.DataFrame:
    by_stage = fy27.groupby("Under Contract")["Revenue"].agg(Pipeline="sum", Records="count")
    table = STAGE_WEIGHTS.join(by_stage, how="left").fillna(0)
    for s in ["Conservative", "Base", "Upside"]:
        table[f"{s}_Weighted"] = table["Pipeline"] * table[s]
    return table


def share_table(fy27: pd.DataFrame, keys: list[str], top: int | None = None) -> pd.DataFrame:
    t = fy27.groupby(keys)["Revenue"].sum().sort_values(ascending=False).to_frame("FY27_Pipeline")
    t["Share"] = t["FY27_Pipeline"] / fy27["Revenue"].sum()
    return t.head(top) if top else t


def run() -> dict:
    raw = load_raw()
    raw_total = pd.to_numeric(raw["Revenue"].str.replace(",", "", regex=False)).sum()
    c, dups = clean(raw)
    fy27 = fy27_forward(c)

    rec = reconciliation(raw_total, c, dups)
    scen = weighted_scenarios(fy27)
    divisions = share_table(fy27, ["Division"])
    customers = share_table(fy27, ["Customer"], top=10)
    projects = share_table(fy27, ["Customer", "Project"], top=10)
    quarters = fy27.groupby("Quarter_Clean")["Revenue"].sum().to_frame("FY27_Pipeline")
    fy26_fwd_by_div = c.query("Analysis_Class == 'Forward pipeline' and Year == 2026").groupby("Division")["Revenue"].sum()

    OUT.mkdir(exist_ok=True)
    c.to_csv(OUT / "pipeline_clean.csv", index=False)
    dups.to_csv(OUT / "duplicates_removed.csv", index=False)
    rec.to_csv(OUT / "reconciliation.csv", index=False)
    scen.to_csv(OUT / "fy27_weighted_scenarios.csv")
    divisions.to_csv(OUT / "fy27_by_division.csv")
    customers.to_csv(OUT / "fy27_top_customers.csv")
    projects.to_csv(OUT / "fy27_top_projects.csv")
    quarters.to_csv(OUT / "fy27_by_quarter.csv")

    return {
        "clean": c,
        "duplicates": dups,
        "reconciliation": rec,
        "scenarios": scen,
        "divisions": divisions,
        "customers": customers,
        "projects": projects,
        "quarters": quarters,
        "fy26_forward_by_division": fy26_fwd_by_div,
        "fy27_total": fy27["Revenue"].sum(),
    }


def _m(x: float) -> str:
    return f"${x / 1e6:,.1f}M"


if __name__ == "__main__":
    r = run()
    s = r["scenarios"]
    print("Reconciliation")
    for _, row in r["reconciliation"].iterrows():
        print(f"  {row.Line}  {row.Description:<45} {row.Amount:>18,.0f}")
    print(f"\nFY27 forward pipeline (submitted): {_m(r['fy27_total'])}")
    for k in ["Conservative", "Base", "Upside"]:
        print(f"  {k:<13} weighted: {_m(s[f'{k}_Weighted'].sum())}")
    top = r["projects"].iloc[0]
    print(f"\nLargest FY27 project: {r['projects'].index[0]} {_m(top.FY27_Pipeline)} ({top.Share:.2%})")
    d4 = r["divisions"].loc["Division 4", "FY27_Pipeline"]
    print(f"Division 4 FY27: ${d4:,.0f} vs FY26 forward {_m(r['fy26_forward_by_division']['Division 4'])}")
