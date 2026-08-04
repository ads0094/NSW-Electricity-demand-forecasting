# Model-ready dataset report

## Result

**PASS**

| Check | Result |
| --- | ---: |
| Model rows | 122,736 |
| First demand interval ending | 2019-01-01 00:30:00 |
| Last demand interval ending | 2026-01-01 00:00:00 |
| Rows missing matched weather | 0 |
| Public-holiday half-hours | 4,320 |
| Sydney daylight-saving half-hours | 61,584 |

Each model row represents the preceding half-hour. Hourly weather is matched to
the hour containing the interval start. This avoids inventing half-hour weather
values and keeps the final midnight-ending demand interval with the prior day.
