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

import re

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
                   seed: int = 1, window: tuple[int, int] = EVENT_WINDOW, weights: str | None = None,
                   anticipation: int = 0, post_avg: tuple[int, int] = POST_AVG, balance: bool = True) -> dict:
    """ATT(g,t) de Callaway & Sant'Anna via le paquet ``differences``, agrégés en event study.

    Conventions préenregistrées : période de base **universelle** (référence −1 ; coefficients pré rapportés
    à −1), panel (jamais « coupes répétées »), contrôle « pas encore traités » (ou « jamais traités »),
    doublement robuste quand des covariables sont fournies. Les unités dont la cohorte dépasse la dernière
    année observée sont recodées « jamais traitées » et comptées.

    Inférence : les fonctions d'influence des agrégats par période relative (stockées par ``differences``)
    donnent la matrice de covariance complète des coefficients ; elle sert (i) à l'écart-type exact de la
    moyenne +1..+5 (``post_avg``), (ii) au test de Wald joint des coefficients −8..−2 (``pre_wald``), (iii) aux
    bandes simultanées sup-t par bootstrap multiplicateur (Rademacher, ``boot`` tirages) quand ``boot > 0``.
    Avec ``cluster``, les fonctions d'influence sont sommées par grappe avant le calcul (sandwich groupé usuel) ;
    les écarts-types « analytiques » de ``differences`` ignorent ``cluster_var`` (seul son bootstrap en tient
    compte, par moyennes de grappe), d'où ce calcul direct.

    ``anticipation = a`` déplace la référence à −1−a (les coefficients −1..−a sont alors rapportés). ``balance=False``
    garde un panel structurellement déséquilibré (placebo H5a : les unités sortent à leur vraie bascule) sans
    basculer sur l'estimateur en coupes répétées.

    Renvoie ``{"event", "simple", "post_avg", "pre_wald_p", "pre_wald", "info", "model", "gt"}``.
    """
    from differences import ATTgt

    keep = [unit, time, cohort, y] + (covariates or []) + ([cluster] if cluster and cluster not in (unit, time) else []) + ([weights] if weights else [])
    d = df[list(dict.fromkeys(keep))].dropna().copy()
    tmax = int(d[time].max())
    late = d.loc[d[cohort] > tmax, unit].nunique()
    d.loc[d[cohort] > tmax, cohort] = 0
    d[cohort] = d[cohort].where(d[cohort] > 0)          # NaN = jamais traité pour ``differences``
    # panel équilibré : unités observées toutes les années de la fenêtre (les autres sont exclues et comptées)
    counts = d.groupby(unit)[time].nunique()
    n_unbalanced = int((counts < counts.max()).sum())
    if balance:
        d = d[d[unit].isin(counts[counts == counts.max()].index)]
    panel = d.set_index([unit, time]).sort_index()
    fml = y if not covariates else f"{y} ~ " + " + ".join(covariates)
    att = ATTgt(data=panel, cohort_column=cohort, base_period="universal", anticipation=anticipation)
    kw = dict(formula=fml, est_method=est_method if covariates else "reg", control_group=control,
              boot_iterations=0, random_state=seed, progress_bar=False, as_repeated_cross_section=False)
    if cluster and cluster != unit:
        _patch_differences_cluster()
        kw["cluster_var"] = cluster
    if weights:
        kw["weights_column"] = weights
    att.fit(**kw)

    ev = _normalise_agg(att.aggregate("event"))
    ag = att._result_dict[att.sample_names[0]]["aggregate_inst"]
    evl = ag.event
    rels_all = np.array([int(e.relative_period) for e in evl])
    IF = np.column_stack([np.asarray(e.influence_func, float) for e in evl])
    n_units = IF.shape[0]
    n_clusters = n_units
    if cluster and cluster != unit:
        # grappes ≠ unités : sommer les fonctions d'influence par grappe (sandwich groupé usuel, (1/n²) Σ_c S_c S_c' ;
        # ``differences`` utilise des moyennes par grappe, identique à grappes de taille égale)
        cl = d.groupby(unit)[cluster].first().sort_index()
        if len(cl) != n_units:
            raise RuntimeError(f"fonctions d'influence : {n_units} lignes pour {len(cl)} unités")
        IF = pd.DataFrame(IF).groupby(cl.to_numpy()).sum().to_numpy()
        n_clusters = IF.shape[0]
    V = IF.T @ IF / n_units ** 2
    se_if = np.sqrt(np.diag(V))
    est_all = np.array([float(e.ATT) for e in evl])
    # bandes simultanées sup-t (bootstrap multiplicateur Rademacher sur les fonctions d'influence)
    cband = None
    if boot and boot > 0:
        rng = np.random.default_rng(seed)
        ok = se_if > 0
        tmax_draws = []
        for _ in range(int(boot)):
            w = rng.choice([-1.0, 1.0], size=IF.shape[0])
            delta = (w @ IF) / n_units
            tmax_draws.append(np.max(np.abs(delta[ok] / se_if[ok])))
        crit = float(np.quantile(tmax_draws, 0.95))
        cband = (est_all - crit * se_if, est_all + crit * se_if, crit)

    # composition par période relative (cohortes et unités traitées contribuant)
    gt = att.results()
    gt.columns = [c[-1] if isinstance(c, tuple) else c for c in gt.columns]
    gt = gt.reset_index()
    gt["rel"] = gt["time"] - gt["cohort"]
    treated_units = d[d[cohort].notna()].groupby(cohort)[unit].nunique()
    comp = gt.groupby("rel").agg(n_cohorts=("cohort", "nunique"),
                                 n_units_rel=("cohort", lambda s: int(sum(treated_units.get(g, 0) for g in s.unique()))))
    ref = -1 - int(anticipation)
    sel = (rels_all >= window[0]) & (rels_all <= window[1]) & (rels_all != ref)
    tidy_ev = _tidy(rels_all[sel], est_all[sel], se_if[sel], "cs")
    tidy_ev["n_cohorts"] = [int(comp.n_cohorts.get(r, 0)) for r in rels_all[sel]]
    tidy_ev["n_units_rel"] = [int(comp.n_units_rel.get(r, 0)) for r in rels_all[sel]]
    if cband is not None:
        tidy_ev["cband_low"] = cband[0][sel]
        tidy_ev["cband_high"] = cband[1][sel]
    # moyenne +1..+k (k = dernière période disponible ≤ post_avg[1]) avec covariance complète
    post_mask = (rels_all >= post_avg[0]) & (rels_all <= post_avg[1])
    k = int(post_mask.sum())
    if k:
        w = post_mask.astype(float) / k
        pa_est, pa_se = float(w @ est_all), float(np.sqrt(w @ V @ w))
        kmax = int(rels_all[post_mask].max())
    else:
        pa_est, pa_se, kmax = np.nan, np.nan, 0
    tidy_post = _tidy([f"ATT[{post_avg[0]},{kmax}]"], [pa_est], [pa_se], "cs")
    tidy_post["k_periods"] = k
    # test de Wald joint des coefficients pré (−8..−2) avec la covariance des fonctions d'influence
    pre_mask = (rels_all >= window[0]) & (rels_all <= ref - 1)
    pre_w = _wald(est_all[pre_mask], V[np.ix_(pre_mask, pre_mask)])
    simple = _normalise_agg(att.aggregate("simple"))
    tidy_simple = _tidy(["ATT"], simple["estimate"].values[:1], simple["se"].values[:1], "cs")
    info = {"years": (int(d[time].min()), int(d[time].max())), "years_model": (int(gt.time.min()), int(gt.time.max())),
            "cohorts": sorted(int(c) for c in gt.cohort.unique()), "rel_available": (int(rels_all.min()), int(rels_all.max())),
            "n_units": int(n_units), "n_clusters": int(n_clusters), "n_never": int(d.loc[d[cohort].isna(), unit].nunique()), "n_recoded_never_after_window": int(late),
            "n_unbalanced_dropped": n_unbalanced if balance else 0, "n_unbalanced_kept": 0 if balance else n_unbalanced,
            "as_rcs": bool(getattr(att, "_as_rcs", False)), "k_post": k, "ref": ref, "n_obs": int(len(d)),
            "cband_crit": cband[2] if cband else np.nan}
    return {"event": tidy_ev, "simple": tidy_simple, "post_avg": tidy_post, "pre_wald_p": pre_w["p_value"], "pre_wald": pre_w,
            "info": info, "model": att, "gt": gt, "V": V, "rels": rels_all, "est": est_all}


