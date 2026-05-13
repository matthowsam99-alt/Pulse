# Pulse Australia — Data Pipeline

Fetches, normalises and serves Australian social and economic indicator data for the Pulse visualisation app.

## Structure

```
aus-pulse/
├── pipeline/
│   ├── schema.py              # Standard data schema + indicator registry (all 46)
│   └── fetchers/
│       ├── rba.py             # RBA tables: cash rate, M2, debt, gold, credit, terms of trade
│       └── abs.py             # ABS API: CPI, unemployment, population, wages, GDP, housing
├── data/
│   ├── events.json            # All historical events for chart overlay
│   ├── raw/                   # Raw downloaded files (gitignored)
│   ├── processed/             # Normalised per-indicator JSON files
│   └── output/                # Final files for CDN / front-end consumption
├── .github/workflows/
│   └── refresh.yml            # GitHub Actions: monthly scheduled refresh
├── run_pipeline.py            # Main runner
└── requirements.txt
```

## Output schema

Every indicator outputs a JSON file like:

```json
{
  "id": "cash_rate",
  "label": "Cash rate",
  "category": "economy",
  "unit": "%",
  "unit_label": "%",
  "frequency": "monthly",
  "source": "RBA Table A2",
  "source_url": "https://...",
  "description": "The RBA's official cash rate target...",
  "first_year": 1990,
  "last_updated": "2026-04",
  "projection_start": "2025-01",
  "series": [
    { "date": "1990-01", "value": 17.5, "projected": false },
    { "date": "2025-01", "value": 4.35, "projected": false },
    { "date": "2025-06", "value": 4.1,  "projected": true }
  ]
}
```

## Running locally

```bash
pip install -r requirements.txt

# Run everything
python run_pipeline.py

# Run specific source
python run_pipeline.py --source rba
python run_pipeline.py --source abs
```

## Adding a new indicator

1. Add to `INDICATOR_REGISTRY` in `pipeline/schema.py`
2. Write a fetcher function in the relevant fetcher file
3. Add to that file's `run_all()` function
4. Run pipeline and check output

## Data sources

| Source | What | URL |
|--------|------|-----|
| RBA Statistical Tables | Cash rate, M2, household debt, credit, gold, terms of trade | rba.gov.au/statistics/tables |
| ABS Data API | CPI, unemployment, GDP, population, wages, housing | api.data.abs.gov.au |
| AIHW | Suicide, homelessness, life expectancy, mental health | aihw.gov.au |
| Treasury | Government debt, spending, tax revenue | treasury.gov.au |
| BOM | Temperature anomaly, drought | bom.gov.au |

## Refresh schedule

Monthly via GitHub Actions (1st of each month). Manual trigger available in GitHub UI.
Most indicators update quarterly or annually — monthly refresh ensures we catch RBA and ABS monthly releases.
