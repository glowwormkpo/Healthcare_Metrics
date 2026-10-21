"""
Step 2: Aggregate cleaned PBJ staffing to useful grains and enrich with
ProviderInfo / SurveySummary / Penalties context (facility-level attributes).
Produces the tables the metrics + dashboard scripts consume.
"""
import pandas as pd
import numpy as np

UP = "/sessions/clever-vibrant-feynman/mnt/uploads/"
OUT = "/sessions/clever-vibrant-feynman/mnt/outputs/"

df = pd.read_pickle(OUT + "pbj_clean.pkl")

# ---------------------------------------------------------------
# 1. Facility x Day (already have it) -> Facility x Month aggregate
# ---------------------------------------------------------------
agg_cols = {
    "MDScensus": "mean",
    "Hrs_RN": "sum", "Hrs_RN_emp": "sum", "Hrs_RN_ctr": "sum",
    "Hrs_LPN": "sum", "Hrs_LPN_emp": "sum", "Hrs_LPN_ctr": "sum",
    "Hrs_CNA": "sum", "Hrs_CNA_emp": "sum", "Hrs_CNA_ctr": "sum",
    "Total_Nurse_Hrs": "sum", "Total_Nurse_Hrs_emp": "sum", "Total_Nurse_Hrs_ctr": "sum",
}
# For the ratio-safe subset, compute mean daily ratio too
df_ratio_safe = df[df["include_in_ratio_calcs"]]

fac_month = df.groupby(["PROVNUM", "PROVNAME", "STATE", "CITY", "COUNTY_NAME", "Month"], as_index=False).agg(agg_cols)
ratio_by_month = df_ratio_safe.groupby(["PROVNUM", "Month"], as_index=False)["nurse_hrs_per_census"].mean().rename(
    columns={"nurse_hrs_per_census": "avg_nurse_hrs_per_patient_day"})
fac_month = fac_month.merge(ratio_by_month, on=["PROVNUM", "Month"], how="left")
fac_month["contract_share"] = fac_month["Total_Nurse_Hrs_ctr"] / fac_month["Total_Nurse_Hrs"].replace(0, np.nan)

fac_month.to_csv(OUT + "facility_month.csv", index=False)
print("facility_month.csv:", fac_month.shape)

# ---------------------------------------------------------------
# 2. Facility x full quarter (Q2 2024) summary, for a single facility-level table
# ---------------------------------------------------------------
fac_q = df.groupby(["PROVNUM", "PROVNAME", "STATE", "CITY", "COUNTY_NAME"], as_index=False).agg(agg_cols)
ratio_by_fac = df_ratio_safe.groupby("PROVNUM", as_index=False)["nurse_hrs_per_census"].mean().rename(
    columns={"nurse_hrs_per_census": "avg_nurse_hrs_per_patient_day"})
fac_q = fac_q.merge(ratio_by_fac, on="PROVNUM", how="left")
fac_q["contract_share"] = fac_q["Total_Nurse_Hrs_ctr"] / fac_q["Total_Nurse_Hrs"].replace(0, np.nan)
fac_q = fac_q.rename(columns={"MDScensus": "avg_census_q2"})

# ---------------------------------------------------------------
# 3. Enrichment: ProviderInfo (ownership type, beds, ratings), SurveySummary (deficiencies), Penalties
# ---------------------------------------------------------------
prov = pd.read_csv(UP + "NH_ProviderInfo_Oct2024.csv", dtype=str, encoding="cp1252")
prov_keep = prov[[
    "CMS Certification Number (CCN)", "Ownership Type", "Number of Certified Beds",
    "Provider Type", "Overall Rating", "Staffing Rating", "Health Inspection Rating",
    "QM Rating", "Continuing Care Retirement Community", "Special Focus Status", "Abuse Icon",
]].rename(columns={"CMS Certification Number (CCN)": "PROVNUM"})
for c in ["Number of Certified Beds", "Overall Rating", "Staffing Rating", "Health Inspection Rating", "QM Rating"]:
    prov_keep[c] = pd.to_numeric(prov_keep[c], errors="coerce")

