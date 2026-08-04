"""Validate the model-ready NSW half-hourly scheduled-demand dataset."""

from __future__ import annotations

import argparse
import csv
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
EXPECTED_REGION = "NSW1"
EXPECTED_FREQUENCY = timedelta(minutes=30)


@dataclass(frozen=True)
class ValidatedRow:
    interval_end: datetime
    region_id: str
    demand_mw: float


@dataclass(frozen=True)
class QualitySummary:
    rows: int
    start: datetime
    end: datetime
    duplicate_timestamps: int
    missing_intervals: int
    unexpected_intervals: int
    missing_values: int
    non_positive_values: int
    unexpected_regions: tuple[str, ...]
    minimum_mw: float
    mean_mw: float
    median_mw: float
    maximum_mw: float
    annual_rows: dict[int, int]
    annual_mean_mw: dict[int, float]


def read_demand_csv(path: Path) -> tuple[list[ValidatedRow], int]:
    """Parse validated rows and count blank demand values."""

    rows: list[ValidatedRow] = []
    missing_values = 0
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        expected_columns = {
            "interval_end_nem_time",
            "region_id",
            "scheduled_demand_mw",
        }
        if set(reader.fieldnames or ()) != expected_columns:
            raise ValueError(
                f"Unexpected columns {reader.fieldnames}; expected {sorted(expected_columns)}"
            )

        for line_number, row in enumerate(reader, start=2):
            raw_demand = row["scheduled_demand_mw"].strip()
            if not raw_demand:
                missing_values += 1
                continue
            try:
                rows.append(
                    ValidatedRow(
                        interval_end=datetime.strptime(
                            row["interval_end_nem_time"], TIMESTAMP_FORMAT
                        ),
                        region_id=row["region_id"],
                        demand_mw=float(raw_demand),
                    )
                )
            except ValueError as error:
                raise ValueError(f"Invalid value on CSV line {line_number}: {error}") from error
    if not rows:
        raise ValueError("Dataset contains no valid demand rows")
    return rows, missing_values


def expected_interval_count(start: datetime, end: datetime) -> int:
    """Return the inclusive number of half-hour interval endings."""

    duration = end - start
    if duration % EXPECTED_FREQUENCY:
        raise ValueError("Dataset boundaries do not align to half-hour intervals")
    return int(duration / EXPECTED_FREQUENCY) + 1


def summarize(rows: Iterable[ValidatedRow], missing_values: int = 0) -> QualitySummary:
    """Calculate completeness and descriptive quality checks."""

    materialized = sorted(rows, key=lambda row: row.interval_end)
    if not materialized:
        raise ValueError("Cannot summarize an empty dataset")

    timestamp_counts = Counter(row.interval_end for row in materialized)
    unique_timestamps = sorted(timestamp_counts)
    duplicate_timestamps = sum(count - 1 for count in timestamp_counts.values())
    expected = expected_interval_count(unique_timestamps[0], unique_timestamps[-1])
    missing_intervals = expected - len(unique_timestamps)
    unexpected_intervals = sum(
        current - previous != EXPECTED_FREQUENCY
        for previous, current in zip(unique_timestamps, unique_timestamps[1:])
    )

    demands = [row.demand_mw for row in materialized]
    annual_demands: dict[int, list[float]] = defaultdict(list)
    for row in materialized:
        # Interval-ending midnight belongs to the preceding half-hour/day.
        demand_year = (row.interval_end - timedelta(microseconds=1)).year
        annual_demands[demand_year].append(row.demand_mw)

    regions = {row.region_id for row in materialized}
    return QualitySummary(
        rows=len(materialized),
        start=unique_timestamps[0],
        end=unique_timestamps[-1],
        duplicate_timestamps=duplicate_timestamps,
        missing_intervals=missing_intervals,
        unexpected_intervals=unexpected_intervals,
        missing_values=missing_values,
        non_positive_values=sum(value <= 0 for value in demands),
        unexpected_regions=tuple(sorted(regions - {EXPECTED_REGION})),
        minimum_mw=min(demands),
        mean_mw=statistics.fmean(demands),
        median_mw=statistics.median(demands),
        maximum_mw=max(demands),
        annual_rows={year: len(values) for year, values in sorted(annual_demands.items())},
        annual_mean_mw={
            year: statistics.fmean(values)
            for year, values in sorted(annual_demands.items())
        },
    )


def quality_status(summary: QualitySummary) -> str:
    """Return PASS only when all structural validation checks succeed."""

    failures = (
        summary.duplicate_timestamps,
        summary.missing_intervals,
        summary.unexpected_intervals,
        summary.missing_values,
        summary.non_positive_values,
        len(summary.unexpected_regions),
    )
    return "PASS" if not any(failures) else "REVIEW REQUIRED"


def render_markdown(summary: QualitySummary) -> str:
    """Render a concise, versionable Markdown quality report."""

    annual_lines = "\n".join(
        f"| {year} | {summary.annual_rows[year]:,} | {summary.annual_mean_mw[year]:,.2f} |"
        for year in summary.annual_rows
    )
    regions = ", ".join(summary.unexpected_regions) or "None"
    return f"""# NSW scheduled-demand data quality report

## Result

**{quality_status(summary)}**

This report validates the locally generated half-hourly dataset. The source CSV
is reproducible and intentionally excluded from Git.

## Coverage and integrity

| Check | Result |
| --- | ---: |
| First interval ending | {summary.start.strftime(TIMESTAMP_FORMAT)} |
| Last interval ending | {summary.end.strftime(TIMESTAMP_FORMAT)} |
| Valid rows | {summary.rows:,} |
| Duplicate timestamps | {summary.duplicate_timestamps:,} |
| Missing half-hour intervals | {summary.missing_intervals:,} |
| Non-30-minute timestamp gaps | {summary.unexpected_intervals:,} |
| Missing demand values | {summary.missing_values:,} |
| Non-positive demand values | {summary.non_positive_values:,} |
| Unexpected regions | {regions} |

## Demand summary

| Statistic | Scheduled demand (MW) |
| --- | ---: |
| Minimum | {summary.minimum_mw:,.2f} |
| Mean | {summary.mean_mw:,.2f} |
| Median | {summary.median_mw:,.2f} |
| Maximum | {summary.maximum_mw:,.2f} |

## Annual coverage

| Year | Half-hour rows | Mean scheduled demand (MW) |
| --- | ---: | ---: |
{annual_lines}

The final timestamp is `2026-01-01 00:00:00` because AEMO uses interval-ending
timestamps: it represents the last half-hour of 31 December 2025.
"""


def validate(input_path: Path, report_path: Path) -> QualitySummary:
    rows, missing_values = read_demand_csv(input_path)
    summary = summarize(rows, missing_values)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_markdown(summary), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/nsw_scheduled_demand_half_hourly.csv"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/data_quality_report.md"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = validate(args.input, args.report)
    print(f"{quality_status(summary)}: validated {summary.rows:,} rows")
    print(f"Report: {args.report}")


if __name__ == "__main__":
    main()
