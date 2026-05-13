"""
ABS Fetcher — Australian Bureau of Statistics Data API
Base URL: https://data.api.abs.gov.au/rest/data/
All dataflow IDs and keys discovered from live API 2026-05.
"""

import requests
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from pipeline.schema import Indicator, save_indicator

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed")
os.makedirs(OUTPUT_DIR, exist_ok=True)

ABS_API = "https://data.api.abs.gov.au/rest/data"
HEADERS = {"Accept": "application/vnd.sdmx.data+csv;version=1.0"}

def fetch_abs(dataflow, key, start="1970", filters=None):
    url = f"{ABS_API}/{dataflow}/{key}"
    params = {"startPeriod": start, "detail": "dataonly"}
    print(f"  Fetching {dataflow}/{key}...")
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        r.raise_for_status()
        from io import StringIO
        df = pd.read_csv(StringIO(r.text))
        if filters:
            for col, val in filters.items():
                if col in df.columns:
                    df = df[df[col].astype(str) == str(val)]
        print(f"    → {len(df)} rows")
        return df
    except requests.exceptions.HTTPError as e:
        print(f"    ✗ HTTP {e.response.status_code}")
        return pd.DataFrame()
    except Exception as e:
        print(f"    ✗ {e}")
        return pd.DataFrame()

def to_series(df, time_col="TIME_PERIOD", val_col="OBS_VALUE"):
    if df.empty or time_col not in df.columns or val_col not in df.columns:
        return []
    series = []
    for _, row in df.iterrows():
        try:
            date = str(row[time_col])
            if "-Q" in date:
                yr, q = date.split("-Q")
                date = f"{yr}-{int(q)*3:02d}"
            elif "-S" in date:
                yr, s = date.split("-S")
                date = f"{yr}-{int(s)*6:02d}"
            val = float(row[val_col])
            if pd.isna(val): continue
            series.append({"date": date, "value": round(val, 4), "projected": False})
        except Exception:
            continue
    series.sort(key=lambda x: x["date"])
    if series:
        print(f"    → {len(series)} points ({series[0]['date']} – {series[-1]['date']})")
    return series

# ── CPI ───────────────────────────────────────────────────────────────────────
def fetch_cpi():
    # All groups CPI, Australia, quarterly, original
    df = fetch_abs("ABS,CPI", "1.10001.10.50.Q", "1948")
    series = to_series(df)
    if not series: return None
    return Indicator(
        id="cpi", label="CPI", category="economy",
        unit="index", unit_label="", frequency="quarterly",
        source="ABS 6401.0",
        source_url="https://data.api.abs.gov.au/rest/data/ABS,CPI",
        description="Consumer Price Index — All groups, Australia. Base: 2011-12 = 100.",
        first_year=1948, last_updated=series[-1]["date"],
        series=series, projection_start="2026-01",
    )

# ── Unemployment ──────────────────────────────────────────────────────────────
def fetch_unemployment():
    # LF: M13=unemployment rate, SEX=3 persons, AGE=1599 all,
    # TSEST=20 seasonally adjusted, REGION=AUS, FREQ=M
    df = fetch_abs("ABS,LF", "M13.3.1599.20.AUS.M", "1978")
    if df.empty:
        df = fetch_abs("ABS,LF", "M13.3.1599.10.AUS.M", "1978")
    series = to_series(df)
    if not series: return None
    return Indicator(
        id="unemployment", label="Unemployment rate", category="wellbeing",
        unit="%", unit_label="%", frequency="monthly",
        source="ABS 6202.0",
        source_url="https://data.api.abs.gov.au/rest/data/ABS,LF",
        description="Unemployment rate, seasonally adjusted, all persons.",
        first_year=1978, last_updated=series[-1]["date"],
        series=series, projection_start="2026-01",
    )

# ── Population ───────────────────────────────────────────────────────────────
def fetch_population():
    # ERP_COMP_Q: MEASURE=1 (ERP level), REGION=1 (Australia), FREQ=Q
    df = fetch_abs("ABS,ERP_COMP_Q", "all", "1981",
                   filters={"MEASURE": "1", "REGION": "1"})
    if df.empty:
        df = fetch_abs("ABS,ERP_COMP_Q", "1.1.Q", "1981")
    series = to_series(df)
    if not series: return None
    return Indicator(
        id="population", label="Total population", category="demographics",
        unit="count", unit_label="", frequency="quarterly",
        source="ABS 3101.0",
        source_url="https://data.api.abs.gov.au/rest/data/ABS,ERP_COMP_Q",
        description="Estimated Resident Population of Australia.",
        first_year=1981, last_updated=series[-1]["date"],
        series=series, projection_start="2026-01",
    )

