"""
Pulse Australia — Standard indicator schema
Every indicator outputs a JSON file conforming to this structure.
"""

from dataclasses import dataclass, asdict
from typing import Optional
import json
from datetime import datetime


@dataclass
class DataPoint:
    date: str        # ISO format: YYYY-MM or YYYY
    value: float
    projected: bool = False


@dataclass
class Indicator:
    id: str                      # snake_case unique identifier
    label: str                   # Human readable name
    category: str                # Economy | Housing | Demographics | Wellbeing | Government | Environment
    unit: str                    # AUD, %, per 100k, index, Mt, etc
    unit_label: str              # Display string e.g. "$" or "%" or " yrs"
    frequency: str               # monthly | quarterly | annual
    source: str                  # e.g. "RBA Table A2"
    source_url: str
    description: str             # One sentence explaining what this measures
    first_year: int              # Earliest reliable data year
    last_updated: str            # YYYY-MM
    series: list                 # List of DataPoint dicts
    projection_start: Optional[str] = "2025-01"  # Where projected data begins
    notes: Optional[str] = None  # Methodology notes, series breaks etc
    real_adjusted: Optional[bool] = False  # Whether values are inflation-adjusted
    base_year: Optional[str] = None  # Base year for real values e.g. "2022-23"


def save_indicator(indicator: Indicator, output_dir: str):
    """Save indicator to standard JSON file."""
    data = asdict(indicator)
    path = f"{output_dir}/{indicator.id}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  ✓ Saved {indicator.id} ({len(indicator.series)} data points)")
    return path


