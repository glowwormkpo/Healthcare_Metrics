"""
Builds Healthcare_Metrics_Analysis.ipynb by actually executing each cell's
code against the real uploaded data and capturing text/plot output, so the
notebook opens already-run (like File > Save after Kernel > Run All).
"""
import io, base64, contextlib, json, sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ns = {}
cells = []
exec_count = [0]

def md(text):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(keepends=True)})

def code(src, capture_plot=False):
    src = src.strip("\n")
    buf = io.StringIO()
    outputs = []
    with contextlib.redirect_stdout(buf):
        exec(src, ns)
    text = buf.getvalue()
    if text:
        outputs.append({"output_type": "stream", "name": "stdout", "text": text.splitlines(keepends=True)})
    if capture_plot:
        fig = plt.gcf()
        bio = io.BytesIO()
        fig.savefig(bio, format="png", dpi=100, bbox_inches="tight")
        bio.seek(0)
        b64 = base64.b64encode(bio.read()).decode()
        outputs.append({
            "output_type": "display_data",
            "data": {"image/png": b64, "text/plain": ["<Figure size>"]},
            "metadata": {"image/png": {"width": 700}},
        })
        plt.close(fig)
    exec_count[0] += 1
    cells.append({
        "cell_type": "code", "execution_count": exec_count[0], "metadata": {},
        "outputs": outputs, "source": src.splitlines(keepends=True),
    })

# =====================================================================
md("""# Healthcare Metrics Project — Nurse Staffing Analysis
Full analysis pipeline: load → EDA → clean → enrich → metrics → visualize → answer the analytical questions.

**Primary source:** CMS Payroll-Based Journal (PBJ) Daily Nurse Staffing, Q2 2024
**Enrichment sources:** CMS Nursing Home Compare Provider Data Catalog (Provider Info, Survey Summary, Penalties), October 2024 release

Run this notebook from a folder containing the original uploaded CSVs (or edit `DATA_DIR` below).""")

code("""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

pd.set_option("display.max_columns", 50)
plt.rcParams["figure.dpi"] = 100

DATA_DIR = "./"  # folder containing the original CMS CSVs
""")
# Override for THIS build run only, so we execute against the real uploaded files while
# the notebook's visible source stays portable (relative path) for whoever downloads it.
ns["DATA_DIR"] = "/sessions/clever-vibrant-feynman/mnt/uploads/"

# ---------------------------------------------------------------
md("## 1. Load the primary dataset")
code("""
pbj = pd.read_csv(DATA_DIR + "PBJ_Daily_Nurse_Staffing_Q2_2024.csv",
                   dtype={"PROVNUM": str, "COUNTY_FIPS": str},
                   low_memory=False, encoding="cp1252")
print("Shape:", pbj.shape)
pbj.head(3)
""")

# ---------------------------------------------------------------
md("""## 2. Exploratory Data Analysis
Check structure, missing values, duplicates, and date range before cleaning.""")
code("""
print("Dtypes:")
print(pbj.dtypes.value_counts())
print()
print("Missing values (any column):", pbj.isna().sum().sum())
print("Duplicate rows:", pbj.duplicated().sum())
print("Duplicate PROVNUM+WorkDate pairs:", pbj.duplicated(subset=["PROVNUM","WorkDate"]).sum())
print("Unique facilities:", pbj["PROVNUM"].nunique())
print("Unique states/territories:", pbj["STATE"].nunique())
print("WorkDate range (raw int):", pbj["WorkDate"].min(), "-", pbj["WorkDate"].max())
""")

# ---------------------------------------------------------------
md("""## 3. Data Cleaning
- Convert `WorkDate` from `YYYYMMDD` integer to a real date
- Derive `Total_Nurse_Hrs` (RN + LPN + CNA — the three direct-care categories)
- Flag rows unsafe for ratio calculations: zero census, implausible ratio (>24 hrs/patient/day),
  and one known data-entry error identified during EDA (provider 145446, 2024-05-25)""")
