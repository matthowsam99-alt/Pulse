"""
RBA Fetcher — Reserve Bank of Australia statistical tables
All data is publicly available at stable URLs as Excel/CSV files.
Tables fetched: A2 (cash rate), D1 (credit), D3 (money), E2 (debt ratios), G5 (trade/gold)
"""

import requests
import pandas as pd
import numpy as np
import io
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.schema import Indicator, DataPoint, save_indicator

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# RBA base URL for statistical tables
RBA_BASE = "https://www.rba.gov.au/statistics/tables"

RBA_TABLES = {
    "A2":  f"{RBA_BASE}/xls/a02hist.xlsx",   # Cash rate
    "D1":  f"{RBA_BASE}/xls/d01hist.xlsx",   # Credit aggregates
    "D3":  f"{RBA_BASE}/xls/d03hist.xlsx",   # Money supply (M1, M2, M3)
    "E2":  f"{RBA_BASE}/xls/e02hist.xlsx",   # Household debt ratios
    "G5":  f"{RBA_BASE}/xls/g05hist.xlsx",   # Exchange rates / commodity prices
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (AusPulse Data Pipeline; research project)"
}


def fetch_rba_table(table_id: str) -> pd.DataFrame:
    """Download and parse an RBA Excel statistical table."""
    url = RBA_TABLES[table_id]
    print(f"  Fetching RBA {table_id} from {url}...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        # RBA tables have metadata rows at top; data starts after the header row
        df = pd.read_excel(io.BytesIO(r.content), sheet_name=0, header=None)
        return df
    except Exception as e:
        print(f"  ✗ Failed to fetch RBA {table_id}: {e}")
        return None


def find_data_start(df: pd.DataFrame) -> int:
    """Find the row where actual date data begins in an RBA table."""
    for i, row in df.iterrows():
        val = str(row.iloc[0]).strip()
        # RBA dates are like 'Jan 1990' or '1990-01-01'
        if len(val) >= 4 and (val[:3].isalpha() or val[:4].isdigit()):
            try:
                pd.to_datetime(val)
                return i
            except:
                continue
    return 10  # fallback


def parse_date(val) -> str:
    """Normalise RBA date formats to YYYY-MM."""
    try:
        dt = pd.to_datetime(str(val))
        return dt.strftime("%Y-%m")
    except:
        return None


def clean_series(df: pd.DataFrame, date_col: int, value_col: int,
                 start_row: int, label: str) -> list:
    """Extract a clean series of DataPoint dicts from a raw RBA dataframe."""
    points = []
    for i in range(start_row, len(df)):
        try:
            date_str = parse_date(df.iloc[i, date_col])
            if not date_str:
                continue
            val = df.iloc[i, value_col]
            if pd.isna(val) or val == "" or str(val).strip() == "":
                continue
            val = float(val)
            if np.isnan(val):
                continue
            points.append({"date": date_str, "value": round(val, 4), "projected": False})
        except Exception:
            continue
    print(f"    → {label}: {len(points)} points ({points[0]['date'] if points else 'n/a'} – {points[-1]['date'] if points else 'n/a'})")
    return points


# ── Individual indicator fetchers ─────────────────────────────────────────────

def fetch_cash_rate():
    """RBA Table A2 — Official Cash Rate target, monthly."""
    df = fetch_rba_table("A2")
    if df is None:
        return None

    start = find_data_start(df)

    # Find cash rate column — look for header containing 'cash' or 'Cash'
    header_row = start - 1
    target_col = None
    for col in range(1, min(10, len(df.columns))):
        cell = str(df.iloc[header_row, col]).lower() if header_row >= 0 else ""
        if "cash" in cell or "ocr" in cell.lower():
            target_col = col
            break
    if target_col is None:
        target_col = 1  # fallback to first data column

    series = clean_series(df, 0, target_col, start, "Cash rate")
    if not series:
        return None

    return Indicator(
        id="cash_rate",
        label="Cash rate",
        category="economy",
        unit="%",
        unit_label="%",
        frequency="monthly",
        source="RBA Table A2",
        source_url=RBA_TABLES["A2"],
        description="The RBA's official cash rate target — the key interest rate in the Australian economy.",
        first_year=1990,
        last_updated=series[-1]["date"],
        series=series,
        notes="Prior to 1990 the cash rate was not formally targeted. Series begins January 1990."
    )


def fetch_m2_money_supply():
    """RBA Table D3 — Money supply aggregates, monthly."""
    df = fetch_rba_table("D3")
    if df is None:
        return None

    start = find_data_start(df)

    # Find M2 or M3 column
    target_col = None
    for row_i in range(0, min(start, 15)):
        for col in range(1, len(df.columns)):
            cell = str(df.iloc[row_i, col]).strip()
            if cell == "M2" or cell == "M3":
                target_col = col
                break
        if target_col:
            break
    if target_col is None:
        target_col = 3  # fallback

    series = clean_series(df, 0, target_col, start, "M2 money supply")
    if not series:
        return None

    return Indicator(
        id="m2_money_supply",
        label="M2 money supply",
        category="economy",
        unit="AUD_bn",
        unit_label="$bn",
        frequency="monthly",
        source="RBA Table D3",
        source_url=RBA_TABLES["D3"],
        description="Broad money supply (M2/M3) — total money in the Australian economy including deposits.",
        first_year=1977,
        last_updated=series[-1]["date"],
        series=series,
        notes="Values in $millions. Converted to $billions in output."
    )


def fetch_household_debt():
    """RBA Table E2 — Household debt to income ratios, quarterly."""
    df = fetch_rba_table("E2")
    if df is None:
        return None

    start = find_data_start(df)

    # E2 typically has total household debt ratio in first or second data column
    target_col = 1

    series = clean_series(df, 0, target_col, start, "Household debt ratio")
    if not series:
        return None

    return Indicator(
        id="household_debt_ratio",
        label="Household debt to income",
        category="economy",
        unit="%",
        unit_label="%",
        frequency="quarterly",
        source="RBA Table E2",
        source_url=RBA_TABLES["E2"],
        description="Total household debt as a percentage of annual household disposable income.",
        first_year=1977,
        last_updated=series[-1]["date"],
        series=series,
        notes="Australia has one of the highest household debt ratios in the world."
    )


def fetch_private_credit():
    """RBA Table D1 — Private sector credit growth, monthly."""
    df = fetch_rba_table("D1")
    if df is None:
        return None

    start = find_data_start(df)

    # D1 — look for total credit column (usually last main column)
    target_col = None
    for row_i in range(0, min(start, 15)):
        for col in range(1, len(df.columns)):
            cell = str(df.iloc[row_i, col]).lower()
            if "total" in cell or "all" in cell:
                target_col = col
                break
        if target_col:
            break
    if target_col is None:
        target_col = 4

    series = clean_series(df, 0, target_col, start, "Private credit")
    if not series:
        return None

    return Indicator(
        id="private_credit_growth",
        label="Private credit growth",
        category="economy",
        unit="%",
        unit_label="%",
        frequency="monthly",
        source="RBA Table D1",
        source_url=RBA_TABLES["D1"],
        description="Annual growth rate of total private sector credit (housing, personal, business).",
        first_year=1977,
        last_updated=series[-1]["date"],
        series=series,
    )


def fetch_gold_price():
    """RBA Table G5 — Commodity prices including gold in AUD, monthly."""
    df = fetch_rba_table("G5")
    if df is None:
        return None

    start = find_data_start(df)

    # Find gold column
    target_col = None
    for row_i in range(0, min(start, 15)):
        for col in range(1, len(df.columns)):
            cell = str(df.iloc[row_i, col]).lower()
            if "gold" in cell:
                target_col = col
                break
        if target_col:
            break
    if target_col is None:
        target_col = 1

    series = clean_series(df, 0, target_col, start, "Gold price AUD")
    if not series:
        return None

    return Indicator(
        id="gold_aud",
        label="Gold spot price (AUD)",
        category="economy",
        unit="AUD",
        unit_label="$",
        frequency="monthly",
        source="RBA Table G5",
        source_url=RBA_TABLES["G5"],
        description="Gold spot price in Australian dollars per troy ounce.",
        first_year=1969,
        last_updated=series[-1]["date"],
        series=series,
    )


def fetch_terms_of_trade():
    """RBA Table G5 — Terms of trade index, quarterly."""
    df = fetch_rba_table("G5")
    if df is None:
        return None

    start = find_data_start(df)

    # Find terms of trade column
    target_col = None
    for row_i in range(0, min(start, 15)):
        for col in range(1, len(df.columns)):
            cell = str(df.iloc[row_i, col]).lower()
            if "terms" in cell or "trade" in cell:
                target_col = col
                break
        if target_col:
            break
    if target_col is None:
        target_col = 2

    series = clean_series(df, 0, target_col, start, "Terms of trade")
    if not series:
        return None

    return Indicator(
        id="terms_of_trade",
        label="Terms of trade",
        category="economy",
        unit="index",
        unit_label="",
        frequency="quarterly",
        source="RBA Table G5",
        source_url=RBA_TABLES["G5"],
        description="Ratio of export prices to import prices — how much imports Australia can buy with its exports.",
        first_year=1970,
        last_updated=series[-1]["date"],
        series=series,
        notes="Captures the mining boom/bust cycle and China trade relationship clearly."
    )


# ── Run all RBA fetchers ──────────────────────────────────────────────────────

def run_all():
    print("\n🏦 Fetching RBA data...\n")
    fetchers = [
        fetch_cash_rate,
        fetch_m2_money_supply,
        fetch_household_debt,
        fetch_private_credit,
        fetch_gold_price,
        fetch_terms_of_trade,
    ]
    results = []
    for fn in fetchers:
        try:
            indicator = fn()
            if indicator and indicator.series:
                save_indicator(indicator, OUTPUT_DIR)
                results.append(indicator.id)
            else:
                print(f"  ✗ {fn.__name__} returned no data")
        except Exception as e:
            print(f"  ✗ {fn.__name__} failed: {e}")
    print(f"\n✅ RBA complete — {len(results)}/{len(fetchers)} indicators saved")
    return results


if __name__ == "__main__":
    run_all()
