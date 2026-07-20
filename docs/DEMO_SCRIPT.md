# AQI Sentinel — 3-Minute Demo Script

## 0:00–0:20 — The decision gap

“Cities already receive AQI readings. The missing layer is the decision: **which ward, which likely source, which intervention, and how urgently?** AQI Sentinel turns a signal into an evidence-backed action plan.”

Show the city map and station overview.

## 0:20–0:55 — Detect and forecast

1. Select **Anand Vihar** on the map.
2. Point out its AQI marker and the station overview.
3. Open the **72-hour forecast** card.

Say: “The forecast card labels its own evidence state. A green *Holdout Evaluated* badge means the displayed RMSE comes from a time-ordered holdout comparison against a persistence baseline. An amber *Demo Forecast* badge is clearly a scenario fallback—not a performance claim.”

## 0:55–1:45 — Explain and intervene

Click the station and let the pipeline run.

Say: “The system runs four connected steps: forecast the hotspot, attribute likely sources using wind and spatial cues, rank officers’ actions, then issue a health advisory.”

Show, in order:

- Dominant source category and confidence
- AQI trend and 48-hour outlook
- Ranked action card and response timeframe
- Municipal recommendation and supporting rationale

Say: “Instead of sending every inspector everywhere, the city sees where intervention is most urgent and why.”

## 1:45–2:20 — Protect people, not just averages

Change the language selector to Hindi, Kannada, or Tamil.

Say: “The same incident becomes a ward-level, language-appropriate citizen health advisory. This connects operational intelligence to public-health action.”

## 2:20–2:50 — Scale

Toggle Delhi + Mumbai.

Say: “The platform separates ingestion, forecast, attribution, and enforcement services. Adding a city means onboarding station, land-use, and regulated-source layers—not rebuilding the product.”

## 2:50–3:00 — Closing

“AQI Sentinel turns a pollution reading into a prioritised intervention before exposure becomes a public-health emergency.”

## Judge Q&A: truthful answers

**Is the source attribution causal proof?**  
No. It is decision-support attribution using spatial and meteorological signals. It should guide inspection, then be verified with field evidence and emissions inventories.

**Is every forecast live and validated?**  
No. The UI labels synthetic demo continuity separately. Validated claims are limited to runs with saved, held-out evaluation metrics.

**What is the next production step?**  
Integrate authenticated CPCB feeds, city permit/industry registries, remote-sensing layers, and audit the recommendation outcomes.
