"""
Step 4: Prepare the JSON payload the dashboard will embed.
Fixes the daily-national ratio (needs to be the mean of facility-level daily
ratios, not sum(hours)/mean(census)), and trims/rounds everything for a
reasonably sized HTML file.
"""
import os
import pandas as pd
import numpy as np
import json

OUT = os.environ.get("OUT_DIR", "data/")  # where outputs are written

df = pd.read_pickle(OUT + "pbj_clean.pkl")
df_ratio_safe = df[df["include_in_ratio_calcs"]]

# ---- correct daily national trend: mean census across facilities, mean ratio across facilities, sum hours ----
daily = df.groupby("WorkDate").agg(
    total_nurse_hrs=("Total_Nurse_Hrs", "sum"),
    total_nurse_hrs_ctr=("Total_Nurse_Hrs_ctr", "sum"),
    avg_census=("MDScensus", "mean"),
).reset_index()
daily_ratio = df_ratio_safe.groupby("WorkDate")["nurse_hrs_per_census"].mean().reset_index().rename(
    columns={"nurse_hrs_per_census": "avg_ratio"})
daily = daily.merge(daily_ratio, on="WorkDate", how="left")
daily["contract_share"] = daily["total_nurse_hrs_ctr"] / daily["total_nurse_hrs"]
daily["WorkDate"] = daily["WorkDate"].dt.strftime("%Y-%m-%d")

daily_json = [
    {"date": r.WorkDate, "avg_census": round(r.avg_census, 1), "avg_ratio": round(r.avg_ratio, 2),
     "contract_share": round(r.contract_share * 100, 2)}
    for r in daily.itertuples()
]

# ---- state summary ----
state_summary = pd.read_csv(OUT + "state_summary.csv")
state_json = [
    {"state": r.STATE, "total_hours": round(r.Total_Nurse_Hrs), "avg_census": round(r.avg_census_q2, 1),
     "avg_ratio": round(r.avg_nurse_hrs_per_patient_day, 2) if pd.notna(r.avg_nurse_hrs_per_patient_day) else None,
     "contract_share": round(r.contract_share * 100, 2) if pd.notna(r.contract_share) else None,
     "emp_hours": round(r.Total_Nurse_Hrs_emp), "ctr_hours": round(r.Total_Nurse_Hrs_ctr)}
    for r in state_summary.itertuples()
]

# ---- facility-level detail table (trimmed columns, full 14,564 rows) ----
fac = pd.read_csv(OUT + "facility_summary.csv", dtype={"PROVNUM": str})
fac_cols = fac[[
    "PROVNUM", "PROVNAME", "STATE", "CITY", "avg_census_q2", "Total_Nurse_Hrs",
    "avg_nurse_hrs_per_patient_day", "contract_share", "Ownership Type",
    "Number of Certified Beds", "Overall Rating", "Staffing Rating",
    "Total Number of Health Deficiencies", "num_penalties", "total_fines",
]].copy()
fac_cols.columns = ["provnum", "provname", "state", "city", "avg_census", "total_hours",
                     "avg_ratio", "contract_share", "ownership", "beds", "overall_rating",
                     "staffing_rating", "health_deficiencies", "num_penalties", "total_fines"]
fac_cols["avg_census"] = fac_cols["avg_census"].round(1)
fac_cols["total_hours"] = fac_cols["total_hours"].round(0)
fac_cols["avg_ratio"] = fac_cols["avg_ratio"].round(2)
fac_cols["contract_share"] = (fac_cols["contract_share"] * 100).round(2)
fac_cols["total_fines"] = fac_cols["total_fines"].round(0)
facility_json = fac_cols.to_dict(orient="records")
# pandas can't hold None in a float64 column (silently reverts to NaN), so clean at dict level
for rec in facility_json:
    for k, v in rec.items():
        if isinstance(v, float) and np.isnan(v):
            rec[k] = None

# ---- answer tables ----
top10 = pd.read_csv(OUT + "answer_top10_busiest.csv")
top10_json = [{"provname": r.PROVNAME, "state": r.STATE, "total_hours": round(r.Total_Nurse_Hrs),
                "avg_census": round(r.avg_census_q2, 1)} for r in top10.itertuples()]

lowcov = pd.read_csv(OUT + "answer_lowest_coverage.csv")
lowcov_json = []
for _, r in lowcov.iterrows():
    lowcov_json.append({
        "provname": r["PROVNAME"], "state": r["STATE"],
        "avg_ratio": round(r["avg_nurse_hrs_per_patient_day"], 2),
        "avg_census": round(r["avg_census_q2"], 1),
        "overall_rating": (None if pd.isna(r["Overall Rating"]) else int(r["Overall Rating"])),
        "staffing_rating": (None if pd.isna(r["Staffing Rating"]) else int(r["Staffing Rating"])),
    })

contract_rank = pd.read_csv(OUT + "answer_state_contract_reliance.csv")
contract_rank_json = [{"state": r.STATE, "contract_share": round(r.contract_share * 100, 2),
                        "avg_ratio": round(r.avg_nurse_hrs_per_patient_day, 2)} for r in contract_rank.itertuples()]

# ---- national KPIs ----
national_contract_share = fac["Total_Nurse_Hrs_ctr"].sum() / fac["Total_Nurse_Hrs"].sum()
kpis = {
    "total_facilities": int(fac["PROVNUM"].nunique()),
    "total_hours": round(fac["Total_Nurse_Hrs"].sum()),
    "avg_ratio": round(fac["avg_nurse_hrs_per_patient_day"].mean(), 2),
    "contract_share": round(national_contract_share * 100, 2),
    "avg_census": round(fac["avg_census_q2"].mean(), 1),
    "num_states": int(fac["STATE"].nunique()),
}

payload = {
    "kpis": kpis,
    "daily": daily_json,
    "states": state_json,
    "facilities": facility_json,
    "top10_busiest": top10_json,
    "lowest_coverage": lowcov_json,
    "contract_reliance": contract_rank_json,
}

with open(OUT + "dashboard_data.json", "w") as f:
    json.dump(payload, f)

print("KPIs:", kpis)
print("daily rows:", len(daily_json))
print("state rows:", len(state_json))
print("facility rows:", len(facility_json))
print("JSON file size (MB):", round(__import__("os").path.getsize(OUT + "dashboard_data.json") / 1e6, 2))
