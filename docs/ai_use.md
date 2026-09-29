# AI use

The case allowed any tools, including AI assistants, on the condition that I could stand behind every number and reproduce headline figures live. This is where I used AI and how I checked it.

## Original Excel submission

| Where AI was used | How I checked it |
|---|---|
| Brainstorming what kinds of data issues to look for (trailing spaces, spelling variants, nulls, duplicates) | Filtered every column myself in Excel and confirmed counts before and after each cleaning step |
| Suggesting the four analysis classes: historical actual, FY26 YTD, future YTD exception, forward pipeline | Filtered the Clean tab by each class and tied counts and totals to the reconciliation |
| Suggesting the reconciliation waterfall structure | Wrote every SUMIFS myself, all referencing the Pipeline table, no hardcoded values |
| Suggesting which pivots to build | Set the stage weights myself from the stage definitions, with a rationale column for each |
| Drafting some wording for the Output and Questions tabs | Rewrote in my own words to match what I actually found |

## Python rebuild (this repo)

| Where AI was used | How I checked it |
|---|---|
| Porting the Power Query steps to pandas and scaffolding the repo | Merged the Python output to the original Excel `Clean` tab on `Src_RowID` and compared every column: 1,145 of 1,145 rows match on division, customer, project, segment, stage, quarter, analysis class and all flags |
| Writing the tests | Every asserted value was checked against the submitted deck; where the deck and Excel log disagreed, the difference is documented in the data quality log rather than silently picked |
