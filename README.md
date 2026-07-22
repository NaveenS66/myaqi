# AQI Sentinel — Urban Air Quality Intelligence

AQI Sentinel helps Indian city teams move from *“AQI is high”* to *“what should we do, where, and why?”*

It combines station observations, weather context, source-attribution heuristics, forecast modelling, and an enforcement-prioritisation agent into a map-first decision interface.

## The intervention loop

1. **Detect** — view CAAQMS stations and AQI severity on the city map.
2. **Forecast** — estimate the next 24–72 hours at station level.
3. **Explain** — show likely source categories and an attribution confidence score.
4. **Prioritise** — generate a ranked inspection/action list for officers.
5. **Protect** — issue ward-level citizen advice in English, Hindi, Kannada, or Tamil.

## What is implemented

- FastAPI backend with AQI, forecast, attribution, enforcement, advisory, and metadata endpoints
- React + Leaflet dashboard for Delhi and Mumbai stations
- LightGBM training workflow with a persistence-baseline comparison
- Wind-sector and land-use-informed source-attribution engine
- Ranked municipal intervention cards with response timeframe and supporting rationale
- Multi-language citizen health advisory output
- Open-Meteo weather integration and OpenAQ data-ingestion attempt with local cache support

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r ../requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

## Evidence and responsible-demo note

This prototype is designed to remain usable when public data services are unavailable. In that situation it uses cached data or clearly labelled synthetic/demo fallbacks. **Synthetic outputs must not be represented as live CPCB/OpenAQ observations or validated forecast performance.**

For the hackathon demo, show the data-status label and describe source attribution as a decision-support estimate, not a regulatory finding. Claims of forecast RMSE improvement should only be shown after running the holdout evaluation on the corresponding station dataset.

## Architecture

```text
CAAQMS / OpenAQ + Open-Meteo + spatial source layers
                         │
                         ▼
             FastAPI intelligence layer
      ┌────────────┬────────────┬────────────┐
      │ Forecast   │ Attribution│ Enforcement│
      │ (LightGBM) │ (wind/land │ (priority +│
      │            │ use cues)  │ action)    │
      └────────────┴────────────┴────────────┘
                         │
                         ▼
          React + Leaflet operations dashboard
                         │
                         ▼
      Municipal action list + citizen advisories
```

## Tech

Python, FastAPI, pandas, NumPy, scikit-learn, LightGBM, Open-Meteo, OpenAQ, React, Vite, Leaflet, Tailwind CSS.

## Submission narrative

**AQI Sentinel converts a pollution signal into an evidence-backed intervention plan before it becomes a public-health emergency.**


## Submission evidence

- [Architecture](docs/ARCHITECTURE.md)
- [Judging evidence ledger](docs/JUDGING_EVIDENCE.md)
- [Forecast validation protocol](docs/FORECAST_VALIDATION_PROTOCOL.md)
- [90-day municipal pilot plan](docs/PILOT_PLAN.md)
- [Judge Q&A](docs/JUDGE_QA.md)
- [3-minute demo script](docs/DEMO_SCRIPT.md)

The platform exposes evidence state in the user interface. Unavailable observations are never represented as live data, and inspection priorities always require human field verification.
