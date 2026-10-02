"""Tests du module d'estimation sur un panel SYNTHÉTIQUE.

Ces données n'existent que pour vérifier que le code retrouve un effet connu. Elles ne sont jamais
écrites dans data/, figures/ ou tables/, et aucun chiffre du papier n'en provient.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import did  # noqa: E402

TRUE_ATT = -0.05


def make_panel(n_units=400, t0=2004, t1=2019, seed=0, effect=TRUE_ATT, dynamic=False):
    rng = np.random.default_rng(seed)
    units = np.arange(n_units)
    cohorts = rng.choice([0, 2010, 2012, 2014, 2016], size=n_units, p=[0.3, 0.15, 0.25, 0.2, 0.1])
    alpha_u = rng.normal(0, 0.3, n_units)
    rows = []
    for t in range(t0, t1 + 1):
        gamma_t = 0.02 * (t - t0) + rng.normal(0, 0.02)
        for u in units:
            g = cohorts[u]
            rel = t - g if g > 0 else None
            tau = 0.0
            if rel is not None and rel >= 0:
                tau = effect * (1 + 0.1 * min(rel, 5)) if dynamic else effect
            y = 1.0 + alpha_u[u] + gamma_t + tau + rng.normal(0, 0.05)
            rows.append((u, t, g, y))
    df = pd.DataFrame(rows, columns=["unit", "year", "cohort", "y"])
    df["treat"] = ((df.cohort > 0) & (df.year >= df.cohort)).astype(int)
    return df


@pytest.fixture(scope="module")
def panel():
    return make_panel()


def test_add_cohort_matches_dgp(panel):
    d = did.add_cohort(panel.drop(columns="cohort"), "unit", "year", "treat")
    assert (d["cohort"] == panel["cohort"]).all()


def test_drop_always_treated(panel):
    d = did.drop_always_treated(panel, "year", min_pre=3)
    assert d["cohort"].isin([0, 2010, 2012, 2014, 2016]).all()
    d2 = did.drop_always_treated(panel.assign(cohort=panel.cohort.replace(2010, 2005)), "year", min_pre=3)
    assert 2005 not in d2["cohort"].unique()


def test_twfe_recovers_homogeneous_effect(panel):
    t = did.twfe_att(panel, "y", "unit", "year")
    assert abs(t["estimate"].iloc[0] - TRUE_ATT) < 0.01
    ev = did.twfe_event_study(panel, "y", "unit", "year")
    pre = ev[ev.term < -1]
    post = ev[(ev.term >= 1) & (ev.term <= 5)]
    assert pre["estimate"].abs().max() < 0.02
    assert abs(post["estimate"].mean() - TRUE_ATT) < 0.01


def test_cs_recovers_effect(panel):
    res = did.cs_event_study(panel, "y", "unit", "year", control="not_yet_treated")
    post = res["post_avg"]["estimate"].iloc[0]
    assert abs(post - TRUE_ATT) < 0.015, post
    ev = res["event"]
    assert ev[ev.term < -1]["estimate"].abs().max() < 0.03
    assert set(ev.columns) >= {"term", "estimate", "se", "ci_low", "ci_high", "estimator"}


def test_did2s_and_sunab_run(panel):
    d2 = did.did2s_event_study(panel, "y", "unit", "year")
    assert abs(d2[(d2.term >= 1) & (d2.term <= 5)]["estimate"].mean() - TRUE_ATT) < 0.015
    sa = did.sunab_event_study(panel, "y", "unit", "year")
    assert abs(sa[(sa.term >= 1) & (sa.term <= 5)]["estimate"].mean() - TRUE_ATT) < 0.02


def test_poisson_counts():
    rng = np.random.default_rng(3)
    p = make_panel(n_units=200, effect=-0.08)
    p["women"] = rng.integers(200, 2000, len(p))
    p["births"] = rng.poisson(np.exp(p["y"] - 1.0 + np.log(p["women"]) - 3.0))
    t = did.twfe_att(p, "births", "unit", "year", poisson=True, exposure="women")
    assert abs(t["estimate"].iloc[0] + 0.08) < 0.03


def test_mde_permutation_is_positive(panel):
    m = did.mde_permutation(panel, "y", "unit", "year", n_perm=15, seed=2)
    assert m["n_perm_ok"] >= 10 and m["mde"] > 0 and abs(m["placebo_mean"]) < 0.02


def test_meta_random_effects():
    r = did.meta_random_effects([-0.05, -0.04, -0.06], [0.0001, 0.0002, 0.00015], ["A", "B", "C"])
    assert -0.06 < r["estimate"] < -0.04 and r["ci_low"] < r["estimate"] < r["ci_upp"]
