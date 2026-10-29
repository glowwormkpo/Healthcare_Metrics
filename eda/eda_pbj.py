import os
import pandas as pd
import numpy as np

path = os.path.join(os.environ.get("RAW_DIR", "raw_data/"), "PBJ_Daily_Nurse_Staffing_Q2_2024.csv")

df = pd.read_csv(path, dtype={"PROVNUM": str, "COUNTY_FIPS": str}, low_memory=False, encoding="cp1252")

print("=== SHAPE ===")
print(df.shape)

print("\n=== DTYPES ===")
print(df.dtypes)

print("\n=== DATE RANGE ===")
df["WorkDate_parsed"] = pd.to_datetime(df["WorkDate"], format="%Y%m%d", errors="coerce")
print("WorkDate min/max:", df["WorkDate_parsed"].min(), df["WorkDate_parsed"].max())
print("Unparseable dates:", df["WorkDate_parsed"].isna().sum())
print("Unique CY_Qtr values:", df["CY_Qtr"].unique())

print("\n=== MISSING VALUES (top 15) ===")
print(df.isna().sum().sort_values(ascending=False).head(15))

print("\n=== DUPLICATE ROWS (full) ===")
print(df.duplicated().sum())

print("\n=== DUPLICATE on PROVNUM+WorkDate (should be unique key) ===")
print(df.duplicated(subset=["PROVNUM", "WorkDate"]).sum())

print("\n=== UNIQUE PROVIDERS / STATES ===")
print("Unique PROVNUM:", df["PROVNUM"].nunique())
print("Unique STATE:", df["STATE"].nunique())
print("States list:", sorted(df["STATE"].dropna().unique().tolist()))

print("\n=== MDScensus stats ===")
print(df["MDScensus"].describe())
print("Zero census rows:", (df["MDScensus"] == 0).sum())
print("Negative census rows:", (df["MDScensus"] < 0).sum())

hrs_cols = [c for c in df.columns if c.startswith("Hrs_")]
print("\n=== Hours columns:", hrs_cols)
print(df[hrs_cols].describe().T[["min","max","mean","std"]])

print("\n=== Negative hours check ===")
for c in hrs_cols:
    neg = (df[c] < 0).sum()
    if neg > 0:
        print(f"{c}: {neg} negative values")

print("\n=== Outlier check: total nurse hours vs census (potential unrealistic ratios) ===")
df["Total_Nurse_Hrs"] = df["Hrs_RN"] + df["Hrs_LPN"] + df["Hrs_CNA"]
df["ratio"] = df["Total_Nurse_Hrs"] / df["MDScensus"].replace(0, np.nan)
print(df["ratio"].describe())
print("Rows with census=0 but nonzero hours:", ((df["MDScensus"]==0) & (df["Total_Nurse_Hrs"]>0)).sum())
print("Rows with ratio > 24 (>24 nurse-hrs per patient per day, implausible):", (df["ratio"] > 24).sum())

print("\n=== emp+ctr = total consistency check (Hrs_RN) ===")
mismatch = (df["Hrs_RN_emp"].fillna(0) + df["Hrs_RN_ctr"].fillna(0) - df["Hrs_RN"]).abs()
print("Max abs mismatch RN emp+ctr vs total:", mismatch.max())
print("Rows with mismatch > 0.01:", (mismatch > 0.01).sum())

print("\n=== Sample rows ===")
print(df.head(3).to_string())
