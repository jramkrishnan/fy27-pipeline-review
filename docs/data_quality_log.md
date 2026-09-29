# Data quality log

The four divisional submissions were pasted together as received. Before any number went to the CFO, every column was profiled and each issue below was logged with how it was found, how the fix was tested, what was done, and which headline number would move if it had been missed.

IDs match the `# DQ-xx` comments in [`src/clean.py`](../src/clean.py). Dollar figures are recomputed by the Python rebuild; where they differ from the original Excel log, the Python figure is shown and the difference noted.

| ID | Column | Issue | Rows | $ on rows | How found | How tested | Treatment | Headline if missed | Status |
|---|---|---|---|---|---|---|---|---|---|
| DQ-01 | Project | Missing project ID | 148 (92 in Division 4) | $318.0M | Power Query showed error values | Filtered to nulls, counted by division | Filled "Not provided", `Project_Issue` flag, rows kept | None directly; project level checks impossible for these rows | Open |
| DQ-02 | Division | Trailing space on "Division 3 " | 8 | $1.7M | Filter dropdown showed Division 3 twice | Distinct labels before and after trim | Trim and collapse whitespace | Division 3 split across two labels | Solved |
| DQ-03 | Under Contract | Trailing space on "Executable " | 13 | $6.1M | Filter dropdown showed two Executable labels | Executable count 174 + 13 = 187 after trim | Trim | Executable stage understated | Solved |
| DQ-04 | Division | No division on three FY27 rows | 3 | $3.0M | Null in filter | Filtered nulls | "Unknown" bucket, kept in pipeline | Unattributed FY27 revenue | Open |
| DQ-05 | Customer | Customer 2 as "Customer 02", "customer 2", "Customer  2" | 84 | $98M | Multiple Customer 2 variants in dropdown | Distinct customers fall from 52 to 49 | Regex to canonical "Customer N" | Largest historical customer understated by $98M | Solved |
| DQ-06 | Segment | Null and "N/A"; Segment 3 absent | 14 | $5.5M | Filter dropdown | 5 nulls, 9 N/A | "Unknown" | Segment view skewed | Open |
| DQ-07 | Under Contract | Go Get / GO GET / Go-Get, forecasted / Forecasted | 136 | $37.8M | Dropdown | Group by stage after mapping | Mapped to the five defined stages | Stage totals and weights split | Solved |
| DQ-08 | Under Contract | "Contracted" matches no defined stage | 122 after dedup (131 raw); 34 in FY27 | $50.4M; $33.8M in FY27 | Label not in prompt's stage list | Filtered, split by year | Kept as "Contracted (unclassified)", weighted 70% | FY27 plan number depends on it directly | Open |
| DQ-09 | Revenue | Stored as text with thousands separators | 9 | $6.0M | Column profiling | Count of non-numeric values | Strip commas, convert | Revenue understated $6.0M | Solved |
| DQ-10 | Month / Quarter | Quarter label disagrees with month (e.g. Mar in Q2) | 7 | $1.4M | Group by month and quarter | Compare `Quarter` to month-derived `Quarter_Clean` | Original kept, `Quarter_Clean` added, `Quarter_Mismatch` flag | Quarterly allocation wrong | Solved, convention to confirm |
| DQ-11 | Year / Under Contract | FY27 rows labelled YTD in Sept 2026 | 2 | $4.0M | YTD filtered by year | `Future_YTD_Issue` = 2 rows | Excluded from actuals and pipeline | Counted as actuals, or double counted | Open |
| DQ-12 | Revenue | Negative FY26 YTD amounts | 4 | −$1.27M | Filter revenue < 0 | 4 rows confirmed | Kept, `Negative_Revenue_Issue` flag | FY26 actuals off by $1.3M if dropped | Open |
| DQ-13 | Revenue | Single $26M FY27 row (Customer 14, Project 47, Q1) | 1 | $26.0M (16.0% of FY27) | Sorted FY27 rows by revenue | Src_RowID 1081 | Kept, `Large_Opportunity_Review` flag | Plan number and concentration | Open |
| DQ-14 | Revenue | Exactly $150,000 across all divisions | 27 | $4.1M | Frequency of round values | 28 rows before dedup, 27 after | Kept, `Round_Amount_Review` flag | None; possible placeholders | Open |
| DQ-15 | All | 27 exact duplicate rows, one pasted block, Division 3 FY26 Sept | 27 | $6.4M | Duplicate check across all original columns | 1,172 → 1,145; Src_RowID 1020 to 1046 | Removed, written to `duplicates_removed.csv` | FY26 forward pipeline overstated $6.4M | Closed |

## Differences from the original Excel log

| Item | Excel log | Rebuild | Note |
|---|---|---|---|
| DQ-15 duplicates | $6.3M | $6.38M | Rounding; deck used $6.4M |
| DQ-12 negatives | $1.2M | $1.27M | Rounding; deck used $1.3M |
| DQ-14 round amounts | "Rows affected: 7" | 27 | Typo in rows column; text said 27 |
| DQ-13 Project 47 | $26M, 15.98% | $26M row = 15.98%; project = $33.8M, 20.78% | Both correct at different grain; the deck used the project figure |
| DQ-08 Contracted | 131 rows, $51.66M | 122 rows, $50.4M after dedup | Excel counted before duplicate removal |

## Deliberately not changed

- **Stage weights** stay judgement based. No field in the data supports a measured conversion rate.
- **Negative actuals** stay in. They may be credits or reversals, and dropping them would overstate actuals.
- **Round $150K amounts** stay in. Placeholders are plausible but unproven.
