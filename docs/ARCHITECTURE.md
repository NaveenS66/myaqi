# Architecture Diagram

```mermaid
flowchart LR
  subgraph Signals["Data & spatial signals"]
    AQI["CAAQMS / OpenAQ station observations"]
    WX["Open-Meteo weather forecast"]
    LU["Land use + roads + source registry"]
    RS["Satellite fire / thermal signals"]
  end

  subgraph Intelligence["AQI Sentinel intelligence layer"]
    ING["Ingestion & cache\nwith data-status label"]
    FC["Forecast agent\nLightGBM + persistence baseline"]
    AT["Attribution agent\nwind + spatial cues"]
    EN["Enforcement agent\npriority, rationale, timeframe"]
    AD["Advisory agent\nhealth message + language"]
  end

  subgraph Experience["Decision experience"]
    MAP["React + Leaflet operations map"]
    ACT["Ranked municipal action list"]
    CIT["Citizen health advisory"]
  end

  AQI --> ING
  WX --> FC
  LU --> AT
  RS --> AT
  ING --> FC
  ING --> AT
  FC --> EN
  AT --> EN
  EN --> AD
  FC --> MAP
  AT --> MAP
  EN --> ACT
  AD --> CIT
  MAP --> ACT
```

## Production safeguards

- Ingestion records whether a response is live, cached, or a demo fallback.
- Forecast metrics are reported only from a time-ordered holdout; a 24-hour persistence forecast is the baseline.
- Attribution is an inspection-prioritisation hypothesis, not proof of legal responsibility.
- Recommended enforcement actions require human review and field verification.
