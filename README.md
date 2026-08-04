# NSW Electricity Demand Forecasting

An end-to-end forecasting project for half-hourly operational electricity demand in New South Wales, Australia.

## Project objective

Build a reproducible forecasting pipeline that explains historical NSW electricity-demand patterns and predicts demand for the next 24 hours and 7 days.

The project will combine:

- operational demand published by the Australian Energy Market Operator (AEMO);
- weather observations published by the Bureau of Meteorology (BOM);
- calendar, public-holiday, seasonal, and daylight-saving features; and
- forecasting baselines, statistical models, and machine-learning models.

## Questions we want to answer

1. How does NSW demand vary by time of day, weekday, season, and year?
2. How strongly do temperature and extreme-weather conditions affect demand?
3. How do public holidays and daylight saving alter the normal demand profile?
4. Which forecasting approach performs best on unseen future periods?
5. When and why does the selected model make its largest errors?

## Initial modelling scope

- **Region:** New South Wales (`NSW1` in AEMO data)
- **Target:** half-hourly operational demand in MW
- **Candidate history:** 2019–2025, subject to archive availability and data-quality checks
- **Forecast horizons:** 24 hours and 7 days
- **Validation:** chronological rolling-origin evaluation
- **Metrics:** MAE, RMSE, MAPE, and peak-demand error
- **Baselines:** previous day and previous week
- **Candidate models:** seasonal naive, SARIMA/ETS, Prophet, and gradient-boosted trees

The final model list may change after the data audit. Model selection will be evidence-based rather than based on algorithm complexity.

## Repository structure

```text
data/
  raw/          # downloaded source files; normally not committed
  interim/      # cleaned intermediate data; normally not committed
  processed/    # model-ready data or small documented samples
docs/           # GitHub Pages report
models/         # serialized models and model metadata
notebooks/      # numbered exploratory and modelling notebooks
reports/figures/# generated analysis figures
src/            # reusable data and modelling code
tests/          # automated tests
```

## Planned steps

1. Project charter and reproducible repository scaffold
2. Data acquisition and validation
3. Exploratory analysis and baseline forecasts
4. Model development and time-based evaluation
5. Interactive dashboard and project website
6. Reproduction check and final documented release

## Data sources

- [AEMO operational demand data](https://aemo.com.au/energy-systems/electricity/national-electricity-market-nem/data-nem/operational-demand-data)
- [AEMO NEMWeb market data](https://visualisations.aemo.com.au/aemo/nemweb/)
- [BOM Climate Data Online](https://www.bom.gov.au/climate/data/)

Source licensing, attribution, archive coverage, and redistribution constraints will be documented during the data-audit step.

