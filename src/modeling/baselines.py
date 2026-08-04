"""Evaluate previous-day and previous-week demand forecasting baselines."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


TARGET = "scheduled_demand_mw"
BASELINES = {"Previous day": 48, "Previous week": 48 * 7}


@dataclass(frozen=True)
class MetricSet:
    mae_mw: float
    rmse_mw: float
    mape_percent: float
    daily_peak_mae_mw: float
    bias_mw: float
    observations: int


def add_baseline_predictions(data: pd.DataFrame) -> pd.DataFrame:
    """Add lagged forecasts without using future target observations."""

    result = data.sort_values("interval_end_nem_time").copy()
    for name, lag in BASELINES.items():
        result[name] = result[TARGET].shift(lag)
    return result


def calculate_metrics(frame: pd.DataFrame, prediction_column: str) -> MetricSet:
    valid = frame[["interval_start_nem_time", TARGET, prediction_column]].dropna()
    actual = valid[TARGET].to_numpy(dtype=float)
    predicted = valid[prediction_column].to_numpy(dtype=float)
    errors = predicted - actual
    dates = valid["interval_start_nem_time"].dt.date
    daily = pd.DataFrame({"date": dates, "actual": actual, "predicted": predicted})
    daily_peaks = daily.groupby("date")[["actual", "predicted"]].max()
    return MetricSet(
        mae_mw=float(np.mean(np.abs(errors))),
        rmse_mw=float(np.sqrt(np.mean(errors**2))),
        mape_percent=float(np.mean(np.abs(errors / actual)) * 100),
        daily_peak_mae_mw=float(np.mean(np.abs(daily_peaks["predicted"] - daily_peaks["actual"]))),
        bias_mw=float(np.mean(errors)),
        observations=len(valid),
    )


def evaluate(data: pd.DataFrame) -> dict[str, dict[str, MetricSet]]:
    predicted = add_baseline_predictions(data)
    results: dict[str, dict[str, MetricSet]] = {}
    for period_name, year in (("Validation (2024)", 2024), ("Test (2025)", 2025)):
        period = predicted[predicted["year"] == year]
        results[period_name] = {
            baseline: calculate_metrics(period, baseline) for baseline in BASELINES
        }
    return results


def render_report(results: dict[str, dict[str, MetricSet]]) -> str:
    lines = []
    for period, baselines in results.items():
        for baseline, metrics in baselines.items():
            lines.append(
                f"| {period} | {baseline} | {metrics.mae_mw:,.1f} | "
                f"{metrics.rmse_mw:,.1f} | {metrics.mape_percent:.2f}% | "
                f"{metrics.daily_peak_mae_mw:,.1f} | {metrics.bias_mw:,.1f} | "
                f"{metrics.observations:,} |"
            )
    test_results = results["Test (2025)"]
    best = min(test_results, key=lambda name: test_results[name].mae_mw)
    best_metrics = test_results[best]
    return f"""# Baseline forecast evaluation

## Evaluation design

- Historical development period: 2019–2023
- Validation period: 2024
- Final test period: 2025
- Previous-day forecast: demand from 48 half-hours earlier
- Previous-week forecast: demand from 336 half-hours earlier
- Peak-demand error: mean absolute error between actual and predicted daily maxima

## Results

| Period | Baseline | MAE (MW) | RMSE (MW) | MAPE | Daily peak MAE (MW) | Bias (MW) | Rows |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(lines)}

## Benchmark to beat

The stronger 2025 baseline is **{best}**, with MAE **{best_metrics.mae_mw:,.1f} MW**,
RMSE **{best_metrics.rmse_mw:,.1f} MW**, and MAPE **{best_metrics.mape_percent:.2f}%**.
Any advanced model should improve on this result using the same chronological
test period. The 2025 test results must not be used for model tuning.

![Baseline forecasts over a summer fortnight](figures/baseline-forecast-comparison.png)
"""


def save_comparison_figure(data: pd.DataFrame, destination: Path) -> None:
    predicted = add_baseline_predictions(data)
    sample = predicted[
        (predicted["interval_start_nem_time"] >= "2025-01-15")
        & (predicted["interval_start_nem_time"] < "2025-01-29")
    ]
    fig, axis = plt.subplots(figsize=(12, 5.5))
    axis.plot(sample["interval_start_nem_time"], sample[TARGET], label="Actual", color="#172554", linewidth=2)
    axis.plot(sample["interval_start_nem_time"], sample["Previous day"], label="Previous day", color="#D97706", linewidth=1.2, alpha=0.85)
    axis.plot(sample["interval_start_nem_time"], sample["Previous week"], label="Previous week", color="#0F766E", linewidth=1.2, alpha=0.85)
    axis.set(title="Baseline forecasts over a summer fortnight", xlabel="Interval start (NEM time)", ylabel="Scheduled demand (MW)")
    axis.legend(frameon=False, ncols=3)
    axis.spines[["top", "right"]].set_visible(False)
    fig.autofmt_xdate()
    fig.tight_layout()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=160, bbox_inches="tight")
    plt.close(fig)


def load_data(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        parse_dates=["interval_end_nem_time", "interval_start_nem_time"],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/nsw_demand_features.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/baseline_evaluation.md"))
    parser.add_argument("--figure", type=Path, default=Path("reports/figures/baseline-forecast-comparison.png"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = load_data(args.input)
    results = evaluate(data)
    args.report.write_text(render_report(results), encoding="utf-8")
    save_comparison_figure(data, args.figure)
    print(f"Wrote baseline report: {args.report}")


if __name__ == "__main__":
    main()
