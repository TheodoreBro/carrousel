#!/usr/bin/env python
"""Brésil et Espagne — échantillon, MDE et estimations (préregistration §3, §5 ; addenda A5 et A6), avec les mêmes fonctions que la
France et la Colombie (``05_estimate.py`` : run_block, Collector, familles de Holm ; ``common/did.py``). Un seul pilote paramétré
par pays (CONFIGS) : unité = município/municipio × groupe d'âge, résultat = log(naissances + 0,5 pour 1 000 femmes), grappes = unité
géographique.

Usage :
    python scripts/15_estimate_country.py --country BR --part sample     # échantillon et MDE (avant toute estimation)
    python scripts/15_estimate_country.py --country BR --part all        # sample h1 h2 h3 h5 h6 robust summary
    python scripts/15_estimate_country.py --country ES --part h2 --fast  # vérification (tables/est_es_smoke)

Sorties : tables/est_<pays>/<partie>.csv, tables/est_<pays>_all.csv, tables/t_estimates_<pays>.md, t_sample_<pays>.md, t_mde_<pays>.md.
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
GROUPS, G2539, G1524 = e5.GROUPS, e5.G2539, e5.G1524
MIN_PRE = 3
log = e5.log

CONFIGS = {
    "BR": dict(
        name="Brésil", tag="br", addendum="A5", unit_name="município", cluster_alt=("uf", "grappes = UF (27)"),
        years=(2003, 2024), cohort_col="cohort_4g_1", censored_col="censored_4g_1",
        cohorts_label="2014-2023", first_year_note="cohorte 2014 = première observation utilisable (A5)",
        # covariables de pré-période (A5) : log population 2010, part des femmes 15-49 en 2010, niveau et pente 2008-2013 du log du taux
        cov_static=[("log_pop", "pop_2010", "log"), ("share_women_1549", "share_women_1549_2010", None)],
        pre_window=(2008, 2013), covs=["log_pop", "share_women_1549", "level_pre", "pretrend_pre"],
        marriages=dict(start=2013, note="H3a (A5) : mariages homme-femme par âge de l'épouse, IBGE table 4412, fenêtre 2013-2024 (pré-période courte)"),
        married_births=None, rank=False,
        h6=[("pop_2010", "population 2010", "tercile"), ("region", "grande région", "category")],
        robust_windows=[((2008, 2024), "fenêtre 2008-2024"), ((2003, 2023), "fenêtre 2003-2023 (sans l'année provisoire 2024)"),
                        ((2003, 2019), "fenêtre 2003-2019 (hors COVID) ; cohortes 2020-2023 = contrôle")],
        robust_cohorts=[("cohort_4g_2", "censored_4g_1", "traitement = 4G par ≥ 2 opérateurs", "H1"),
                        ("cohort_3g_1", "censored_3g_1", "traitement = 3G ≥ 1 opérateur (censurés au 2013-12 exclus)", "3G")],
        robust_drop_first=("cohort 2014 exclue (première observation utilisable 2014-12, A5)", 2014),
        weights="women", placebo_shift=3,
    ),
    "ES": dict(
        name="Espagne", tag="es", addendum="A6", unit_name="municipio (> 10 000 habitants)", cluster_alt=("prov", "grappes = province (52)"),
        years=(2007, 2022), cohort_col="cohort_lte_50", censored_col="censored_lte_50",
        cohorts_label="2013-2016", first_year_note="cohorte 2013 = premier instantané (déc. 2013), gardée en primaire (A6)",
        cov_static=[("log_pop", "pop_2013", "log"), ("share_women_1549", "share_women_1549_2013", None), ("share_foreign", "share_foreign_1012", None)],
        pre_window=(2008, 2012), covs=["log_pop", "share_women_1549", "share_foreign", "pretrend_pre"],
        marriages=dict(start=2008, note="H3a (A6) : mariages de femmes (couples homme-femme) par âge, INE microdonnées, fenêtre 2008-2022"),
        married_births=dict(col="births_married", label="mères mariées", note="H3b (A6) : mères mariées (l'union libre n'est pas distinguée) ; dénominateur = toutes les femmes"),
        rank=True,
        h6=[("pop_2013", "population 2013", "tercile")],
        robust_windows=[((2007, 2019), "fenêtre 2007-2019 (hors COVID)")],
        robust_cohorts=[("cohort_lte_90", "censored_lte_90", "traitement = LTE ≥ 90 % de la population", "H1")],
        robust_drop_first=("cohorte 2013 exclue (premier instantané, A6)", 2013),
        weights="women", placebo_shift=3,
    ),
}
CFG: dict = {}
Y_ALL = "log(naissances+0,5 / 1 000 f. 15-49)"
Y_2539 = "log(naissances+0,5 / 1 000 f. 25-39)"


# ----------------------------------------------------------------------------- panels

def static() -> pd.DataFrame:
    t = pd.read_parquet(PROC / f"{CFG['tag']}_treatment_static.parquet")
    s = pd.read_parquet(PROC / f"{CFG['tag']}_static.parquet")
    dup = [c for c in s.columns if c != "municipio" and c in t.columns]
    return t.merge(s.drop(columns=dup), on="municipio", how="inner")


def outcomes() -> pd.DataFrame:
    return pd.read_parquet(PROC / f"{CFG['tag']}_outcomes_mun_age.parquet")


def covariates(oc: pd.DataFrame) -> pd.DataFrame:
    st = static().set_index("municipio")
    cov = pd.DataFrame(index=st.index)
    for name, col, tr in CFG["cov_static"]:
        cov[name] = np.log(st[col]) if tr == "log" else st[col]
    y0, y1 = CFG["pre_window"]
    m = oc.groupby(["municipio", "year"], as_index=False)[["births", "women"]].sum()
    pre = m[m.year.between(y0, y1)].assign(y=lambda d: np.log((d.births + 0.5) / d.women * 1000)).pivot(index="municipio", columns="year", values="y")
    X = np.array(pre.columns, float) - np.mean(pre.columns)
    L = pre.values
    ok = np.isfinite(L)
    lbar = np.nanmean(np.where(ok, L, np.nan), axis=1)
    num = np.nansum(X[None, :] * (np.where(ok, L, np.nan) - lbar[:, None]), axis=1)
    den = np.where(ok, X[None, :] ** 2, 0).sum(1)
    cov["level_pre"] = pd.Series(lbar, index=pre.index).reindex(cov.index)
    cov["pretrend_pre"] = pd.Series(num / den, index=pre.index).reindex(cov.index)
    return cov.reset_index()


def mun_age_panel(cohort_col: str | None = None, censored_col: str | None = None, drop_censored: bool = True, years=None) -> pd.DataFrame:
    cohort_col = cohort_col or CFG["cohort_col"]
    censored_col = censored_col or CFG["censored_col"]
    years = years or CFG["years"]
    oc = outcomes()
    st = static()
    keep = ["municipio", cohort_col, censored_col] + [c for c in ("region", "uf", "prov", "pop_2010", "pop_2013") if c in st.columns and c not in oc.columns]
    d = oc.merge(st[keep], on="municipio", how="inner")
    d = d[d.year.between(*years) & (d.women > 0)].copy()
    if drop_censored:
        d = d[~d[censored_col].astype(bool)]
    d["cohort"] = d[cohort_col].fillna(0).astype(int)
    d["y_log"] = np.log((d.births + 0.5) / d.women * 1000)
    d["y_rate"] = d.births / d.women * 1000
    d["y_asinh"] = np.arcsinh(d.y_rate)
    if "marriages" in d:
        d["y_marr"] = np.log((d.marriages + 0.5) / d.women * 1000)
    if CFG["married_births"]:
        c = CFG["married_births"]["col"]
        d["y_married"] = np.log((d[c] + 0.5) / d.women * 1000)
        d["y_unmarried"] = np.log((d.births_civ_known - d[c] + 0.5) / d.women * 1000)
    if CFG["rank"]:
        d["y_rank1"] = np.log((d.births_rank1 + 0.5) / d.women * 1000)
        d["y_rank2"] = np.log((d.births_rank_known - d.births_rank1 + 0.5) / d.women * 1000)
    d["unit"] = d.municipio + "_" + d.age_group
    if "uf" not in d and "prov" not in d:
        d["uf"] = d.municipio.str[:2]
    return d


SUM_COLS = ["births", "women", "marriages", "births_married", "births_civ_known", "births_rank1", "births_rank_known"]


def aggregate(d: pd.DataFrame, groups: list[str], label: str) -> pd.DataFrame:
    keys = ["municipio", "year", "cohort"] + [c for c in ("region", "uf", "prov") if c in d.columns]
    sums = {c: (c, "sum") for c in SUM_COLS if c in d.columns}
    firsts = {c: (c, "first") for c in ("pop_2010", "pop_2013") if c in d.columns}
    s = d[d.age_group.isin(groups)].groupby(keys, as_index=False).agg(**sums, **firsts)
    s["age_group"] = label
    s["y_log"] = np.log((s.births + 0.5) / s.women * 1000)
    s["y_rate"] = s.births / s.women * 1000
    s["y_asinh"] = np.arcsinh(s.y_rate)
    if "marriages" in s:
        s["y_marr"] = np.log((s.marriages + 0.5) / s.women * 1000)
    if "births_married" in s:
        s["y_married"] = np.log((s.births_married + 0.5) / s.women * 1000)
        s["y_unmarried"] = np.log((s.births_civ_known - s.births_married + 0.5) / s.women * 1000)
    if "births_rank1" in s:
        s["y_rank1"] = np.log((s.births_rank1 + 0.5) / s.women * 1000)
        s["y_rank2"] = np.log((s.births_rank_known - s.births_rank1 + 0.5) / s.women * 1000)
    s["unit"] = s.municipio + "_" + label
    return s


def with_covs(d: pd.DataFrame, cov: pd.DataFrame) -> pd.DataFrame:
    dup = [c for c in cov.columns if c != "municipio" and c in d.columns]
    return d.drop(columns=dup).merge(cov, on="municipio", how="left")


def _base(args):
    d = mun_age_panel()
    cov = covariates(outcomes())
    covs = CFG["covs"]
    a = with_covs(aggregate(d, GROUPS, "15-49"), cov)
    return d, cov, covs, a, a.dropna(subset=covs)


# ----------------------------------------------------------------------------- échantillon et MDE

def part_sample(args) -> None:
    d, cov, covs, a, ac = _base(args)
    a2539 = aggregate(d, G2539, "25-39")
    tag, name = CFG["tag"], CFG["name"]
    rows = []
    for lab, sub in ((f"H1 {CFG['unit_name'].split(' ')[0]} 15-49", a), (f"H2b {CFG['unit_name'].split(' ')[0]} 25-39", a2539)) + \
            tuple((f"H2 {CFG['unit_name'].split(' ')[0]} {g}", d[d.age_group == g]) for g in GROUPS):
        sub = did.drop_always_treated(sub, "year", "cohort", MIN_PRE)
        rows.append({"spécification": lab, "unités": sub.unit.nunique(), "années": f"{sub.year.min()}-{sub.year.max()}", "unités-années": len(sub),
                     "unités traitées": sub[sub.cohort > 0].unit.nunique(), "jamais traitées": sub[sub.cohort == 0].unit.nunique(),
                     "cohortes": f"{int(sub[sub.cohort > 0].cohort.min())}-{int(sub[sub.cohort > 0].cohort.max())}"})
    rows.append({"spécification": "H1 avec covariables", "unités": ac.unit.nunique(), "années": f"{ac.year.min()}-{ac.year.max()}", "unités-années": len(ac),
                 "unités traitées": ac[ac.cohort > 0].unit.nunique(), "jamais traitées": ac[ac.cohort == 0].unit.nunique(), "cohortes": CFG["cohorts_label"]})
    t = pd.DataFrame(rows)
    t.to_csv(TABLES / f"t_sample_{tag}.csv", index=False)
    mde = []
    for lab, sub in ((f"H1 15-49", a), (f"H2b 25-39", a2539)) + tuple((f"H2 {g}", d[d.age_group == g]) for g in GROUPS):
        sub = did.drop_always_treated(sub, "year", "cohort", MIN_PRE)
        r = did.mde_permutation(sub, "y_log", "unit", "year", "cohort", n_perm=20 if args.fast else 200, seed=1)
        mde.append({"hypothèse": lab, "sd placebo": r["sd_placebo"], "MDE (80 %, 5 %) en log ≈ %": r["mde"], "permutations": r["n_perm_ok"], "moyenne placebo": r["placebo_mean"]})
        log(f"  MDE {lab} : {100 * r['mde']:.2f} % ({r['n_perm_ok']} permutations)")
    m = pd.DataFrame(mde)
    m.to_csv(TABLES / f"t_mde_{tag}.csv", index=False)
    lines = [f"# {name} — échantillons et MDE (généré par scripts/15_estimate_country.py --country {args.country} --part sample)", "",
             f"Unité = {CFG['unit_name']} ; cohorte = `{CFG['cohort_col']}` ({CFG['first_year_note']}) ; censurés exclus : {int(static()[CFG['censored_col']].sum())}. "
             "Règle « ≥ 3 ans de pré-période » appliquée.", "", t.to_markdown(index=False), "",
             "MDE par permutation des cohortes (80 %, 5 %), TWFE statique sur log(naissances + 0,5 / 1 000 femmes) :", "", m.to_markdown(index=False, floatfmt=".4f")]
    (TABLES / f"t_sample_{tag}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (TABLES / f"t_mde_{tag}.md").write_text(m.to_markdown(index=False, floatfmt=".4f") + "\n", encoding="utf-8")
    log("\n".join(lines))


# ----------------------------------------------------------------------------- parties

def part_h1(args) -> None:
    col = e5.Collector("h1")
    d, cov, covs, a, ac = _base(args)
    log(f"H1 : {a.unit.nunique():,} unités, avec covariables {ac.unit.nunique():,}")
    e5.run_block(col, ac, "y_log", "H1", "H1", Y_ALL, "primaire : unités avec covariables", "unit", covs=covs, boot=args.boot, nboot_cluster=args.nboot,
                 estimators=("cs",), notes=f"spécification primaire ({CFG['addendum']})", balanced_post=True)
    e5.run_block(col, ac, "y_log", "H1", "H1", Y_ALL, "unités avec covariables, comparaisons", "unit", covs=covs, estimators=("sunab", "did2s", "twfe"),
                 poisson=("births", "women"), notes="comparaisons de la spécification primaire")
    e5.run_block(col, a, "y_log", "H1", "H1", Y_ALL, "toutes unités, sans covariables", "unit", boot=args.boot, poisson=("births", "women"))
    if (ac.cohort == 0).any():
        e5.run_block(col, ac, "y_log", "H1", "H1", Y_ALL, "covariables, contrôle = jamais traités", "unit", covs=covs, control="never_treated", estimators=("cs",))
    else:
        col.add_scalar("H1", "H1", Y_ALL, "covariables, contrôle = jamais traités", "cs", "non estimable", np.nan, np.nan, 0, 0,
                       "aucune unité jamais traitée sur la fenêtre : contrôle = pas encore traités seulement", aggregation="note")
    for y, lab in (("y_rate", "naissances / 1 000 f. 15-49 (taux brut)"), ("y_asinh", "asinh(taux)")):
        e5.run_block(col, ac, y, "H1", "H1", lab, "unités avec covariables", "unit", covs=covs, estimators=("cs",))
    e5.run_block(col, ac, "y_log", "H1", "H1", Y_ALL, "unités avec covariables, référence −2 (anticipation = 1)", "unit", covs=covs, estimators=("cs",),
                 anticipation=1, exploratory=True, notes="complément A2 : année −1 partiellement exposée")
    e5.run_block(col, ac, "y_log", "H1", "H1", Y_ALL, "unités avec covariables, régression de résultat seule (est_method = reg)", "unit", covs=covs,
                 estimators=("cs",), est_method="reg", exploratory=True, notes="complément A2")
    col.save()


SAMP = "unités avec covariables, bascule 4G"


def part_h2(args) -> None:
    col = e5.Collector("h2")
    d, cov, covs, a, ac = _base(args)
    a2539 = with_covs(aggregate(d, G2539, "25-39"), cov).dropna(subset=covs)
    a1524 = with_covs(aggregate(d, G1524, "15-24"), cov).dropna(subset=covs)
    r = e5.run_block(col, a2539, "y_log", "H2", "H2b", Y_2539, SAMP, "unit", covs=covs, boot=args.boot, nboot_cluster=args.nboot, poisson=("births", "women"),
                     notes=f"test primaire du papier ({CFG['name']})", balanced_post=True)
    e5.run_block(col, a2539, "y_log", "H2", "H2b", Y_2539, "unités, sans covariables", "unit", estimators=("cs", "twfe"))
    for y, lab in (("y_rate", "naissances / 1 000 f. 25-39 (taux brut)"), ("y_asinh", "asinh(naissances / 1 000 f. 25-39)")):
        e5.run_block(col, a2539, y, "H2", "H2b", lab, SAMP, "unit", covs=covs, estimators=("cs",))
    e5.run_block(col, a2539, "y_log", "H2", "H2b", Y_2539, SAMP + ", référence −2 (anticipation = 1)", "unit", covs=covs, estimators=("cs",), anticipation=1, exploratory=True)
    fam_a, fam_c = [], []
    for g in GROUPS:
        sub = with_covs(d[d.age_group == g], cov).dropna(subset=covs)
        hyp = "H2a" if g in G1524 else "H2c"
        rg = e5.run_block(col, sub, "y_log", "H2", hyp, f"log(naissances+0,5 / 1 000 f. {g})", SAMP, "unit", covs=covs, poisson=("births", "women"))
        if "cs" in rg:
            (fam_a if g in G1524 else fam_c).append(e5._member(rg, f"log(naissances+0,5 / 1 000 f. {g})", sub, "municipio"))
    e5.holm_family(col, "H2", "H2c", SAMP, fam_c, "25-29, 30-34, 35-39, 40-49")
    e5.holm_family(col, "H2", "H2a", SAMP, fam_a, "15-19, 20-24")
    r1 = e5.run_block(col, a1524, "y_log", "H2", "H2d", "log(naissances+0,5 / 1 000 f. 15-24)", SAMP, "unit", covs=covs, estimators=("cs",))
    if "cs" in r and "cs" in r1:
        p1, p2 = r1["cs"]["post_avg"].iloc[0], r["cs"]["post_avg"].iloc[0]
        base = with_covs(d[d.age_group.isin(G1524 + G2539)], cov).dropna(subset=covs)

        def stat(b):
            x1, x2 = with_covs(aggregate(b, G1524, "15-24"), cov), with_covs(aggregate(b, G2539, "25-39"), cov)
            return did.cs_post_avg(x1, "y_log", "unit", "year", "cohort", covariates=covs) - did.cs_post_avg(x2, "y_log", "unit", "year", "cohort", covariates=covs)

        bs = did.cluster_bootstrap(base, "municipio", stat, n_boot=args.nboot, seed=1, strata="cohort")
        col.add_scalar("H2", "H2d", "ATT 15-24 − ATT 25-39", SAMP, "cs", "différence (bootstrap conjoint)", float(p1.estimate - p2.estimate), bs["se_boot"],
                       base.municipio.nunique(), len(base), f"bootstrap par unité géographique stratifié par cohorte, {bs['n_boot_ok']} tirages ; quantiles [{bs['q025']:+.4f}, {bs['q975']:+.4f}]",
                       aggregation="difference")
    col.save()


def part_h3(args) -> None:
    col = e5.Collector("h3")
    d, cov, covs, a, ac = _base(args)
    res_a, res_b = {}, {}
    mr = CFG["marriages"]
    noted = False
    if mr and "marriages" in d:
        have = sorted(d[d.marriages.notna()].year.unique())
        missing = [y for y in range(mr["start"], CFG["years"][1] + 1) if y not in have]
        if missing:
            col.add_scalar("H3", "H3a", "mariages de femmes / 1 000 f.", CFG["unit_name"], "—", "non estimé", np.nan, np.nan, 0, 0,
                           f"mariages absents pour {missing[0]}-{missing[-1]} au moment de l'exécution (API IBGE indisponible, voir data_log.md) ; H3a à relancer", aggregation="note")
            mr, noted = None, True
    if mr:
        for g, grp in (("25-39", G2539), ("15-24", G1524)):
            sub = with_covs(aggregate(d[d.year >= mr["start"]], grp, g), cov).dropna(subset=covs)
            sub = sub.dropna(subset=["y_marr"])
            res_a[g] = e5.run_block(col, sub, "y_marr", "H3", "H3a", f"log(mariages de femmes+0,5 / 1 000 f. {g})", SAMP + f", fenêtre {mr['start']}-{CFG['years'][1]}", "unit",
                                    covs=covs, estimators=("cs", "twfe"), boot=args.boot if g == "25-39" else 0, notes=mr["note"])
    elif not noted:
        col.add_scalar("H3", "H3a", "mariages / PACS / parts en couple", CFG["unit_name"], "—", "non testable", np.nan, np.nan, 0, 0,
                       f"aucune série de mariages par unité × âge ({CFG['addendum']})", aggregation="note")
    mb = CFG["married_births"]
    if mb:
        for g, grp in (("25-39", G2539), ("15-24", G1524)):
            sub = with_covs(aggregate(d, grp, g), cov).dropna(subset=covs)
            res_b[g] = e5.run_block(col, sub, "y_married", "H3", "H3b", f"log(naissances de {mb['label']}+0,5 / 1 000 f. {g})", SAMP, "unit", covs=covs,
                                    estimators=("cs", "twfe"), boot=args.boot if g == "25-39" else 0, notes=mb["note"])
            e5.run_block(col, sub, "y_unmarried", "H3", "H3b complément", f"log(naissances de mères non mariées+0,5 / 1 000 f. {g})", SAMP, "unit", covs=covs,
                         estimators=("cs",), exploratory=True)
    else:
        col.add_scalar("H3", "H3b", "naissances de mères en couple", CFG["unit_name"], "—", "non testable", np.nan, np.nan, 0, 0,
                       f"pas d'état civil de la mère dans la source des naissances ({CFG['addendum']})", aggregation="note")
    col.add_scalar("H3", "H3c", "naissances par femme en couple", CFG["unit_name"], "—", "non testable", np.nan, np.nan, 0, 0,
                   f"pas de femmes en couple par âge au niveau de l'unité ({CFG['addendum']})", aggregation="note")
    # règle §6 : H3a − H3b (25-39) par bootstrap conjoint, seulement si les deux existent sur une même fenêtre
    if "25-39" in res_a and "25-39" in res_b and "cs" in res_a["25-39"] and "cs" in res_b["25-39"]:
        pa, pb = res_a["25-39"]["cs"]["post_avg"].iloc[0], res_b["25-39"]["cs"]["post_avg"].iloc[0]
        base = with_covs(d[d.age_group.isin(G2539) & (d.year >= mr["start"])], cov).dropna(subset=covs)

        def stat(b):
            x = with_covs(aggregate(b, G2539, "25-39"), cov)
            return did.cs_post_avg(x, "y_marr", "unit", "year", "cohort", covariates=covs) - did.cs_post_avg(x, "y_married", "unit", "year", "cohort", covariates=covs)

        bs = did.cluster_bootstrap(base, "municipio", stat, n_boot=args.nboot, seed=1, strata="cohort")
        col.add_scalar("§6 canal", "§6", "ATT H3a − ATT H3b (25-39)", SAMP, "cs", "différence (bootstrap conjoint)", float(pa.estimate - pb.estimate), bs["se_boot"],
                       base.municipio.nunique(), len(base), f"H3a {pa.estimate:+.4f}, H3b {pb.estimate:+.4f} ; {bs['n_boot_ok']} tirages ; quantiles [{bs['q025']:+.4f}, {bs['q975']:+.4f}]",
                       aggregation="decision")
    else:
        col.add_scalar("§6 canal", "§6", "ATT H3a − ATT H3b", CFG["unit_name"], "—", "non applicable", np.nan, np.nan, 0, 0,
                       "la règle §6 exige H3a et H3b sur la même fenêtre", aggregation="note")
    col.save()


def part_h5(args) -> None:
    col = e5.Collector("h5")
    d, cov, covs, a, ac = _base(args)
    f = ac.copy()
    f["true_cohort"] = f.cohort
    f = f[(f.true_cohort == 0) | (f.year < f.true_cohort)].copy()
    k = CFG["placebo_shift"]
    f["cohort"] = np.where(f.true_cohort > 0, f.true_cohort - k, 0)
    e5.run_block(col, f, "y_log", "H5", "H5a", Y_ALL, f"bascule fictive −{k} ans, années pré-traitement seules", "unit", covs=covs, estimators=("cs", "twfe"),
                 notes="placebo : aucun effet attendu ; périodes relatives fictives ≤ +2", balance=False)
    col.add_scalar("H5", "H5b", "décès pour 1 000 habitants", CFG["unit_name"], "—", "non construit", np.nan, np.nan, 0, 0,
                   f"décès non téléchargés à ce stade ({CFG['addendum']})", aggregation="note")
    e5.run_block(col, ac, "y_log", "H5", "H5c", Y_ALL, "primaire : unités avec covariables", "unit", covs=covs, estimators=("cs",),
                 notes="H5c sur la spécification primaire (même estimation que H1)")
    e5.run_block(col, ac, "y_log", "H5", "H5c", Y_ALL, "unités avec covariables sans la tendance de pré-période", "unit", covs=[c for c in covs if c != "pretrend_pre"],
                 estimators=("cs",), notes="H5c sans la tendance de pré-période")
    a2539 = with_covs(aggregate(d, G2539, "25-39"), cov).dropna(subset=covs)
    e5.run_block(col, a2539, "y_log", "H5", "H5c", Y_2539, "unités avec covariables (H2b)", "unit", covs=covs, estimators=("cs",), notes="H5c sur H2b")
    col.save()


def part_h6(args) -> None:
    col = e5.Collector("h6")
    d, cov, covs, a, ac = _base(args)
    fam = []

    def sub_block(sub, label, y="y_log", outcome=Y_ALL):
        r = e5.run_block(col, sub, y, "H6", "H6", outcome, label, "unit", covs=covs, estimators=("cs",), notes="spécification primaire sur le sous-groupe")
        if "cs" in r:
            fam.append(e5._member(r, outcome + " — " + label, sub, "unit"))

    for var, name, kind in CFG["h6"]:
        if kind == "tercile":
            q = ac.drop_duplicates("municipio")[var].quantile([1 / 3, 2 / 3]).values
            ac["_ter"] = ac[var].map(lambda x: 1 if x <= q[0] else 2 if x <= q[1] else 3)
            for k in (1, 2, 3):
                sub_block(ac[ac._ter == k], f"{name} : tercile {k}")
        else:
            for v in sorted(ac[var].dropna().unique()):
                sub_block(ac[ac[var] == v], f"{name} : {v}")
    if CFG["rank"]:
        sub_block(ac, "rang 1", "y_rank1", "log(naissances de rang 1+0,5 / 1 000 f. 15-49)")
        sub_block(ac, "rang 2 et plus", "y_rank2", "log(naissances de rang 2++0,5 / 1 000 f. 15-49)")
    e5.holm_family(col, "H6", "H6", "unités avec covariables", fam, f"les {len(fam)} sous-groupes H6")
    col.save()


def part_robust(args) -> None:
    col = e5.Collector("robust")
    d, cov, covs, a, ac = _base(args)
    kw = dict(covs=covs, estimators=("cs",))
    for (y0, y1), lab in CFG["robust_windows"]:
        e5.run_block(col, ac[ac.year.between(y0, y1)], "y_log", "robustesse", "H1", Y_ALL, lab, "unit", **kw)
    e5.run_block(col, ac[~ac.year.isin([2020, 2021])], "y_log", "robustesse", "H1", Y_ALL, "sans 2020-2021", "unit", **kw)
    ccol, clab = CFG["cluster_alt"]
    e5.run_block(col, ac, "y_log", "robustesse", "H1", Y_ALL, clab, "unit", cluster=ccol, covs=covs, estimators=("cs", "twfe"))
    e5.run_block(col, a, "y_log", "robustesse", "H1", Y_ALL, "pondéré par les femmes 15-49, CS sans covariables", "unit", estimators=("cs",), weights=CFG["weights"],
                 exploratory=True, notes="pondération (A2)")
    for ccol2, cen, lab, hyp in CFG["robust_cohorts"]:
        dd = with_covs(aggregate(mun_age_panel(ccol2, cen), GROUPS, "15-49"), cov).dropna(subset=covs)
        e5.run_block(col, dd, "y_log", "robustesse", hyp, Y_ALL, lab, "unit", **kw)
    lab, first = CFG["robust_drop_first"]
    e5.run_block(col, ac[ac.cohort != first], "y_log", "robustesse", "H1", Y_ALL, lab, "unit", **kw)
    a2539 = with_covs(aggregate(d, G2539, "25-39"), cov).dropna(subset=covs)
    e5.run_block(col, a2539[~a2539.year.isin([2020, 2021])], "y_log", "robustesse", "H2b", Y_2539, "sans 2020-2021", "unit", **kw)
    e5.run_block(col, a2539[a2539.cohort != first], "y_log", "robustesse", "H2b", Y_2539, lab, "unit", **kw)
    col.save()


def part_summary(args) -> None:
    files = sorted(p for p in e5.EST.glob("*.csv") if not p.name.startswith("_"))
    if not files:
        return
    tag = CFG["tag"]
    allr = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    out_dir = e5.EST if "smoke" in e5.EST.name else TABLES
    allr.to_csv(out_dir / f"est_{tag}_all.csv", index=False)
    key = allr[allr.aggregation.isin(e5.KEY_AGGS)]
    lines = [f"# Estimations {CFG['name']} — synthèse (généré par scripts/15_estimate_country.py --country {args.country} --part summary)", "",
             f"Toutes les estimations : `tables/est_{tag}_all.csv`. Mêmes conventions que la France (`t_estimates_fr.md`). Unité = {CFG['unit_name']} ; "
             f"cohorte = `{CFG['cohort_col']}` ({CFG['first_year_note']}) ; addendum {CFG['addendum']}.", ""]
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
    (out_dir / f"t_estimates_{tag}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "commit": e5._git_rev(), "args": vars(args), "n_rows": int(len(allr)),
                "inputs": {p.name: time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime)) for p in sorted(PROC.glob(f"{tag}_*.parquet"))}}
    (e5.EST / "_run.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"synthèse : {len(key)} lignes clés, {len(allr)} coefficients")


PARTS = {"sample": part_sample, "h1": part_h1, "h2": part_h2, "h3": part_h3, "h5": part_h5, "h6": part_h6, "robust": part_robust, "summary": part_summary}


def main() -> int:
    global CFG
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--country", required=True, choices=sorted(CONFIGS))
    ap.add_argument("--part", nargs="+", default=["all"])
    ap.add_argument("--boot", type=int, default=999)
    ap.add_argument("--nboot", type=int, default=50)
    ap.add_argument("--fast", action="store_true")
    a = ap.parse_args()
    CFG = CONFIGS[a.country]
    if a.fast:
        a.boot, a.nboot = 49, 3
    e5.EST = TABLES / (f"est_{CFG['tag']}_smoke" if a.fast else f"est_{CFG['tag']}")
    parts = list(PARTS) if a.part == ["all"] else a.part
    for p in parts:
        if p not in PARTS:
            raise SystemExit(f"partie inconnue : {p}")
        log(f"=== partie {p}")
        PARTS[p](a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