def _wald(b: np.ndarray, V: np.ndarray) -> dict:
    """Test de Wald joint H0 : b = 0 avec covariance V (pseudo-inverse pour la stabilité numérique)."""
    from scipy.stats import chi2
    b = np.asarray(b, float)
    if b.size == 0:
        return {"stat": np.nan, "df": 0, "p_value": np.nan}
    stat = float(b @ np.linalg.pinv(V) @ b)
    k = int(np.linalg.matrix_rank(V))
    return {"stat": stat, "df": k, "p_value": float(chi2.sf(stat, k)) if k else np.nan}


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
    """Somme des t² des coefficients pré-traitement (périodes < ref) comparée à un χ²(k) : ce n'est un test
    de Wald que si les coefficients sont indépendants (ils ne le sont pas en général). Conservé comme
    diagnostic ; le test joint avec covariance est ``_wald`` (utilisé par ``cs_event_study`` et par
    ``wald_pre_pyfixest`` pour les modèles pyfixest)."""
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


def _fe_formula(unit: str, time: str, extra_fe: str | None) -> str:
    return f"{unit} + {time}" + (f" + {extra_fe}" if extra_fe else "")


def _recode_late(df: pd.DataFrame, time: str, cohort: str) -> pd.DataFrame:
    """Cohortes postérieures à la dernière année observée → jamais traitées sur la fenêtre (même règle que CS)."""
    d = df.copy()
    d.loc[d[cohort] > d[time].max(), cohort] = 0
    return d