def load_indicator(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


# ── Category definitions ──────────────────────────────────────────────────────

CATEGORIES = {
    "economy":      {"label": "Economy",      "color": "#E07B39"},
    "housing":      {"label": "Housing",      "color": "#C0392B"},
    "demographics": {"label": "Demographics", "color": "#2980B9"},
    "wellbeing":    {"label": "Wellbeing",    "color": "#27AE60"},
    "government":   {"label": "Government",   "color": "#8E44AD"},
    "environment":  {"label": "Environment",  "color": "#16A085"},
}

# ── Indicator registry (all 46) ───────────────────────────────────────────────
# Used by the front-end to know what exists before fetching data

INDICATOR_REGISTRY = [
    # ECONOMY
    {"id": "median_wage",           "label": "Median wage",                  "category": "economy",      "unit": "AUD",     "unit_label": "$"},
    {"id": "wage_price_index",      "label": "Wage price index",             "category": "economy",      "unit": "index",   "unit_label": ""},
    {"id": "cpi",                   "label": "CPI",                          "category": "economy",      "unit": "index",   "unit_label": ""},
    {"id": "cash_rate",             "label": "Cash rate",                    "category": "economy",      "unit": "%",       "unit_label": "%"},
    {"id": "gdp_per_capita",        "label": "GDP per capita",               "category": "economy",      "unit": "AUD",     "unit_label": "$"},
    {"id": "productivity",          "label": "Productivity (GDP/hr)",        "category": "economy",      "unit": "index",   "unit_label": ""},
    {"id": "terms_of_trade",        "label": "Terms of trade",               "category": "economy",      "unit": "index",   "unit_label": ""},
    {"id": "household_debt_ratio",  "label": "Household debt to income",     "category": "economy",      "unit": "%",       "unit_label": "%"},
    {"id": "m2_money_supply",       "label": "M2 money supply",              "category": "economy",      "unit": "AUD_bn",  "unit_label": "$bn"},
    {"id": "private_credit_growth", "label": "Private credit growth",        "category": "economy",      "unit": "%",       "unit_label": "%"},
    {"id": "asx200",                "label": "ASX 200",                      "category": "economy",      "unit": "index",   "unit_label": ""},
    {"id": "gold_aud",              "label": "Gold spot price (AUD)",        "category": "economy",      "unit": "AUD",     "unit_label": "$"},
    {"id": "consumer_confidence",   "label": "Consumer confidence",          "category": "economy",      "unit": "index",   "unit_label": ""},
    {"id": "business_investment",   "label": "Business investment % GDP",    "category": "economy",      "unit": "%",       "unit_label": "%"},
    {"id": "current_account",       "label": "Current account balance",      "category": "economy",      "unit": "AUD_bn",  "unit_label": "$bn"},
    # HOUSING
    {"id": "median_house_price",    "label": "Median house price",           "category": "housing",      "unit": "AUD",     "unit_label": "$"},
    {"id": "price_to_income",       "label": "Price-to-income ratio",        "category": "housing",      "unit": "ratio",   "unit_label": "x"},
    {"id": "rental_vacancy",        "label": "Rental vacancy rate",          "category": "housing",      "unit": "%",       "unit_label": "%"},
    {"id": "housing_approvals",     "label": "Housing approvals",            "category": "housing",      "unit": "count",   "unit_label": ""},
    {"id": "social_housing",        "label": "Social housing stock",         "category": "housing",      "unit": "count",   "unit_label": ""},
    {"id": "investor_mortgages",    "label": "Investor share of mortgages",  "category": "housing",      "unit": "%",       "unit_label": "%"},
    # DEMOGRAPHICS
    {"id": "population",            "label": "Total population",             "category": "demographics", "unit": "count",   "unit_label": ""},
    {"id": "population_growth",     "label": "Population growth rate",       "category": "demographics", "unit": "%",       "unit_label": "%"},
    {"id": "net_migration",         "label": "Net overseas migration",       "category": "demographics", "unit": "count",   "unit_label": ""},
    {"id": "birth_rate",            "label": "Birth rate (per 1000)",        "category": "demographics", "unit": "per_1000","unit_label": ""},
    {"id": "median_age",            "label": "Median age",                   "category": "demographics", "unit": "years",   "unit_label": " yrs"},
    {"id": "dependency_ratio",      "label": "Dependency ratio",             "category": "demographics", "unit": "%",       "unit_label": "%"},
    {"id": "urbanisation_rate",     "label": "Urbanisation rate",            "category": "demographics", "unit": "%",       "unit_label": "%"},
    # WELLBEING
    {"id": "unemployment",          "label": "Unemployment rate",            "category": "wellbeing",    "unit": "%",       "unit_label": "%"},
    {"id": "life_expectancy",       "label": "Life expectancy",              "category": "wellbeing",    "unit": "years",   "unit_label": " yrs"},
    {"id": "suicide_rate",          "label": "Suicide rate (per 100k)",      "category": "wellbeing",    "unit": "per_100k","unit_label": ""},
    {"id": "homelessness",          "label": "Homelessness (per 100k)",      "category": "wellbeing",    "unit": "per_100k","unit_label": ""},
    {"id": "antidepressants",       "label": "Antidepressant prescriptions", "category": "wellbeing",    "unit": "per_100k","unit_label": ""},
    {"id": "food_bank_usage",       "label": "Food bank usage",              "category": "wellbeing",    "unit": "count",   "unit_label": ""},
    {"id": "prison_population",     "label": "Prison population (per 100k)", "category": "wellbeing",    "unit": "per_100k","unit_label": ""},
    {"id": "gini_coefficient",      "label": "Gini coefficient",             "category": "wellbeing",    "unit": "index",   "unit_label": ""},
    # GOVERNMENT
    {"id": "net_govt_debt",         "label": "Net government debt % GDP",    "category": "government",   "unit": "%",       "unit_label": "%"},
    {"id": "govt_spending",         "label": "Government spending % GDP",    "category": "government",   "unit": "%",       "unit_label": "%"},
    {"id": "tax_revenue",           "label": "Tax revenue % GDP",            "category": "government",   "unit": "%",       "unit_label": "%"},
    {"id": "public_servants",       "label": "Number of public servants",    "category": "government",   "unit": "count",   "unit_label": ""},
    {"id": "welfare_spending",      "label": "Welfare spending % GDP",       "category": "government",   "unit": "%",       "unit_label": "%"},
    {"id": "infrastructure_spend",  "label": "Infrastructure spending",      "category": "government",   "unit": "AUD_bn",  "unit_label": "$bn"},
    # ENVIRONMENT
    {"id": "co2_emissions",         "label": "CO₂ emissions (Mt)",           "category": "environment",  "unit": "Mt",      "unit_label": " Mt"},
    {"id": "renewable_energy",      "label": "Renewable energy %",           "category": "environment",  "unit": "%",       "unit_label": "%"},
    {"id": "temp_anomaly",          "label": "Avg temperature anomaly",      "category": "environment",  "unit": "°C",      "unit_label": "°C"},
    {"id": "drought_index",         "label": "Drought index",                "category": "environment",  "unit": "index",   "unit_label": ""},
]