survey = pd.read_csv(UP + "NH_SurveySummary_Oct2024.csv", dtype=str, encoding="cp1252")
survey["Total Number of Health Deficiencies"] = pd.to_numeric(survey["Total Number of Health Deficiencies"], errors="coerce")
survey["Total Number of Fire Safety Deficiencies"] = pd.to_numeric(survey["Total Number of Fire Safety Deficiencies"], errors="coerce")
# Survey summary has 1 row per provider per inspection cycle; keep most recent cycle (Inspection Cycle == 1)
survey_recent = survey[survey["Inspection Cycle"] == "1"][[
    "CMS Certification Number (CCN)", "Total Number of Health Deficiencies", "Total Number of Fire Safety Deficiencies"
]].rename(columns={"CMS Certification Number (CCN)": "PROVNUM"})

pen = pd.read_csv(UP + "NH_Penalties_Oct2024.csv", dtype=str, encoding="cp1252")
pen["Fine Amount"] = pd.to_numeric(pen["Fine Amount"], errors="coerce")
pen_agg = pen.groupby("CMS Certification Number (CCN)", as_index=False).agg(
    num_penalties=("Penalty Type", "count"),
    total_fines=("Fine Amount", "sum"),
).rename(columns={"CMS Certification Number (CCN)": "PROVNUM"})

fac_summary = fac_q.merge(prov_keep, on="PROVNUM", how="left") \
                    .merge(survey_recent, on="PROVNUM", how="left") \
                    .merge(pen_agg, on="PROVNUM", how="left")
fac_summary["num_penalties"] = fac_summary["num_penalties"].fillna(0)
fac_summary["total_fines"] = fac_summary["total_fines"].fillna(0)

fac_summary.to_csv(OUT + "facility_summary.csv", index=False)
print("facility_summary.csv:", fac_summary.shape)
print(fac_summary.head(3).to_string())

# ---------------------------------------------------------------
# 4. State x Month aggregate (for dashboard trend charts)
# ---------------------------------------------------------------
state_month = df.groupby(["STATE", "Month"], as_index=False).agg(agg_cols)
ratio_state_month = df_ratio_safe.groupby(["STATE", "Month"], as_index=False)["nurse_hrs_per_census"].mean().rename(
    columns={"nurse_hrs_per_census": "avg_nurse_hrs_per_patient_day"})
state_month = state_month.merge(ratio_state_month, on=["STATE", "Month"], how="left")
state_month["contract_share"] = state_month["Total_Nurse_Hrs_ctr"] / state_month["Total_Nurse_Hrs"].replace(0, np.nan)
state_month.to_csv(OUT + "state_month.csv", index=False)
print("state_month.csv:", state_month.shape)

# ---------------------------------------------------------------
# 5. State x full quarter summary
# ---------------------------------------------------------------
state_q = df.groupby("STATE", as_index=False).agg(agg_cols)
ratio_state_q = df_ratio_safe.groupby("STATE", as_index=False)["nurse_hrs_per_census"].mean().rename(
    columns={"nurse_hrs_per_census": "avg_nurse_hrs_per_patient_day"})
state_q = state_q.merge(ratio_state_q, on="STATE", how="left")
state_q["contract_share"] = state_q["Total_Nurse_Hrs_ctr"] / state_q["Total_Nurse_Hrs"].replace(0, np.nan)
state_q = state_q.rename(columns={"MDScensus": "avg_census_q2"})
state_q.to_csv(OUT + "state_summary.csv", index=False)
print("state_summary.csv:", state_q.shape)

# ---------------------------------------------------------------
# 6. Daily national trend (for a simple time series)
# ---------------------------------------------------------------
daily = df.groupby("WorkDate", as_index=False).agg(agg_cols)
daily["contract_share"] = daily["Total_Nurse_Hrs_ctr"] / daily["Total_Nurse_Hrs"].replace(0, np.nan)
daily.to_csv(OUT + "daily_national.csv", index=False)
print("daily_national.csv:", daily.shape)

print("\nDone.")
