# Bengaluru Air Pollution Analysis — DEV EDA Submission

**Team:** Shreyas · Yajash · Adarsh · Abhigyan  
**Topic:** Air Pollution Data Analysis in Bengaluru — based on the earlier DEV PPT.  
**Period:** 2015-01-01 through 2016-12-31; **granularity:** one city-level observation per calendar day.

## Sources and provenance

- **Original real-world data:** [Kaggle — Air Quality Data in India (2015–2020)](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india), compiled from the **Central Pollution Control Board (CPCB)** data.
- **Specific public subset analyzed:** [`city_day.csv` public GitHub copy](https://github.com/edusatyaki/DataAnalyticsProjrectIdeas/blob/main/01_National_Air_Quality/data/Google%20Sheets%20Datasheets/city_day.csv). This file contains the 2015–2016 extract. The pipeline filters it to the 731 Bengaluru rows.
- **Official live reference:** [data.gov.in CPCB AQI resource](https://www.data.gov.in/resource/real-time-air-quality-index-various-locations). This is *not* the historical dataset used to compute the figures below.
- **GitHub code:** https://github.com/Abhigyan-Shekhar/bengaluru-air-pollution-eda

The published historical dataset is not a live view of air quality in 2026. It also does **not** support station-level or hourly findings.

## Run the analysis end-to-end

```bash
python -m pip install -r requirements.txt
python analysis.py --download --input data/city_day.csv --out outputs
```

This downloads the actual public source CSV and runs the analysis. To avoid an external download, place the source CSV under `data/city_day.csv` and run without `--download`.

The script creates `outputs/analysis_summary.json`, `outputs/descriptive_statistics.csv`, `outputs/missing_outlier_audit.csv`, `outputs/before_cleaning_preview.csv`, `outputs/after_cleaning_preview.csv`, `outputs/multivariate_correlation.csv`, `outputs/cleaned_bengaluru_2015_2016.csv`, `outputs/chart_interpretations.csv`, and eleven **full daily-data charts** under `outputs/charts/` (histogram, categorical bars, time series, year, season, boxplot, two true daily scatter plots, correlations, heatmap and a severity-group chart).

The PowerPoint's charts are **verified summary graphics** produced from the same genuine 731-row extract. The full daily-data scatterplots and boxplots are produced on your machine when you execute `analysis.py`; they are *not* fabricated in advance.

## Ten objectives, analyses and preliminary results

| # | Objective | Verified finding for 2015–2016 extract | Chart / evidence |
|---|---|---|---|
| 1 | Audit coverage, missingness, duplicates, invalid values and IQR outliers | 731 rows; 94 missing AQI, 120 missing PM2.5, 331 missing PM10; 0 duplicate city-days; 13 AQI IQR outliers flagged | QA audit, missingness, outlier charts |
| 2 | Describe the distribution of AQI | mean 108.72, median 101, P90 175, range 20–342 across 637 observed AQI days | Histogram and descriptive statistics |
| 3 | Estimate AQI severity-category frequencies | Moderate 292, Satisfactory 249, Good 65, Poor 27, Very Poor 4, Severe 0 | Category bars |
| 4 | Determine how AQI changes month by month | July 2015 mean 160.55, August 2016 mean 64.54; Jan–Feb 2015 have no observed AQI | Monthly line plot |
| 5 | Compare year-wise mean AQI and coverage | 2015 112.57 on 286 days vs 2016 105.58 on 351 days | Annual bars, with counts |
| 6 | Compare mean AQI across seasons | Winter 122.42; pre-monsoon 111.65; monsoon 101.71; post-monsoon 104.25 | Seasonal bars |
| 7 | Compare observed weekdays and weekends | Weekdays 107.07 on 454 days vs weekends 112.83 on 183 days | Group comparison; true daily-data boxplot when run |
| 8 | Quantify AQI association with PM2.5 and PM10 | PM2.5 r = 0.296 (n=603); PM10 r = 0.529 (n=391) | Two scatterplots when run; correlation bars |
| 9 | Quantify relationships of gaseous pollutants with AQI | CO r=.344 (n=628), NO2 r=.157 (n=636), SO2 r=.102 (n=636), O3 r=.081 (n=572) | Correlation bar chart |
| 10 | Understand multivariate pollutant co-variation | PM2.5–NO2 r=.446; PM10–NO2 r=.439; PM2.5–PM10 r=.341 | Seven-variable heatmap |

All correlations are Pearson pairwise-complete observational correlations and are **not causal claims**. Sample sizes differ because of missingness; these values must be interpreted with care. AQI is constructed using pollutant information, so relationships with pollutant variables are partly mechanical, not independent causes.

## Data cleaning — before / after

1. **Data types:** parse `Date` with `pd.to_datetime` and pollutants/AQI with `pd.to_numeric(errors='coerce')`.
2. **Duplicates:** identify and drop duplicate `City` + `Date` records (none detected in the extracted sample).
3. **Invalid data:** convert negative numeric values and invalid dates to null, with an audit count (none detected in the tested core numeric fields).
4. **Missing values:** preserve `NaN` in observed AQI and pollutant columns; report missingness for each field. Add optional clearly named `*_imputed` and `*_was_imputed` pollutant columns for possible subsequent ML scenarios, but **never use imputed values in the reported correlations or AQI statistics**. `Xylene` is entirely missing in this extract and must not be interpreted.
5. **Outliers:** flag points beyond Tukey's 1.5×IQR fences. Do not automatically remove severe pollution observations; flag them for review and test sensitivity if needed.
6. **AQI categories:** rederive categories from valid AQI values and compare with the source labels; zero label mismatches were detected.

Before/after examples can be found in the PPT and in `outputs/` after you run the pipeline. **No missing AQI is artificially invented.**

## Chart explanations (marking requirement)

Each of the 11 chart slides in the PPT contains four explicitly labeled fields: **why this chart**, **pattern observed**, **what it indicates**, and **conclusion**. When you run `analysis.py`, the complete, auditable mapping is also exported as `outputs/chart_interpretations.csv`.

## Insights

- In the observed sample, Satisfactory and Moderate conditions dominate; Good represents 65 of 637 recorded-AQI days.
- PM10 has the strongest positive pairwise AQI association among six plotted pollutants (r=.529), but PM10's large missing fraction and differing paired samples caution against treating it as the sole driver.
- Mean observed AQI is higher in winter than during the monsoon; unequal data coverage and no weather controls limit interpretation.
- The sample contains high-AQI episodes up to 342; clipping or deleting them without evidence would conceal potentially meaningful events.

## Limitations

- The data are historical (2015–2016), not current and not directly representative of 2026.
- City-day observations cannot reveal hourly rush-hour peaks or neighborhood/station hotspots.
- Missingness is substantial and may not be random; annual and seasonal comparisons have unequal coverage.
- The dataset contains no contemporaneous meteorological, traffic, population-exposure or intervention variables to isolate causes.
- The data are a downstream public GitHub extract of the Kaggle/CPCB original; for publication or new analysis, check upstream provenance and coverage.

## Future scope

Expand to the complete historical city dataset, obtain long-term station/hourly CPCB or OpenAQ history, add weather and traffic covariates, evaluate sensitivity to missingness and outliers, and consider time-series forecasting with proper chronological validation.

## Suggested GitHub repository structure

Upload all repository files; optionally omit large generated chart files if size is an issue, but keep evidence and your presentation. GitHub repository: https://github.com/Abhigyan-Shekhar/bengaluru-air-pollution-eda