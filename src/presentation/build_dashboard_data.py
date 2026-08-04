"""Build compact aggregated JSON for the static project dashboard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def build_payload(data: pd.DataFrame) -> dict:
    prepared = data.copy()
    prepared["date"] = prepared["interval_start_nem_time"].dt.date.astype(str)
    prepared["time_of_day"] = prepared["hour"] + prepared["half_hour"] * 0.5

    daily = (
        prepared.groupby("date")
        .agg(
            mean_mw=("scheduled_demand_mw", "mean"),
            peak_mw=("scheduled_demand_mw", "max"),
            minimum_mw=("scheduled_demand_mw", "min"),
            temperature_c=("temperature_2m", "mean"),
        )
        .reset_index()
    )
    annual = (
        prepared.groupby("year")["scheduled_demand_mw"]
        .mean()
        .round(1)
        .rename("mean_mw")
        .reset_index()
    )
    seasonal = (
        prepared.groupby(["season", "time_of_day"], observed=True)["scheduled_demand_mw"]
        .mean()
        .round(1)
        .reset_index()
    )
    day_type = (
        prepared.assign(day_type=prepared["is_weekend"].map({0: "Weekday", 1: "Weekend"}))
        .groupby(["day_type", "time_of_day"])["scheduled_demand_mw"]
        .mean()
        .round(1)
        .reset_index()
    )
    peak = prepared.loc[prepared["scheduled_demand_mw"].idxmax()]
    return {
        "summary": {
            "rows": int(len(prepared)),
            "start": prepared["interval_start_nem_time"].min().isoformat(),
            "end": prepared["interval_end_nem_time"].max().isoformat(),
            "mean_mw": round(float(prepared["scheduled_demand_mw"].mean()), 1),
            "peak_mw": round(float(peak["scheduled_demand_mw"]), 1),
            "peak_time": peak["interval_end_nem_time"].isoformat(),
            "test_mae_mw": 279.4,
            "baseline_improvement_percent": 47.9,
        },
        "daily": daily.round(1).to_dict(orient="records"),
        "annual": annual.to_dict(orient="records"),
        "seasonal": seasonal.to_dict(orient="records"),
        "day_type": day_type.to_dict(orient="records"),
        "model_metrics": [
            {"model": "Previous day", "mae_mw": 535.9, "mape_percent": 7.20},
            {"model": "Ridge regression", "mae_mw": 414.9, "mape_percent": 5.54},
            {"model": "Gradient boosting", "mae_mw": 279.4, "mape_percent": 3.78},
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/nsw_demand_features.csv"))
    parser.add_argument("--output", type=Path, default=Path("docs/data/dashboard.json"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = pd.read_csv(args.input, parse_dates=["interval_end_nem_time", "interval_start_nem_time"])
    payload = build_payload(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote dashboard data: {args.output}")


if __name__ == "__main__":
    main()
