import unittest

import pandas as pd

from src.presentation.build_dashboard_data import build_payload


class DashboardDataTests(unittest.TestCase):
    def test_payload_aggregates_without_exposing_half_hour_rows(self):
        data = pd.DataFrame(
            {
                "interval_start_nem_time": pd.to_datetime(["2025-01-01 00:00", "2025-01-01 00:30"]),
                "interval_end_nem_time": pd.to_datetime(["2025-01-01 00:30", "2025-01-01 01:00"]),
                "scheduled_demand_mw": [100.0, 200.0],
                "temperature_2m": [20.0, 22.0],
                "hour": [0, 0],
                "half_hour": [0, 1],
                "year": [2025, 2025],
                "season": ["summer", "summer"],
                "is_weekend": [0, 0],
            }
        )
        payload = build_payload(data)
        self.assertEqual(len(payload["daily"]), 1)
        self.assertEqual(payload["daily"][0]["mean_mw"], 150.0)
        self.assertEqual(payload["summary"]["rows"], 2)


if __name__ == "__main__":
    unittest.main()
