# Judging Evidence Ledger

Use this document to keep the presentation technically accurate.

| Judge criterion | Evidence shown in prototype | What we claim |
|---|---|---|
| Innovation | Signal → forecast → attribution → enforcement → advisory workflow | AQI Sentinel operationalises several data signals into one intervention workflow 
| Business impact | Ranked action list, timeframes, officer narrative, multilingual advice | Reduces the time to form an intervention hypothesis | 
| Technical excellence | FastAPI, React/Leaflet, LightGBM training workflow, time-ordered holdout and persistence comparator | A reproducible model-evaluation path is implemented | 
| Scalability | Service separation and multi-city station design | New cities can be onboarded through data-layer configuration | 
| UX | Map, station selection, evidence status badge, ranked actions, language selector | Operators can trace signal to recommended action in one interface | 

## Metric rules

1. Only show RMSE, persistence RMSE, and improvement when the forecast card says **HOLDOUT EVALUATED**.
2. Never present **DEMO FORECAST** as a prediction accuracy result.
3. Describe attribution confidence as a prioritisation confidence, not legal proof of responsibility.
4. When asked about data availability, state whether the run uses live, cached, or synthetic fallback data.
5. Pair every recommended action with a human-review step before enforcement.

## Strongest defensible one-line claim

> AQI Sentinel reduces the analyst’s path from a high-AQI signal to an explainable, ranked intervention hypothesis—from manual multi-dashboard investigation to a single decision workspace.

## One metric to add before final submission

Run the training endpoint for one station with a verified historical dataset, save its time-ordered holdout result, and capture:

- Model RMSE
- 24-hour persistence RMSE
- Improvement percentage
- Training and holdout period
- Number of observations

Show this in the deck with the exact station and data period.
