# Healthcare Metrics Project — EDA Summary

**Scope:** All 22 uploaded files — the primary PBJ nurse staffing dataset plus the full CMS Nursing Home Compare / Provider Data Catalog release (Oct 2024), COVID vaccination data (Oct 27, 2024), and the FY2024 SNF Value-Based Purchasing files.

## Join structure

Every file links on a 6-character facility ID: `PROVNUM` in the PBJ file, `CMS Certification Number (CCN)` everywhere else. Both must be read as **text, not numeric** — leading zeros are meaningful (e.g. `015009`) and Excel/pandas will silently strip them if not typed correctly. This key ties all 22 files into one facility-level model.

## Primary dataset: PBJ_Daily_Nurse_Staffing_Q2_2024.csv

- 1,325,324 rows × 33 columns — one row per provider per day.
- Perfectly complete panel: 14,564 unique providers × 91 days (Apr 1–Jun 30, 2024) = 1,325,324 rows exactly. No missing dates, no duplicate provider/date pairs, no full duplicate rows.
- Zero missing values in any column.
- `WorkDate` is stored as an integer (`YYYYMMDD`, e.g. `20240401`) — needs explicit conversion (`format="%Y%m%d"`), not a generic datetime parse (which misreads it as a Unix timestamp).
- No negative staffing hours anywhere.
- Internal consistency check passed: employed hours + contract hours reconcile exactly to the reported total for every staffing category (RN, LPN, CNA, etc.).
- **Data quality flags:**
  - 320 rows have `MDScensus = 0`; 151 of those still report nonzero staffing hours — worth a documented handling rule rather than a blanket drop, since some may be legitimate (e.g. facility temporarily emptied) vs. entry errors.
  - One clear data-entry error: provider `145446` (Marigold Rehabilitation HCC, IL), 5/25/2024, reports `Hrs_LPN_ctr = 13,801.50` for a facility with a census of 83 — almost certainly a decimal-shift typo (likely ~138). This single row is what drags the column max and skews the outlier distribution.
  - 55 rows (of 1.3M) show a total-nurse-hours-to-census ratio above 24 hours/patient/day, which is implausible and should be flagged/reviewed rather than trusted at face value.
- 52 distinct state/territory codes present (50 states + DC + PR).

## Supporting CMS files (20 files)

- **Zero full-row duplicates in every single file** — clean on that front across the board.
- Join coverage against the PBJ provider set is remarkably consistent at **~98.2–98.3%** across ProviderInfo, Ownership, SurveySummary, SurveyDates, MDS & Claims quality measures, COVID vaccination, Penalties, Health/Fire Safety citations, SNF QRP provider data, and VBP facility performance. This makes sense: those files cover ~14,814 currently-active facilities vs. PBJ's 14,564 (PBJ requires a Q2 2024 staffing submission, so the gap is likely closures, new openings, or staffing non-reporters).
- Two files use a genuinely different population and don't join to PBJ meaningfully: `Swing_Bed_SNF_data` (hospital-based swing-bed units, not standalone nursing homes) and the SNF QRP *National* data (a single national-aggregate row, not per-facility). Both are usable but belong in a separate branch of analysis, not joined 1:1 to nursing homes.
- All the "high null%" columns turned out to be structurally expected, not data quality problems: footnote columns are populated *only* when CMS suppresses or flags a value (per the footnote code table in the data dictionary), so >90% null on a footnote column is normal. Similarly, `Payment Denial Start Date/Length` in Penalties is ~89% null simply because most penalties are fines, not payment denials.

## Net assessment

This is unusually clean public data — CMS's own dictionary and consistent key structure do most of the work for us. The cleaning stage mainly needs to: (1) type PROVNUM/CCN as text everywhere, (2) convert `WorkDate` correctly, (3) decide a rule for the census=0 / outlier-ratio rows in PBJ, (4) cap or exclude the one extreme LPN-hours outlier, and (5) carry a flag for the ~250 facilities in the broader universe that don't appear in PBJ, so they don't just silently vanish from staffing-based metrics.

## Next step

Ready to move into cleaning + building the metrics (nurse-to-patient ratio, contract vs. permanent staff reliance, staffing trends by state, plus quality/citation context from the enrichment files) and then the dashboard. Let me know if you want to review/adjust anything above first, or if I should proceed straight into that build.
