# Forecast Validation Protocol

## Purpose

Produce a judge-verifiable, station-level comparison between the forecasting model and a simple persistence baseline.

## Before the demo

1. Ingest one continuous station history with timestamps and AQI.
2. Run training with the final 21 days held out in time order.
3. Export evidence:

```bash
cd backend
python export_evaluation_report.py --output ../artifacts/forecast_evaluation.csv
```

4. Put the resulting CSV beside the deck or link it in the submission.

## What may be claimed

Only rows present in the exported report may be described as **holdout evaluated**. For each station, report:

- model RMSE;
- persistence RMSE (AQI at t−24h);
- percentage improvement;
- train and holdout row counts;
- evaluation date.

Do not average across stations without showing every station-level result. Do not claim 1 km coverage when validation is only station-level.
