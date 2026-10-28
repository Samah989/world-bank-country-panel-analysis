"""
Thin client for the World Bank Indicators API (api.worldbank.org/v2).

The WB API is free, no key needed, and covers ~1,600 indicators × 217+
countries+aggregates × 1960-present. Response shape has one quirk: every
response is a 2-element JSON array where element 0 is pagination metadata
and element 1 is the actual data rows. We hide that here.

Docs:
- Basic call structure: https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-basic-api-call-structure
- Indicator search: https://data.worldbank.org/indicator
- Country classifications: https://api.worldbank.org/v2/country?format=json

Example
-------
    from src.wb_client import fetch_indicator

    gdp = fetch_indicator("NY.GDP.PCAP.KD", countries="all", start=1990, end=2023)
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Iterable
from urllib.parse import urlencode

import pandas as pd
import requests

log = logging.getLogger(__name__)

BASE = "https://api.worldbank.org/v2"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(exist_ok=True)

TIMEOUT = 60
RETRIES = 5
BACKOFF = 2


def _cache_path(indicator: str, countries: str, start: int, end: int) -> Path:
    key = json.dumps({"i": indicator, "c": countries, "s": start, "e": end}, sort_keys=True)
    digest = hashlib.md5(key.encode()).hexdigest()[:10]
    countries_slug = countries[:40].replace(";", "_")
    return DATA_DIR / f"{indicator}__{countries_slug}__{start}-{end}__{digest}.parquet"


def _get_json(url: str) -> list:
    """GET with retry. WB returns a 2-element list: [meta, rows]."""
    for attempt in range(1, RETRIES + 1):
        try:
            r = requests.get(url, timeout=TIMEOUT)
            r.raise_for_status()
            payload = r.json()
            if not isinstance(payload, list) or len(payload) < 2:
                # WB returns {"message": [...]} on error, not the usual list shape.
                raise ValueError(f"Unexpected response shape: {str(payload)[:200]}")
            return payload
        except (requests.HTTPError, requests.ConnectionError, requests.Timeout, ValueError) as e:
            if attempt == RETRIES:
                raise
            sleep_for = BACKOFF * (2 ** (attempt - 1))
            log.warning("API error %s (attempt %d/%d); sleeping %ds", e, attempt, RETRIES, sleep_for)
            time.sleep(sleep_for)
    raise RuntimeError("unreachable")


def fetch_indicator(
    indicator: str,
    countries: str = "all",
    start: int = 1960,
    end: int = 2024,
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Pull one indicator across countries and years.

    Parameters
    ----------
    indicator : str
        WB indicator code, e.g. "NY.GDP.PCAP.KD" (GDP per capita, constant $).
    countries : str
        "all" or a semicolon-joined list of ISO3 codes (e.g. "USA;GBR;FRA").
    start, end : int
        Year range (inclusive).
    use_cache : bool
        Reuse a cached parquet if present.

    Returns
    -------
    pd.DataFrame with columns: country_id, country, indicator_id, indicator,
    year, value, unit, obs_status.
    """
    cache = _cache_path(indicator, countries, start, end)
    if use_cache and cache.exists():
        log.info("Cache hit: %s", cache.name)
        return pd.read_parquet(cache)

    params = {
        "format": "json",
        "date": f"{start}:{end}",
        "per_page": 20000,  # WB max per page
        "page": 1,
    }
    rows: list[dict] = []
    while True:
        url = f"{BASE}/country/{countries}/indicator/{indicator}?{urlencode(params)}"
        log.info("Fetching page %d: %s", params["page"], url)
        meta, page_rows = _get_json(url)
        rows.extend(page_rows or [])
        total_pages = meta.get("pages", 1)
        if params["page"] >= total_pages:
            break
        params["page"] += 1

    df = pd.DataFrame([
        {
            "country_id": r["country"]["id"],
            "country": r["country"]["value"],
            "iso3": r.get("countryiso3code"),
            "indicator_id": r["indicator"]["id"],
            "indicator": r["indicator"]["value"],
            "year": int(r["date"]),
            "value": r["value"],
            "unit": r.get("unit"),
            "obs_status": r.get("obs_status"),
        }
        for r in rows
    ])
    if not df.empty:
        df.to_parquet(cache, index=False)
        log.info("Cached %d rows → %s", len(df), cache.name)
    return df


