"""Static charts for the README.  python -m src.charts"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.analysis import OUT, fy27_forward, run

BLUE, BLUE_LIGHT, ORANGE = "#2a78d6", "#9ec5f4", "#eb6834"
INK, INK_2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK_2,
    "xtick.color": INK_2, "ytick.color": INK_2, "axes.spines.top": False,
    "axes.spines.right": False, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.titleweight": "bold", "axes.titlesize": 12, "axes.titlelocation": "left",
    "text.parse_math": False,
})


def _money(ax, axis="y"):
    fmt = matplotlib.ticker.FuncFormatter(lambda v, _: f"${v / 1e6:,.0f}M")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def reconciliation_chart(rec: pd.DataFrame, path):
    steps = rec[rec.Line.isin(list("ABDEFG"))].copy()
    labels = ["Submitted", "Duplicates", "FY24-25 actuals", "FY26 YTD actuals", "FY27 rows marked YTD", "Forward pipeline"]
    fy27 = rec.loc[rec.Line == "H", "Amount"].iloc[0]
    fig, ax = plt.subplots(figsize=(8, 4))
    running = 0
    for i, (lab, amt) in enumerate(zip(labels, steps.Amount)):
        if i in (0, len(labels) - 1):
            ax.barh(i, amt, color=BLUE, height=0.6)
            running = amt
            ax.text(amt, i, f"  ${amt / 1e6:,.1f}M", va="center", color=INK)
        else:
            start = running
            running += amt
            ax.barh(i, -amt, left=running, color=BLUE_LIGHT, height=0.6)
            ax.text(start, i, f"  -${-amt / 1e6:,.1f}M", va="center", color=INK_2)
    ax.barh(len(labels), fy27, color=ORANGE, height=0.6)
    ax.text(fy27, len(labels), f"  ${fy27 / 1e6:,.1f}M", va="center", color=INK)
    ax.set_yticks(range(len(labels) + 1), labels + ["of which FY27"])
    ax.invert_yaxis()
    _money(ax, "x")
    ax.grid(axis="x", color=GRID)
    ax.set_axisbelow(True)
    ax.set_title("From $636M submitted to $162.7M of FY27 pipeline")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def stage_chart(scen: pd.DataFrame, path):
    s = scen.sort_values("Pipeline")
    fig, ax = plt.subplots(figsize=(8, 3.8))
    y = range(len(s))
    ax.barh([i + 0.18 for i in y], s.Pipeline, height=0.34, color=BLUE_LIGHT, label="Submitted")
    ax.barh([i - 0.18 for i in y], s.Base_Weighted, height=0.34, color=BLUE, label="Base weighted")
    for i, (p, w, wt) in enumerate(zip(s.Pipeline, s.Base_Weighted, s.Base)):
        ax.text(p, i + 0.18, f" ${p / 1e6:,.1f}M", va="center", fontsize=9, color=INK_2)
        ax.text(w, i - 0.18, f" ${w / 1e6:,.1f}M at {wt:.0%}", va="center", fontsize=9, color=INK)
    ax.set_yticks(list(y), s.index)
    _money(ax, "x")
    ax.grid(axis="x", color=GRID)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="lower right")
    ax.set_title(f"FY27 by stage: ${s.Pipeline.sum() / 1e6:,.1f}M submitted, ${s.Base_Weighted.sum() / 1e6:,.1f}M base case")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def quarter_chart(clean: pd.DataFrame, path):
    fy27 = fy27_forward(clean)
    big = fy27[fy27.Large_Opportunity_Review].groupby("Quarter_Clean")["Revenue"].sum()
    total = fy27.groupby("Quarter_Clean")["Revenue"].sum()
    rest = total - big.reindex(total.index, fill_value=0)
    big = big.reindex(total.index, fill_value=0)
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.bar(total.index, rest, color=BLUE, width=0.55, label="All other FY27 rows")
    ax.bar(total.index, big, bottom=rest, color=ORANGE, width=0.55, label="Project 47, single $26M row")
    for q, t in total.items():
        ax.text(q, t, f"${t / 1e6:,.1f}M", ha="center", va="bottom", color=INK)
    _money(ax)
    ax.grid(axis="y", color=GRID)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper right")
    ax.set_title("The Q1 FY27 spike is one row")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def division_chart(divisions: pd.DataFrame, fy26: pd.Series, path):
    idx = ["Division 1", "Division 2", "Division 3", "Division 4"]
    a = fy26.reindex(idx, fill_value=0)
    b = divisions["FY27_Pipeline"].reindex(idx, fill_value=0)
    x = range(len(idx))
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.bar([i - 0.2 for i in x], a, width=0.38, color=BLUE_LIGHT, label="FY26 forward (Jul to Dec)")
    ax.bar([i + 0.2 for i in x], b, width=0.38, color=BLUE, label="FY27 forward")
    ax.annotate("$31K", (3.2, b.iloc[3]), xytext=(3.2, 20e6), ha="center", color=ORANGE,
                fontweight="bold", arrowprops=dict(arrowstyle="-", color=ORANGE))
    ax.set_xticks(list(x), idx)
    _money(ax)
    ax.grid(axis="y", color=GRID)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("Division 4 submitted almost no FY27 pipeline")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    r = run()
    d = OUT / "charts"
    d.mkdir(parents=True, exist_ok=True)
    reconciliation_chart(r["reconciliation"], d / "01_reconciliation.png")
    stage_chart(r["scenarios"], d / "02_fy27_by_stage.png")
    quarter_chart(r["clean"], d / "03_fy27_by_quarter.png")
    division_chart(r["divisions"], r["fy26_forward_by_division"], d / "04_division_4.png")
    print("charts written to", d)
