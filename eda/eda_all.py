import pandas as pd
import numpy as np
import gc, os

UP = "/sessions/clever-vibrant-feynman/mnt/uploads/"

files = [
    "NH_ProviderInfo_Oct2024.csv",
    "NH_Ownership_Oct2024.csv",
    "NH_SurveySummary_Oct2024.csv",
    "NH_HealthCitations_Oct2024.csv",
    "NH_FireSafetyCitations_Oct2024.csv",
    "NH_QualityMsr_MDS_Oct2024.csv",
    "NH_QualityMsr_Claims_Oct2024.csv",
    "NH_SurveyDates_Oct2024.csv",
    "NH_Penalties_Oct2024.csv",
    "NH_CovidVaxProvider_20241027.csv",
    "NH_CovidVaxAverages_20241027.csv",
    "NH_StateUSAverages_Oct2024.csv",
    "NH_HlthInspecCutpointsState_Oct2024.csv",
    "NH_DataCollectionIntervals_Oct2024.csv",
    "NH_CitationDescriptions_Oct2024.csv",
    "Skilled_Nursing_Facility_Quality_Reporting_Program_Provider_Data_Oct2024.csv",
    "Skilled_Nursing_Facility_Quality_Reporting_Program_National_Data_Oct2024.csv",
    "Swing_Bed_SNF_data_Oct2024.csv",
    "FY_2024_SNF_VBP_Facility_Performance.csv",
    "FY_2024_SNF_VBP_Aggregate_Performance.csv",
]

# PBJ provider set for join coverage check
pbj_provs = set(pd.read_csv(UP+"PBJ_Daily_Nurse_Staffing_Q2_2024.csv", usecols=["PROVNUM"], dtype=str, encoding="cp1252")["PROVNUM"].unique())
print(f"PBJ unique providers: {len(pbj_provs)}\n")

ccn_col_candidates = ["CMS Certification Number (CCN)", "PROVNUM"]

for f in files:
    path = UP + f
    try:
        df = pd.read_csv(path, dtype=str, low_memory=False, encoding="cp1252")
    except Exception as e:
        print(f"{f}: FAILED TO READ - {e}")
        continue
    print(f"=== {f} ===")
    print(f"shape: {df.shape}")
    dup = df.duplicated().sum()
    print(f"full duplicate rows: {dup}")
    null_pct = (df.isna().mean()*100).round(1)
    high_null = null_pct[null_pct > 20].sort_values(ascending=False)
    if len(high_null) > 0:
        print(f"columns >20% null: {dict(high_null.head(8))}")
    else:
        print("no columns with >20% null")
    ccn_col = next((c for c in ccn_col_candidates if c in df.columns), None)
    if ccn_col:
        vals = set(df[ccn_col].dropna().unique())
        overlap = len(vals & pbj_provs)
        print(f"join key '{ccn_col}': {len(vals)} unique, {overlap} overlap with PBJ providers ({overlap/len(vals)*100:.1f}% of file's keys found in PBJ)" if vals else "no values")
    print()
    del df
    gc.collect()