code("""
pbj["WorkDate"] = pd.to_datetime(pbj["WorkDate"], format="%Y%m%d")
pbj["Month"] = pbj["WorkDate"].dt.to_period("M").astype(str)

pbj["Total_Nurse_Hrs"] = pbj["Hrs_RN"] + pbj["Hrs_LPN"] + pbj["Hrs_CNA"]
pbj["Total_Nurse_Hrs_emp"] = pbj["Hrs_RN_emp"] + pbj["Hrs_LPN_emp"] + pbj["Hrs_CNA_emp"]
pbj["Total_Nurse_Hrs_ctr"] = pbj["Hrs_RN_ctr"] + pbj["Hrs_LPN_ctr"] + pbj["Hrs_CNA_ctr"]

pbj["flag_zero_census"] = pbj["MDScensus"] == 0
pbj["nurse_hrs_per_census"] = np.where(pbj["MDScensus"] > 0, pbj["Total_Nurse_Hrs"] / pbj["MDScensus"], np.nan)
pbj["flag_outlier_ratio"] = pbj["nurse_hrs_per_census"] > 24
pbj["flag_data_entry_error"] = (pbj["PROVNUM"] == "145446") & (pbj["WorkDate"] == pd.Timestamp("2024-05-25"))
pbj["include_in_ratio_calcs"] = ~(pbj["flag_zero_census"] | pbj["flag_outlier_ratio"] | pbj["flag_data_entry_error"])

print("Rows flagged zero census:", pbj["flag_zero_census"].sum())
print("Rows flagged outlier ratio (>24 hrs/patient/day):", pbj["flag_outlier_ratio"].sum())
print("Rows flagged data-entry error:", pbj["flag_data_entry_error"].sum())
print("Rows excluded from ratio calcs:", (~pbj["include_in_ratio_calcs"]).sum(), "of", len(pbj))
""")

# ---------------------------------------------------------------
md("## 4. Aggregate to facility level (Q2 2024 totals)")
code("""
agg_cols = {
    "MDScensus": "mean",
    "Hrs_RN": "sum", "Hrs_RN_emp": "sum", "Hrs_RN_ctr": "sum",
    "Hrs_LPN": "sum", "Hrs_LPN_emp": "sum", "Hrs_LPN_ctr": "sum",
    "Hrs_CNA": "sum", "Hrs_CNA_emp": "sum", "Hrs_CNA_ctr": "sum",
    "Total_Nurse_Hrs": "sum", "Total_Nurse_Hrs_emp": "sum", "Total_Nurse_Hrs_ctr": "sum",
}
ratio_safe = pbj[pbj["include_in_ratio_calcs"]]

fac_q = pbj.groupby(["PROVNUM","PROVNAME","STATE","CITY","COUNTY_NAME"], as_index=False).agg(agg_cols)
ratio_by_fac = ratio_safe.groupby("PROVNUM", as_index=False)["nurse_hrs_per_census"].mean() \\
                          .rename(columns={"nurse_hrs_per_census": "avg_nurse_hrs_per_patient_day"})
fac_q = fac_q.merge(ratio_by_fac, on="PROVNUM", how="left")
fac_q["contract_share"] = fac_q["Total_Nurse_Hrs_ctr"] / fac_q["Total_Nurse_Hrs"].replace(0, np.nan)
fac_q = fac_q.rename(columns={"MDScensus": "avg_census_q2"})
print("facility-level table:", fac_q.shape)
fac_q.head(3)
""")

