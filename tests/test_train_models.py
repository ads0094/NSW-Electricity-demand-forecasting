import unittest

import pandas as pd

from src.modeling.train_models import FEATURE_COLUMNS, prepare_features


class ModelFeatureTests(unittest.TestCase):
    def test_demand_lags_do_not_use_current_or_future_targets(self):
        periods = 400
        data = pd.DataFrame(
            {
                "interval_end_nem_time": pd.date_range("2025-01-01 00:30", periods=periods, freq="30min"),
                "scheduled_demand_mw": range(periods),
                "temperature_2m": 20.0,
                "relative_humidity_2m": 50.0,
                "apparent_temperature": 20.0,
                "precipitation": 0.0,
                "wind_speed_10m": 10.0,
                "shortwave_radiation": 0.0,
                "is_weekend": 0,
                "is_public_holiday": 0,
                "is_sydney_dst": 1,
                "hour": [index // 2 % 24 for index in range(periods)],
                "half_hour": [index % 2 for index in range(periods)],
                "day_of_week": 1,
                "year": 2025,
            }
        )
        prepared = prepare_features(data)
        first = prepared.iloc[0]
        self.assertEqual(first["scheduled_demand_mw"], 336)
        self.assertEqual(first["demand_lag_1_day"], 288)
        self.assertEqual(first["demand_lag_1_week"], 0)
        self.assertTrue(set(FEATURE_COLUMNS).issubset(prepared.columns))


if __name__ == "__main__":
    unittest.main()