# ── Wage Price Index ──────────────────────────────────────────────────────────
def fetch_wage_price_index():
    # WPI: MEASURE=2, INDEX=THRPIB, SECTOR=1, INDUSTRY=TOT,
    # TSEST=10, REGION=AUS, FREQ=Q
    df = fetch_abs("ABS,WPI", "2.THRPIB.1.TOT.10.AUS.Q", "1997")
    if df.empty:
        df = fetch_abs("ABS,WPI", "all", "1997",
                       filters={"REGION": "AUS", "SECTOR": "3",
                                "INDUSTRY": "TOT", "FREQ": "Q"})
    series = to_series(df)
    if not series: return None
    return Indicator(
        id="wage_price_index", label="Wage price index", category="economy",
        unit="index", unit_label="", frequency="quarterly",
        source="ABS 6345.0",
        source_url="https://data.api.abs.gov.au/rest/data/ABS,WPI",
        description="Wage Price Index — measures changes in price of labour.",
        first_year=1997, last_updated=series[-1]["date"],
        series=series, projection_start="2026-01",
    )

# ── Average Weekly Earnings (proxy for median wage) ──────────────────────────
def fetch_median_wage():
    # AWE: MEASURE=1 (AWE), ESTIMATE_TYPE=1 (ordinary time),
    # SEX=3 (persons), SECTOR=7 (all), INDUSTRY=E (all),
    # TSEST=10, REGION=AUS, FREQ=S (semi-annual)
    df = fetch_abs("ABS,AWE", "1.1.3.7.E.10.AUS.S", "1981")
    if df.empty:
        df = fetch_abs("ABS,AWE", "all", "1981",
                       filters={"SEX": "3", "SECTOR": "7",
                                "ESTIMATE_TYPE": "1", "REGION": "AUS"})
    series = to_series(df)
    if not series: return None
    return Indicator(
        id="median_wage", label="Average weekly earnings (real)", category="economy",
        unit="AUD", unit_label="$", frequency="annual",
        source="ABS AWE 6302.0",
        source_url="https://data.api.abs.gov.au/rest/data/ABS,AWE",
        description="Average weekly ordinary time earnings, all persons. Used as proxy for median wage.",
        first_year=1981, last_updated=series[-1]["date"],
        series=series, projection_start="2026-01",
        real_adjusted=False,
        notes="Average weekly earnings (not median). Published semi-annually. Nominal dollars.",
    )

# ── GDP — National Accounts expenditure ──────────────────────────────────────
def fetch_gdp():
    # ANA_EXP row1: ABS:ANA_EXP(1.0.0),FCH,FCE,SSS,10,AUS,Q
    # Columns: MEASURE, DATA_ITEM, SECTOR, TSEST, REGION, FREQ
    # MEASURE=FCH (chain vol index), DATA_ITEM=GDP, SECTOR=SSS, TSEST=20 SA
    df = fetch_abs("ABS,ANA_EXP", "all", "1959",
                   filters={"DATA_ITEM": "GDP", "TSEST": "20",
                            "REGION": "AUS", "FREQ": "Q"})
    if df.empty:
        # Try MEASURE filter instead - FCH = chain volume
        df = fetch_abs("ABS,ANA_EXP", "all", "1959",
                       filters={"MEASURE": "FCH", "DATA_ITEM": "GDP",
                                "REGION": "AUS", "FREQ": "Q"})
    if df.empty:
        # Try current price measure
        df = fetch_abs("ABS,ANA_EXP", "all", "1959",
                       filters={"DATA_ITEM": "GDP", "REGION": "AUS", "FREQ": "Q"})
    series = to_series(df)
    if not series: return None
    return Indicator(
        id="gdp_per_capita", label="GDP (chain volume)", category="economy",
        unit="index", unit_label="", frequency="quarterly",
        source="ABS 5206.0 ANA_EXP",
        source_url="https://data.api.abs.gov.au/rest/data/ABS,ANA_EXP",
        description="Gross Domestic Product chain volume measure, seasonally adjusted, Australia.",
        first_year=1959, last_updated=series[-1]["date"],
        series=series, projection_start="2026-01",
        real_adjusted=True, base_year="2022-23",
        notes="Chain volume GDP index. Not per capita — overlaid with population gives living standards picture.",
    )

# ── House prices ──────────────────────────────────────────────────────────────
def fetch_house_prices():
    # RES_DWELL_ST: MEASURE=2 (mean price), REGION=1 (Australia), FREQ=Q
    df = fetch_abs("ABS,RES_DWELL_ST", "all", "2003",
                   filters={"MEASURE": "2", "REGION": "1"})
    if df.empty:
        df = fetch_abs("ABS,RES_DWELL_ST", "2.1.Q", "2003")
    series = to_series(df)
    if not series: return None
    return Indicator(
        id="median_house_price", label="Mean house price", category="housing",
        unit="AUD", unit_label="$", frequency="quarterly",
        source="ABS Residential Dwellings",
        source_url="https://data.api.abs.gov.au/rest/data/ABS,RES_DWELL_ST",
        description="Mean price of established residential dwellings, Australia.",
        first_year=2003, last_updated=series[-1]["date"],
        series=series, projection_start="2026-01",
    )

