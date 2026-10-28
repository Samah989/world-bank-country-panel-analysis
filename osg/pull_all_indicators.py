"""
Batch pull of every World Bank indicator used by RQ1/RQ2/RQ3, plus the
country classification. Writes parquet files to ./data/.
"""
import sys
import logging

sys.path.insert(0, ".")
from src.wb_client import (
    fetch_indicators, fetch_country_metadata,
    RQ1_INDICATORS, RQ2_INDICATORS, RQ3_INDICATORS,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Union of everything, dedup preserves order.
all_indicators = list(dict.fromkeys([
    *RQ1_INDICATORS.keys(),
    *RQ2_INDICATORS.keys(),
    *RQ3_INDICATORS.keys(),
]))

# One wide pull for each RQ's year window keeps cache filenames deterministic.
fetch_indicators(list(RQ1_INDICATORS), countries="all", start=1996, end=2023)
fetch_indicators(list(RQ2_INDICATORS), countries="all", start=2000, end=2022)
fetch_indicators(list(RQ3_INDICATORS), countries="all", start=1990, end=2022)
fetch_country_metadata()

print(f"Pulled {len(all_indicators)} unique indicators + country metadata.")