def _post_from_model(m, names_by_rel: dict, estimator: str, post_avg=POST_AVG) -> pd.DataFrame:
    """Moyenne +1..+k des coefficients d'un modèle pyfixest avec covariance complète (w'Vw)."""
    coef = m.coef()
    V = pd.DataFrame(m._vcov, index=m._coefnames, columns=m._coefnames)
    idx = [n for r, n in names_by_rel.items() if post_avg[0] <= r <= post_avg[1] and n in coef.index]
    if not idx:
        return _tidy([f"ATT[{post_avg[0]},0]"], [np.nan], [np.nan], estimator)
    w = np.ones(len(idx)) / len(idx)
    kmax = max(r for r, n in names_by_rel.items() if n in idx)
    return _tidy([f"ATT[{post_avg[0]},{kmax}]"], [float(w @ coef.loc[idx].values)], [float(np.sqrt(w @ V.loc[idx, idx].values @ w))], estimator)


def _pre_wald_from_model(m, names_by_rel: dict, window=EVENT_WINDOW) -> dict:
    coef = m.coef()
    V = pd.DataFrame(m._vcov, index=m._coefnames, columns=m._coefnames)
    idx = [n for r, n in names_by_rel.items() if window[0] <= r <= -2 and n in coef.index]
    return _wald(coef.loc[idx].values, V.loc[idx, idx].values) if idx else {"stat": np.nan, "df": 0, "p_value": np.nan}


def twfe_event_study(df: pd.DataFrame, y: str, unit: str, time: str, cohort: str = "cohort",
                     cluster: str | None = None, window=EVENT_WINDOW, weights: str | None = None,
                     extra_fe: str | None = None, covariates: list[str] | None = None) -> dict:
    """Event study TWFE naïve (comparaison, préreg. §5). Renvoie {"event", "post_avg", "pre_wald"}.
    ``extra_fe`` : effets fixes supplémentaires (ex. "year^dens_cat" pour les chocs concurrents, §4.1)."""
    import pyfixest as pf

    d = add_rel_time(_recode_late(df, time, cohort), time, cohort, window=window)
    d, names = _event_dummies(d, window=window)
    xs = names + (covariates or [])
    fml = f"{y} ~ {' + '.join(xs)} | {_fe_formula(unit, time, extra_fe)}"
    m = pf.feols(fml, data=d, vcov={"CRV1": cluster or unit}, weights=weights)
    t = m.tidy().reset_index()
    t = t[t["Coefficient"].isin(names)]
    by_rel = {_name_to_rel(n): n for n in names}
    ev = _tidy([_name_to_rel(n) for n in t["Coefficient"]], t["Estimate"], t["Std. Error"], "twfe")
    return {"event": ev, "post_avg": _post_from_model(m, by_rel, "twfe"), "pre_wald": _pre_wald_from_model(m, by_rel, window), "model": m}


