"""Tests du module d'estimation sur un panel SYNTHÉTIQUE.

Ces données n'existent que pour vérifier que le code retrouve un effet connu. Elles ne sont jamais
écrites dans data/, figures/ ou tables/, et aucun chiffre du papier n'en provient.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import did  # noqa: E402

warnings.filterwarnings("ignore")
TRUE_ATT = -0.05


def make_panel(n_units=400, t0=2004, t1=2019, seed=0, effect=TRUE_ATT, dynamic=False, never_share=0.3):
    rng = np.random.default_rng(seed)
    units = np.arange(n_units)
    p_treated = (1 - never_share) / 4
    cohorts = rng.choice([0, 2010, 2012, 2014, 2016], size=n_units, p=[never_share] + [p_treated] * 4)
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
    r = did.twfe_event_study(panel, "y", "unit", "year")
    ev = r["event"]
    assert -1 not in ev.term.tolist()                       # référence −1 omise
    assert ev[ev.term < -1]["estimate"].abs().max() < 0.02
    assert abs(r["post_avg"]["estimate"].iloc[0] - TRUE_ATT) < 0.01
    assert r["post_avg"]["term"].iloc[0] == "ATT[1,5]"
    assert 0 <= r["pre_wald"]["p_value"] <= 1


def test_cs_recovers_effect(panel):
    res = did.cs_event_study(panel, "y", "unit", "year", control="not_yet_treated")
    post = res["post_avg"]["estimate"].iloc[0]
    assert abs(post - TRUE_ATT) < 0.015, post
    ev = res["event"]
    assert -1 not in ev.term.tolist()
    assert ev[ev.term < -1]["estimate"].abs().max() < 0.03
    assert set(ev.columns) >= {"term", "estimate", "se", "ci_low", "ci_high", "estimator", "n_cohorts", "n_units_rel"}
    info = res["info"]
    assert info["n_never"] > 0 and info["as_rcs"] is False and info["k_post"] == 5
    assert 0 <= res["pre_wald_p"] <= 1


def test_cs_se_matches_influence_functions(panel):
    """L'écart-type par fonctions d'influence reproduit celui du paquet (sans grappe) ; l'écart-type de
    ATT[1,5] tient compte de la covariance (différent de la formule sous indépendance)."""
    res = did.cs_event_study(panel, "y", "unit", "year")
    agg = res["model"].aggregate("event")
    pk = agg[("EventAggregation", "analytic", "std_error")]
    pk.index = [int(i) for i in pk.index]
    ev = res["event"].set_index("term")
    assert np.allclose(ev.se.values, pk.reindex(ev.index).values, rtol=1e-6)
    post = ev[(ev.index >= 1) & (ev.index <= 5)]
    indep = np.sqrt((post.se ** 2).sum()) / len(post)
    assert not np.isclose(res["post_avg"]["se"].iloc[0], indep, rtol=0.02)


def test_cs_cluster_changes_se(panel):
    p = panel.copy()
    p["cl"] = p.unit % 10
    r0 = did.cs_event_study(p, "y", "unit", "year")
    r1 = did.cs_event_study(p, "y", "unit", "year", cluster="cl")
    assert r1["info"]["n_clusters"] == 10 and r0["info"]["n_clusters"] == p.unit.nunique()
    assert np.isclose(r0["post_avg"]["estimate"].iloc[0], r1["post_avg"]["estimate"].iloc[0])
    assert not np.isclose(r0["post_avg"]["se"].iloc[0], r1["post_avg"]["se"].iloc[0])


def test_cs_bands_and_no_never_treated():
    p = make_panel(n_units=200, never_share=0.0, seed=4)
    res = did.cs_event_study(p, "y", "unit", "year", boot=49)
    info = res["info"]
    assert info["n_never"] == 0
    assert info["years_model"][1] < info["years"][1]                      # troncature : dernière cohorte = contrôle
    ev = res["event"]
    assert {"cband_low", "cband_high"} <= set(ev.columns)
    assert ((ev.cband_high - ev.cband_low) >= (ev.ci_high - ev.ci_low) - 1e-12).all()


def test_cs_recodes_late_cohorts(panel):
    p = panel.copy()
    p.loc[p.cohort == 2016, "cohort"] = 2025                              # au-delà de la fenêtre
    res = did.cs_event_study(p, "y", "unit", "year")
    assert res["info"]["n_recoded_never_after_window"] == panel[panel.cohort == 2016].unit.nunique()


def test_did2s_and_sunab_run(panel):
    d2 = did.did2s_event_study(panel, "y", "unit", "year")
    assert abs(d2["post_avg"]["estimate"].iloc[0] - TRUE_ATT) < 0.015
    sa = did.sunab_event_study(panel, "y", "unit", "year")
    assert abs(sa["post_avg"]["estimate"].iloc[0] - TRUE_ATT) < 0.02
    assert sa["post_avg"]["se"].iloc[0] > 0 and 0 <= sa["pre_wald"]["p_value"] <= 1
    with pytest.raises(ValueError):
        did.sunab_event_study(make_panel(n_units=100, never_share=0.0), "y", "unit", "year")


def test_extra_fe_and_covariates(panel):
    p = panel.copy()
    p["grp"] = p.unit % 3
    p["x"] = p.unit % 5
    r = did.twfe_event_study(p, "y", "unit", "year", extra_fe="year^grp")
    assert abs(r["post_avg"]["estimate"].iloc[0] - TRUE_ATT) < 0.01
    t = did.twfe_att(p, "y", "unit", "year", extra_fe="year^grp")
    assert abs(t["estimate"].iloc[0] - TRUE_ATT) < 0.01


def test_poisson_offset_equals_weighted_rate():
    rng = np.random.default_rng(3)
    p = make_panel(n_units=200, effect=-0.08)
    p["women"] = rng.integers(200, 2000, len(p))
    p["births"] = rng.poisson(np.exp(p["y"] - 1.0 + np.log(p["women"]) - 3.0))
    t = did.twfe_att(p, "births", "unit", "year", poisson=True, exposure="women")
    assert abs(t["estimate"].iloc[0] + 0.08) < 0.03
    assert t["term"].iloc[1] == "ATT en % du taux contrefactuel"
    assert np.isclose(t["estimate"].iloc[1], 100 * (np.exp(t["estimate"].iloc[0]) - 1))
    # Poisson sur le taux pondéré par l'exposition : mêmes équations de score que l'offset
    import pyfixest as pf
    d = did._recode_late(p, "year", "cohort").copy()
    d["treat_post"] = ((d.cohort > 0) & (d.year >= d.cohort)).astype(int)
    d["rate"] = d.births / d.women
    m = pf.fepois("rate ~ treat_post | unit + year", data=d, weights="women")
    assert abs(float(m.coef().iloc[0]) - t["estimate"].iloc[0]) < 1e-3


def test_cluster_bootstrap_stratified(panel):
    stat = lambda d: float(did.twfe_att(d, "y", "unit", "year")["estimate"].iloc[0])  # noqa: E731
    bs = did.cluster_bootstrap(panel, "unit", stat, n_boot=8, seed=3, strata="cohort")
    assert bs["n_boot_ok"] == 8 and bs["se_boot"] > 0 and bs["q025"] <= bs["q975"]
    vec = lambda d: np.array([stat(d), 2 * stat(d)])  # noqa: E731
    bv = did.cluster_bootstrap(panel, "unit", vec, n_boot=5, seed=3)
    assert bv["se_boot"].shape == (2,) and np.isclose(bv["se_boot"][1], 2 * bv["se_boot"][0])


def test_holm_and_wald():
    adj = did.holm([0.01, 0.04, 0.03])
    assert np.allclose(adj, [0.03, 0.06, 0.06])
    w = did._wald(np.array([0.0, 0.0]), np.eye(2))
    assert w["stat"] == 0 and w["df"] == 2 and w["p_value"] == 1.0


def test_mde_permutation_is_positive(panel):
    m = did.mde_permutation(panel, "y", "unit", "year", n_perm=15, seed=2)
    assert m["n_perm_ok"] >= 10 and m["mde"] > 0 and abs(m["placebo_mean"]) < 0.02


def test_meta_random_effects():
    r = did.meta_random_effects([-0.05, -0.04, -0.06], [0.0001, 0.0002, 0.00015], ["A", "B", "C"])
    assert -0.06 < r["estimate"] < -0.04 and r["ci_low"] < r["estimate"] < r["ci_upp"]


def test_balanced_post_matches_full_when_all_cohorts_observed():
    q = make_panel(n_units=200, seed=5, t0=2004, t1=2025)       # toutes les cohortes observées jusqu'à +5
    r = did.cs_event_study(q, "y", "unit", "year")
    b = did.cs_balanced_post(r)
    assert np.isclose(b["tidy"]["estimate"].iloc[0], r["post_avg"]["estimate"].iloc[0])
    assert abs(b["tidy"]["se"].iloc[0] - r["post_avg"]["se"].iloc[0]) < 0.1 * r["post_avg"]["se"].iloc[0]
    p = make_panel(n_units=200, seed=2)                             # cohorte 2016 non observée jusqu'à +5 (fin 2019)
    rb = did.cs_balanced_post(did.cs_event_study(p, "y", "unit", "year"))
    assert 2016 not in rb["cohorts"] and rb["k"] == 5
    q2 = make_panel(n_units=150, never_share=0.0, seed=3)           # sans jamais traités : identification tronquée
    r2 = did.cs_event_study(q2, "y", "unit", "year")
    assert all(g + 5 <= r2["info"]["years_model"][1] for g in did.cs_balanced_post(r2)["cohorts"])


def test_event_dummies_only_with_support():
    p = make_panel(n_units=100, seed=1, t1=2012)
    d = did.add_rel_time(p, "year", "cohort")
    d, names = did._event_dummies(d)
    assert "ev_p8" not in names and "ev_p2" in names


def test_poisson_pct_row_carries_coefficient_p():
    rng = np.random.default_rng(3)
    p = make_panel(n_units=100, effect=-0.08)
    p["women"] = rng.integers(200, 2000, len(p))
    p["births"] = rng.poisson(np.exp(p["y"] - 1.0 + np.log(p["women"]) - 3.0))
    t = did.twfe_att(p, "births", "unit", "year", poisson=True, exposure="women")
    assert "p" in t.columns and np.isclose(t["p"].iloc[0], t["p"].iloc[1])
