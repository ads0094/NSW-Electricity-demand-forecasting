"""Create reproducible exploratory analysis figures and findings."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


SEASON_ORDER = ["summer", "autumn", "winter", "spring"]
FIGURE_DPI = 160


def format_time_of_day(decimal_hour: float) -> str:
    total_minutes = round(decimal_hour * 60)
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def load_features(path: Path) -> pd.DataFrame:
    data = pd.read_csv(
        path,
        parse_dates=["interval_end_nem_time", "interval_start_nem_time"],
    )
    required = {
        "scheduled_demand_mw",
        "temperature_2m",
        "season",
        "is_weekend",
        "is_public_holiday",
        "year",
        "hour",
        "half_hour",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Feature table is missing columns: {sorted(missing)}")
    return data


def configure_plotting() -> None:
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams.update(
        {
            "axes.titleweight": "bold",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
        }
    )


def save_annual_demand(data: pd.DataFrame, destination: Path) -> pd.Series:
    annual = data.groupby("year")["scheduled_demand_mw"].mean()
    fig, axis = plt.subplots(figsize=(9, 5))
    axis.plot(annual.index, annual.values, marker="o", linewidth=2.2, color="#176B87")
    axis.fill_between(annual.index, annual.values, annual.min() - 100, alpha=0.12, color="#176B87")
    axis.set(title="Average NSW scheduled demand by year", xlabel="Year", ylabel="Demand (MW)")
    axis.set_ylim(annual.min() - 100, annual.max() + 100)
    for year, value in annual.items():
        axis.annotate(f"{value:,.0f}", (year, value), xytext=(0, 8), textcoords="offset points", ha="center")
    fig.tight_layout()
    fig.savefig(destination, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)
    return annual


def save_seasonal_profiles(data: pd.DataFrame, destination: Path) -> pd.DataFrame:
    prepared = data.assign(time_of_day=data["hour"] + data["half_hour"] * 0.5)
    profiles = (
        prepared.groupby(["season", "time_of_day"], observed=True)["scheduled_demand_mw"]
        .mean()
        .unstack("season")
        .reindex(columns=SEASON_ORDER)
    )
    fig, axis = plt.subplots(figsize=(10, 5.5))
    palette = dict(zip(SEASON_ORDER, sns.color_palette("colorblind", 4)))
    for season in SEASON_ORDER:
        axis.plot(profiles.index, profiles[season], label=season.title(), linewidth=2.1, color=palette[season])
    axis.set(
        title="Average half-hourly demand profile by Australian season",
        xlabel="NEM time (hour)",
        ylabel="Demand (MW)",
        xticks=range(0, 25, 3),
    )
    axis.legend(frameon=False, ncols=4)
    fig.tight_layout()
    fig.savefig(destination, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)
    return profiles


def save_day_type_profiles(data: pd.DataFrame, destination: Path) -> pd.DataFrame:
    prepared = data.assign(
        time_of_day=data["hour"] + data["half_hour"] * 0.5,
        day_type=data["is_weekend"].map({0: "Weekday", 1: "Weekend"}),
    )
    profiles = prepared.groupby(["day_type", "time_of_day"])["scheduled_demand_mw"].mean().unstack("day_type")
    fig, axis = plt.subplots(figsize=(10, 5.5))
    for day_type, color in (("Weekday", "#176B87"), ("Weekend", "#D97706")):
        axis.plot(profiles.index, profiles[day_type], label=day_type, linewidth=2.2, color=color)
    axis.set(
        title="Weekday and weekend demand profiles",
        xlabel="NEM time (hour)",
        ylabel="Demand (MW)",
        xticks=range(0, 25, 3),
    )
    axis.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(destination, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)
    return profiles


def save_temperature_relationship(data: pd.DataFrame, destination: Path) -> pd.DataFrame:
    prepared = data.assign(temperature_bin=data["temperature_2m"].round())
    relationship = prepared.groupby("temperature_bin")["scheduled_demand_mw"].agg(["mean", "count"])
    relationship = relationship[relationship["count"] >= 48]
    fig, axis = plt.subplots(figsize=(9, 5.5))
    axis.plot(relationship.index, relationship["mean"], color="#A23B72", linewidth=2.4)
    axis.scatter(relationship.index, relationship["mean"], color="#A23B72", s=24)
    axis.set(
        title="Temperature–demand relationship",
        xlabel="Bankstown temperature (°C, rounded)",
        ylabel="Average demand (MW)",
    )
    fig.tight_layout()
    fig.savefig(destination, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)
    return relationship


def save_peak_intervals(data: pd.DataFrame, destination: Path) -> pd.DataFrame:
    peaks = data.nlargest(10, "scheduled_demand_mw").sort_values("scheduled_demand_mw")
    labels = peaks["interval_end_nem_time"].dt.strftime("%d %b %Y %H:%M")
    fig, axis = plt.subplots(figsize=(9, 5.5))
    axis.barh(labels, peaks["scheduled_demand_mw"], color="#C44536")
    axis.set(title="Ten highest NSW demand intervals", xlabel="Scheduled demand (MW)", ylabel="Interval ending (NEM time)")
    axis.bar_label(axis.containers[0], fmt="{:,.0f}", padding=4)
    axis.set_xlim(peaks["scheduled_demand_mw"].min() - 500, peaks["scheduled_demand_mw"].max() + 500)
    fig.tight_layout()
    fig.savefig(destination, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)
    return peaks


def render_report(
    data: pd.DataFrame,
    annual: pd.Series,
    seasonal: pd.DataFrame,
    day_type: pd.DataFrame,
    temperature: pd.DataFrame,
    peaks: pd.DataFrame,
) -> str:
    peak = peaks.loc[peaks["scheduled_demand_mw"].idxmax()]
    highest_year = int(annual.idxmax())
    lowest_year = int(annual.idxmin())
    evening_slot = 18.0
    weekday_gap = day_type.loc[evening_slot, "Weekday"] - day_type.loc[evening_slot, "Weekend"]
    hottest_bin = float(temperature["mean"].idxmax())
    summer_peak_time = format_time_of_day(float(seasonal["summer"].idxmax()))
    winter_peak_time = format_time_of_day(float(seasonal["winter"].idxmax()))
    holiday_mean = data.loc[data["is_public_holiday"] == 1, "scheduled_demand_mw"].mean()
    non_holiday_mean = data.loc[data["is_public_holiday"] == 0, "scheduled_demand_mw"].mean()
    holiday_difference = (holiday_mean / non_holiday_mean - 1) * 100

    return f"""# Exploratory analysis: NSW scheduled demand

