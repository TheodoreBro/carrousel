#!/usr/bin/env python
"""Colombie — échantillon, MDE et estimations (préregistration §3, §5 ; addendum A4), avec les mêmes fonctions que la France
(``scripts/05_estimate.py`` : run_block, Collector, familles de Holm ; ``scripts/common/did.py``).

Usage :
    python scripts/11_co_estimate.py --part sample            # tableau d'échantillon et MDE (avant toute estimation)
    python scripts/11_co_estimate.py --part all               # sample h1 h2 h3 h5 h6 robust summary
    python scripts/11_co_estimate.py --part h2 --fast         # vérification (sorties dans tables/est_co_smoke)

Unité = municipio (× groupe d'âge) ; cohorte = première année avec ≥ 50 % de la population couverte en 4G (A4) ; municipios
déjà couverts au premier trimestre observé (2015-T4) exclus du primaire (censure à gauche). Fenêtre 1998-2024 ; cohortes 2016-2023.
Résultat = log(naissances + 0,5 pour 1 000 femmes) ; grappes = municipio.

Sorties : tables/est_co/<partie>.csv, tables/est_co_all.csv, tables/t_estimates_co.md, tables/t_sample_co.md, tables/t_mde_co.md.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import did  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "tables"
_spec = importlib.util.spec_from_file_location("e5", Path(__file__).resolve().parent / "05_estimate.py")
e5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e5)

GROUPS = e5.GROUPS
G2539, G1524 = e5.G2539, e5.G1524
YEARS = (1998, 2024)
MIN_PRE = 3
Y_ALL = "log(naissances+0,5 / 1 000 f. 15-49)"
Y_2539 = "log(naissances+0,5 / 1 000 f. 25-39)"
COVS = ["share_cab", "log_pop", "share_edu_sup", "pretrend_1014"]
log = e5.log


# ----------------------------------------------------------------------------- panels

def static() -> pd.DataFrame:
    return pd.read_parquet(PROC / "co_treatment_static.parquet")


def covariates(oc: pd.DataFrame) -> pd.DataFrame:
    """Contrôles de pré-période par municipio (A4) : part de population en cabecera 2015, log population 2015, part des
    naissances de mères diplômées du supérieur 2013-2015, pente MCO 2010-2014 du log du taux 15-49."""
    st = static().set_index("municipio")
    cov = pd.DataFrame({"share_cab": st.share_cab, "log_pop": np.log(st.pop_total)})
    m = oc.groupby(["municipio", "year"], as_index=False)[["births", "births_edu_sup", "births_edu_known", "women"]].sum()
    e = m[m.year.between(2013, 2015)].groupby("municipio")[["births_edu_sup", "births_edu_known"]].sum()
    cov["share_edu_sup"] = (e.births_edu_sup / e.births_edu_known.where(e.births_edu_known > 0)).reindex(cov.index)
    pre = m[m.year.between(2010, 2014)].assign(y=lambda d: np.log((d.births + 0.5) / d.women * 1000)).pivot(index="municipio", columns="year", values="y")
    X = np.array(pre.columns, float) - np.mean(pre.columns)
    L = pre.values
    ok = np.isfinite(L)
    lbar = np.nanmean(np.where(ok, L, np.nan), axis=1)
    num = np.nansum(X[None, :] * (np.where(ok, L, np.nan) - lbar[:, None]), axis=1)
    den = np.where(ok, X[None, :] ** 2, 0).sum(1)
    cov["pretrend_1014"] = pd.Series(num / den, index=pre.index).reindex(cov.index)
    return cov.reset_index()


def mun_age_panel(cohort_col: str = "cohort_4g_50", censored_col: str = "censored_4g_50", drop_censored: bool = True,
                  years: tuple[int, int] = YEARS) -> pd.DataFrame:
    oc = pd.read_parquet(PROC / "co_outcomes_mun_age.parquet")
    st = static()
    d = oc.merge(st[["municipio", cohort_col, censored_col, "share_cab", "pop_total", "first_obs"]], on="municipio", how="inner")
    d = d[d.year.between(*years) & (d.women > 0)].copy()
    if drop_censored:
        d = d[~d[censored_col].astype(bool)]
    d["cohort"] = d[cohort_col].fillna(0).astype(int)
    d["y_log"] = np.log((d.births + 0.5) / d.women * 1000)
    d["y_rate"] = d.births / d.women * 1000
    d["y_asinh"] = np.arcsinh(d.y_rate)
    d["y_union"] = np.log((d.births_union + 0.5) / d.women * 1000)
    d["y_nonunion"] = np.log((d.births_civ_known - d.births_union + 0.5) / d.women * 1000)
    d["y_rank1"] = np.log((d.births_rank1 + 0.5) / d.women * 1000)
    d["y_rank2"] = np.log((d.births_rank_known - d.births_rank1 + 0.5) / d.women * 1000)
    d["unit"] = d.municipio + "_" + d.age_group
    d["dep"] = d.municipio.str[:2]
    return d


def aggregate(d: pd.DataFrame, groups: list[str], label: str) -> pd.DataFrame:
    s = d[d.age_group.isin(groups)].groupby(["municipio", "year", "cohort", "dep"], as_index=False).agg(
        births=("births", "sum"), women=("women", "sum"), births_union=("births_union", "sum"), births_civ_known=("births_civ_known", "sum"),
        births_rank1=("births_rank1", "sum"), births_rank_known=("births_rank_known", "sum"), share_cab=("share_cab", "first"), pop_total=("pop_total", "first"))
    s["age_group"] = label
    for c, num in (("y_log", s.births), ("y_union", s.births_union), ("y_nonunion", s.births_civ_known - s.births_union),
                   ("y_rank1", s.births_rank1), ("y_rank2", s.births_rank_known - s.births_rank1)):
        s[c] = np.log((num + 0.5) / s.women * 1000)
    s["y_rate"] = s.births / s.women * 1000
    s["y_asinh"] = np.arcsinh(s.y_rate)
    s["unit"] = s.municipio + "_" + label
    return s


def with_covs(d: pd.DataFrame, cov: pd.DataFrame) -> pd.DataFrame:
    return d.merge(cov, on="municipio", how="left")


# ----------------------------------------------------------------------------- échantillon et MDE

def part_sample(args) -> None:
    d = mun_age_panel()
    cov = covariates(pd.read_parquet(PROC / "co_outcomes_mun_age.parquet"))
    a = aggregate(d, GROUPS, "15-49")
    a2539 = aggregate(d, G2539, "25-39")
    rows = []
    for name, sub, unit in (("H1 municipio 15-49", a, "unit"), ("H2b municipio 25-39", a2539, "unit")) + tuple((f"H2 municipio {g}", d[d.age_group == g], "unit") for g in GROUPS):
        sub = did.drop_always_treated(sub, "year", "cohort", MIN_PRE)
        rows.append({"spécification": name, "unités": sub[unit].nunique(), "années": f"{sub.year.min()}-{sub.year.max()}", "unités-années": len(sub),
                     "unités traitées": sub[sub.cohort > 0][unit].nunique(), "jamais traitées": sub[sub.cohort == 0][unit].nunique(),
                     "cohortes": f"{int(sub[sub.cohort > 0].cohort.min())}-{int(sub[sub.cohort > 0].cohort.max())}"})
    ac = with_covs(a, cov).dropna(subset=COVS)
    rows.append({"spécification": "H1 municipio 15-49 avec covariables", "unités": ac.unit.nunique(), "années": f"{ac.year.min()}-{ac.year.max()}", "unités-années": len(ac),
                 "unités traitées": ac[ac.cohort > 0].unit.nunique(), "jamais traitées": ac[ac.cohort == 0].unit.nunique(), "cohortes": "2016-2023"})
    t = pd.DataFrame(rows)
    t.to_csv(TABLES / "t_sample_co.csv", index=False)
    mde = []
    for name, sub in (("H1 municipio 15-49", a), ("H2b municipio 25-39", a2539)) + tuple((f"H2 municipio {g}", d[d.age_group == g]) for g in GROUPS):
        sub = did.drop_always_treated(sub, "year", "cohort", MIN_PRE)
        r = did.mde_permutation(sub, "y_log", "unit", "year", "cohort", n_perm=20 if args.fast else 200, seed=1)
        mde.append({"hypothèse": name, "sd placebo": r["sd_placebo"], "MDE (80 %, 5 %) en log ≈ %": r["mde"], "permutations": r["n_perm_ok"], "moyenne placebo": r["placebo_mean"]})
        log(f"  MDE {name} : {100 * r['mde']:.2f} % ({r['n_perm_ok']} permutations)")
    m = pd.DataFrame(mde)
    m.to_csv(TABLES / "t_mde_co.csv", index=False)
    lines = ["# Colombie — échantillons et MDE (généré par scripts/11_co_estimate.py --part sample)", "",
             f"Municipios censurés à gauche (4G ≥ 50 % dès 2015-T4) exclus : {int(static().censored_4g_50.sum())}. Règle « ≥ 3 ans de pré-période » appliquée.", "",
             t.to_markdown(index=False), "", "MDE par permutation des cohortes (80 %, 5 %), TWFE statique sur log(naissances + 0,5 / 1 000 femmes) :", "",
             m.to_markdown(index=False, floatfmt=".4f")]
    (TABLES / "t_sample_co.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (TABLES / "t_mde_co.md").write_text(m.to_markdown(index=False, floatfmt=".4f") + "\n", encoding="utf-8")
    log("\n".join(lines))


# ----------------------------------------------------------------------------- parties

def part_h1(args) -> None:
    col = e5.Collector("h1")
    d = mun_age_panel()
    cov = covariates(pd.read_parquet(PROC / "co_outcomes_mun_age.parquet"))
    a = with_covs(aggregate(d, GROUPS, "15-49"), cov)
    ac = a.dropna(subset=COVS)
    log(f"H1 : {a.unit.nunique():,} municipios, avec covariables {ac.unit.nunique():,}")
    e5.run_block(col, ac, "y_log", "H1", "H1", Y_ALL, "primaire : municipios avec covariables", "unit", covs=COVS, boot=args.boot, nboot_cluster=args.nboot,
                 estimators=("cs",), notes="spécification primaire (A4) ; municipios censurés à gauche exclus", balanced_post=True)
    e5.run_block(col, ac, "y_log", "H1", "H1", Y_ALL, "municipios avec covariables, comparaisons", "unit", covs=COVS, estimators=("sunab", "did2s", "twfe"),
                 poisson=("births", "women"), notes="comparaisons de la spécification primaire")
    e5.run_block(col, a, "y_log", "H1", "H1", Y_ALL, "tous municipios, sans covariables", "unit", boot=args.boot, poisson=("births", "women"))
    e5.run_block(col, ac, "y_log", "H1", "H1", Y_ALL, "covariables, contrôle = jamais traités", "unit", covs=COVS, control="never_treated", estimators=("cs",))
    for y, lab in (("y_rate", "naissances / 1 000 f. 15-49 (taux brut)"), ("y_asinh", "asinh(taux)")):
        e5.run_block(col, ac, y, "H1", "H1", lab, "municipios avec covariables", "unit", covs=COVS, estimators=("cs",))
    e5.run_block(col, ac, "y_log", "H1", "H1", Y_ALL, "municipios avec covariables, référence −2 (anticipation = 1)", "unit", covs=COVS, estimators=("cs",),
                 anticipation=1, exploratory=True, notes="complément A2 : année −1 partiellement exposée")
    e5.run_block(col, ac, "y_log", "H1", "H1", Y_ALL, "municipios avec covariables, régression de résultat seule (est_method = reg)", "unit", covs=COVS,
                 estimators=("cs",), est_method="reg", exploratory=True, notes="complément A2")
    col.save()


def part_h2(args) -> None:
    col = e5.Collector("h2")
    d = mun_age_panel()
    cov = covariates(pd.read_parquet(PROC / "co_outcomes_mun_age.parquet"))
    a2539 = with_covs(aggregate(d, G2539, "25-39"), cov).dropna(subset=COVS)
    a1524 = with_covs(aggregate(d, G1524, "15-24"), cov).dropna(subset=COVS)
    samp = "municipios avec covariables, bascule 4G ≥ 50 %"
    r = e5.run_block(col, a2539, "y_log", "H2", "H2b", Y_2539, samp, "unit", covs=COVS, boot=args.boot, nboot_cluster=args.nboot, poisson=("births", "women"),
                     notes="test primaire du papier (Colombie)", balanced_post=True)
    e5.run_block(col, a2539, "y_log", "H2", "H2b", Y_2539, "municipios, sans covariables", "unit", estimators=("cs", "twfe"))
    for y, lab in (("y_rate", "naissances / 1 000 f. 25-39 (taux brut)"), ("y_asinh", "asinh(naissances / 1 000 f. 25-39)")):
        e5.run_block(col, a2539, y, "H2", "H2b", lab, samp, "unit", covs=COVS, estimators=("cs",))
    e5.run_block(col, a2539, "y_log", "H2", "H2b", Y_2539, samp + ", référence −2 (anticipation = 1)", "unit", covs=COVS, estimators=("cs",), anticipation=1, exploratory=True)
    fam_a, fam_c = [], []
    for g in GROUPS:
        sub = with_covs(d[d.age_group == g], cov).dropna(subset=COVS)
        hyp = "H2a" if g in G1524 else "H2c"
        rg = e5.run_block(col, sub, "y_log", "H2", hyp, f"log(naissances+0,5 / 1 000 f. {g})", samp, "unit", covs=COVS, poisson=("births", "women"))
        if "cs" in rg:
            (fam_a if g in G1524 else fam_c).append(e5._member(rg, f"log(naissances+0,5 / 1 000 f. {g})", sub, "municipio"))
    e5.holm_family(col, "H2", "H2c", samp, fam_c, "25-29, 30-34, 35-39, 40-49")
    e5.holm_family(col, "H2", "H2a", samp, fam_a, "15-19, 20-24")
    r1 = e5.run_block(col, a1524, "y_log", "H2", "H2d", "log(naissances+0,5 / 1 000 f. 15-24)", samp, "unit", covs=COVS, estimators=("cs",))
    if "cs" in r and "cs" in r1:
        p1, p2 = r1["cs"]["post_avg"].iloc[0], r["cs"]["post_avg"].iloc[0]
        base = with_covs(d[d.age_group.isin(G1524 + G2539)], cov).dropna(subset=COVS)

        def stat(b):
            x1, x2 = aggregate(b, G1524, "15-24"), aggregate(b, G2539, "25-39")
            x1, x2 = with_covs(x1, cov), with_covs(x2, cov)
            return did.cs_post_avg(x1, "y_log", "unit", "year", "cohort", covariates=COVS) - did.cs_post_avg(x2, "y_log", "unit", "year", "cohort", covariates=COVS)

        bs = did.cluster_bootstrap(base, "municipio", stat, n_boot=args.nboot, seed=1, strata="cohort")
        col.add_scalar("H2", "H2d", "ATT 15-24 − ATT 25-39", samp, "cs", "différence (bootstrap conjoint)", float(p1.estimate - p2.estimate), bs["se_boot"],
                       base.municipio.nunique(), len(base), f"bootstrap par municipio stratifié par cohorte, {bs['n_boot_ok']} tirages ; quantiles [{bs['q025']:+.4f}, {bs['q975']:+.4f}]",
                       aggregation="difference")
    col.save()


def part_h3(args) -> None:
    col = e5.Collector("h3")
    d = mun_age_panel()
    cov = covariates(pd.read_parquet(PROC / "co_outcomes_mun_age.parquet"))
    samp = "municipios avec covariables, bascule 4G ≥ 50 %"
    col.add_scalar("H3", "H3a", "mariages / PACS / parts en couple", "municipio", "—", "non testable", np.nan, np.nan, 0, 0,
                   "aucune série de mariages par municipio × âge en Colombie (A4) ; H3a et H3c non testés", aggregation="note")
    res = {}
    for g, sub in (("25-39", aggregate(d, G2539, "25-39")), ("15-24", aggregate(d, G1524, "15-24"))):
        sub = with_covs(sub, cov).dropna(subset=COVS)
        res[g] = e5.run_block(col, sub, "y_union", "H3", "H3b", f"log(naissances de mères en union+0,5 / 1 000 f. {g})", samp, "unit", covs=COVS,
                              estimators=("cs", "twfe"), boot=args.boot if g == "25-39" else 0,
                              notes="H3b (A4) : mères mariées ou en union libre ; dénominateur = toutes les femmes (pas de femmes en union par âge au municipio)")
        e5.run_block(col, sub, "y_nonunion", "H3", "H3b complément", f"log(naissances de mères hors union+0,5 / 1 000 f. {g})", samp, "unit", covs=COVS, estimators=("cs",),
                     exploratory=True)
        sub["share_union"] = sub.births_union / sub.births_civ_known.where(sub.births_civ_known > 0)
        e5.run_block(col, sub.dropna(subset=["share_union"]), "share_union", "H3", "H3b complément", f"part des naissances de mères en union, {g}", samp, "unit", covs=COVS,
                     estimators=("cs",), exploratory=True)
    col.save()


def part_h5(args) -> None:
    col = e5.Collector("h5")
    d = mun_age_panel()
    cov = covariates(pd.read_parquet(PROC / "co_outcomes_mun_age.parquet"))
    a = with_covs(aggregate(d, GROUPS, "15-49"), cov).dropna(subset=COVS)
    f = a.copy()
    f["true_cohort"] = f.cohort
    f = f[(f.true_cohort == 0) | (f.year < f.true_cohort)].copy()
    f["cohort"] = np.where(f.true_cohort > 0, f.true_cohort - 3, 0)
    pl = "placebo : aucun effet attendu ; périodes relatives fictives ≤ +2"
    e5.run_block(col, f, "y_log", "H5", "H5a", Y_ALL, "municipio, bascule fictive −3 ans, années pré-traitement seules", "unit", covs=COVS, estimators=("cs", "twfe"),
                 notes=pl, balance=False)
    col.add_scalar("H5", "H5b", "décès pour 1 000 habitants", "municipio", "—", "non construit", np.nan, np.nan, 0, 0,
                   "décès EEVV non téléchargés à ce stade (A4)", aggregation="note")
    e5.run_block(col, a, "y_log", "H5", "H5c", Y_ALL, "primaire : municipios avec covariables", "unit", covs=COVS, estimators=("cs",),
                 notes="H5c sur la spécification primaire (même estimation que H1)")
    e5.run_block(col, a, "y_log", "H5", "H5c", Y_ALL, "municipios avec covariables sans la tendance 2010-2014", "unit", covs=[c for c in COVS if c != "pretrend_1014"],
                 estimators=("cs",), notes="H5c sans la tendance de pré-période")
    a2539 = with_covs(aggregate(d, G2539, "25-39"), cov).dropna(subset=COVS)
    e5.run_block(col, a2539, "y_log", "H5", "H5c", Y_2539, "municipios avec covariables (H2b)", "unit", covs=COVS, estimators=("cs",), notes="H5c sur H2b")
    col.save()


def part_h6(args) -> None:
    col = e5.Collector("h6")
    d = mun_age_panel()
    cov = covariates(pd.read_parquet(PROC / "co_outcomes_mun_age.parquet"))
    a = with_covs(aggregate(d, GROUPS, "15-49"), cov).dropna(subset=COVS)
    fam = []

    def sub_block(sub, label, y="y_log", outcome=Y_ALL):
        r = e5.run_block(col, sub, y, "H6", "H6", outcome, label, "unit", covs=COVS, estimators=("cs",), notes="spécification primaire sur le sous-groupe")
        if "cs" in r:
            fam.append(e5._member(r, outcome + " — " + label, sub, "unit"))

    for var, name in (("share_cab", "part de population en cabecera 2015 (densité)"), ("pop_total", "population 2015")):
        q = a.drop_duplicates("municipio")[var].quantile([1 / 3, 2 / 3]).values
        a["_ter"] = a[var].map(lambda x: 1 if x <= q[0] else 2 if x <= q[1] else 3)
        for k in (1, 2, 3):
            sub_block(a[a._ter == k], f"{name} : tercile {k}")
    sub_block(a, "rang 1", "y_rank1", "log(naissances de rang 1+0,5 / 1 000 f. 15-49)")
    sub_block(a, "rang 2 et plus", "y_rank2", "log(naissances de rang 2++0,5 / 1 000 f. 15-49)")
    e5.holm_family(col, "H6", "H6", "municipios avec covariables", fam, f"les {len(fam)} sous-groupes H6")
    col.save()


def part_robust(args) -> None:
    col = e5.Collector("robust")
    d = mun_age_panel()
    cov = covariates(pd.read_parquet(PROC / "co_outcomes_mun_age.parquet"))
    a = with_covs(aggregate(d, GROUPS, "15-49"), cov).dropna(subset=COVS)
    kw = dict(covs=COVS, estimators=("cs",))
    e5.run_block(col, a[a.year >= 2008], "y_log", "robustesse", "H1", Y_ALL, "fenêtre 2008-2024", "unit", **kw)
    e5.run_block(col, a[a.year <= 2019], "y_log", "robustesse", "H1", Y_ALL, "fenêtre 1998-2019 (hors COVID) ; cohortes 2020-2023 = contrôle", "unit", **kw)
    e5.run_block(col, a[~a.year.isin([2020, 2021])], "y_log", "robustesse", "H1", Y_ALL, "sans 2020-2021", "unit", **kw)
    e5.run_block(col, a, "y_log", "robustesse", "H1", Y_ALL, "grappes = departamento", "unit", cluster="dep", covs=COVS, estimators=("cs", "twfe"))
    e5.run_block(col, a, "y_log", "robustesse", "H1", Y_ALL, "pondéré par les femmes 15-49 (2015), CS sans covariables", "unit", estimators=("cs",), weights="women",
                 exploratory=True, notes="pondération (A2)")
    for ccol, cen, lab in (("cohort_4g_90", "censored_4g_90", "traitement = 4G ≥ 90 % de la population"), ("cohort_4g_cab", "censored_4g_50", "traitement = 4G à la cabecera"),
                           ("cohort_3g_50", "censored_3g_50", "traitement = 3G ≥ 50 % (robustesse)")):
        dd = with_covs(aggregate(mun_age_panel(ccol, cen), GROUPS, "15-49"), cov).dropna(subset=COVS)
        e5.run_block(col, dd, "y_log", "robustesse", "H1" if "3G" not in lab else "3G", Y_ALL, lab, "unit", **kw)
    dd = mun_age_panel(drop_censored=False)
    dd.loc[dd.censored_4g_50.astype(bool), "cohort"] = 2015
    dd = with_covs(aggregate(dd, GROUPS, "15-49"), cov).dropna(subset=COVS)
    e5.run_block(col, dd, "y_log", "robustesse", "H1", Y_ALL, "municipios censurés inclus avec cohorte 2015 (borne haute)", "unit", exploratory=True, **kw)
    a2539 = with_covs(aggregate(d, G2539, "25-39"), cov).dropna(subset=COVS)
    e5.run_block(col, a2539[~a2539.year.isin([2020, 2021])], "y_log", "robustesse", "H2b", Y_2539, "sans 2020-2021", "unit", **kw)
    e5.run_block(col, a2539[a2539.year >= 2008], "y_log", "robustesse", "H2b", Y_2539, "fenêtre 2008-2024", "unit", **kw)
    col.save()


def part_summary(args) -> None:
    files = sorted(p for p in e5.EST.glob("*.csv") if not p.name.startswith("_"))
    if not files:
        return
    allr = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    out_dir = e5.EST if "smoke" in e5.EST.name else TABLES
    allr.to_csv(out_dir / "est_co_all.csv", index=False)
    key = allr[allr.aggregation.isin(e5.KEY_AGGS)]
    lines = ["# Estimations Colombie — synthèse (généré par scripts/11_co_estimate.py --part summary)", "",
             "Toutes les estimations : `tables/est_co_all.csv`. Mêmes conventions que la France (`t_estimates_fr.md`). Unité = municipio ; "
             "municipios censurés à gauche (4G ≥ 50 % dès 2015-T4) exclus du primaire (A4).", ""]
    for fam, g in key.groupby("family", sort=False):
        lines += [f"## {fam}", "", "| hyp. | résultat | échantillon | estimateur | terme | estimation | es | IC 95 % | p | n unités | n obs | expl. | notes |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in g.iterrows():
            ci = f"[{r.ci_low:+.4f}, {r.ci_high:+.4f}]" if np.isfinite(r.ci_low) else ""
            pv = f"{r.p:.3f}" if np.isfinite(r.p) else ""
            est = f"{r.estimate:+.4f}" if np.isfinite(r.estimate) else ""
            se = f"{r.se:.4f}" if np.isfinite(r.se) else ""
            lines.append(f"| {r.hypothesis} | {r.outcome} | {r['sample']} | {r.estimator} | {r.term} | {est} | {se} | {ci} | {pv} | {r.n_units:,} | {r.n_obs:,} | "
                         f"{'oui' if r.exploratory else ''} | {str(r.notes)[:220]} |")
        lines.append("")
    (out_dir / "t_estimates_co.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "commit": e5._git_rev(), "args": vars(args), "n_rows": int(len(allr)),
                "inputs": {p.name: time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime)) for p in sorted(PROC.glob("co_*.parquet"))}}
    (e5.EST / "_run.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"synthèse : {len(key)} lignes clés, {len(allr)} coefficients")


PARTS = {"sample": part_sample, "h1": part_h1, "h2": part_h2, "h3": part_h3, "h5": part_h5, "h6": part_h6, "robust": part_robust, "summary": part_summary}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--part", nargs="+", default=["all"])
    ap.add_argument("--boot", type=int, default=999)
    ap.add_argument("--nboot", type=int, default=50)
    ap.add_argument("--fast", action="store_true")
    a = ap.parse_args()
    if a.fast:
        a.boot, a.nboot = 49, 3
    e5.EST = TABLES / ("est_co_smoke" if a.fast else "est_co")
    parts = list(PARTS) if a.part == ["all"] else a.part
    for p in parts:
        if p not in PARTS:
            raise SystemExit(f"partie inconnue : {p}")
        log(f"=== partie {p}")
        PARTS[p](a)
    if "summary" not in parts and a.part == ["all"]:
        part_summary(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