def sunab_event_study(df: pd.DataFrame, y: str, unit: str, time: str, cohort: str = "cohort",
                      cluster: str | None = None, window=EVENT_WINDOW, weights: str | None = None,
                      extra_fe: str | None = None, covariates: list[str] | None = None) -> dict:
    """Event study saturée cohorte × période relative (Sun & Abraham 2021), implémentée directement.

    Régression à effets fixes unité et année de ``y`` sur les indicatrices 1[cohorte = g] × 1[rel = r]
    pour chaque cohorte traitée g et chaque période relative r de la fenêtre (référence r = −1 ;
    extrémités binnées), les unités jamais traitées (``cohort == 0``) servant de contrôle. Les
    coefficients sont ensuite agrégés par r avec pour poids la part de chaque cohorte parmi les
    unités traitées observées en r ; la variance de l'agrégat vient de la matrice de covariance
    groupée des coefficients.
    """
    import pyfixest as pf

    cols = list(dict.fromkeys([unit, time, cohort, y] + ([weights] if weights else []) + (covariates or []) + ([cluster] if cluster and cluster not in (unit, time) else [])))
    if extra_fe:
        cols += [c for c in re.split(r"[+^\s]+", extra_fe) if c and c not in cols]
    d = add_rel_time(_recode_late(df[cols].dropna(), time, cohort), time, cohort, window=window)
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
    xs = names + (covariates or [])
    m = pf.feols(f"{y} ~ {' + '.join(xs)} | {_fe_formula(unit, time, extra_fe)}", data=d, vcov={"CRV1": cluster or unit}, weights=weights)
    coef = m.coef()
    V = pd.DataFrame(m._vcov, index=m._coefnames, columns=m._coefnames)
    # agrégation par période relative : W (n_rel × n_coef) de poids = parts de cohortes ; covariance W V W'
    rows, out_rel = [], []
    for r in rels:
        cells = [(g, n) for (g, rr, n) in meta if rr == r and n in coef.index]
        if not cells:
            continue
        shares = np.array([((d[cohort] == g) & (d["rel"] == r)).sum() for g, _ in cells], float)
        wrow = pd.Series(0.0, index=coef.index)
        wrow.loc[[n for _, n in cells]] = shares / shares.sum()
        rows.append(wrow.values); out_rel.append(r)
    W = np.array(rows)
    est = W @ coef.values
    Vagg = W @ V.values @ W.T
    ev = _tidy(out_rel, est, np.sqrt(np.diag(Vagg)), "sunab")
    rel_arr = np.array(out_rel)
    pm = (rel_arr >= POST_AVG[0]) & (rel_arr <= POST_AVG[1])
    if pm.any():
        w = pm.astype(float) / pm.sum()
        post = _tidy([f"ATT[{POST_AVG[0]},{int(rel_arr[pm].max())}]"], [float(w @ est)], [float(np.sqrt(w @ Vagg @ w))], "sunab")
    else:
        post = _tidy(["ATT[1,0]"], [np.nan], [np.nan], "sunab")
    prm = (rel_arr >= window[0]) & (rel_arr <= -2)
    return {"event": ev, "post_avg": post, "pre_wald": _wald(est[prm], Vagg[np.ix_(prm, prm)]), "model": m}


def _materialize_fe(d: pd.DataFrame, extra_fe: str | None) -> tuple[pd.DataFrame, str | None]:
    """Remplace les interactions ``a^b`` d'une formule d'effets fixes par des colonnes explicites ``a_x_b`` (pour les
    fonctions pyfixest qui n'acceptent pas « ^ », comme did2s)."""
    if not extra_fe or "^" not in extra_fe:
        return d, extra_fe
    terms = []
    for term in [t.strip() for t in extra_fe.split("+") if t.strip()]:
        if "^" in term:
            parts = [p.strip() for p in term.split("^")]
            name = "_x_".join(parts)
            d[name] = d[parts[0]].astype(str)
            for p in parts[1:]:
                d[name] = d[name] + "_" + d[p].astype(str)
            terms.append(name)
        else:
            terms.append(term)
    return d, " + ".join(terms)


