"""
Step 3: Compute the 5 selected metrics and answer the 5 analytical questions
from the requirements doc, using the aggregated tables from step 2.
"""
import pandas as pd
import numpy as np

OUT = "/sessions/clever-vibrant-feynman/mnt/outputs/"

fac_summary = pd.read_csv(OUT + "facility_summary.csv", dtype={"PROVNUM": str})
state_summary = pd.read_csv(OUT + "state_summary.csv")
state_month = pd.read_csv(OUT + "state_month.csv")
daily_national = pd.read_csv(OUT + "daily_national.csv", parse_dates=["WorkDate"])

print("############ METRIC 1: Nurse-to-Patient Ratio (avg nurse hrs / patient / day) ############")
print(fac_summary["avg_nurse_hrs_per_patient_day"].describe())

print("\n############ METRIC 2: Total Nurse Hours (Q2 2024, national) ############")
print("Total nurse hours, all facilities, Q2 2024:", fac_summary["Total_Nurse_Hrs"].sum())

print("\n############ METRIC 3: Contract vs Permanent Staff Ratio (national avg) ############")
national_contract_share = fac_summary["Total_Nurse_Hrs_ctr"].sum() / fac_summary["Total_Nurse_Hrs"].sum()
print(f"National contract share of nurse hours: {national_contract_share:.2%}")

print("\n############ METRIC 4: Average Patient Census (national) ############")
print("Average census per facility per day (Q2 2024):", fac_summary["avg_census_q2"].mean())

print("\n############ METRIC 5: Hospitals with Highest Staffing Hours (Top 10) ############")
top10 = fac_summary.nlargest(10, "Total_Nurse_Hrs")[["PROVNUM", "PROVNAME", "STATE", "Total_Nurse_Hrs", "avg_census_q2"]]
print(top10.to_string())
top10.to_csv(OUT + "answer_top10_busiest.csv", index=False)

print("\n\n===================== ANALYTICAL QUESTIONS =====================")

print("\nQ1: Relationship between nurse staffing levels and patient census?")
corr = fac_summary[["Total_Nurse_Hrs", "avg_census_q2"]].corr().iloc[0, 1]
print(f"Correlation (facility-level, Total_Nurse_Hrs vs avg_census_q2): {corr:.2f}")
# Also correlate the *rate* (hrs/patient/day) against census to see if bigger facilities are understaffed per-capita
corr2 = fac_summary[["avg_nurse_hrs_per_patient_day", "avg_census_q2"]].corr().iloc[0, 1]
print(f"Correlation (avg_nurse_hrs_per_patient_day vs avg_census_q2): {corr2:.2f}")

print("\nQ2: Which hospitals have the highest staffing hours? (see answer_top10_busiest.csv)")
print(top10[["PROVNAME", "STATE", "Total_Nurse_Hrs"]].to_string(index=False))

print("\nQ3: Average staffing levels by state (top 10 by avg nurse hrs/patient/day)?")
state_rank = state_summary.sort_values("avg_nurse_hrs_per_patient_day", ascending=False)[
    ["STATE", "avg_nurse_hrs_per_patient_day", "avg_census_q2", "contract_share"]]
print(state_rank.head(10).to_string(index=False))
state_rank.to_csv(OUT + "answer_state_staffing_ranked.csv", index=False)

print("\nQ4: Which facilities have the lowest nurse-to-patient coverage? (Bottom 10, min 30-day avg census to exclude tiny/noisy facilities)")
low_cov = fac_summary[fac_summary["avg_census_q2"] >= 30].nsmallest(10, "avg_nurse_hrs_per_patient_day")[
    ["PROVNUM", "PROVNAME", "STATE", "avg_nurse_hrs_per_patient_day", "avg_census_q2", "Overall Rating", "Staffing Rating"]]
print(low_cov.to_string(index=False))
low_cov.to_csv(OUT + "answer_lowest_coverage.csv", index=False)

print("\nQ5: Are certain states relying more on contract nurses? (Top 10 by contract share)")
contract_rank = state_summary.sort_values("contract_share", ascending=False)[
    ["STATE", "contract_share", "avg_nurse_hrs_per_patient_day"]]
print(contract_rank.head(10).to_string(index=False))
contract_rank.to_csv(OUT + "answer_state_contract_reliance.csv", index=False)

print("\nDone.")
