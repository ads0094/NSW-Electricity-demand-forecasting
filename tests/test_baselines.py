from datetime import datetime, timedelta
import unittest

import pandas as pd

from src.modeling.baselines import add_baseline_predictions, calculate_metrics


class BaselineTests(unittest.TestCase):
    def test_previous_day_and_week_use_expected_lags(self):
        periods = 400
        data = pd.DataFrame(
            {
                "interval_end_nem_time": pd.date_range("2025-01-01 00:30", periods=periods, freq="30min"),
                "scheduled_demand_mw": range(periods),
            }
        )
        result = add_baseline_predictions(data)
        self.assertEqual(result.loc[48, "Previous day"], 0)
        self.assertEqual(result.loc[336, "Previous week"], 0)

    def test_metrics_match_simple_example(self):
        data = pd.DataFrame(
            {
                "interval_start_nem_time": [
                    datetime(2025, 1, 1) + timedelta(minutes=30 * index)
                    for index in range(2)
                ],
                "scheduled_demand_mw": [100.0, 200.0],
                "prediction": [110.0, 180.0],
            }
        )
        metrics = calculate_metrics(data, "prediction")
        self.assertAlmostEqual(metrics.mae_mw, 15.0)
        self.assertAlmostEqual(metrics.rmse_mw, (250.0) ** 0.5)
        self.assertAlmostEqual(metrics.mape_percent, 10.0)
        self.assertAlmostEqual(metrics.daily_peak_mae_mw, 20.0)
        self.assertAlmostEqual(metrics.bias_mw, -5.0)


if __name__ == "__main__":
    unittest.main()
