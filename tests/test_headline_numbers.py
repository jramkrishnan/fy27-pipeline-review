"""Every headline number in the deck, pinned.

The original case asked candidates to reproduce headline numbers live in the
interview. These tests do that on every run: if a cleaning rule changes and a
number moves, the test says which one.
"""

import pytest

from src.analysis import STAGE_WEIGHTS, run
from src.clean import clean, load_raw


@pytest.fixture(scope="module")
def r():
    return run()


def approx(x, rel=1e-9):
    return pytest.approx(x, rel=rel)


# Data quality: counts before and after each rule
def test_row_counts(r):
    assert len(load_raw()) == 1172
    assert len(r["duplicates"]) == 27
    assert len(r["clean"]) == 1145


def test_duplicates_are_one_pasted_block_from_division_3(r):
    d = r["duplicates"]
    assert set(d["Division"]) == {"Division 3"}
    assert set(d["Year"]) == {2026}
    assert sorted(d["Src_RowID"]) == list(range(1020, 1047))
    assert d["Revenue"].sum() == approx(6_379_505.50, rel=1e-6)


def test_labels_are_normalised(r):
    c = r["clean"]
    assert set(c["Division"]) == {"Division 1", "Division 2", "Division 3", "Division 4", "Unknown"}
    assert not c["Customer"].str.contains(r"customer|  | 0\d", regex=True).any()
    assert c["Customer"].nunique() == 49
    stages = set(c["Under Contract"]) - {"2024", "2025"}
    assert stages == {
        "YTD", "Executable", "Contracted Backlog", "Forecasted",
        "Contracted Pipeline", "Go-Get", "Contracted (unclassified)",
    }


def test_flag_counts(r):
    c = r["clean"]
    assert c["Project_Issue"].sum() == 148
    assert (c.loc[c["Project_Issue"], "Division"] == "Division 4").sum() == 92
    assert c["Quarter_Mismatch"].sum() == 7
    assert c["Future_YTD_Issue"].sum() == 2
    assert c["Negative_Revenue_Issue"].sum() == 4
    assert c["Round_Amount_Review"].sum() == 27
    assert c.loc[c["Large_Opportunity_Review"], "Src_RowID"].tolist() == [1081]


# Reconciliation waterfall
def test_reconciliation_ties_out(r):
    rec = r["reconciliation"].set_index("Line")["Amount"]
    assert rec["A"] == approx(635_968_267.37, rel=1e-8)
    assert rec["D"] == approx(-309_318_943, rel=1e-6)
    assert rec["E"] == approx(-72_438_675, rel=1e-6)
    assert rec["F"] == approx(-4_000_000)
    assert rec["G"] == approx(243_831_144, rel=1e-6)
    assert rec["H"] == approx(162_674_619, rel=1e-6)


# FY27 recommendation
def test_weighted_scenarios(r):
    s = r["scenarios"]
    assert s["Pipeline"].sum() == approx(r["fy27_total"])
    assert round(s["Conservative_Weighted"].sum() / 1e6, 1) == 70.7
    assert round(s["Base_Weighted"].sum() / 1e6, 1) == 92.5
    assert round(s["Upside_Weighted"].sum() / 1e6, 1) == 114.3


def test_weights_are_monotonic_by_certainty():
    ordered = ["Executable", "Contracted Backlog", "Forecasted", "Contracted Pipeline", "Go-Get"]
    for col in ["Conservative", "Base", "Upside"]:
        w = STAGE_WEIGHTS.loc[ordered, col].tolist()
        assert w == sorted(w, reverse=True)
    assert (STAGE_WEIGHTS["Conservative"] <= STAGE_WEIGHTS["Base"]).all()
    assert (STAGE_WEIGHTS["Base"] <= STAGE_WEIGHTS["Upside"]).all()


# Concentration and anomalies
def test_concentration(r):
    top_project = r["projects"].iloc[0]
    assert r["projects"].index[0] == ("Customer 14", "Project 47")
    assert round(top_project["Share"] * 100, 2) == 20.78
    assert round(r["customers"].loc["Customer 14", "Share"] * 100, 1) == 31.2


def test_division_4_fy27_gap(r):
    assert r["divisions"].loc["Division 4", "FY27_Pipeline"] == approx(31_100)
    assert round(r["fy26_forward_by_division"]["Division 4"] / 1e6, 1) == 13.7


def test_cleaning_is_deterministic():
    a, _ = clean(load_raw())
    b, _ = clean(load_raw())
    assert a.equals(b)
