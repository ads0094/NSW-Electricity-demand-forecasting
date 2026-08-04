from pathlib import Path
import unittest

import pandas as pd

from src.analysis.eda import format_time_of_day, load_features


class EdaTests(unittest.TestCase):
    def test_decimal_half_hour_is_formatted_as_clock_time(self):
        self.assertEqual(format_time_of_day(17.5), "17:30")

    def test_missing_required_feature_is_rejected(self):
        path = Path("tests/.test_incomplete_features.csv")
        try:
            pd.DataFrame(
                {
                    "interval_end_nem_time": ["2025-01-01 00:30:00"],
                    "interval_start_nem_time": ["2025-01-01 00:00:00"],
                }
            ).to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "missing columns"):
                load_features(path)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
