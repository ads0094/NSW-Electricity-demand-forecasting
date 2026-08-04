# NSW scheduled-demand data quality report

## Result

**PASS**

This report validates the locally generated half-hourly dataset. The source CSV
is reproducible and intentionally excluded from Git.

## Coverage and integrity

| Check | Result |
| --- | ---: |
| First interval ending | 2019-01-01 00:30:00 |
| Last interval ending | 2026-01-01 00:00:00 |
| Valid rows | 122,736 |
| Duplicate timestamps | 0 |
| Missing half-hour intervals | 0 |
| Non-30-minute timestamp gaps | 0 |
| Missing demand values | 0 |
| Non-positive demand values | 0 |
| Unexpected regions | None |

## Demand summary

| Statistic | Scheduled demand (MW) |
| --- | ---: |
| Minimum | 3,439.57 |
| Mean | 7,723.11 |
| Median | 7,574.30 |
| Maximum | 13,750.99 |

## Annual coverage

| Year | Half-hour rows | Mean scheduled demand (MW) |
| --- | ---: | ---: |
| 2019 | 17,520 | 8,055.98 |
| 2020 | 17,568 | 7,768.16 |
| 2021 | 17,520 | 7,617.32 |
| 2022 | 17,520 | 7,718.63 |
| 2023 | 17,520 | 7,579.47 |
| 2024 | 17,568 | 7,648.57 |
| 2025 | 17,520 | 7,673.74 |

The final timestamp is `2026-01-01 00:00:00` because AEMO uses interval-ending
timestamps: it represents the last half-hour of 31 December 2025.
