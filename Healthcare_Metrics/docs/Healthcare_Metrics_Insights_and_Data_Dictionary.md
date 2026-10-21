# Healthcare Metrics Project — Insights, Methodology & Data Dictionary

## 1. Overview

This analysis covers nurse staffing at 14,564 U.S. nursing homes across 52 states/territories over Q2 2024 (April 1 – June 30), using CMS's Payroll-Based Journal (PBJ) Daily Nurse Staffing dataset as the core source, enriched with CMS Provider Data Catalog files (Provider Information, Survey Summary, Penalties) for facility context. The goal, per the project requirements, was to understand nurse-to-patient ratios, staffing trends, contract-labor reliance, and facilities at risk of understaffing.

## 2. Data Dictionary — fields used in the analysis

### From `PBJ_Daily_Nurse_Staffing_Q2_2024.csv` (primary dataset)

| Field | Meaning |
|---|---|
| PROVNUM | 6-character facility ID (join key to all other CMS files, called CCN elsewhere) |
| PROVNAME / CITY / STATE / COUNTY_NAME | Facility identity and location |
| WorkDate | Calendar date of the staffing record (one row per facility per day) |
| MDScensus | Number of residents present that day (patient census) |
| Hrs_RN / Hrs_LPN / Hrs_CNA | Total daily hours for Registered Nurses, Licensed Practical Nurses, and Certified Nursing Assistants |
| Hrs_*_emp / Hrs_*_ctr | Same hours split into employed staff vs. contracted (agency/travel) staff |

