"""Train and compare leakage-safe day-ahead demand forecasting models."""

from __future__ import annotations

import argparse
import math
from dataclasses import asdict
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.modeling.baselines import MetricSet, calculate_metrics


TARGET = "scheduled_demand_mw"
LAG_COLUMNS = {"demand_lag_1_day": 48, "demand_lag_1_week": 336}
FEATURE_COLUMNS = [
    "demand_lag_1_day",
    "demand_lag_1_week",
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "wind_speed_10m",
    "shortwave_radiation",
    "is_weekend",
    "is_public_holiday",
    "is_sydney_dst",
    "hour_sin",
    "hour_cos",
    "week_sin",
    "week_cos",
    "year_trend",
]


def prepare_features(data: pd.DataFrame) -> pd.DataFrame:
    """Create features available at least one day before each target interval."""

    prepared = data.sort_values("interval_end_nem_time").copy()
    for name, lag in LAG_COLUMNS.items():
        prepared[name] = prepared[TARGET].shift(lag)
    half_hour_index = prepared["hour"] * 2 + prepared["half_hour"]
    prepared["hour_sin"] = np.sin(2 * np.pi * half_hour_index / 48)
    prepared["hour_cos"] = np.cos(2 * np.pi * half_hour_index / 48)
    prepared["week_sin"] = np.sin(2 * np.pi * prepared["day_of_week"] / 7)
    prepared["week_cos"] = np.cos(2 * np.pi * prepared["day_of_week"] / 7)
    prepared["year_trend"] = prepared["year"] - prepared["year"].min()
    return prepared.dropna(subset=FEATURE_COLUMNS + [TARGET]).copy()


def candidate_models():
    return {
        "Ridge regression": make_pipeline(StandardScaler(), Ridge(alpha=10.0)),
        "Gradient boosting": HistGradientBoostingRegressor(
            learning_rate=0.08,
            max_iter=250,
            max_leaf_nodes=31,
            min_samples_leaf=40,
            l2_regularization=1.0,
            random_state=42,
        ),
    }


def fit_and_score(model, train: pd.DataFrame, evaluation: pd.DataFrame) -> tuple[object, MetricSet, pd.DataFrame]:
    model.fit(train[FEATURE_COLUMNS], train[TARGET])
    scored = evaluation[["interval_start_nem_time", TARGET]].copy()
    scored["prediction"] = model.predict(evaluation[FEATURE_COLUMNS])
    return model, calculate_metrics(scored, "prediction"), scored


def train_and_evaluate(data: pd.DataFrame):
    prepared = prepare_features(data)
    development = prepared[prepared["year"] <= 2023]
    validation = prepared[prepared["year"] == 2024]
    test = prepared[prepared["year"] == 2025]
    if min(len(development), len(validation), len(test)) == 0:
        raise ValueError("Development, validation, and test periods must all contain rows")

    validation_results = {}
    fitted = {}
    for name, model in candidate_models().items():
        fitted_model, metrics, _ = fit_and_score(model, development, validation)
        fitted[name] = fitted_model
        validation_results[name] = metrics

    selected_name = min(validation_results, key=lambda name: validation_results[name].mae_mw)
    final_model = candidate_models()[selected_name]
    final_train = prepared[prepared["year"] <= 2024]
    final_model, test_metrics, test_predictions = fit_and_score(final_model, final_train, test)
    return selected_name, validation_results, final_model, test_metrics, test_predictions


def metric_row(label: str, metrics: MetricSet) -> str:
    return (
        f"| {label} | {metrics.mae_mw:,.1f} | {metrics.rmse_mw:,.1f} | "
        f"{metrics.mape_percent:.2f}% | {metrics.daily_peak_mae_mw:,.1f} | "
        f"{metrics.bias_mw:,.1f} |"
    )


def render_report(selected_name: str, validation_results: dict[str, MetricSet], test_metrics: MetricSet) -> str:
    validation_rows = "\n".join(
        metric_row(f"{name} — validation 2024", metrics)
        for name, metrics in validation_results.items()
    )
    baseline_mae = 535.9
    improvement = (baseline_mae - test_metrics.mae_mw) / baseline_mae * 100
    return f"""# Trained model results

## Model selection

Models were fitted on 2019–2023 and selected using 2024 only. **{selected_name}**
had the lowest validation MAE, so it was refitted using 2019–2024 and evaluated
once on the 2025 test period.

| Model and period | MAE (MW) | RMSE (MW) | MAPE | Daily peak MAE (MW) | Bias (MW) |
| --- | ---: | ---: | ---: | ---: | ---: |
{validation_rows}
{metric_row(f'{selected_name} — test 2025', test_metrics)}

## Result

The selected model's 2025 MAE is **{test_metrics.mae_mw:,.1f} MW**, an
**{improvement:.1f}% improvement** over the previous-day baseline MAE of 535.9 MW.
Its test RMSE is **{test_metrics.rmse_mw:,.1f} MW**, MAPE is
**{test_metrics.mape_percent:.2f}%**, and daily peak MAE is
**{test_metrics.daily_peak_mae_mw:,.1f} MW**.

![Selected model forecast comparison](figures/model-forecast-comparison.png)

## Important limitation

Historical ERA5 reanalysis is used as a proxy for weather information that would
be available from a real forecast. This isolates the value of weather features
but can make performance optimistic compared with production, where weather
forecasts contain error. Demand lag features are restricted to one day and one
week, so they are available for a 24-hour-ahead forecast.
"""


def save_figure(predictions: pd.DataFrame, destination: Path) -> None:
    sample = predictions[
        (predictions["interval_start_nem_time"] >= "2025-01-15")
        & (predictions["interval_start_nem_time"] < "2025-01-29")
    ]
    fig, axis = plt.subplots(figsize=(12, 5.5))
    axis.plot(sample["interval_start_nem_time"], sample[TARGET], label="Actual", color="#172554", linewidth=2)
    axis.plot(sample["interval_start_nem_time"], sample["prediction"], label="Model", color="#B45309", linewidth=1.5)
    axis.set(title="Selected model over a summer fortnight", xlabel="Interval start (NEM time)", ylabel="Scheduled demand (MW)")
    axis.legend(frameon=False)
    axis.spines[["top", "right"]].set_visible(False)
    fig.autofmt_xdate()
    fig.tight_layout()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=160, bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/nsw_demand_features.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/model_evaluation.md"))
    parser.add_argument("--figure", type=Path, default=Path("reports/figures/model-forecast-comparison.png"))
    parser.add_argument("--model", type=Path, default=Path("models/selected_forecaster.joblib"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = pd.read_csv(args.input, parse_dates=["interval_end_nem_time", "interval_start_nem_time"])
    selected, validation, model, test, predictions = train_and_evaluate(data)
    args.report.write_text(render_report(selected, validation, test), encoding="utf-8")
    save_figure(predictions, args.figure)
    args.model.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURE_COLUMNS, "metrics": asdict(test)}, args.model)
    print(f"Selected model: {selected}")
    print(f"2025 test MAE: {test.mae_mw:,.1f} MW")


if __name__ == "__main__":
    main()
