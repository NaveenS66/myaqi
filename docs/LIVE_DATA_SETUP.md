
# Live Data Setup

AQI Sentinel distinguishes verified observations from scenario data. Live mode
requires an OpenAQ v3 API key and never substitutes synthetic AQI when a
provider fails.

## Configure OpenAQ

1. Create an OpenAQ API key through the official OpenAQ account flow.
2. Copy `.env.example` to `.env` and set `OPENAQ_API_KEY`.
3. Start the backend. Every returned station row carries its provenance.

## What the platform reports

- `observed_openaq_pm25_derived_aqi`: measured OpenAQ PM2.5 concentration,
  transformed using the CPCB PM2.5 sub-index. It is a provisional AQI proxy,
  not an official multi-pollutant CPCB AQI.
- `unavailable`: no verified observation was available. The product suppresses
  enforcement recommendations rather than creating data.
- `demo_scenario`: clearly-labelled offline scenario data only.

For a city deployment, replace the provisional OpenAQ proxy with authenticated
CPCB feeds and preserve the raw observation, source timestamp, averaging window
and transformation in the audit log.

