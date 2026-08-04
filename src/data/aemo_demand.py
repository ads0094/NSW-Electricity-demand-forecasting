"""Download and prepare AEMO NSW scheduled-demand data."""

from __future__ import annotations

import argparse
import csv
import io
import sys
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Iterator


BASE_URL = (
    "https://www.nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/"
    "{year}/MMSDM_{year}_{month:02d}/MMSDM_Historical_Data_SQLLoader/DATA/"
)
REGION_ID = "NSW1"
TABLE_ID = ("DISPATCH", "REGIONSUM")
TIMESTAMP_FORMAT = "%Y/%m/%d %H:%M:%S"


@dataclass(frozen=True)
class DemandRecord:
    """A five-minute scheduled-demand observation."""

    interval_end: datetime
    demand_mw: float


@dataclass(frozen=True)
class HalfHourDemand:
    """A validated half-hour scheduled-demand observation."""

    interval_end: datetime
    demand_mw: float
    source_intervals: int


def archive_urls(year: int, month: int) -> tuple[str, ...]:
    """Return current and legacy candidate URLs for a monthly archive."""

    base = BASE_URL.format(year=year, month=month)
    timestamp = f"{year}{month:02d}010000"
    return (
        base
        + "PUBLIC_ARCHIVE%23DISPATCHREGIONSUM%23FILE01%23"
        + timestamp
        + ".zip",
        base + f"PUBLIC_DVD_DISPATCHREGIONSUM_{timestamp}.zip",
    )


def download_month(year: int, month: int, destination: Path) -> Path:
    """Download one monthly archive, trying AEMO's current and legacy names."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return destination

    errors: list[str] = []
    for url in archive_urls(year, month):
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                destination.write_bytes(response.read())
            return destination
        except urllib.error.HTTPError as error:
            errors.append(f"{url}: HTTP {error.code}")
        except urllib.error.URLError as error:
            errors.append(f"{url}: {error.reason}")

    raise RuntimeError("AEMO archive download failed:\n" + "\n".join(errors))


def _data_rows(archive: Path) -> Iterator[dict[str, str]]:
    """Yield DISPATCH/REGIONSUM rows from an AEMO monthly ZIP archive."""

    with zipfile.ZipFile(archive) as zipped:
        csv_names = [name for name in zipped.namelist() if name.upper().endswith(".CSV")]
        if len(csv_names) != 1:
            raise ValueError(f"Expected one CSV in {archive}, found {len(csv_names)}")

        with zipped.open(csv_names[0]) as binary_file:
            text_file = io.TextIOWrapper(binary_file, encoding="utf-8-sig", newline="")
            reader = csv.reader(text_file)
            header: list[str] | None = None

            for row in reader:
                if len(row) < 3 or tuple(row[1:3]) != TABLE_ID:
                    continue
                if row[0] == "I":
                    header = row
                elif row[0] == "D":
                    if header is None:
                        raise ValueError(f"Data row encountered before header in {archive}")
                    yield dict(zip(header, row))


def read_nsw_scheduled_demand(archive: Path) -> list[DemandRecord]:
    """Read non-intervention NSW1 scheduled demand from an AEMO archive."""

    records: dict[datetime, DemandRecord] = {}
    for row in _data_rows(archive):
        if row["REGIONID"] != REGION_ID or row["INTERVENTION"] != "0":
            continue
        interval_end = datetime.strptime(row["SETTLEMENTDATE"], TIMESTAMP_FORMAT)
        record = DemandRecord(interval_end, float(row["CLEAREDSUPPLY"]))
        if interval_end in records:
            raise ValueError(f"Duplicate NSW1 interval: {interval_end}")
        records[interval_end] = record

    if not records:
        raise ValueError(f"No non-intervention NSW1 records found in {archive}")
    return sorted(records.values(), key=lambda record: record.interval_end)


def half_hour_end(interval_end: datetime) -> datetime:
    """Map a five-minute ending interval to its half-hour ending interval."""

    shifted = interval_end - timedelta(minutes=5)
    floor = shifted.replace(minute=(shifted.minute // 30) * 30, second=0, microsecond=0)
    return floor + timedelta(minutes=30)


def aggregate_half_hour(
    records: Iterable[DemandRecord],
) -> tuple[list[HalfHourDemand], list[datetime]]:
    """Average complete groups of six five-minute demand observations."""

    groups: dict[datetime, list[DemandRecord]] = defaultdict(list)
    for record in records:
        groups[half_hour_end(record.interval_end)].append(record)

    complete: list[HalfHourDemand] = []
    incomplete: list[datetime] = []
    for interval_end, group in sorted(groups.items()):
        unique_times = {record.interval_end for record in group}
        if len(group) != 6 or len(unique_times) != 6:
            incomplete.append(interval_end)
            continue
        complete.append(
            HalfHourDemand(
                interval_end=interval_end,
                demand_mw=sum(record.demand_mw for record in group) / 6,
                source_intervals=6,
            )
        )
    return complete, incomplete


def write_half_hour_csv(records: Iterable[HalfHourDemand], destination: Path) -> None:
    """Write model-ready half-hour records to CSV."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["interval_end_nem_time", "region_id", "scheduled_demand_mw"])
        for record in records:
            writer.writerow(
                [
                    record.interval_end.strftime("%Y-%m-%d %H:%M:%S"),
                    REGION_ID,
                    f"{record.demand_mw:.5f}",
                ]
            )


def month_range(start_year: int, start_month: int, end_year: int, end_month: int):
    """Yield inclusive calendar months."""

    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        yield year, month
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def build_dataset(start: str, end: str, raw_dir: Path, output: Path) -> None:
    """Download, validate, aggregate, and combine a range of monthly archives."""

    start_date = datetime.strptime(start, "%Y-%m")
    end_date = datetime.strptime(end, "%Y-%m")
    if start_date > end_date:
        raise ValueError("start month must not be after end month")

    all_records: list[HalfHourDemand] = []
    incomplete_total: list[datetime] = []
    for year, month in month_range(
        start_date.year, start_date.month, end_date.year, end_date.month
    ):
        archive = raw_dir / f"dispatchregionsum_{year}_{month:02d}.zip"
        print(f"Processing {year}-{month:02d}", file=sys.stderr)
        download_month(year, month, archive)
        five_minute = read_nsw_scheduled_demand(archive)
        half_hourly, incomplete = aggregate_half_hour(five_minute)
        all_records.extend(half_hourly)
        incomplete_total.extend(incomplete)

    by_time = {record.interval_end: record for record in all_records}
    if len(by_time) != len(all_records):
        raise ValueError("Duplicate half-hour intervals detected across monthly archives")
    write_half_hour_csv(by_time.values(), output)
    print(
        f"Wrote {len(by_time):,} complete half-hours; "
        f"excluded {len(incomplete_total):,} incomplete half-hours",
        file=sys.stderr,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2019-01", help="First month, YYYY-MM")
    parser.add_argument("--end", default="2025-12", help="Last month, YYYY-MM")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/aemo"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/nsw_scheduled_demand_half_hourly.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_dataset(args.start, args.end, args.raw_dir, args.output)


if __name__ == "__main__":
    main()
