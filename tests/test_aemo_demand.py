from datetime import datetime, timedelta
from pathlib import Path
import unittest

from src.data.aemo_demand import (
    DemandRecord,
    aggregate_half_hour,
    archive_urls,
    half_hour_end,
    write_half_hour_csv,
)


class ArchiveUrlTests(unittest.TestCase):
    def test_current_and_legacy_names_are_available(self):
        current, legacy = archive_urls(2025, 1)

        self.assertIn("MMSDM_2025_01", current)
        self.assertIn("PUBLIC_ARCHIVE%23DISPATCHREGIONSUM", current)
        self.assertTrue(legacy.endswith("PUBLIC_DVD_DISPATCHREGIONSUM_202501010000.zip"))


class AggregationTests(unittest.TestCase):
    def test_midnight_is_assigned_to_previous_half_hour(self):
        timestamp = datetime(2025, 2, 1, 0, 0)
        self.assertEqual(half_hour_end(timestamp), timestamp)

    def test_six_intervals_are_averaged(self):
        start = datetime(2025, 1, 1, 0, 5)
        records = [
            DemandRecord(start + timedelta(minutes=5 * index), float(index + 1))
            for index in range(6)
        ]

        complete, incomplete = aggregate_half_hour(records)

        self.assertEqual(incomplete, [])
        self.assertEqual(len(complete), 1)
        self.assertEqual(complete[0].interval_end, datetime(2025, 1, 1, 0, 30))
        self.assertEqual(complete[0].demand_mw, 3.5)

    def test_incomplete_half_hour_is_reported_and_excluded(self):
        start = datetime(2025, 1, 1, 0, 5)
        records = [DemandRecord(start + timedelta(minutes=5 * index), 100.0) for index in range(5)]

        complete, incomplete = aggregate_half_hour(records)

        self.assertEqual(complete, [])
        self.assertEqual(incomplete, [datetime(2025, 1, 1, 0, 30)])

    def test_output_has_documented_columns(self):
        start = datetime(2025, 1, 1, 0, 5)
        records = [DemandRecord(start + timedelta(minutes=5 * index), 100.0) for index in range(6)]
        complete, _ = aggregate_half_hour(records)

        output = Path("tests/.test_demand_output.csv")
        try:
            write_half_hour_csv(complete, output)
            lines = output.read_text(encoding="utf-8").splitlines()
        finally:
            output.unlink(missing_ok=True)

        self.assertEqual(
            lines[0], "interval_end_nem_time,region_id,scheduled_demand_mw"
        )
        self.assertEqual(lines[1], "2025-01-01 00:30:00,NSW1,100.00000")


if __name__ == "__main__":
    unittest.main()
