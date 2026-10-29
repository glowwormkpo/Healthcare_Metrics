"""
Step 1: Clean the primary PBJ Daily Nurse Staffing dataset.
Per requirements.md section 4 (Data Cleaning):
 - handle missing values where appropriate (none present, but document)
 - remove duplicate rows (none present)
 - ensure WorkDate is datetime
 - verify staffing hours numeric (already are)
 - check unrealistic staffing values (extreme outliers) -> flag, cap/exclude
 - create derived columns for total nurse hours
"""
import os
import pandas as pd
import numpy as np

UP = os.environ.get("RAW_DIR", "raw_data/")  # folder holding the CMS source CSVs
OUT = os.environ.get("OUT_DIR", "data/")  # where outputs are written

df = pd.read_csv(UP + "PBJ_Daily_Nurse_Staffing_Q2_2024.csv",
                  dtype={"PROVNUM": str, "COUNTY_FIPS": str},
                  low_memory=False, encoding="cp1252")

# --- date handling ---
df["WorkDate"] = pd.to_datetime(df["WorkDate"], format="%Y%m%d")
df["Month"] = df["WorkDate"].dt.to_period("M").astype(str)

# --- de-dup (defensive; EDA showed none) ---
before = len(df)
df = df.drop_duplicates(subset=["PROVNUM", "WorkDate"])
assert len(df) == before, "unexpected duplicates found"

# --- derived total nurse hours (RN + LPN + CNA, the three direct-care nursing categories) ---
df["Total_Nurse_Hrs"] = df["Hrs_RN"] + df["Hrs_LPN"] + df["Hrs_CNA"]
df["Total_Nurse_Hrs_emp"] = df["Hrs_RN_emp"] + df["Hrs_LPN_emp"] + df["Hrs_CNA_emp"]
df["Total_Nurse_Hrs_ctr"] = df["Hrs_RN_ctr"] + df["Hrs_LPN_ctr"] + df["Hrs_CNA_ctr"]

# --- outlier handling ---
# Flag: census = 0 (can't compute a ratio; census may be legitimately empty that day)
df["flag_zero_census"] = df["MDScensus"] == 0

# Flag: nurse-hours-per-patient-day ratio implausible (>24 hrs/patient/day is not physically
# sensible for a facility-wide average, since it exceeds one caregiver-day per resident)
df["nurse_hrs_per_census"] = np.where(df["MDScensus"] > 0, df["Total_Nurse_Hrs"] / df["MDScensus"], np.nan)
df["flag_outlier_ratio"] = df["nurse_hrs_per_census"] > 24

# Flag + fix the one severe data-entry error identified in EDA (PROVNUM 145446, 2024-05-25,
# Hrs_LPN_ctr = 13,801.50 -- a ~100x decimal-shift typo relative to that facility's typical
# LPN contract hours of ~5-15/day). We exclude this single record's hour columns from
# hours-based aggregates rather than guessing a "corrected" value.
mask_bad = (df["PROVNUM"] == "145446") & (df["WorkDate"] == pd.Timestamp("2024-05-25"))
df["flag_data_entry_error"] = mask_bad
print(f"Data-entry-error rows flagged: {mask_bad.sum()}")

# Build an "analysis" flag: True if the row is safe to include in ratio/rate calculations
df["include_in_ratio_calcs"] = (~df["flag_zero_census"]) & (~df["flag_outlier_ratio"]) & (~df["flag_data_entry_error"])

print("Rows total:", len(df))
print("Rows flagged zero census:", df["flag_zero_census"].sum())
print("Rows flagged outlier ratio (>24 hrs/census):", df["flag_outlier_ratio"].sum())
print("Rows excluded from ratio calcs:", (~df["include_in_ratio_calcs"]).sum())

# --- save cleaned dataset ---
df.to_pickle(OUT + "pbj_clean.pkl")
df.to_csv(OUT + "pbj_clean.csv", index=False)
print("Saved pbj_clean.pkl / pbj_clean.csv", df.shape)
