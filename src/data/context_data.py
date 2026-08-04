"""Download hourly weather and NSW public-holiday context data."""

from __future__ import annotations

import argparse
import csv
import io
import json
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


WEATHER_ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
BANKSTOWN_AIRPORT = {"latitude": -33.9244, "longitude": 150.9883}
WEATHER_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "wind_speed_10m",
    "shortwave_radiation",
)
HOLIDAY_URLS = (
    "https://data.gov.au/data/dataset/b1bc6077-dadd-4f61-9f8c-002ab2cdff10/"
    "resource/bda4d4f2-7fde-4bfc-8a23-a6eefc8cef80/download/"
    "australian_public_holidays_2019.csv",
    "https://data.gov.au/data/dataset/b1bc6077-dadd-4f61-9f8c-002ab2cdff10/"
    "resource/c4163dc4-4f5a-4cae-b787-43ef0fcf8d8b/download/"
    "australian_public_holidays_2020.csv",
    "https://data.gov.au/data/dataset/b1bc6077-dadd-4f61-9f8c-002ab2cdff10/"
    "resource/33673aca-0857-42e5-b8f0-9981b4755686/download/"
    "australian-public-holidays-combined-2021-2025.csv",
)


def weather_url(start_date: str, end_date: str) -> str:
    """Build the documented ERA5-Land request for Bankstown Airport."""

    query = urllib.parse.urlencode(
        {
            **BANKSTOWN_AIRPORT,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(WEATHER_VARIABLES),
            "timezone": "Etc/GMT-10",
            "models": "era5",
        }
    )
    return f"{WEATHER_ENDPOINT}?{query}"


def download_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "nsw-demand-project/1.0"})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def download_weather(start_date: str, end_date: str, destination: Path) -> int:
    """Download hourly ERA5-Land weather and write a compact CSV."""

    payload = json.loads(download_bytes(weather_url(start_date, end_date)))
    hourly = payload["hourly"]
    times = hourly["time"]
    for variable in WEATHER_VARIABLES:
        if len(hourly[variable]) != len(times):
            raise ValueError(f"Weather length mismatch for {variable}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["time_nem", *WEATHER_VARIABLES])
        for index, timestamp in enumerate(times):
            writer.writerow([timestamp, *(hourly[name][index] for name in WEATHER_VARIABLES)])
    return len(times)


def _normalized_holiday_rows(payload: bytes):
    text = payload.decode("utf-8-sig")
    for row in csv.DictReader(io.StringIO(text)):
        normalized = {key.strip().lower(): (value or "").strip() for key, value in row.items()}
        jurisdiction = normalized.get("jurisdiction", "")
        if jurisdiction not in {"nsw", "australia", "national"}:
            continue
        date_text = normalized.get("date", "")
        parsed_date = None
        for format_string in ("%Y%m%d", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                parsed_date = datetime.strptime(date_text, format_string).date()
                break
            except ValueError:
                continue
        if parsed_date is None:
            raise ValueError(f"Unrecognized holiday date: {date_text!r}")
        name = normalized.get("holiday name") or normalized.get("name")
        yield parsed_date.isoformat(), name, jurisdiction.upper()


def download_holidays(destination: Path) -> int:
    """Download and combine official NSW/national public-holiday CSV files."""

    unique_rows = set()
    for url in HOLIDAY_URLS:
        unique_rows.update(_normalized_holiday_rows(download_bytes(url)))

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["date", "holiday_name", "jurisdiction"])
        writer.writerows(sorted(unique_rows))
    return len(unique_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2019-01-01")
    parser.add_argument("--end", default="2025-12-31")
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    weather_rows = download_weather(
        args.start, args.end, args.output_dir / "bankstown_weather_hourly.csv"
    )
    holiday_rows = download_holidays(args.output_dir / "nsw_public_holidays.csv")
    print(f"Wrote {weather_rows:,} hourly weather rows")
    print(f"Wrote {holiday_rows:,} NSW/national holiday rows")


if __name__ == "__main__":
    main()
