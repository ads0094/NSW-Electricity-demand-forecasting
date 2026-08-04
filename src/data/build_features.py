"""Combine demand, weather, holidays, and calendar features."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


DEMAND_FORMAT = "%Y-%m-%d %H:%M:%S"
WEATHER_FORMAT = "%Y-%m-%dT%H:%M"
WEATHER_COLUMNS = (
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "wind_speed_10m",
    "shortwave_radiation",
)


@dataclass(frozen=True)
class BuildSummary:
    rows: int
    first_interval: datetime
    last_interval: datetime
    holiday_rows: int
    dst_rows: int
    missing_weather_rows: int


def demand_period(interval_end: datetime) -> tuple[datetime, datetime]:
    """Return interval start and its model weather hour in fixed NEM time."""

    interval_start = interval_end - timedelta(minutes=30)
    weather_hour = interval_start.replace(minute=0, second=0, microsecond=0)
    return interval_start, weather_hour


def australian_season(month: int) -> str:
    if month in (12, 1, 2):
        return "summer"
    if month in (3, 4, 5):
        return "autumn"
    if month in (6, 7, 8):
        return "winter"
    return "spring"


def is_sydney_dst(interval_start: datetime) -> int:
    """Flag NSW daylight saving using transition instants in fixed NEM time."""

    def first_sunday(year: int, month: int) -> datetime:
        first = datetime(year, month, 1, 2, 0)
        return first + timedelta(days=(6 - first.weekday()) % 7)

    if interval_start.month >= 10:
        start = first_sunday(interval_start.year, 10)
        end = first_sunday(interval_start.year + 1, 4)
    else:
        start = first_sunday(interval_start.year - 1, 10)
        end = first_sunday(interval_start.year, 4)
    return int(start <= interval_start < end)


def read_weather(path: Path) -> dict[datetime, dict[str, str]]:
    weather = {}
    with path.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            timestamp = datetime.strptime(row["time_nem"], WEATHER_FORMAT)
            if timestamp in weather:
                raise ValueError(f"Duplicate weather timestamp: {timestamp}")
            values = {column: row[column] for column in WEATHER_COLUMNS}
            if any(value in ("", "None") for value in values.values()):
                raise ValueError(f"Missing weather value at {timestamp}")
            weather[timestamp] = values
    return weather


def read_holidays(path: Path) -> dict[str, str]:
    holidays: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            date = row["date"]
            name = row["holiday_name"]
            if date in holidays and name not in holidays[date].split("; "):
                holidays[date] += f"; {name}"
            else:
                holidays[date] = name
    return holidays


def build_feature_table(
    demand_path: Path,
    weather_path: Path,
    holiday_path: Path,
    output_path: Path,
) -> BuildSummary:
    weather = read_weather(weather_path)
    holidays = read_holidays(holiday_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = holiday_rows = dst_rows = missing_weather_rows = 0
    first_interval = last_interval = None
    fieldnames = [
        "interval_end_nem_time",
        "interval_start_nem_time",
        "region_id",
        "scheduled_demand_mw",
        *WEATHER_COLUMNS,
        "year",
        "month",
        "day",
        "day_of_week",
        "hour",
        "half_hour",
        "is_weekend",
        "season",
        "is_public_holiday",
        "holiday_name",
        "is_sydney_dst",
    ]

    with demand_path.open(encoding="utf-8", newline="") as demand_source, output_path.open(
        "w", encoding="utf-8", newline=""
    ) as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for demand in csv.DictReader(demand_source):
            interval_end = datetime.strptime(demand["interval_end_nem_time"], DEMAND_FORMAT)
            interval_start, weather_hour = demand_period(interval_end)
            weather_values = weather.get(weather_hour)
            if weather_values is None:
                missing_weather_rows += 1
                continue

            date = interval_start.date().isoformat()
            holiday_name = holidays.get(date, "")
            holiday_flag = int(bool(holiday_name))
            dst_flag = is_sydney_dst(interval_start)
            writer.writerow(
                {
                    **demand,
                    "interval_start_nem_time": interval_start.strftime(DEMAND_FORMAT),
                    **weather_values,
                    "year": interval_start.year,
                    "month": interval_start.month,
                    "day": interval_start.day,
                    "day_of_week": interval_start.weekday(),
                    "hour": interval_start.hour,
                    "half_hour": interval_start.minute // 30,
                    "is_weekend": int(interval_start.weekday() >= 5),
                    "season": australian_season(interval_start.month),
                    "is_public_holiday": holiday_flag,
                    "holiday_name": holiday_name,
                    "is_sydney_dst": dst_flag,
                }
            )
            rows += 1
            holiday_rows += holiday_flag
            dst_rows += dst_flag
            first_interval = first_interval or interval_end
            last_interval = interval_end

    if first_interval is None or last_interval is None:
        raise ValueError("Feature table contains no rows")
    return BuildSummary(
        rows=rows,
        first_interval=first_interval,
        last_interval=last_interval,
        holiday_rows=holiday_rows,
        dst_rows=dst_rows,
        missing_weather_rows=missing_weather_rows,
    )


def render_report(summary: BuildSummary) -> str:
    status = "PASS" if summary.missing_weather_rows == 0 else "REVIEW REQUIRED"
    return f"""# Model-ready dataset report

## Result

**{status}**

| Check | Result |
| --- | ---: |
| Model rows | {summary.rows:,} |
| First demand interval ending | {summary.first_interval.strftime(DEMAND_FORMAT)} |
| Last demand interval ending | {summary.last_interval.strftime(DEMAND_FORMAT)} |
| Rows missing matched weather | {summary.missing_weather_rows:,} |
| Public-holiday half-hours | {summary.holiday_rows:,} |
| Sydney daylight-saving half-hours | {summary.dst_rows:,} |

Each model row represents the preceding half-hour. Hourly weather is matched to
the hour containing the interval start. This avoids inventing half-hour weather
values and keeps the final midnight-ending demand interval with the prior day.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--demand", type=Path, default=Path("data/processed/nsw_scheduled_demand_half_hourly.csv")
    )
    parser.add_argument(
        "--weather", type=Path, default=Path("data/processed/bankstown_weather_hourly.csv")
    )
    parser.add_argument(
        "--holidays", type=Path, default=Path("data/processed/nsw_public_holidays.csv")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/processed/nsw_demand_features.csv")
    )
    parser.add_argument(
        "--report", type=Path, default=Path("reports/model_dataset_report.md")
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build_feature_table(args.demand, args.weather, args.holidays, args.output)
    args.report.write_text(render_report(summary), encoding="utf-8")
    print(f"Wrote {summary.rows:,} model-ready rows")
    print(f"Missing weather matches: {summary.missing_weather_rows:,}")
    print(f"Report: {args.report}")


if __name__ == "__main__":
    main()
