# Judging Evidence Ledger

## Claim status

| Product claim | Status | Evidence shown in demo | Limitation |
|---|---|---|---|
| Station observations | Live when provider responds; otherwise explicitly unavailable | Data-status badge and source timestamp | No synthetic value is labelled live |
| 24–72h forecast | Measured only after a saved time-ordered holdout run | Model RMSE vs 24h persistence RMSE | Demo forecast is labelled scenario only |
| Source attribution | Inspection-prioritisation hypothesis | Wind, source-registry and land-use inputs; confidence | Not legal or causal proof |
| Enforcement recommendation | Human-reviewed decision support | Evidence status, ranked actions, rationale | Never an automated enforcement order |
| Multilingual advisory | Implemented | English, Hindi, Kannada, Tamil selector | Health copy should be approved locally |

## Forecast evaluation protocol

- Train per station on observations strictly before the holdout window.
- Hold out the most recent 21 days.
- Compare LightGBM RMSE with the 24-hour persistence baseline.
- Record station, date range, row counts, model RMSE, baseline RMSE and percentage improvement.
- Do not show an accuracy claim when these artefacts are absent.

## Demo-safe wording

Say: “This ranks inspection hypotheses from observed and spatial signals.”
Do not say: “The platform proves that a named source caused pollution.”
Say: “Forecast performance is reported only when the card shows **Holdout Evaluated**.”