def fetch_indicators(
    indicators: Iterable[str],
    countries: str = "all",
    start: int = 1960,
    end: int = 2024,
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Pull multiple indicators and pivot into a country-year wide table.

    Returns a DataFrame with columns: iso3, country, year, <indicator_id_1>, ...
    """
    frames = []
    for ind in indicators:
        df = fetch_indicator(ind, countries=countries, start=start, end=end, use_cache=use_cache)
        if df.empty:
            continue
        keep = df[["iso3", "country", "year", "indicator_id", "value"]].copy()
        wide = keep.pivot_table(
            index=["iso3", "country", "year"],
            columns="indicator_id",
            values="value",
            aggfunc="first",
        )
        frames.append(wide)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, axis=1).reset_index()
    # Drop pure-aggregate rows (region/income aggregates have iso3 like "WLD",
    # "EAS" etc.). Callers who want them can pass keep_aggregates=True later.
    return out


def fetch_country_metadata(use_cache: bool = True) -> pd.DataFrame:
    """Country list with region + income classification (needed to filter aggregates)."""
    cache = DATA_DIR / "country_metadata.parquet"
    if use_cache and cache.exists():
        return pd.read_parquet(cache)

    rows = []
    page = 1
    while True:
        url = f"{BASE}/country?format=json&per_page=500&page={page}"
        meta, chunk = _get_json(url)
        rows.extend(chunk or [])
        if page >= meta.get("pages", 1):
            break
        page += 1

    df = pd.DataFrame([
        {
            "iso3": r["id"],
            "iso2": r.get("iso2Code"),
            "name": r.get("name"),
            "region_id": r["region"]["id"] if r.get("region") else None,
            "region": r["region"]["value"] if r.get("region") else None,
            "income_id": r["incomeLevel"]["id"] if r.get("incomeLevel") else None,
            "income": r["incomeLevel"]["value"] if r.get("incomeLevel") else None,
            "capital": r.get("capitalCity"),
            "lat": r.get("latitude"),
            "lon": r.get("longitude"),
        }
        for r in rows
    ])
    df["is_aggregate"] = df["region_id"] == "NA"  # WB marks aggregates as region 'NA'
    df.to_parquet(cache, index=False)
    return df


# ---------------------------------------------------------------------------
# Curated indicator bundles for the three RQs. Kept in one place so the OSG
# job and the notebooks agree.
# ---------------------------------------------------------------------------

RQ1_INDICATORS = {  # Trade / capital / education -> GDP per capita
    # Note: RL.EST, CC.EST, GE.EST (World Governance Indicators) were dropped  - 
    # the WB v2 API returns "indicator not found" for them from the default
    # database. Substitute controls: trade openness, capital formation,
    # education, population.
    "NY.GDP.PCAP.KD":     "GDP per capita, constant 2015 US$",
    "NY.GDP.PCAP.KD.ZG":  "GDP per capita growth (annual %)",
    "SP.POP.TOTL":        "Population, total",
    "NE.TRD.GNFS.ZS":     "Trade (% of GDP)",
    "NE.GDI.TOTL.ZS":     "Gross capital formation (% of GDP)",
    "SE.SEC.CUAT.LO.ZS":  "Educational attainment, at least lower secondary (%)",
}

RQ2_INDICATORS = {  # Health spending -> life expectancy (gender)
    "SH.XPD.CHEX.GD.ZS":  "Current health expenditure (% of GDP)",
    "SH.XPD.CHEX.PC.CD":  "Current health expenditure per capita (US$)",
    "SP.DYN.LE00.IN":     "Life expectancy at birth, total (years)",
    "SP.DYN.LE00.FE.IN":  "Life expectancy at birth, female (years)",
    "SP.DYN.LE00.MA.IN":  "Life expectancy at birth, male (years)",
    "SP.DYN.IMRT.IN":     "Infant mortality rate (per 1,000 live births)",
    "NY.GDP.PCAP.KD":     "GDP per capita, constant 2015 US$",
    "SP.POP.TOTL":        "Population, total",
    "SH.MED.PHYS.ZS":     "Physicians per 1,000 people",
}

RQ3_INDICATORS = {  # Environmental Kuznets Curve
    "EN.GHG.CO2.PC.CE.AR5": "CO2 emissions per capita (t)",
    "NY.GDP.PCAP.KD":       "GDP per capita, constant 2015 US$",
    "NE.TRD.GNFS.ZS":       "Trade (% of GDP)",
    "EG.USE.PCAP.KG.OE":    "Energy use per capita (kg oil eq.)",
    "SP.URB.TOTL.IN.ZS":    "Urban population (% of total)",
    "SP.POP.TOTL":          "Population, total",
    "NV.IND.MANF.ZS":       "Manufacturing, value added (% of GDP)",
}
