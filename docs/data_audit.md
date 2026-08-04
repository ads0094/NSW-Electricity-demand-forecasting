# Data audit: NSW electricity demand

## Target selection

This project uses **scheduled demand** for the AEMO region `NSW1`.

AEMO's operational-demand publication is the conceptually preferred target, but
its convenient archive retention is approximately 13 months. The project's
planned 2019–2025 modelling period requires a longer, consistent history.
AEMO's monthly NEMWeb Market Management System archive provides that coverage.

The selected source is:

- package: `DISPATCH`
- table: `REGIONSUM`
- region: `NSW1`
- field: `CLEAREDSUPPLY`
- raw frequency: five minutes
- model frequency: half-hourly
- unit: MW

AEMO identifies `DISPATCHREGIONSUM.CLEAREDSUPPLY` as the source of scheduled
demand used in its NEM data dashboard. Scheduled demand is not interchangeable
with operational demand. This distinction must remain visible in reports,
figures, and model documentation.

## Half-hour aggregation

Each half-hour target is the arithmetic mean of its six five-minute ending
intervals. For example, the interval ending at 00:30 contains observations
ending at 00:05, 00:10, 00:15, 00:20, 00:25, and 00:30.

An aggregated interval is valid only when all six distinct five-minute records
are present. Incomplete intervals are reported by validation and excluded from
the model-ready output.

## Initial sample validation

The January 2025 archive was used to confirm the schema and expected coverage.

| Check | Result |
| --- | ---: |
| NSW1 five-minute records | 8,928 |
| Unique NSW1 timestamps | 8,928 |
| Expected records | 8,928 |
| Missing five-minute intervals | 0 |
| Minimum `TOTALDEMAND` | 4,188.12 MW |
| Mean `TOTALDEMAND` | 7,230.11 MW |
| Maximum `TOTALDEMAND` | 12,128.62 MW |

These descriptive values were part of the archive audit. The forecasting target
is `CLEAREDSUPPLY`, not `TOTALDEMAND`.

## Raw-data policy

Downloaded AEMO archives and generated datasets are ignored by Git. The
repository contains code, tests, metadata, and documentation needed to reproduce
them, rather than redistributing the raw files.

## Sources

- [AEMO NEM data dashboard](https://aemo.com.au/energy-systems/electricity/national-electricity-market-nem/data-nem/data-dashboard-nem)
- [AEMO NEMWeb market data](https://visualisations.aemo.com.au/aemo/nemweb/)
- [AEMO operational demand data](https://aemo.com.au/energy-systems/electricity/national-electricity-market-nem/data-nem/operational-demand-data)
