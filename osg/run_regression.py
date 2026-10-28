"""
Run one WB RQ regression at scale on OSPool. Reads pre-pulled parquet from
./data (from pull_data.submit), fits the model, bootstraps SEs at the
country level.

CLI:
    python run_regression.py --rq 1|2|3 --bootstrap N --out results/
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from src.wb_client import (
    fetch_indicators, fetch_country_metadata,
    RQ1_INDICATORS, RQ2_INDICATORS, RQ3_INDICATORS,
)
from src.regression import fixed_effects_panel


def build(rq: int):
    meta = fetch_country_metadata()
    real = set(meta.loc[~meta["is_aggregate"], "iso3"])

    if rq == 1:
        panel = fetch_indicators(list(RQ1_INDICATORS), "all", 1996, 2023)
        panel = panel[panel["iso3"].isin(real)].copy()
        panel["log_gdp_pc"] = np.log(panel["NY.GDP.PCAP.KD"].replace(0, np.nan))
        panel["log_pop"]    = np.log(panel["SP.POP.TOTL"].replace(0, np.nan))
        panel = panel.rename(columns={
            "NE.TRD.GNFS.ZS":    "trade_share",
            "NE.GDI.TOTL.ZS":    "invest_share",
            "SE.SEC.CUAT.LO.ZS": "sec_educ_share",
        })
        return panel, "log_gdp_pc", ["trade_share", "invest_share",
                                     "sec_educ_share", "log_pop"]

    if rq == 2:
        panel = fetch_indicators(list(RQ2_INDICATORS), "all", 2000, 2022)
        panel = panel[panel["iso3"].isin(real)].copy()
        panel["log_health_pc"] = np.log(panel["SH.XPD.CHEX.PC.CD"].replace(0, np.nan))
        panel["log_gdp_pc"]    = np.log(panel["NY.GDP.PCAP.KD"].replace(0, np.nan))
        panel["log_pop"]       = np.log(panel["SP.POP.TOTL"].replace(0, np.nan))
        panel = panel.rename(columns={
            "SP.DYN.LE00.IN": "le_total", "SH.MED.PHYS.ZS": "physicians_per_1k",
        })
        return panel, "le_total", ["log_health_pc", "log_gdp_pc", "physicians_per_1k", "log_pop"]

    if rq == 3:
        panel = fetch_indicators(list(RQ3_INDICATORS), "all", 1990, 2022)
        panel = panel[panel["iso3"].isin(real)].copy()
        panel["log_co2_pc"]    = np.log(panel["EN.GHG.CO2.PC.CE.AR5"].replace(0, np.nan))
        panel["log_gdp_pc"]    = np.log(panel["NY.GDP.PCAP.KD"].replace(0, np.nan))
        panel["log_gdp_pc_sq"] = panel["log_gdp_pc"] ** 2
        panel["log_pop"]       = np.log(panel["SP.POP.TOTL"].replace(0, np.nan))
        panel = panel.rename(columns={
            "SP.URB.TOTL.IN.ZS": "urban_share", "NV.IND.MANF.ZS": "manufacturing_share",
        })
        return panel, "log_co2_pc", ["log_gdp_pc", "log_gdp_pc_sq", "log_pop",
                                     "urban_share", "manufacturing_share"]

    raise SystemExit(f"unknown RQ: {rq}")


def bootstrap(panel, dep, regs, n_boot, entity="iso3"):
    countries = panel[entity].unique()
    rng = np.random.default_rng(0)
    coefs = []
    for _ in range(n_boot):
        draw = rng.choice(countries, size=len(countries), replace=True)
        sub = panel[panel[entity].isin(draw)]
        try:
            r = fixed_effects_panel(sub, dep, regs,
                                    entity_effects=True, time_effects=True, name="boot")
            coefs.append(r.coef_table["coef"])
        except Exception:
            continue
    return pd.DataFrame(coefs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rq", type=int, required=True, choices=[1, 2, 3])
    ap.add_argument("--bootstrap", type=int, default=0)
    ap.add_argument("--out", type=Path, default=Path("results"))
    args = ap.parse_args()
    args.out.mkdir(exist_ok=True)

    panel, dep, regs = build(args.rq)
    main_res = fixed_effects_panel(panel, dep, regs,
                                   entity_effects=True, time_effects=True, name=f"RQ{args.rq}")
    main_res.coef_table.to_csv(args.out / f"rq{args.rq}_main.csv")
    print(main_res.as_markdown())

    if args.bootstrap > 0:
        boots = bootstrap(panel, dep, regs, args.bootstrap)
        summary = pd.DataFrame({
            "boot_mean": boots.mean(),
            "boot_sd":   boots.std(),
            "boot_p025": boots.quantile(0.025),
            "boot_p975": boots.quantile(0.975),
        })
        summary.to_csv(args.out / f"rq{args.rq}_bootstrap.csv")
        print(summary)


if __name__ == "__main__":
    main()
