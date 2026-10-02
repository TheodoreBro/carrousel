"""Estimateurs de différences-de-différences échelonnées et outils d'inférence.

Conventions communes (préregistration §5) :
- ``unit`` : identifiant d'unité (commune, département × âge, município…) ;
- ``time`` : année entière ;
- ``cohort`` : première année de traitement de l'unité ; ``0`` (ou NaN) pour les unités jamais
  traitées sur la fenêtre ;
- ``y`` : résultat (log du taux, taux, ou compte selon la fonction).

Toutes les fonctions renvoient des DataFrames « tidy » (une ligne par coefficient) avec les
colonnes ``term``, ``estimate``, ``se``, ``ci_low``, ``ci_high``, ``estimator`` pour alimenter
``05_figures.py`` et ``06_tables.py`` sans retraitement.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

EVENT_WINDOW = (-8, 8)
POST_AVG = (1, 5)      # agrégat primaire : moyenne des périodes +1 à +5


# ----------------------------------------------------------------------------- préparation

def add_cohort(df: pd.DataFrame, unit: str, time: str, treat: str, out: str = "cohort") -> pd.DataFrame:
    """Cohorte = première année où ``treat`` vaut 1 ; 0 si jamais traité."""
    first = df.loc[df[treat] == 1].groupby(unit)[time].min().rename(out)
    d = df.merge(first, on=unit, how="left")
    d[out] = d[out].fillna(0).astype(int)
    return d


def add_rel_time(df: pd.DataFrame, time: str, cohort: str = "cohort", out: str = "rel",
                 window: tuple[int, int] = EVENT_WINDOW) -> pd.DataFrame:
    """Temps relatif borné aux extrémités de la fenêtre ; NaN pour les jamais traités."""
    d = df.copy()
    rel = d[time] - d[cohort]
    rel = rel.where(d[cohort] > 0)
    d[out] = rel.clip(lower=window[0], upper=window[1])
    return d


def drop_always_treated(df: pd.DataFrame, time: str, cohort: str = "cohort", min_pre: int = 3) -> pd.DataFrame:
    """Exclut les unités traitées avant ``min_pre`` années de pré-période observées (préreg. §4.2)."""
    t0 = df[time].min()
    keep = (df[cohort] == 0) | (df[cohort] - t0 >= min_pre)
    return df.loc[keep].copy()


def _tidy(term, est, se, estimator, alpha=0.05):
    from scipy.stats import norm
    z = norm.ppf(1 - alpha / 2)
    est, se = np.asarray(est, float), np.asarray(se, float)
    return pd.DataFrame({"term": list(term), "estimate": est, "se": se,
                         "ci_low": est - z * se, "ci_high": est + z * se, "estimator": estimator})


# ----------------------------------------------------------------------------- Callaway & Sant'Anna

def cs_event_study(df: pd.DataFrame, y: str, unit: str, time: str, cohort: str = "cohort",
                   covariates: list[str] | None = None, control: str = "not_yet_treated",
                   est_method: str = "dr", cluster: str | None = None, boot: int = 0,
                   seed: int = 1, window: tuple[int, int] = EVENT_WINDOW) -> dict:
    """ATT(g,t) de Callaway & Sant'Anna via le paquet ``differences``.

    Renvoie ``{"event": tidy, "simple": tidy, "post_avg": tidy, "pre_wald_p": float}``.
    ``post_avg`` est la moyenne des effets +1..+5 (agrégat primaire de la préregistration).
    """
    from differences import ATTgt

    keep = [unit, time, cohort, y] + (covariates or []) + ([cluster] if cluster and cluster not in (unit, time) else [])
    d = df[list(dict.fromkeys(keep))].dropna().copy()
    d[cohort] = d[cohort].where(d[cohort] > 0)          # NaN = jamais traité pour ``differences``
    panel = d.set_index([unit, time]).sort_index()
    fml = y if not covariates else f"{y} ~ " + " + ".join(covariates)
    att = ATTgt(data=panel, cohort_column=cohort)
    kw = dict(formula=fml, est_method=est_method if covariates else "reg", control_group=control,
              boot_iterations=boot, random_state=seed, progress_bar=False)
    if cluster and cluster != unit:
        _patch_differences_cluster()
        kw["cluster_var"] = cluster
    att.fit(**kw)

    ev = _normalise_agg(att.aggregate("event"))
    ev = ev[(ev["rel"] >= window[0]) & (ev["rel"] <= window[1])]
    tidy_ev = _tidy(ev["rel"].astype(int), ev["estimate"], ev["se"], "cs")

    simple = _normalise_agg(att.aggregate("simple"))
    tidy_simple = _tidy(["ATT"], simple["estimate"].values[:1], simple["se"].values[:1], "cs")

    post = ev[(ev["rel"] >= POST_AVG[0]) & (ev["rel"] <= POST_AVG[1])]
    # moyenne simple des coefficients ; écart-type approché par la moyenne des variances / k
    # (borne haute si les coefficients sont positivement corrélés ; le bootstrap de l'event study
    # donne la version exacte quand boot > 0)
    k = len(post)
    tidy_post = _tidy([f"ATT[{POST_AVG[0]},{POST_AVG[1]}]"], [post["estimate"].mean()],
                      [np.sqrt((post["se"] ** 2).sum()) / k if k else np.nan], "cs")
    pre_p = pre_trend_test(tidy_ev)["p_value"]
    return {"event": tidy_ev, "simple": tidy_simple, "post_avg": tidy_post, "pre_wald_p": pre_p, "model": att}


def _patch_differences_cluster() -> None:
    """``differences`` 0.3 indexe la colonne de grappe comme une Series puis appelle une validation qui
    attend un DataFrame (plantage « 'Series' object has no attribute 'columns' »). On convertit à la volée."""
    import differences.models.attgt.attgt as mod

    if getattr(mod, "_cluster_patched", False):
        return
    orig = mod.get_cluster_groups

    def patched(data, cluster_var):
        if isinstance(data, pd.Series):
            data = data.to_frame()
        return orig(data=data, cluster_var=cluster_var)

    mod.get_cluster_groups = patched
    mod._cluster_patched = True


def _normalise_agg(agg: pd.DataFrame) -> pd.DataFrame:
    """Aplatit la sortie de ``differences`` (colonnes MultiIndex, index = période relative) en
    colonnes ``rel``, ``estimate``, ``se``."""
    a = agg.copy()
    if isinstance(a.columns, pd.MultiIndex):
        a.columns = [str(c[-1]) for c in a.columns]
    else:
        a.columns = [str(c) for c in a.columns]
    a = a.reset_index()
    ren = {}
    for c in a.columns:
        lc = c.lower()
        if lc in ("att", "estimate", "coef"):
            ren[c] = "estimate"
        elif lc in ("std_error", "se", "std.error", "std_err"):
            ren[c] = "se"
        elif lc in ("relative_period", "event_time", "rel_period", "rel"):
            ren[c] = "rel"
    return a.rename(columns=ren)


def pre_trend_test(tidy_event: pd.DataFrame, ref: int = -1) -> dict:
    """Test de Wald approché de nullité conjointe des coefficients pré-traitement (périodes < ref),
    en supposant les coefficients non corrélés (approximation conservatrice dans la pratique courante ;
    le test exact est fourni par le bootstrap de l'estimateur quand il est disponible)."""
    from scipy.stats import chi2

    pre = tidy_event[tidy_event["term"].astype(int) < ref]
    if pre.empty:
        return {"stat": np.nan, "df": 0, "p_value": np.nan}
    stat = float(((pre["estimate"] / pre["se"]) ** 2).sum())
    k = int(len(pre))
    return {"stat": stat, "df": k, "p_value": float(chi2.sf(stat, k))}


# ----------------------------------------------------------------------------- TWFE et variantes

def _event_dummies(d: pd.DataFrame, rel: str = "rel", window=EVENT_WINDOW, ref: int = -1) -> tuple[pd.DataFrame, list[str]]:
    names = []
    for r in range(window[0], window[1] + 1):
        if r == ref:
            continue
        n = f"ev_m{abs(r)}" if r < 0 else f"ev_p{r}"
        d[n] = (d[rel] == r).astype(int)
        names.append(n)
    return d, names


def _name_to_rel(n: str) -> int:
    return -int(n[4:]) if n.startswith("ev_m") else int(n[4:])


def twfe_event_study(df: pd.DataFrame, y: str, unit: str, time: str, cohort: str = "cohort",
                     cluster: str | None = None, window=EVENT_WINDOW, weights: str | None = None) -> pd.DataFrame:
    """Event study TWFE naïve (rapportée à titre de comparaison, préreg. §5)."""
    import pyfixest as pf

    d = add_rel_time(df, time, cohort, window=window)
    d, names = _event_dummies(d, window=window)
    fml = f"{y} ~ {' + '.join(names)} | {unit} + {time}"
    m = pf.feols(fml, data=d, vcov={"CRV1": cluster or unit}, weights=weights)
    t = m.tidy().reset_index()
    t = t[t["Coefficient"].isin(names)]
    return _tidy([_name_to_rel(n) for n in t["Coefficient"]], t["Estimate"], t["Std. Error"], "twfe")


def sunab_event_study(df: pd.DataFrame, y: str, unit: str, time: str, cohort: str = "cohort",
                      cluster: str | None = None, window=EVENT_WINDOW, weights: str | None = None) -> pd.DataFrame:
    """Event study saturée cohorte × période relative (Sun & Abraham 2021), implémentée directement.

    Régression à effets fixes unité et année de ``y`` sur les indicatrices 1[cohorte = g] × 1[rel = r]
    pour chaque cohorte traitée g et chaque période relative r de la fenêtre (référence r = −1 ;
    extrémités binnées), les unités jamais traitées (``cohort == 0``) servant de contrôle. Les
    coefficients sont ensuite agrégés par r avec pour poids la part de chaque cohorte parmi les
    unités traitées observées en r ; la variance de l'agrégat vient de la matrice de covariance
    groupée des coefficients.
    """
    import pyfixest as pf

    d = add_rel_time(df[[unit, time, cohort, y] + ([weights] if weights else [])].dropna(), time, cohort, window=window)
    if (d[cohort] == 0).sum() == 0:
        raise ValueError("Sun & Abraham : il faut des unités jamais traitées (cohort == 0) comme contrôle.")
    cohorts = sorted(c for c in d[cohort].unique() if c > 0)
    rels = [r for r in range(window[0], window[1] + 1) if r != -1]
    names, meta = [], []
    for g in cohorts:
        for r in rels:
            mask = (d[cohort] == g) & (d["rel"] == r)
            if mask.sum() == 0:
                continue
            n = f"sa_{g}_{'m' + str(abs(r)) if r < 0 else 'p' + str(r)}"
            d[n] = mask.astype(int)
            names.append(n)
            meta.append((g, r, n))
    m = pf.feols(f"{y} ~ {' + '.join(names)} | {unit} + {time}", data=d, vcov={"CRV1": cluster or unit}, weights=weights)
    coef = m.coef()
    V = pd.DataFrame(m._vcov, index=m._coefnames, columns=m._coefnames)
    out_rel, out_est, out_se = [], [], []
    for r in rels:
        cells = [(g, n) for (g, rr, n) in meta if rr == r and n in coef.index]
        if not cells:
            continue
        shares = np.array([((d[cohort] == g) & (d["rel"] == r)).sum() for g, _ in cells], float)
        w = shares / shares.sum()
        idx = [n for _, n in cells]
        est = float(np.dot(w, coef.loc[idx].values))
        var = float(w @ V.loc[idx, idx].values @ w)
        out_rel.append(r); out_est.append(est); out_se.append(np.sqrt(var))
    return _tidy(out_rel, out_est, out_se, "sunab")


def did2s_event_study(df: pd.DataFrame, y: str, unit: str, time: str, cohort: str = "cohort",
                      cluster: str | None = None, window=EVENT_WINDOW) -> pd.DataFrame:
    """Two-stage DiD de Gardner (2022) via ``pyfixest.did2s``."""
    import pyfixest as pf

    d = add_rel_time(df, time, cohort, window=window)
    d["treat_post"] = ((d[cohort] > 0) & (d[time] >= d[cohort])).astype(int)
    d, names = _event_dummies(d, window=window)
    m = pf.did2s(d, yname=y, first_stage=f"~ 0 | {unit} + {time}",
                 second_stage=f"~ 0 + {' + '.join(names)}", treatment="treat_post", cluster=cluster or unit)
    t = m.tidy().reset_index()
    t = t[t["Coefficient"].isin(names)]
    return _tidy([_name_to_rel(n) for n in t["Coefficient"]], t["Estimate"], t["Std. Error"], "did2s")


def twfe_att(df: pd.DataFrame, y: str, unit: str, time: str, cohort: str = "cohort",
             cluster: str | None = None, poisson: bool = False, exposure: str | None = None) -> pd.DataFrame:
    """ATT statique TWFE ; en Poisson à effets fixes si ``poisson`` (compte ``y``, ``log(exposure)`` en contrôle)."""
    import pyfixest as pf

    d = df.copy()
    d["treat_post"] = ((d[cohort] > 0) & (d[time] >= d[cohort])).astype(int)
    vc = {"CRV1": cluster or unit}
    if poisson:
        if exposure:
            d["log_exp"] = np.log(d[exposure].clip(lower=1e-9))
            m = pf.fepois(f"{y} ~ treat_post + log_exp | {unit} + {time}", data=d, vcov=vc)
        else:
            m = pf.fepois(f"{y} ~ treat_post | {unit} + {time}", data=d, vcov=vc)
        lab = "twfe_poisson"
    else:
        m = pf.feols(f"{y} ~ treat_post | {unit} + {time}", data=d, vcov=vc)
        lab = "twfe"
    t = m.tidy().reset_index()
    t = t[t["Coefficient"] == "treat_post"]
    return _tidy(["ATT"], t["Estimate"], t["Std. Error"], lab)


# ----------------------------------------------------------------------------- puissance

def mde_permutation(df: pd.DataFrame, y: str, unit: str, time: str, cohort: str = "cohort",
                    n_perm: int = 200, seed: int = 1, alpha: float = 0.05, power: float = 0.80,
                    estimator=None) -> dict:
    """Taille d'effet minimale détectable par permutation des cohortes entre unités.

    On réattribue aléatoirement les cohortes observées aux unités (la distribution des dates de
    bascule est conservée, le lien avec les unités est rompu), on ré-estime l'ATT, et l'écart-type
    des ATT placebo sert d'écart-type de référence : MDE ≈ (z_{1-α/2} + z_{power}) × sd.
    ``estimator`` : fonction (df) → float ; par défaut l'ATT statique TWFE (rapide).
    """
    from scipy.stats import norm

    rng = np.random.default_rng(seed)
    units = df[[unit, cohort]].drop_duplicates(unit).reset_index(drop=True)
    est = estimator or (lambda d: float(twfe_att(d, y, unit, time, cohort)["estimate"].iloc[0]))
    placebo = []
    for _ in range(n_perm):
        perm = units.copy()
        perm[cohort] = rng.permutation(perm[cohort].values)
        d = df.drop(columns=[cohort]).merge(perm, on=unit, how="left")
        try:
            placebo.append(est(d))
        except Exception:  # noqa: BLE001 — une permutation dégénérée n'arrête pas le calcul
            continue
    sd = float(np.std(placebo, ddof=1)) if len(placebo) > 2 else np.nan
    return {"sd_placebo": sd, "mde": (norm.ppf(1 - alpha / 2) + norm.ppf(power)) * sd,
            "n_perm_ok": len(placebo), "placebo_mean": float(np.mean(placebo)) if placebo else np.nan}


# ----------------------------------------------------------------------------- synthèse entre pays

def meta_random_effects(estimates, variances, names=None, alpha: float = 0.05) -> dict:
    """Méta-analyse à effets aléatoires (REML itéré) via statsmodels ; renvoie estimation poolée,
    intervalle de confiance, tau², I² et le tableau par pays."""
    from statsmodels.stats.meta_analysis import combine_effects

    res = combine_effects(np.asarray(estimates, float), np.asarray(variances, float),
                          method_re="iterated", row_names=names, alpha=alpha)
    summ = res.summary_frame()
    pooled = summ.loc["random effect"] if "random effect" in summ.index else summ.iloc[-1]
    return {"estimate": float(pooled["eff"]), "ci_low": float(pooled["ci_low"]), "ci_upp": float(pooled["ci_upp"]),
            "tau2": float(res.tau2), "i2": float(getattr(res, "i2", np.nan)), "table": summ}


# ----------------------------------------------------------------------------- compléments Étape 3

def holm(pvals) -> np.ndarray:
    """Correction de Holm (famille de tests) ; renvoie les p ajustées dans l'ordre d'entrée."""
    p = np.asarray(pvals, float)
    n = len(p)
    order = np.argsort(p)
    adj = np.empty(n)
    running = 0.0
    for rank, idx in enumerate(order):
        val = min(1.0, (n - rank) * p[idx])
        running = max(running, val)
        adj[idx] = running
    return adj


def p_from_z(est, se) -> float:
    from scipy.stats import norm
    est, se = float(est), float(se)
    return float(2 * norm.sf(abs(est / se))) if se > 0 else np.nan


def difference_test(est1, se1, est2, se2) -> dict:
    """Test de différence de deux estimations supposées indépendantes (approximation : les deux
    échantillons partagent les unités, la covariance est ignorée ; dit dans le papier)."""
    d = float(est1) - float(est2)
    se = float(np.sqrt(se1 ** 2 + se2 ** 2))
    return {"diff": d, "se": se, "p": p_from_z(d, se)}


def cs_post_avg(df: pd.DataFrame, y: str, unit: str, time: str, cohort: str = "cohort", **kw) -> float:
    """Moyenne des effets +1..+5 de Callaway & Sant'Anna (estimation ponctuelle seule, pour le bootstrap)."""
    r = cs_event_study(df, y, unit, time, cohort, **kw)
    return float(r["post_avg"]["estimate"].iloc[0])


def cluster_bootstrap(df: pd.DataFrame, unit: str, stat, n_boot: int = 100, seed: int = 1, cluster: str | None = None) -> dict:
    """Bootstrap par grappes (unités ou ``cluster``) d'une statistique ``stat(df) -> float``.

    Rééchantillonne les grappes avec remise ; les grappes tirées plusieurs fois reçoivent un suffixe
    d'identifiant pour rester distinctes. Renvoie l'écart-type bootstrap et les quantiles 2,5 / 97,5 %."""
    rng = np.random.default_rng(seed)
    key = cluster or unit
    groups = {k: g for k, g in df.groupby(key, sort=False)}
    keys = np.array(list(groups))
    draws = []
    for b in range(n_boot):
        pick = rng.choice(keys, size=len(keys), replace=True)
        parts = []
        counts: dict = {}
        for k in pick:
            c = counts.get(k, 0)
            counts[k] = c + 1
            g = groups[k]
            if c:
                g = g.copy()
                g[unit] = g[unit].astype(str) + f"__b{c}"
            parts.append(g)
        boot = pd.concat(parts, ignore_index=True)
        try:
            draws.append(stat(boot))
        except Exception:  # noqa: BLE001
            continue
    draws = np.array(draws, float)
    draws = draws[np.isfinite(draws)]
    return {"se_boot": float(np.std(draws, ddof=1)) if len(draws) > 2 else np.nan,
            "q025": float(np.quantile(draws, 0.025)) if len(draws) > 2 else np.nan,
            "q975": float(np.quantile(draws, 0.975)) if len(draws) > 2 else np.nan,
            "n_boot_ok": int(len(draws))}


def continuous_twfe(df: pd.DataFrame, y: str, x: str, fe: str, cluster: str, weights: str | None = None) -> pd.DataFrame:
    """Régression à effets fixes de ``y`` sur une exposition continue ``x`` (ex. D3), ``fe`` = formule des
    effets fixes pyfixest (ex. "dep^age_group + year^age_group")."""
    import pyfixest as pf

    m = pf.feols(f"{y} ~ {x} | {fe}", data=df, vcov={"CRV1": cluster}, weights=weights)
    t = m.tidy().reset_index()
    t = t[t["Coefficient"] == x]
    return _tidy([x], t["Estimate"], t["Std. Error"], "twfe_continuous")


def iv_2sls(df: pd.DataFrame, y: str, endog: str, instrument: str, fe: str, cluster: str, weights: str | None = None) -> dict:
    """2SLS à effets fixes (pyfixest) : ``y ~ 1 | fe | endog ~ instrument``. Renvoie la forme réduite, le
    premier étage (F) et le coefficient IV."""
    import pyfixest as pf

    vc = {"CRV1": cluster}
    fs = pf.feols(f"{endog} ~ {instrument} | {fe}", data=df, vcov=vc, weights=weights).tidy().reset_index()
    rf = pf.feols(f"{y} ~ {instrument} | {fe}", data=df, vcov=vc, weights=weights).tidy().reset_index()
    iv = pf.feols(f"{y} ~ 1 | {fe} | {endog} ~ {instrument}", data=df, vcov=vc, weights=weights)
    t = iv.tidy().reset_index()
    fsr = fs[fs["Coefficient"] == instrument].iloc[0]
    rfr = rf[rf["Coefficient"] == instrument].iloc[0]
    ivr = t[t["Coefficient"].astype(str).str.contains(endog)].iloc[0]
    return {"first_stage": (float(fsr["Estimate"]), float(fsr["Std. Error"])),
            "first_stage_F": float((fsr["Estimate"] / fsr["Std. Error"]) ** 2),
            "reduced_form": (float(rfr["Estimate"]), float(rfr["Std. Error"])),
            "iv": (float(ivr["Estimate"]), float(ivr["Std. Error"])), "n": int(iv._N)}
