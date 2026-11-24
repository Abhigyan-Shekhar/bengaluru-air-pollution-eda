"""Reproducible Bengaluru air quality EDA (historical city-day records, 2015–2016)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import urlretrieve

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DATA_URL = ("https://raw.githubusercontent.com/edusatyaki/DataAnalyticsProjrectIdeas/"
            "main/01_National_Air_Quality/data/Google%20Sheets%20Datasheets/city_day.csv")
POLLUTANTS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]
CORE = ["AQI"] + POLLUTANTS
ALL_NUMERIC = ["PM2.5", "PM10", "NO", "NO2", "NOx", "NH3",
               "CO", "SO2", "O3", "Benzene", "Toluene", "Xylene", "AQI"]
CHARTS = Path("outputs/charts")


def load_data(path: str | Path) -> pd.DataFrame:
    data = pd.read_csv(path, low_memory=False)
    data.columns = data.columns.str.strip()
    data["City"] = data["City"].astype("string").str.strip()
    return data.loc[data["City"].str.lower() == "bengaluru"].copy()


def aqi_category(value):
    if pd.isna(value):
        return np.nan
    if value <= 50: return "Good"
    if value <= 100: return "Satisfactory"
    if value <= 200: return "Moderate"
    if value <= 300: return "Poor"
    if value <= 400: return "Very Poor"
    return "Severe"


def season(month):
    if month in (12, 1, 2): return "Winter"
    if month in (3, 4, 5): return "Pre-monsoon"
    if month in (6, 7, 8, 9): return "Monsoon"
    return "Post-monsoon"


def iqr_bounds(series: pd.Series):
    observed = series.dropna()
    if len(observed) < 4:
        return float("nan"), float("nan")
    q1, q3 = observed.quantile([.25, .75])
    iqr = q3 - q1
    return float(q1 - 1.5 * iqr), float(q3 + 1.5 * iqr)


def audit_and_clean(raw: pd.DataFrame):
    data = raw.copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    invalid_dates = int(data["Date"].isna().sum())
    duplicates = int(data.duplicated(subset=["City", "Date"]).sum())
    bad_values = {}
    for field in ALL_NUMERIC:
        if field not in data:
            data[field] = np.nan
        values = pd.to_numeric(data[field], errors="coerce")
        bad_values[field] = int((values < 0).sum())
        data[field] = values.mask(values < 0)
    missing_before = {field: int(data[field].isna().sum()) for field in ALL_NUMERIC}
    data = data.dropna(subset=["Date"]).drop_duplicates(["City", "Date"]).sort_values("Date").reset_index(drop=True)
    iqr_outliers = {}
    for field in CORE:
        low, high = iqr_bounds(data[field])
        data[field + "_iqr_outlier"] = data[field].notna() & ((data[field] < low) | (data[field] > high))
        iqr_outliers[field] = int(data[field + "_iqr_outlier"].sum())
    # Keep original observed measurements; optional imputations are separately labelled.
    for field in POLLUTANTS:
        data[field + "_was_imputed"] = data[field].isna()
        data[field + "_imputed"] = data[field].fillna(data[field].median())
    data["AQI_Bucket"] = data["AQI"].apply(aqi_category)
    data["year"] = data["Date"].dt.year
    data["month"] = data["Date"].dt.month
    data["season"] = data["month"].map(season)
    data["daytype"] = np.where(data["Date"].dt.dayofweek >= 5, "Weekend", "Weekday")
    quality = {
        "raw_rows": int(len(raw)), "clean_rows": int(len(data)),
        "duplicates_city_date": duplicates,
        "invalid_dates": invalid_dates,
        "invalid_negative_values": bad_values,
        "missing_before": missing_before,
        "missing_after": {field: int(data[field].isna().sum()) for field in ALL_NUMERIC},
        "iqr_outliers": iqr_outliers,
    }
    return data, quality


def _stat(series: pd.Series):
    s = series.dropna()
    return {"n": int(len(s)), "mean": round(float(s.mean()), 2) if len(s) else None,
            "median": round(float(s.median()), 2) if len(s) else None,
            "min": round(float(s.min()), 2) if len(s) else None,
            "max": round(float(s.max()), 2) if len(s) else None}


def _groups(frame, group):
    return {str(k): _stat(g["AQI"]) for k, g in frame.groupby(group, observed=True)}


def summarize(df, quality):
    return {
        "rows": int(len(df)),
        "observed_aqi": int(df["AQI"].notna().sum()),
        "aqi": _stat(df["AQI"]),
        "aqi_p90": round(float(df["AQI"].quantile(.9)), 2),
        "categories": {str(k): int(v) for k, v in df["AQI_Bucket"].value_counts().items()},
        "year": _groups(df, "year"),
        "season": _groups(df, "season"),
        "daytype": _groups(df, "daytype"),
        "monthly": _groups(df.assign(year_month=df["Date"].dt.strftime("%Y-%m")), "year_month"),
        "aqi_correlations": {
            field: {"n": int(df[["AQI", field]].dropna().shape[0]),
                    "r": round(float(df["AQI"].corr(df[field])), 3)}
            for field in POLLUTANTS
        },
        "quality": quality,
    }


def _save(fig, name):
    CHARTS.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHARTS / name, dpi=160, bbox_inches="tight")
    plt.close(fig)


def make_plots(df):
    CHARTS.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"figure.figsize": (9, 5), "font.size": 10})
    missing = df[CORE].isna().sum().sort_values(ascending=False)
    fig, ax = plt.subplots()
    missing.plot.bar(ax=ax)
    ax.set(title="Missing readings by variable", ylabel="Missing daily records")
    _save(fig, "01_missingness.png")

    fig, ax = plt.subplots()
    ax.hist(df["AQI"].dropna(), bins=22, edgecolor="white")
    ax.set(title="Distribution of observed AQI", xlabel="AQI", ylabel="Days")
    _save(fig, "02_aqi_histogram.png")

    categories = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
    fig, ax = plt.subplots()
    df["AQI_Bucket"].value_counts().reindex(categories, fill_value=0).plot.bar(ax=ax)
    ax.set(title="Days in each AQI category", ylabel="Observed days")
    _save(fig, "03_aqi_categories.png")

    fig, ax = plt.subplots(figsize=(12, 4))
    df.set_index("Date")["AQI"].resample("MS").mean().plot(ax=ax, marker="o")
    ax.set(title="Mean AQI by month (missing months remain blank)", ylabel="Mean AQI")
    _save(fig, "04_monthly_trend.png")

    fig, ax = plt.subplots()
    df.groupby("year")["AQI"].mean().plot.bar(ax=ax)
    ax.set(title="Observed mean AQI by year", ylabel="Mean AQI")
    _save(fig, "05_year_comparison.png")

    fig, ax = plt.subplots()
    df.groupby("season")["AQI"].mean().reindex(
        ["Winter", "Pre-monsoon", "Monsoon", "Post-monsoon"]).plot.bar(ax=ax)
    ax.set(title="Observed AQI by season", ylabel="Mean AQI")
    _save(fig, "06_seasons.png")

    fig, ax = plt.subplots()
    [ax.boxplot([df.loc[df["daytype"] == label, "AQI"].dropna() for label in
                 ("Weekday", "Weekend")], tick_labels=["Weekday", "Weekend"])]
    ax.set(title="Weekday versus weekend AQI", ylabel="AQI")
    _save(fig, "07_weekday_weekend_boxplot.png")

    for index, field in enumerate(("PM2.5", "PM10"), 8):
        pair = df[[field, "AQI"]].dropna()
        fig, ax = plt.subplots()
        ax.scatter(pair[field], pair["AQI"], alpha=.35, s=16)
        ax.set(title=f"{field} versus AQI (n={len(pair)}; r={pair[field].corr(pair['AQI']):.3f})",
               xlabel=field, ylabel="AQI")
        _save(fig, f"{index:02d}_{field.replace('.', '')}_scatter.png")

    correlations = df[POLLUTANTS].corrwith(df["AQI"]).sort_values()
    fig, ax = plt.subplots()
    correlations.plot.barh(ax=ax)
    ax.set(title="Pearson association with AQI (pairwise complete)", xlabel="Pearson r")
    _save(fig, "10_aqi_correlations.png")

    corr = df[CORE].corr()
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(corr, vmin=-1, vmax=1, cmap="coolwarm")
    ax.set_xticks(range(len(CORE)), CORE, rotation=45, ha="right")
    ax.set_yticks(range(len(CORE)), CORE)
    for i in range(len(CORE)):
        for j in range(len(CORE)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax)
    ax.set(title="Multivariate pollutant correlation")
    _save(fig, "11_multivariate_heatmap.png")


def export_evidence(raw, df, quality, summary, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "cleaned_bengaluru_2015_2016.csv", index=False)
    df[CORE].describe().T.to_csv(out / "descriptive_statistics.csv")
    df[CORE].corr().to_csv(out / "multivariate_correlation.csv")
    raw.head(12).to_csv(out / "before_cleaning_preview.csv", index=False)
    df.head(12).to_csv(out / "after_cleaning_preview.csv", index=False)
    pd.DataFrame([
        {"field": f, "missing_before": quality["missing_before"][f],
         "missing_after": quality["missing_after"][f],
         "invalid_negative": quality["invalid_negative_values"][f],
         "iqr_outliers": quality["iqr_outliers"].get(f, 0)}
        for f in ALL_NUMERIC
    ]).to_csv(out / "missing_outlier_audit.csv", index=False)
    interpretations = [
        ("01_missingness.png", "Bar chart quantifies data gaps", "PM10 has many missing days", "Coverage differs by pollutant", "Compare paired counts before conclusions"),
        ("02_aqi_histogram.png", "Histogram shows numeric distribution", "Median near 101 and a high tail", "High-AQI episodes exist", "Retain valid extreme readings"),
        ("03_aqi_categories.png", "Ordered bars compare severity classes", "Moderate and Satisfactory dominate", "Air quality varies in severity", "Include both categories and counts"),
        ("04_monthly_trend.png", "Line plot follows time", "Monthly averages fluctuate", "Potential seasonal variation", "Missing periods limit comparison"),
        ("05_year_comparison.png", "Bars compare two years", "2015 mean is above 2016", "Observed samples differ", "Account for unequal reporting"),
        ("06_seasons.png", "Bars compare defined season groups", "Winter average is higher", "Seasonal association is plausible", "No causal inference without meteorology"),
        ("07_weekday_weekend_boxplot.png", "Boxplot shows spread and medians", "Weekend and weekday distributions overlap", "Day-type contrast is modest", "Avoid overclaiming traffic causality"),
        ("08_PM25_scatter.png", "Scatter shows paired days", "Positive but noisy association", "PM2.5 alone does not explain AQI", "Use correlation with n"),
        ("09_PM10_scatter.png", "Scatter shows paired days", "Stronger positive association", "PM10 and AQI move together in observed pairs", "Missing PM10 limits generalization"),
        ("10_aqi_correlations.png", "Bars compare Pearson coefficients", "PM10 has largest displayed r", "Associations differ by pollutant", "Not proof of causation"),
        ("11_multivariate_heatmap.png", "Matrix compares many pairs", "Several particulate/NO2 relationships positive", "Pollutants can co-vary", "Need source and weather data for attribution"),
    ]
    pd.DataFrame(interpretations, columns=[
        "chart", "why_this_chart", "observed_pattern", "what_it_indicates", "conclusion"
    ]).to_csv(out / "chart_interpretations.csv", index=False)
    (out / "analysis_summary.json").write_text(json.dumps(summary, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--input", default="data/city_day.csv")
    ap.add_argument("--out", default="outputs")
    args = ap.parse_args()
    source = Path(args.input)
    source.parent.mkdir(parents=True, exist_ok=True)
    if args.download or not source.exists():
        urlretrieve(DATA_URL, source)
    raw = load_data(source)
    cleaned, quality = audit_and_clean(raw)
    result = summarize(cleaned, quality)
    global CHARTS
    CHARTS = Path(args.out) / "charts"
    make_plots(cleaned)
    export_evidence(raw, cleaned, quality, result, args.out)
    print(json.dumps({"rows": result["rows"], "aqi": result["aqi"],
                      "quality": quality}, indent=2))
    print("Created 11 charts and analysis evidence in", args.out)


if __name__ == "__main__":
    main()
