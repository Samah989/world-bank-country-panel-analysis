"""
Panel-regression helpers for country-year data. Same shape as the IPEDS
project's helper: two-way fixed effects, cluster-robust SEs at the country
level.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS


@dataclass
class RegressionResult:
    name: str
    n_obs: int
    n_entities: int
    r2_within: float
    coef_table: pd.DataFrame

    def as_markdown(self) -> str:
        return (
            f"### {self.name}\n\n"
            f"- Observations: {self.n_obs:,}\n"
            f"- Countries: {self.n_entities:,}\n"
            f"- Within R²: {self.r2_within:.3f}\n\n"
            + self.coef_table.round(4).to_markdown()
        )


def _to_panel(df: pd.DataFrame, entity: str = "iso3", time: str = "year") -> pd.DataFrame:
    df = df.copy()
    df[time] = pd.to_numeric(df[time], errors="coerce").astype("Int64")
    df = df.dropna(subset=[entity, time])
    return df.set_index([entity, time])


def fixed_effects_panel(
    df: pd.DataFrame,
    dependent: str,
    regressors: Iterable[str],
    entity_effects: bool = True,
    time_effects: bool = True,
    cluster_entity: bool = True,
    name: str = "panel",
) -> RegressionResult:
    """Two-way fixed-effects panel OLS, cluster-robust SEs at the country level."""
    panel_df = _to_panel(df)
    regressors = list(regressors)
    both = pd.concat([panel_df[dependent], panel_df[regressors]], axis=1).dropna()
    y = both[dependent]
    X = both[regressors]

    model = PanelOLS(y, X, entity_effects=entity_effects, time_effects=time_effects, drop_absorbed=True)
    res = model.fit(cov_type="clustered", cluster_entity=cluster_entity)

    ci = res.conf_int()
    table = pd.DataFrame({
        "coef": res.params,
        "stderr": res.std_errors,
        "tstat": res.tstats,
        "pvalue": res.pvalues,
        "ci_low": ci["lower"],
        "ci_high": ci["upper"],
    })
    return RegressionResult(
        name=name,
        n_obs=int(res.nobs),
        n_entities=int(res.entity_info.total),
        r2_within=float(res.rsquared_within),
        coef_table=table,
    )


def barro_growth_regression(
    df: pd.DataFrame,
    growth: str,
    initial_income: str,
    other_regressors: Iterable[str],
    period_length: int = 5,
    time_col: str = "year",
    entity_col: str = "iso3",
    name: str = "growth",
) -> RegressionResult:
    """
    Barro-style growth regression on non-overlapping period averages.

    - Averages regressors within `period_length` years
    - Uses period-start income for `initial_income` (log)
    - Country and period fixed effects
    """
    df = df.copy()
    df["period"] = (df[time_col] // period_length) * period_length
    # Aggregate: mean of regressors, first-value of initial_income
    agg = {c: "mean" for c in [growth, *other_regressors]}
    agg[initial_income] = "first"
    period_df = df.groupby([entity_col, "period"]).agg(agg).reset_index()
    period_df["log_initial_income"] = np.log(period_df[initial_income].replace(0, np.nan))

    regs = ["log_initial_income", *other_regressors]
    return fixed_effects_panel(
        period_df.rename(columns={"period": "year"}),
        dependent=growth,
        regressors=regs,
        entity_effects=True,
        time_effects=True,
        name=name,
    )