**Derived fields created during cleaning:**
- `Total_Nurse_Hrs` = Hrs_RN + Hrs_LPN + Hrs_CNA (the three direct-care nursing categories; administrative RN/LPN and med-aide/trainee hours were excluded to keep the ratio comparable to CMS's own published "Total Nurse Staffing" definition)
- `nurse_hrs_per_census` = Total_Nurse_Hrs / MDScensus (the core staffing-intensity metric, computed only for rows with a valid, non-outlier census)
- `contract_share` = Total_Nurse_Hrs_ctr / Total_Nurse_Hrs

### From enrichment files (joined on PROVNUM / CMS Certification Number)

| Source file | Fields used | Purpose |
|---|---|---|
| NH_ProviderInfo_Oct2024.csv | Ownership Type, Number of Certified Beds, Overall Rating, Staffing Rating, Health Inspection Rating, QM Rating | Facility context and cross-validation against CMS's own star ratings |
| NH_SurveySummary_Oct2024.csv | Total Number of Health Deficiencies, Total Number of Fire Safety Deficiencies (most recent inspection cycle) | Quality/safety context alongside staffing |
| NH_Penalties_Oct2024.csv | Count of penalties, total fine amount (aggregated per facility) | Regulatory-action context alongside staffing |

## 3. Cleaning decisions

- `WorkDate` (int, `YYYYMMDD`) converted to a proper date; `PROVNUM`/CCN kept as text everywhere to preserve leading zeros.
- No missing values, duplicate rows, or negative hours were found in the source data.
- 320 rows had `MDScensus = 0` (151 of those still reported nonzero hours) — excluded from ratio calculations (can't divide by zero) but retained in hours-based totals.
- 55 rows had an implausible nurse-hours-per-patient-day ratio above 24 — excluded from ratio calculations, retained elsewhere, and flagged.
- One clear data-entry error (provider 145446, 5/25/2024, `Hrs_LPN_ctr` = 13,801.50 — a likely decimal-shift typo) was excluded from ratio calculations rather than "corrected" with a guessed value.
- All exclusions are flagged in the cleaned dataset (`include_in_ratio_calcs` column) rather than deleted, so the choice is auditable.

## 4. The five key metrics

1. **Nurse-to-Patient Ratio** — `(RN + LPN + CNA hours) / patient census`, averaged per facility per day. This is the headline staffing-adequacy metric management asked for.
2. **Total Nurse Hours** — summed by facility / state / month, to size the overall staffing footprint and spot the highest-volume facilities.
3. **Contract vs. Permanent Staff Ratio** — contract hours ÷ total nurse hours. A proxy for staffing stability and reliance on agency/travel labor, which is typically costlier and associated with more care-continuity risk.
4. **Average Patient Census** — mean daily residents per facility/state, needed as the denominator for the ratio metric and as a standalone volume indicator.
5. **Hospitals with Highest Staffing Hours** — a ranked list, useful operationally (largest facilities to monitor) and as a sanity check that hours scale with size.

## 5. Answers to the five analytical questions

**Q1 — Relationship between staffing levels and patient census?**
Total nurse hours correlate very strongly with census (r = 0.92) — larger facilities employ proportionally more staff, as expected. But the *ratio* (hours per patient) correlates weakly negatively with census (r = −0.12), meaning the largest facilities tend to run slightly *leaner* on a per-resident basis rather than richer — a mild economies-of-scale (or understaffing-risk) signal worth watching at the highest-census facilities.

**Q2 — Which hospitals have the highest staffing hours?**
The top 10 are almost all large New York City-area facilities (Isabella Geriatric Center, Coler Rehabilitation, Kings Harbor Multicare, and others), plus one Pennsylvania facility (Cedarbrook Senior Care). This reflects facility size — these are large urban SNFs with 400–700+ average daily residents, not necessarily better-staffed per patient.

**Q3 — Average staffing levels by state?**
Alaska has the highest average ratio (6.06 hrs/patient/day), followed by Puerto Rico, DC, Oregon, Hawaii, and California — a mix of small-facility/low-census states (where ratios run high per-resident) and states with historically stronger staffing mandates (CA, OR).

**Q4 — Which facilities have the lowest nurse-to-patient coverage?**
Among facilities with a meaningful census (30+ residents), the bottom 10 report 0.00–0.16 nurse hours per resident per day. That is minutes of nursing per day, which is not plausible as real staffing, so these values point to reporting problems. Nine of the ten reported zero nurse hours on 21 or more of the quarter's 91 days (one on all 91). Nine of the ten also carry CMS's lowest 1-star staffing rating, and all nine carry CMS's staffing footnote 12 (staffing data not submitted, many days without an RN onsite, or data that failed audit). That overlap shows two sources flagging the same bad data. It does not validate the metric as a measure of true staffing, so near-zero ratios should trigger a data check, not a staffing conclusion. The tenth facility (White River Healthcare, AR) reports zero hours on all 91 days yet shows a 4-star staffing rating, so the two sources disagree there — worth a manual check.

**Q5 — Are certain states relying more on contract nurses?**
Yes, notably Vermont (32.0% of nurse hours from contract staff), Maine (18.2%), New Hampshire (17.1%), Pennsylvania (15.4%), and New Jersey (15.1%) — six of the top ten states are in the Northeast.

**Additional finding — weekends.** Reported nurse hours per resident run about 9% lower on weekends: 3.14 hours on Saturdays and Sundays versus 3.45 on weekdays, while average census stays flat (83.3 vs. 83.5). Every weekend day in the quarter sits below every weekday. The data shows reported hours, not why they dip, so this is a lead for follow-up with CMS's weekend staffing fields, not a conclusion about understaffing.

## 6. Dashboard design reasoning

- **KPI cards** (facilities monitored, avg ratio, contract share, avg census) give management the headline numbers at a glance, matching the "understand nurse-to-patient ratios" and "monitor staffing levels" goals directly.
- **Daily trend chart** (census + ratio, dual-axis) shows whether staffing kept pace with patient load over the quarter, addressing the "compare staffing levels with patient load" requirement.
- **Contract vs. employed doughnut** and **state contract-reliance bar chart** speak directly to "identify overtime/contract-reliance trends."
- **State nurse-hours bar chart** and **top-10 busiest bar chart** support "monitor staffing levels across hospitals and states."
- **Lowest-coverage table** and the full sortable/filterable **facility detail table** (with CMS star ratings, deficiency counts, and fines alongside staffing) directly support "detect facilities with potential staffing shortages" — letting a user cross-reference staffing gaps against quality and compliance history in one place.

## 7. Limitations & caveats

- PBJ staffing data is self-reported by facilities; a small number of rows show reporting gaps or errors (documented in the cleaning section above).
- The ~250-facility difference between PBJ's reporting population (14,564) and the broader active-facility universe in CMS's other files (14,814) means roughly 1.7% of currently active facilities are not represented in the staffing metrics — likely non-reporters, new, or closed facilities.
- Ratios are computed on facility-wide daily averages, not shift-level or unit-level detail, so they can mask within-day or within-unit staffing gaps (e.g., weekend/night understaffing that CMS's own "weekend staffing" fields could reveal in a follow-up analysis).