def did2s_event_study(df: pd.DataFrame, y: str, unit: str, time: str, cohort: str = "cohort",
                      cluster: str | None = None, window=EVENT_WINDOW, extra_fe: str | None = None,
                      covariates: list[str] | None = None) -> dict:
    """Two-stage DiD de Gardner (2022) via ``pyfixest.did2s``. Renvoie {"event", "post_avg", "pre_wald"}. Les
    covariables invariantes dans le temps sont colinéaires aux effets fixes unité du premier étage et sont retirées
    (comptées dans ``dropped_covariates``)."""
    import pyfixest as pf

    d = add_rel_time(_recode_late(df, time, cohort), time, cohort, window=window)
    d["treat_post"] = ((d[cohort] > 0) & (d[time] >= d[cohort])).astype(int)
    d, names = _event_dummies(d, window=window)
    d, fe_extra = _materialize_fe(d, extra_fe)
    dropped = [c for c in (covariates or []) if (d.groupby(unit)[c].nunique() <= 1).all()]
    covs = [c for c in (covariates or []) if c not in dropped]
    # un effet fixe année × groupe emboîte l'effet fixe année : on ne garde que le premier (matrice sinon singulière dans did2s)
    nests_time = bool(fe_extra) and any(t.strip().startswith(f"{time}_x_") for t in fe_extra.split("+"))
    fe = f"{unit} + {fe_extra}" if nests_time else _fe_formula(unit, time, fe_extra)
    fs = ("~ " + " + ".join(covs) if covs else "~ 0") + f" | {fe}"
    m = pf.did2s(d, yname=y, first_stage=fs, second_stage=f"~ 0 + {' + '.join(names)}", treatment="treat_post", cluster=cluster or unit)
    t = m.tidy().reset_index()
    t = t[t["Coefficient"].isin(names)]
    by_rel = {_name_to_rel(n): n for n in names}
    ev = _tidy([_name_to_rel(n) for n in t["Coefficient"]], t["Estimate"], t["Std. Error"], "did2s")
    return {"event": ev, "post_avg": _post_from_model(m, by_rel, "did2s"), "pre_wald": _pre_wald_from_model(m, by_rel, window), "model": m,
            "dropped_covariates": dropped}


def twfe_att(df: pd.DataFrame, y: str, unit: str, time: str, cohort: str = "cohort",
             cluster: str | None = None, poisson: bool = False, exposure: str | None = None,
             extra_fe: str | None = None, covariates: list[str] | None = None, weights: str | None = None) -> pd.DataFrame:
    """ATT statique TWFE ; en Poisson à effets fixes si ``poisson`` (compte ``y``, ``log(exposure)`` en **offset**,
    préreg. §5). Pour le Poisson, une seconde ligne donne l'ATT en % du taux contrefactuel, 100·(exp(β)−1),
    avec IC par transformation des bornes."""
    import pyfixest as pf

    d = _recode_late(df, time, cohort).copy()
    d["treat_post"] = ((d[cohort] > 0) & (d[time] >= d[cohort])).astype(int)
    vc = {"CRV1": cluster or unit}
    xs = "treat_post" + (" + " + " + ".join(covariates) if covariates else "")
    fe = _fe_formula(unit, time, extra_fe)
    if poisson:
        d = d[d[y].notna()]
        if exposure:
            d = d[d[exposure] > 0].copy()
            d["log_exp"] = np.log(d[exposure])
            m = pf.fepois(f"{y} ~ {xs} | {fe}", data=d, vcov=vc, offset="log_exp")
        else:
            m = pf.fepois(f"{y} ~ {xs} | {fe}", data=d, vcov=vc)
        lab = "twfe_poisson"
    else:
        m = pf.feols(f"{y} ~ {xs} | {fe}", data=d, vcov=vc, weights=weights)
        lab = "twfe"
    t = m.tidy().reset_index()
    t = t[t["Coefficient"] == "treat_post"]
    out = _tidy(["ATT"], t["Estimate"], t["Std. Error"], lab)
    if poisson:
        b, s = float(t["Estimate"].iloc[0]), float(t["Std. Error"].iloc[0])
        pct = pd.DataFrame({"term": ["ATT en % du taux contrefactuel"], "estimate": [100 * (np.exp(b) - 1)],
                            "se": [100 * np.exp(b) * s], "ci_low": [100 * (np.exp(b - 1.959964 * s) - 1)],
                            "ci_high": [100 * (np.exp(b + 1.959964 * s) - 1)], "estimator": [lab]})
        out = pd.concat([out, pct], ignore_index=True)
    return out


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