## Main findings

- Average demand was highest in **{highest_year}** ({annual.loc[highest_year]:,.0f} MW) and lowest in **{lowest_year}** ({annual.loc[lowest_year]:,.0f} MW).
- The maximum half-hour was **{peak['scheduled_demand_mw']:,.0f} MW**, ending {peak['interval_end_nem_time']:%d %B %Y at %H:%M} NEM time.
- At 18:00, weekday demand averages **{weekday_gap:,.0f} MW** more than weekend demand.
- The summer average profile peaks around **{summer_peak_time} NEM time**; the winter profile peaks around **{winter_peak_time}**.
- The highest temperature-bin mean occurs near **{hottest_bin:.0f}°C**, supporting a nonlinear temperature effect.
- Public-holiday demand averages **{abs(holiday_difference):.1f}% {'lower' if holiday_difference < 0 else 'higher'}** than non-holiday demand. This comparison is descriptive and not causal.

## Figures

![Annual average demand](figures/annual-average-demand.png)

![Seasonal demand profiles](figures/seasonal-demand-profiles.png)

![Weekday and weekend profiles](figures/day-type-demand-profiles.png)

![Temperature and demand](figures/temperature-demand-relationship.png)

![Peak demand intervals](figures/peak-demand-intervals.png)

## Interpretation limits

The weather series is ERA5 reanalysis for Bankstown Airport and acts as a proxy
for the broader NSW region. Aggregated patterns can combine weather, calendar,
economic, rooftop-solar, and structural effects. Forecast evaluation will use
chronological splits so future observations never leak into model training.
"""


def run(input_path: Path, figure_dir: Path, report_path: Path) -> None:
    configure_plotting()
    data = load_features(input_path)
    figure_dir.mkdir(parents=True, exist_ok=True)
    annual = save_annual_demand(data, figure_dir / "annual-average-demand.png")
    seasonal = save_seasonal_profiles(data, figure_dir / "seasonal-demand-profiles.png")
    day_type = save_day_type_profiles(data, figure_dir / "day-type-demand-profiles.png")
    temperature = save_temperature_relationship(data, figure_dir / "temperature-demand-relationship.png")
    peaks = save_peak_intervals(data, figure_dir / "peak-demand-intervals.png")
    report_path.write_text(
        render_report(data, annual, seasonal, day_type, temperature, peaks),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/nsw_demand_features.csv"))
    parser.add_argument("--figures", type=Path, default=Path("reports/figures"))
    parser.add_argument("--report", type=Path, default=Path("reports/exploratory_analysis.md"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(args.input, args.figures, args.report)
    print(f"Wrote exploratory report: {args.report}")


if __name__ == "__main__":
    main()
