import unittest
from urllib.parse import parse_qs, urlparse

from src.data.context_data import _normalized_holiday_rows, weather_url


class ContextDataTests(unittest.TestCase):
    def test_weather_request_is_fixed_nem_time_and_era5(self):
        query = parse_qs(urlparse(weather_url("2019-01-01", "2019-01-31")).query)
        self.assertEqual(query["timezone"], ["Etc/GMT-10"])
        self.assertEqual(query["models"], ["era5"])
        self.assertIn("temperature_2m", query["hourly"][0])

    def test_holidays_keep_nsw_and_national_only(self):
        payload = (
            "Date,Holiday Name,Jurisdiction\n"
            "20190101,New Year's Day,nsw\n"
            "20190126,Australia Day,australia\n"
            "20190311,Adelaide Cup,sa\n"
        ).encode()
        rows = list(_normalized_holiday_rows(payload))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], "2019-01-01")
        self.assertEqual(rows[1][2], "AUSTRALIA")


if __name__ == "__main__":
    unittest.main()