# ---------------------------------------------------------------
md("""## 5. Enrich with CMS Provider Info, Survey Summary, and Penalties
Joins on the shared facility key (`PROVNUM` = `CMS Certification Number (CCN)`).""")
code("""
prov = pd.read_csv(DATA_DIR + "NH_ProviderInfo_Oct2024.csv", dtype=str, encoding="cp1252")
prov_keep = prov[["CMS Certification Number (CCN)","Ownership Type","Number of Certified Beds",
                   "Overall Rating","Staffing Rating"]].rename(columns={"CMS Certification Number (CCN)":"PROVNUM"})
for c in ["Number of Certified Beds","Overall Rating","Staffing Rating"]:
    prov_keep[c] = pd.to_numeric(prov_keep[c], errors="coerce")

survey = pd.read_csv(DATA_DIR + "NH_SurveySummary_Oct2024.csv", dtype=str, encoding="cp1252")
survey["Total Number of Health Deficiencies"] = pd.to_numeric(survey["Total Number of Health Deficiencies"], errors="coerce")
survey_recent = survey[survey["Inspection Cycle"]=="1"][["CMS Certification Number (CCN)","Total Number of Health Deficiencies"]] \\
                       .rename(columns={"CMS Certification Number (CCN)":"PROVNUM"})

pen = pd.read_csv(DATA_DIR + "NH_Penalties_Oct2024.csv", dtype=str, encoding="cp1252")
pen["Fine Amount"] = pd.to_numeric(pen["Fine Amount"], errors="coerce")
pen_agg = pen.groupby("CMS Certification Number (CCN)", as_index=False).agg(
    num_penalties=("Penalty Type","count"), total_fines=("Fine Amount","sum")
).rename(columns={"CMS Certification Number (CCN)":"PROVNUM"})

fac_summary = fac_q.merge(prov_keep, on="PROVNUM", how="left") \\
                    .merge(survey_recent, on="PROVNUM", how="left") \\
                    .merge(pen_agg, on="PROVNUM", how="left")
fac_summary["num_penalties"] = fac_summary["num_penalties"].fillna(0)
fac_summary["total_fines"] = fac_summary["total_fines"].fillna(0)
print("Enriched facility table:", fac_summary.shape)
print("Join coverage (non-null Overall Rating):", fac_summary["Overall Rating"].notna().mean().round(3))
""")

# ---------------------------------------------------------------
md("""## 6. State-level rollup""")
code("""
state_q = pbj.groupby("STATE", as_index=False).agg(agg_cols)
ratio_state_q = ratio_safe.groupby("STATE", as_index=False)["nurse_hrs_per_census"].mean() \\
                           .rename(columns={"nurse_hrs_per_census":"avg_nurse_hrs_per_patient_day"})
state_q = state_q.merge(ratio_state_q, on="STATE", how="left")
state_q["contract_share"] = state_q["Total_Nurse_Hrs_ctr"] / state_q["Total_Nurse_Hrs"].replace(0, np.nan)
state_q = state_q.rename(columns={"MDScensus":"avg_census_q2"})
print("state-level table:", state_q.shape)
""")

# ---------------------------------------------------------------
md("""## 7. The Five Key Metrics

1. **Nurse-to-Patient Ratio** — (RN+LPN+CNA hours) / census
2. **Total Nurse Hours** — summed nationally / by facility / by state
3. **Contract vs. Permanent Staff Ratio** — contract hours ÷ total hours
4. **Average Patient Census**
5. **Hospitals with Highest Staffing Hours**""")
code("""
print("### Metric 1: Nurse-to-Patient Ratio ###")
print(fac_summary["avg_nurse_hrs_per_patient_day"].describe().round(2))

print("\\n### Metric 2: Total Nurse Hours (Q2 2024, national) ###")
print(f"{fac_summary['Total_Nurse_Hrs'].sum():,.0f} hours")

print("\\n### Metric 3: Contract vs Permanent Staff Ratio (national) ###")
national_contract_share = fac_summary["Total_Nurse_Hrs_ctr"].sum() / fac_summary["Total_Nurse_Hrs"].sum()
print(f"{national_contract_share:.2%} of nurse hours are contract/agency")

print("\\n### Metric 4: Average Patient Census (national) ###")
print(f"{fac_summary['avg_census_q2'].mean():.1f} residents per facility per day")

print("\\n### Metric 5: Top 10 Facilities by Total Nurse Hours ###")
top10 = fac_summary.nlargest(10, "Total_Nurse_Hrs")[["PROVNAME","STATE","Total_Nurse_Hrs","avg_census_q2"]]
print(top10.to_string(index=False))
""")

