from datetime import datetime, timedelta
import unittest

from src.data.validate_demand import (
    ValidatedRow,
    expected_interval_count,
    quality_status,
    render_markdown,
    summarize,
)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        start = datetime(2025, 1, 1, 0, 30)
        self.rows = [
            ValidatedRow(start + timedelta(minutes=30 * index), "NSW1", 100 + index)
            for index in range(4)
        ]

    def test_expected_count_is_inclusive(self):
        self.assertEqual(
            expected_interval_count(
                datetime(2025, 1, 1, 0, 30), datetime(2025, 1, 1, 2, 0)
            ),
            4,
        )

    def test_complete_series_passes(self):
        summary = summarize(self.rows)
        self.assertEqual(quality_status(summary), "PASS")
        self.assertEqual(summary.missing_intervals, 0)
        self.assertEqual(summary.duplicate_timestamps, 0)

    def test_duplicate_is_detected(self):
        summary = summarize([*self.rows, self.rows[0]])
        self.assertEqual(summary.duplicate_timestamps, 1)
        self.assertEqual(quality_status(summary), "REVIEW REQUIRED")

    def test_gap_is_detected(self):
        summary = summarize([self.rows[0], self.rows[2], self.rows[3]])
        self.assertEqual(summary.missing_intervals, 1)
        self.assertEqual(summary.unexpected_intervals, 1)

    def test_report_contains_status_and_annual_table(self):
        report = render_markdown(summarize(self.rows))
        self.assertIn("**PASS**", report)
        self.assertIn("| 2025 | 4 |", report)

    def test_midnight_year_boundary_belongs_to_previous_demand_year(self):
        rows = [ValidatedRow(datetime(2026, 1, 1, 0, 0), "NSW1", 100.0)]
        summary = summarize(rows)
        self.assertEqual(summary.annual_rows, {2025: 1})


if __name__ == "__main__":
    unittest.main()
