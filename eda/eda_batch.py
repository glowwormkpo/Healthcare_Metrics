import os
import pandas as pd
import numpy as np
import sys, gc

UP = os.environ.get("RAW_DIR", "raw_data/")  # folder holding the CMS source CSVs
pbj_provs = set(open(os.path.join(os.environ.get("OUT_DIR", "data/"), "pbj_provs.txt")).read().splitlines())

files = sys.argv[1:]
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
        if vals:
            overlap = len(vals & pbj_provs)
            print(f"join key '{ccn_col}': {len(vals)} unique, {overlap} overlap with PBJ providers ({overlap/len(vals)*100:.1f}%)")
    print()
    del df
    gc.collect()