# ---------------------------------------------------------------
md("## 8. Visualizations")

code("""
fig, ax = plt.subplots(figsize=(8,4.5))
fac_summary["avg_nurse_hrs_per_patient_day"].clip(upper=10).hist(bins=50, ax=ax, color="#2563eb", edgecolor="white")
ax.set_title("Distribution of Nurse-to-Patient Ratio Across Facilities")
ax.set_xlabel("Nurse hours per patient per day")
ax.set_ylabel("Number of facilities")
ax.axvline(fac_summary["avg_nurse_hrs_per_patient_day"].median(), color="#dc2626", linestyle="--", label="Median")
ax.legend()
plt.tight_layout()
""", capture_plot=True)

code("""
top_states = state_q.sort_values("Total_Nurse_Hrs", ascending=False).head(15)
fig, ax = plt.subplots(figsize=(8,5))
ax.barh(top_states["STATE"][::-1], top_states["Total_Nurse_Hrs"][::-1], color="#2563eb")
ax.set_title("Total Nurse Hours by State — Top 15 (Q2 2024)")
ax.set_xlabel("Total nurse hours")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1e6:.1f}M"))
plt.tight_layout()
""", capture_plot=True)

code("""
daily = pbj.groupby("WorkDate").agg(
    total_nurse_hrs=("Total_Nurse_Hrs","sum"), avg_census=("MDScensus","mean")).reset_index()
daily_ratio = ratio_safe.groupby("WorkDate")["nurse_hrs_per_census"].mean().reset_index() \\
                          .rename(columns={"nurse_hrs_per_census":"avg_ratio"})
daily = daily.merge(daily_ratio, on="WorkDate", how="left")

fig, ax1 = plt.subplots(figsize=(9,4.5))
ax2 = ax1.twinx()
ax1.plot(daily["WorkDate"], daily["avg_census"], color="#2563eb", label="Avg census")
ax2.plot(daily["WorkDate"], daily["avg_ratio"], color="#f97316", label="Nurse hrs/patient/day")
ax1.set_ylabel("Avg patient census", color="#2563eb")
ax2.set_ylabel("Nurse hrs/patient/day", color="#f97316")
ax1.set_title("Daily National Trend — Patient Census vs. Nurse Staffing Ratio (Q2 2024)")
fig.autofmt_xdate()
plt.tight_layout()
""", capture_plot=True)

md("""Reported hours per resident dip every weekend while census stays flat.""")

code("""
is_weekend = daily["WorkDate"].dt.dayofweek >= 5
wk_day = daily.loc[~is_weekend, "avg_ratio"].mean()
wk_end = daily.loc[is_weekend, "avg_ratio"].mean()
print(f"Nurse hrs/resident/day: weekdays {wk_day:.2f}, weekends {wk_end:.2f} ({(wk_day - wk_end) / wk_day:.0%} lower on weekends)")
print(f"Avg census: weekdays {daily.loc[~is_weekend, 'avg_census'].mean():.1f}, weekends {daily.loc[is_weekend, 'avg_census'].mean():.1f}")
print("Lowest weekday value:", round(daily.loc[~is_weekend, "avg_ratio"].min(), 2), "| highest weekend value:", round(daily.loc[is_weekend, "avg_ratio"].max(), 2))
""")

