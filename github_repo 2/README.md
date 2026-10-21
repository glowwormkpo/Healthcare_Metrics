# Healthcare Metrics — Nurse Staffing Analysis

Analysis of nurse staffing at 14,564 U.S. nursing homes over Q2 2024, using CMS's Payroll-Based Journal (PBJ) Daily Nurse Staffing dataset enriched with CMS Provider Data Catalog files. See `docs/` for full methodology and findings.

## Repo structure

```
docs/         Methodology, EDA findings, data dictionary, and insights writeup
scripts/      The analysis pipeline, run in order (01 -> 04)
notebooks/    Jupyter notebook version of the full pipeline, pre-executed with output/charts
dashboard/    Self-contained interactive HTML dashboard (open directly in a browser)
data/         Aggregated output tables (facility-level, state-level, and answers to the analytical questions)
```

## Data sources (not included in this repo — see .gitignore)

This analysis is built on CMS public data, which is too large to version in git:

- **PBJ Daily Nurse Staffing, Q2 2024** (`PBJ_Daily_Nurse_Staffing_Q2_2024.csv`, ~220MB) — [CMS Provider Data Catalog](https://data.cms.gov/provider-data/)
- **CMS Nursing Home Compare / Provider Data Catalog, October 2024 release** — Provider Info, Ownership, Survey Summary, Health/Fire Safety Citations, MDS & Claims Quality Measures, Penalties, COVID Vaccination Rates, SNF QRP, SNF VBP files

To reproduce the pipeline from scratch: download these files from CMS and place them in a local folder, then run the scripts in `scripts/` in order (each one reads from `./` by default — edit the `DATA_DIR`/`UP` variable at the top of each script, or run from the folder containing the CSVs). The notebook in `notebooks/` does the same thing end-to-end and already has its output baked in, so you don't need to re-run it just to see the results.

## Quick look

- **Dashboard**: open `dashboard/Healthcare_Metrics_Dashboard.html` in any browser — no server needed, all data is embedded.
- **Notebook**: open `notebooks/Healthcare_Metrics_Analysis.ipynb` in Jupyter to see the full pipeline with pre-run output and charts.
- **Aggregated data**: `data/facility_summary.csv` (one row per facility) and `data/state_summary.csv` (one row per state) are the two most useful starting points if you just want the numbers.

## Key findings

- National nurse-to-patient ratio averages 3.36 hrs/resident/day; contract staff make up 7.7% of total nurse hours nationally.
- Total nurse hours scale strongly with patient census (r ≈ 0.92), but the largest facilities run slightly *leaner* per-resident (r ≈ −0.12 between ratio and census).
- 9 of the 10 facilities with the lowest computed nurse-to-patient coverage (census 30+) carry CMS's own lowest (1-star) Staffing Rating — an independent cross-check on the metric.
- Vermont, Maine, and New Hampshire lean most heavily on contract/agency nursing.

Full details, caveats, and the data dictionary are in `docs/Healthcare_Metrics_Insights_and_Data_Dictionary.md`.
