
# Source Registry Contract

Live source attribution is only as credible as its registry. AQI Sentinel uses
only records marked `verified` with a traceable source URL and verification date.

## Required fields

| Field | Purpose |
|---|---|
| `source_id` | Stable city/board identifier |
| `source_type` | `industry`, `construction`, `traffic_corridor`, `open_burning`, or `diesel_fleet` |
| `name` | Human-readable source name |
| `lat`, `lon` | WGS84 coordinates |
| `verification_status` | Must be `verified` for live use |
| `verified_at` | ISO-8601 verification date |
| `provenance_url` | Permit, registry, incident, or official GIS source |
| `permit_or_case_id` | Optional traceable authority reference |

## Onboarding workflow

1. Export the authoritative city/PCB source register.
2. Validate coordinates, permit status and source type with the owning agency.
3. Retain the original source URL or internal case reference.
4. Load only verified records into `backend/data/source_registry.csv`.
5. Review attribution outcomes against field-inspection findings each month.

Empty registry means **onboarding required**. The product must not infer named
legal targets from unverified source lists.