code("""
cr = state_q.sort_values("contract_share", ascending=False).head(10)
fig, ax = plt.subplots(figsize=(8,4.5))
ax.barh(cr["STATE"][::-1], (cr["contract_share"][::-1]*100), color="#16a34a")
ax.set_title("States Relying Most on Contract Nurses (Top 10)")
ax.set_xlabel("Contract share of nurse hours (%)")
plt.tight_layout()
""", capture_plot=True)

# ---------------------------------------------------------------
md("""## 9. Answering the Five Analytical Questions""")

code("""
print("Q1: Relationship between staffing levels and patient census?")
corr_hours = fac_summary[["Total_Nurse_Hrs","avg_census_q2"]].corr().iloc[0,1]
corr_ratio = fac_summary[["avg_nurse_hrs_per_patient_day","avg_census_q2"]].corr().iloc[0,1]
print(f"  Corr(Total_Nurse_Hrs, census) = {corr_hours:.2f}  -> strong positive, hours scale with facility size")
print(f"  Corr(hrs/patient/day, census) = {corr_ratio:.2f}  -> weak negative, larger facilities run slightly leaner per-resident")
""")

code("""
print("Q2: Which hospitals have the highest staffing hours?")
print(top10[["PROVNAME","STATE","Total_Nurse_Hrs"]].to_string(index=False))
""")

code("""
print("Q3: Average staffing levels by state (top 10 by hrs/patient/day)?")
print(state_q.sort_values("avg_nurse_hrs_per_patient_day", ascending=False)
      [["STATE","avg_nurse_hrs_per_patient_day","avg_census_q2","contract_share"]].head(10).to_string(index=False))
""")

code("""
print("Q4: Which facilities have the lowest nurse-to-patient coverage? (avg census >= 30)")
low_cov = fac_summary[fac_summary["avg_census_q2"]>=30].nsmallest(10, "avg_nurse_hrs_per_patient_day")[
    ["PROVNAME","STATE","avg_nurse_hrs_per_patient_day","avg_census_q2","Overall Rating","Staffing Rating"]]
print(low_cov.to_string(index=False))
print("\\nNote: values this low usually reflect missing or unverified staffing data, not real staffing levels.")
""")

code("""
print("Q5: Are certain states relying more on contract nurses?")
print(state_q.sort_values("contract_share", ascending=False)
      [["STATE","contract_share","avg_nurse_hrs_per_patient_day"]].head(10).to_string(index=False))
""")

# ---------------------------------------------------------------
md("""## 10. Summary

- National nurse-to-patient ratio averages **3.36 hrs/resident/day** (median 3.25), with contract staff making up **7.7%** of total nurse hours nationally.
- Total nurse hours correlate strongly with census (r ≈ 0.92) — staffing scales with facility size — but the *ratio* correlates weakly negatively with census, meaning the largest facilities run slightly leaner per-resident.
- The busiest facilities by total hours are concentrated in large NYC-area SNFs.
- Near-zero computed coverage (0.00–0.16 hrs/resident/day) points to reporting problems, not real staffing: 9 of the 10 lowest-coverage facilities (census 30+) also carry CMS's lowest 1-star staffing rating and a CMS footnote for missing or unverified staffing data, so the overlap is two sources flagging the same bad data. Treat very low values as a data-quality flag.
- Reported nurse hours per resident run about 9% lower on weekends (3.14 vs. 3.45 hrs/resident/day) while census stays flat.
- Vermont, Maine, and New Hampshire lean most heavily on contract/agency nursing; six of the top ten states by contract share are in the Northeast.

See the accompanying `Healthcare_Metrics_Insights_and_Data_Dictionary.md` for full methodology notes, caveats, and the interactive `Healthcare_Metrics_Dashboard_v2.html` for a browsable version of these results.""")

# =====================================================================
notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUT = "/sessions/clever-vibrant-feynman/mnt/outputs/"
with open("/tmp/build/Healthcare_Metrics_Analysis.ipynb", "w") as f:
    json.dump(notebook, f)

print(f"\\n\\nNotebook built with {len(cells)} cells.")