# ── Building activity ─────────────────────────────────────────────────────────
def fetch_housing_approvals():
    # BUILDING_ACTIVITY: MEASURE=NUM (number), REGION=1 (Australia),
    # TYPE_BLDG=100 (all residential), TSEST=10, FREQ=Q
    df = fetch_abs("ABS,BUILDING_ACTIVITY", "all", "1983",
                   filters={"MEASURE": "NUM", "REGION": "1",
                            "TYPE_BLDG": "100", "FREQ": "Q"})
    if df.empty:
        # Try with count measure
        df = fetch_abs("ABS,BUILDING_ACTIVITY", "all", "1983",
                       filters={"REGION": "1", "TYPE_BLDG": "110", "FREQ": "Q"})
    series = to_series(df)
    if not series: return None
    return Indicator(
        id="housing_approvals", label="Building activity (dwellings)", category="housing",
        unit="count", unit_label="", frequency="quarterly",
        source="ABS Building Activity",
        source_url="https://data.api.abs.gov.au/rest/data/ABS,BUILDING_ACTIVITY",
        description="Number of residential dwelling commencements, Australia, quarterly.",
        first_year=1983, last_updated=series[-1]["date"],
        series=series, projection_start="2026-01",
    )

# ── Net overseas migration ────────────────────────────────────────────────────
def fetch_net_migration():
    # NOM_CY: MEASURE=3 (net), AGE=TOT, SEX=3 (persons),
    # REGION=1 (Australia), FREQ=A
    df = fetch_abs("ABS,NOM_CY", "all", "1976",
                   filters={"MEASURE": "3", "AGE": "TOT",
                            "SEX": "3", "REGION": "1"})
    if df.empty:
        df = fetch_abs("ABS,NOM_FY", "all", "1976",
                       filters={"MEASURE": "3", "REGION": "1"})
    series = to_series(df)
    if not series: return None
    return Indicator(
        id="net_migration", label="Net overseas migration", category="demographics",
        unit="count", unit_label="", frequency="annual",
        source="ABS NOM",
        source_url="https://data.api.abs.gov.au/rest/data/ABS,NOM_CY",
        description="Net overseas migration — arrivals minus departures of long-term movers.",
        first_year=1976, last_updated=series[-1]["date"],
        series=series, projection_start="2026-01",
    )

# ── Underemployment ───────────────────────────────────────────────────────────
def fetch_underemployment():
    # LF_UNDER: PARM_ITEM=M26 (underemployment rate), SEX=3,
    # AGE=1599, TSEST=20 SA, REGION=AUS, FREQ=M
    df = fetch_abs("ABS,LF_UNDER", "all", "1978",
                   filters={"PARM_ITEM": "M26", "SEX": "3",
                            "AGE": "1599", "TSEST": "20", "REGION": "1"})
    if df.empty:
        df = fetch_abs("ABS,LF_UNDER", "all", "1978",
                       filters={"PARM_ITEM": "M26", "SEX": "3", "AGE": "1599"})
    series = to_series(df)
    if not series: return None
    return Indicator(
        id="underemployment", label="Underemployment rate", category="wellbeing",
        unit="%", unit_label="%", frequency="monthly",
        source="ABS LF_UNDER",
        source_url="https://data.api.abs.gov.au/rest/data/ABS,LF_UNDER",
        description="Underemployment rate — workers employed but wanting more hours.",
        first_year=1978, last_updated=series[-1]["date"],
        series=series, projection_start="2026-01",
    )

# ── Run all ───────────────────────────────────────────────────────────────────
def run_all():
    print("\n📊 Fetching ABS data...\n")
    fetchers = [
        fetch_cpi, fetch_unemployment, fetch_population,
        fetch_wage_price_index, fetch_median_wage, fetch_gdp,
        fetch_house_prices, fetch_housing_approvals,
        fetch_net_migration, fetch_underemployment,
    ]
    results = []
    for fn in fetchers:
        try:
            ind = fn()
            if ind and ind.series:
                save_indicator(ind, OUTPUT_DIR)
                results.append(ind.id)
            else:
                print(f"  ✗ {fn.__name__} returned no data")
        except Exception as e:
            print(f"  ✗ {fn.__name__} failed: {e}")
    print(f"\n✅ ABS complete — {len(results)}/{len(fetchers)} indicators saved")
    return results

if __name__ == "__main__":
    run_all()
