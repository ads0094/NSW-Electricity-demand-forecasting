from datetime import datetime
import unittest

from src.data.build_features import australian_season, demand_period, is_sydney_dst


class FeatureTimeTests(unittest.TestCase):
    def test_midnight_ending_interval_stays_on_previous_day(self):
        interval_start, weather_hour = demand_period(datetime(2026, 1, 1, 0, 0))
        self.assertEqual(interval_start, datetime(2025, 12, 31, 23, 30))
        self.assertEqual(weather_hour, datetime(2025, 12, 31, 23, 0))

    def test_half_hour_ending_interval_uses_same_hour(self):
        interval_start, weather_hour = demand_period(datetime(2025, 1, 1, 0, 30))
        self.assertEqual(interval_start, datetime(2025, 1, 1, 0, 0))
        self.assertEqual(weather_hour, datetime(2025, 1, 1, 0, 0))

    def test_australian_seasons(self):
        self.assertEqual(australian_season(1), "summer")
        self.assertEqual(australian_season(4), "autumn")
        self.assertEqual(australian_season(7), "winter")
        self.assertEqual(australian_season(10), "spring")

    def test_sydney_dst_uses_fixed_nem_instant(self):
        self.assertEqual(is_sydney_dst(datetime(2025, 1, 15, 12, 0)), 1)
        self.assertEqual(is_sydney_dst(datetime(2025, 7, 15, 12, 0)), 0)
        self.assertEqual(is_sydney_dst(datetime(2025, 10, 5, 1, 30)), 0)
        self.assertEqual(is_sydney_dst(datetime(2025, 10, 5, 2, 0)), 1)


if __name__ == "__main__":
    unittest.main()