def cluster_bootstrap(df: pd.DataFrame, unit: str, stat, n_boot: int = 100, seed: int = 1, cluster: str | None = None,
                      strata: str | None = None) -> dict:
    """Bootstrap par grappes (unités ou ``cluster``) d'une statistique ``stat(df) -> float`` (ou vecteur).

    Rééchantillonne les grappes avec remise, **stratifié** par ``strata`` (ex. la cohorte, pour que la
    composition des cohortes — et donc l'estimand de Callaway & Sant'Anna sans jamais-traités — soit la même
    dans chaque tirage) ; les grappes tirées plusieurs fois reçoivent un suffixe d'identifiant pour rester
    distinctes. Renvoie l'écart-type bootstrap et les quantiles 2,5 / 97,5 % (par composante si vecteur)."""
    rng = np.random.default_rng(seed)
    key = cluster or unit
    groups = {k: g for k, g in df.groupby(key, sort=False)}
    keys = np.array(list(groups))
    if strata:
        strat_of = df.groupby(key, sort=False)[strata].first()
        strata_keys = {s: np.array([k for k in keys if strat_of[k] == s]) for s in strat_of.unique()}
    draws = []
    for b in range(n_boot):
        if strata:
            pick = np.concatenate([rng.choice(ks, size=len(ks), replace=True) for ks in strata_keys.values()])
        else:
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
    if draws.ndim == 1:
        draws = draws[np.isfinite(draws)]
    else:
        draws = draws[np.isfinite(draws).all(axis=1)]
    ok = len(draws) > 2
    return {"se_boot": (np.std(draws, axis=0, ddof=1) if ok else np.nan),
            "q025": (np.quantile(draws, 0.025, axis=0) if ok else np.nan),
            "q975": (np.quantile(draws, 0.975, axis=0) if ok else np.nan),
            "n_boot_ok": int(len(draws)), "draws": draws}


def continuous_twfe(df: pd.DataFrame, y: str, x: str, fe: str, cluster: str, weights: str | None = None) -> pd.DataFrame:
    """Régression à effets fixes de ``y`` sur une exposition continue ``x`` (ex. D3), ``fe`` = formule des
    effets fixes pyfixest (ex. "dep^age_group + year^age_group")."""
    import pyfixest as pf

    m = pf.feols(f"{y} ~ {x} | {fe}", data=df, vcov={"CRV1": cluster}, weights=weights)
    t = m.tidy().reset_index()
    t = t[t["Coefficient"] == x]
    return _tidy([x], t["Estimate"], t["Std. Error"], "twfe_continuous")


def wild_p(m, param: str, reps: int = 9999, seed: int = 1, weights_type: str = "webb") -> float:
    """p-value du wild cluster bootstrap (paquet ``wildboottest`` via pyfixest), poids de Webb par défaut (recommandés
    pour un petit nombre de grappes) ; hypothèse nulle imposée."""
    res = m.wildboottest(param=param, reps=reps, weights_type=weights_type, seed=seed)
    return float(res["Pr(>|t|)"])


def iv_anderson_rubin(df: pd.DataFrame, y: str, endog: str, instrument: str, fe: str, cluster: str, weights: str | None = None,
                      grid: np.ndarray | None = None, reps: int = 999, seed: int = 1, alpha: float = 0.05) -> dict:
    """Intervalle de confiance d'Anderson-Rubin par inversion du test de la forme réduite : pour chaque β de la grille,
    on régresse y − β·endog sur l'instrument (effets fixes ``fe``) et on garde β si la p du wild cluster bootstrap
    dépasse α. Robuste aux instruments faibles et, via le bootstrap sauvage, au petit nombre de grappes."""
    import pyfixest as pf

    if grid is None:
        grid = np.linspace(-1.0, 1.0, 81)
    keep = []
    d = df.copy()
    for b in grid:
        d["_yb"] = d[y] - b * d[endog]
        m = pf.feols(f"_yb ~ {instrument} | {fe}", data=d, vcov={"CRV1": cluster}, weights=weights)
        if wild_p(m, instrument, reps=reps, seed=seed) > alpha:
            keep.append(float(b))
    if not keep:
        return {"ar_low": np.nan, "ar_high": np.nan, "ar_empty": True, "grid": (float(grid[0]), float(grid[-1]))}
    return {"ar_low": min(keep), "ar_high": max(keep), "ar_empty": False, "grid": (float(grid[0]), float(grid[-1])),
            "ar_unbounded": bool(min(keep) == grid[0] or max(keep) == grid[-1])}


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
            "iv": (float(ivr["Estimate"]), float(ivr["Std. Error"])), "n": int(iv._N),
            "models": {"first_stage": pf.feols(f"{endog} ~ {instrument} | {fe}", data=df, vcov=vc, weights=weights),
                       "reduced_form": pf.feols(f"{y} ~ {instrument} | {fe}", data=df, vcov=vc, weights=weights)}}
