#!/usr/bin/env python
"""Étape 3 — estimations France, telles que préenregistrées (docs/preregistration.md §3, §5 ; addendum A1).

Usage :
    python scripts/05_estimate.py --part all            # tout (long : ≈ 2-3 h, bootstraps compris)
    python scripts/05_estimate.py --part h1 h2          # familles choisies
    python scripts/05_estimate.py --part h1 --fast      # bootstraps réduits, pour vérifier que tout tourne

Parties : h1 (effet total commune), h2 (effet par âge, département), h3 (canal), h5 (placebos), h6
(hétérogénéité), iv (2SLS région × âge), robust (fenêtres, définitions du traitement, groupage).

Chaque estimation est une ligne « tidy » dans tables/est/<partie>.csv : famille, hypothèse, résultat,
échantillon, estimateur, terme, estimation, écart-type, IC 95 %, p, n unités, n observations, notes.
`tables/t_estimates_fr.md` (synthèse) est produit par `--part summary` (ou à la fin de `--part all`).

Rien dans ce script ne vient d'une autre étude ; aucune valeur n'est imputée. Les résultats sont
rapportés tels quels, y compris nuls ou contraires aux prédictions.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import warnings
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import did  # noqa: E402
from common.download import raw_files  # noqa: E402
from common.geo import Cog  # noqa: E402

warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
EST = ROOT / "tables" / "est"
GROUPS = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-49"]
G2539 = ["25-29", "30-34", "35-39"]
G1524 = ["15-19", "20-24"]
WINDOW = did.EVENT_WINDOW
COMMUNE_YEARS = (2008, 2024)
DEP_YEARS = (1998, 2024)
MIN_PRE = 3


# ----------------------------------------------------------------------------- collecte des résultats

class Collector:
    def __init__(self, part: str):
        self.part = part
        self.rows: list[dict] = []

    def add(self, family: str, hyp: str, outcome: str, sample: str, tidy: pd.DataFrame, n_units: int, n_obs: int,
            notes: str = "", **extra) -> None:
        for _, r in tidy.iterrows():
            self.rows.append({"part": self.part, "family": family, "hypothesis": hyp, "outcome": outcome, "sample": sample,
                              "estimator": r["estimator"], "term": str(r["term"]), "estimate": float(r["estimate"]),
                              "se": float(r["se"]), "ci_low": float(r["ci_low"]), "ci_high": float(r["ci_high"]),
                              "p": did.p_from_z(r["estimate"], r["se"]), "n_units": int(n_units), "n_obs": int(n_obs),
                              "notes": notes, **extra})

    def add_scalar(self, family: str, hyp: str, outcome: str, sample: str, estimator: str, term: str, est: float, se: float,
                   n_units: int, n_obs: int, notes: str = "", **extra) -> None:
        z = 1.959964
        self.rows.append({"part": self.part, "family": family, "hypothesis": hyp, "outcome": outcome, "sample": sample,
                          "estimator": estimator, "term": term, "estimate": float(est), "se": float(se),
                          "ci_low": float(est) - z * float(se), "ci_high": float(est) + z * float(se), "p": did.p_from_z(est, se),
                          "n_units": int(n_units), "n_obs": int(n_obs), "notes": notes, **extra})

    def save(self) -> pd.DataFrame:
        EST.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(self.rows)
        df.to_csv(EST / f"{self.part}.csv", index=False)
        return df


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ----------------------------------------------------------------------------- panels

def covariates_commune(cog: Cog) -> pd.DataFrame:
    """Contrôles de pré-période par unité (préreg. §4.1) : classe de densité, revenu médian 2012 (Filosofi),
    part de diplômées du supérieur 2011, taux de chômage des femmes 15-24 en 2011 (RP), tendance 2008-2011 des
    naissances. Sauvegardé dans data/processed/fr_covariates_commune.parquet."""
    out = PROC / "fr_covariates_commune.parquet"
    if out.exists():
        return pd.read_parquet(out)
    # Filosofi 2012 : MED12 (xls dans zip, feuille COM)
    z = zipfile.ZipFile(next(p for p in raw_files("fr_insee_filosofi_2012")))
    name = next(n for n in z.namelist() if n.endswith(".xls"))
    sh = pd.read_excel(z.open(name), sheet_name="COM", header=None, dtype=str)
    hdr = max(i for i in range(10) if str(sh.iloc[i, 0]).strip().upper() == "CODGEO")   # 2 lignes CODGEO : libellés puis codes
    filo = sh.iloc[hdr + 1:].copy()
    filo.columns = [str(c).upper() for c in sh.iloc[hdr]]
    filo["unit"] = cog.harmonize(filo.CODGEO)
    filo["med12"] = pd.to_numeric(filo.MED12, errors="coerce")
    filo["nmen12"] = pd.to_numeric(filo.NBMENFISC12, errors="coerce")
    f = filo.dropna(subset=["med12"]).groupby("unit").apply(
        lambda g: np.average(g.med12, weights=g.nmen12.fillna(1).clip(lower=1)), include_groups=False).rename("med12")
    # Diplômes 2011 : femmes non scolarisées 15+ diplômées du supérieur (BAC+2 et plus) / femmes non scolarisées 15+
    p = next(p for p in raw_files("fr_insee_rp_diplomes_2011"))
    sh = pd.read_excel(p, sheet_name="COM_2011", header=None, dtype=str)
    hdr = max(i for i in range(10) if str(sh.iloc[i, 0]).strip().upper() == "CODGEO")
    dip = sh.iloc[hdr + 1:].copy()
    dip.columns = [str(c).upper() for c in sh.iloc[hdr]]
    dip["unit"] = cog.harmonize(dip.CODGEO)
    for c in ["P11_FNSCOL15P", "P11_FNSCOL15P_BACP2", "P11_FNSCOL15P_SUP"]:
        dip[c] = pd.to_numeric(dip[c], errors="coerce")
    d = dip.groupby("unit")[["P11_FNSCOL15P", "P11_FNSCOL15P_BACP2", "P11_FNSCOL15P_SUP"]].sum(min_count=1)
    d["share_fsup"] = (d.P11_FNSCOL15P_BACP2 + d.P11_FNSCOL15P_SUP) / d.P11_FNSCOL15P
    # Chômage des femmes 15-24 en 2011 : base Emploi-Population active 2016 (variables P11_)
    p = next(p for p in raw_files("fr_insee_rp_activite") if "2016" in p.name)
    z = zipfile.ZipFile(p)
    name = next(n for n in z.namelist() if n.lower().endswith(".csv") and "meta" not in n.lower())
    act = pd.read_csv(z.open(name), sep=";", dtype={"CODGEO": str}, usecols=["CODGEO", "P11_FACT1524", "P11_FCHOM1524"])
    act["unit"] = cog.harmonize(act.CODGEO)
    a = act.groupby("unit")[["P11_FACT1524", "P11_FCHOM1524"]].sum(min_count=1)
    a["unemp_f1524"] = a.P11_FCHOM1524 / a.P11_FACT1524
    # tendance 2008-2011 des naissances (log, +0,5) et densité
    oc = pd.read_parquet(PROC / "fr_outcomes_commune.parquet")
    pre = oc[oc.year.between(2008, 2011)].pivot(index="unit", columns="year", values="births")
    trend = ((np.log(pre[2011] + 0.5) - np.log(pre[2008] + 0.5)) / 3).rename("pretrend_0811")
    tr = pd.read_parquet(PROC / "fr_treatment_commune_static.parquet").set_index("unit")
    cov = pd.concat([f, d.share_fsup, a.unemp_f1524, trend, tr.densite], axis=1)
    cov["log_med12"] = np.log(cov.med12)
    cov["dens_cat"] = cov.densite.map(lambda x: 1 if x in (1, 2) else 2 if x in (3, 4) else 3 if x in (5, 6, 7) else np.nan)
    cov["dens_inter"] = (cov.dens_cat == 2).astype(float)
    cov["dens_rural"] = (cov.dens_cat == 3).astype(float)
    cov = cov.reset_index().rename(columns={"index": "unit"})
    cov.to_parquet(out, index=False)
    return cov


COVS = ["log_med12", "share_fsup", "unemp_f1524", "pretrend_0811", "dens_inter", "dens_rural"]


SAMPLE_UNITS: int | None = None     # --sample N : sous-échantillon aléatoire de communes (tests de fonctionnement seulement)


def commune_panel(cohort_col: str = "cohort_4g", years: tuple[int, int] = COMMUNE_YEARS) -> pd.DataFrame:
    tr = pd.read_parquet(PROC / "fr_treatment_commune.parquet")
    oc = pd.read_parquet(PROC / "fr_outcomes_commune.parquet")
    d = oc.merge(tr.drop(columns=["dep", "metro"]), on=["unit", "year"], how="inner")
    d = d[d.metro & d.year.between(*years) & (d.women_1544 > 0)].copy()
    d["cohort"] = d[cohort_col].astype(int)
    d["rate"] = (d.births + 0.5) / d.women_1544 * 1000
    d["y_log"] = np.log(d.rate)
    d["y_rate"] = d.births / d.women_1544 * 1000
    d["y_asinh"] = np.arcsinh(d.y_rate)
    d["y_deaths"] = np.log((d.deaths + 0.5) / d["pop"] * 1000).where(d["pop"] > 0)
    d["unit"] = d.unit.astype(str)
    if SAMPLE_UNITS:
        keep = np.random.default_rng(0).choice(d.unit.unique(), min(SAMPLE_UNITS, d.unit.nunique()), replace=False)
        d = d[d.unit.isin(keep)]
    return d


def dep_age_panel(cohort_col: str = "cohort_d3_50", years: tuple[int, int] = DEP_YEARS) -> pd.DataFrame:
    da = pd.read_parquet(PROC / "fr_outcomes_dep_age.parquet")
    dt = pd.read_parquet(PROC / "fr_treatment_dep.parquet")
    coh = dt.drop_duplicates("dep").set_index("dep")[["cohort_d3_50", "cohort_d3_90"]]
    d = da[da.metro & da.year.between(*years)].merge(dt[["dep", "year", "d3"]], on=["dep", "year"], how="left")
    d = d.merge(coh, left_on="dep", right_index=True, how="left")
    d["d3"] = d.d3.fillna(0.0)                               # avant 2004 : aucune 4G
    d["cohort"] = d[cohort_col].fillna(0).astype(int)
    d["y_log"] = np.log(d.births_per_1000.where(d.births_per_1000 > 0))
    d["y_mar"] = np.log(d.marriages_per_1000.where(d.marriages_per_1000 > 0))
    d["y_bmar"] = np.log((1000 * d.births_married / d.women).where(d.births_married > 0))
    d["unit"] = d.dep + "_" + d.age_group
    return d


def aggregate_ages(d: pd.DataFrame, groups: list[str], label: str) -> pd.DataFrame:
    """Taux agrégé sur plusieurs groupes d'âge (pondéré par les effectifs de femmes)."""
    s = d[d.age_group.isin(groups)].groupby(["dep", "year", "cohort"]).agg(
        births=("births", "sum"), women=("women", "sum"), marriages_f=("marriages_f", "sum"),
        births_married=("births_married", "sum"), d3=("d3", "first")).reset_index()
    s["age_group"] = label
    s["births_per_1000"] = 1000 * s.births / s.women
    s["marriages_per_1000"] = 1000 * s.marriages_f / s.women
    s["y_log"] = np.log(s.births_per_1000.where(s.births_per_1000 > 0))
    s["y_mar"] = np.log(s.marriages_per_1000.where(s.marriages_per_1000 > 0))
    s["y_bmar"] = np.log((1000 * s.births_married / s.women).where(s.births_married > 0))
    s["unit"] = s.dep + "_" + label
    return s


# ----------------------------------------------------------------------------- bloc d'estimation standard

def run_block(col: Collector, d: pd.DataFrame, y: str, family: str, hyp: str, outcome: str, sample: str, unit: str,
              cluster: str | None = None, covs: list[str] | None = None, control: str = "not_yet_treated",
              estimators=("cs", "sunab", "did2s", "twfe"), boot: int = 0, nboot_cluster: int = 0, seed: int = 1,
              notes: str = "", poisson: tuple[str, str] | None = None, min_pre: int = MIN_PRE) -> dict:
    """Estime une spécification complète : CS (event, moyenne +1..+5, simple, test pré-tendance), puis
    comparaisons. ``poisson`` = (compte, exposition) pour l'ATT Poisson à effets fixes."""
    d = did.drop_always_treated(d.dropna(subset=[y]), "year", "cohort", min_pre)
    d = d[np.isfinite(d[y])]
    nu, no = d[unit].nunique(), len(d)
    out = {}
    if "cs" in estimators:
        t0 = time.time()
        r = did.cs_event_study(d, y, unit, "year", "cohort", covariates=covs, control=control, cluster=cluster, boot=boot, seed=seed)
        note = notes + (f" ; covariables : {', '.join(covs)}" if covs else "") + f" ; contrôle = {control}" + (f" ; bootstrap {boot}" if boot else "")
        col.add(family, hyp, outcome, sample, r["event"], nu, no, note, aggregation="event")
        col.add(family, hyp, outcome, sample, r["post_avg"], nu, no, note + " ; écart-type approché (indépendance des coefficients)", aggregation="post_avg_1_5")
        col.add(family, hyp, outcome, sample, r["simple"], nu, no, note, aggregation="simple")
        col.add_scalar(family, hyp, outcome, sample, "cs", "pre_wald_p", r["pre_wald_p"], np.nan, nu, no,
                       "p du test de Wald approché de nullité conjointe des coefficients −8..−2 (H5c)", aggregation="pre_test")
        out["cs"] = r
        log(f"  CS {family}/{hyp} {outcome} [{sample}] : ATT[1,5] = {r['post_avg']['estimate'].iloc[0]:+.4f} "
            f"(es {r['post_avg']['se'].iloc[0]:.4f}), pré-test p = {r['pre_wald_p']:.3f}, {time.time() - t0:.0f} s")
        if nboot_cluster:
            t0 = time.time()
            stat = lambda b: did.cs_post_avg(b, y, unit, "year", "cohort", covariates=covs, control=control)  # noqa: E731
            bs = did.cluster_bootstrap(d, unit, stat, n_boot=nboot_cluster, seed=seed, cluster=cluster)
            col.add_scalar(family, hyp, outcome, sample, "cs", "ATT[1,5]", r["post_avg"]["estimate"].iloc[0], bs["se_boot"], nu, no,
                           f"écart-type par bootstrap par grappes ({bs['n_boot_ok']} tirages, grappe = {cluster or unit}) ; quantiles "
                           f"[{bs['q025']:+.4f}, {bs['q975']:+.4f}]", aggregation="post_avg_1_5_boot")
            log(f"  bootstrap grappes : es = {bs['se_boot']:.4f} ({bs['n_boot_ok']} tirages, {time.time() - t0:.0f} s)")
    if ("sunab" in estimators or "did2s" in estimators) and not (d.cohort == 0).any():
        col.add_scalar(family, hyp, outcome, sample, "sunab/did2s", "non estimable", np.nan, np.nan, nu, no,
                       "aucune unité jamais traitée dans ce panel : Sun & Abraham (contrôle = jamais traitées) et did2s (pyfixest 0.60) "
                       "ne sont pas estimables ; comparaisons = TWFE, Poisson, D3 continu", aggregation="note")
        estimators = tuple(e for e in estimators if e not in ("sunab", "did2s"))
    if "sunab" in estimators and (d.cohort == 0).any():
        try:
            t = did.sunab_event_study(d, y, unit, "year", "cohort", cluster=cluster)
            col.add(family, hyp, outcome, sample, t, nu, no, notes, aggregation="event")
            post = t[t.term.astype(int).between(1, 5)]
            col.add_scalar(family, hyp, outcome, sample, "sunab", "ATT[1,5]", post.estimate.mean(), np.sqrt((post.se ** 2).sum()) / len(post), nu, no,
                           "moyenne +1..+5, écart-type approché", aggregation="post_avg_1_5")
        except Exception as e:  # noqa: BLE001
            log(f"  Sun & Abraham non estimé : {e}")
    if "did2s" in estimators:
        try:
            t = did.did2s_event_study(d, y, unit, "year", "cohort", cluster=cluster)
            col.add(family, hyp, outcome, sample, t, nu, no, notes, aggregation="event")
            post = t[t.term.astype(int).between(1, 5)]
            col.add_scalar(family, hyp, outcome, sample, "did2s", "ATT[1,5]", post.estimate.mean(), np.sqrt((post.se ** 2).sum()) / len(post), nu, no,
                           "moyenne +1..+5, écart-type approché", aggregation="post_avg_1_5")
        except Exception as e:  # noqa: BLE001
            log(f"  did2s non estimé : {e}")
    if "twfe" in estimators:
        t = did.twfe_event_study(d, y, unit, "year", "cohort", cluster=cluster)
        col.add(family, hyp, outcome, sample, t, nu, no, notes, aggregation="event")
        col.add(family, hyp, outcome, sample, did.twfe_att(d, y, unit, "year", "cohort", cluster=cluster), nu, no, notes, aggregation="static")
    if poisson:
        count, expo = poisson
        try:
            t = did.twfe_att(d, count, unit, "year", "cohort", cluster=cluster, poisson=True, exposure=expo)
            t["term"] = "ATT (log du taux contrefactuel)"
            col.add(family, hyp, outcome, sample, t, nu, no, notes + " ; Poisson à effets fixes, exposition = " + expo, aggregation="static")
        except Exception as e:  # noqa: BLE001
            log(f"  Poisson non estimé : {e}")
    return out


# ----------------------------------------------------------------------------- H1 : effet total, commune

def part_h1(args) -> None:
    col = Collector("h1")
    cog = Cog(next(iter(raw_files("fr_insee_cog"))))
    cov = covariates_commune(cog)
    d = commune_panel().merge(cov[["unit"] + COVS], on="unit", how="left")
    dc = d.dropna(subset=COVS)
    log(f"H1 : {d.unit.nunique():,} unités, {len(d):,} obs ; avec covariables : {dc.unit.nunique():,} unités")
    # primaire : CS doublement robuste avec contrôles de pré-période, pas-encore-traités, grappes commune
    run_block(col, dc, "y_log", "H1", "H1", "log(naissances+0,5 / 1 000 f. 15-44)", "primaire : communes avec covariables", "unit",
              covs=COVS, boot=args.boot, nboot_cluster=args.nboot, estimators=("cs",), notes="spécification primaire préenregistrée")
    # sans covariables, toutes les communes ; avec comparaisons
    run_block(col, d, "y_log", "H1", "H1", "log(naissances+0,5 / 1 000 f. 15-44)", "toutes communes, sans covariables", "unit",
              boot=args.boot, poisson=("births", "women_1544"))
    # contrôle = jamais traitées
    run_block(col, dc, "y_log", "H1", "H1", "log(naissances+0,5 / 1 000 f. 15-44)", "covariables, contrôle = jamais traitées", "unit",
              covs=COVS, control="never_treated", estimators=("cs",))
    # sensibilité à la transformation
    for y, lab in (("y_rate", "naissances / 1 000 f. 15-44 (taux brut)"), ("y_asinh", "asinh(taux)")):
        run_block(col, d, y, "H1", "H1", lab, "toutes communes, sans covariables", "unit", estimators=("cs",))
    col.save()


# ----------------------------------------------------------------------------- H2 : effet par âge, département

def part_h2(args) -> None:
    col = Collector("h2")
    d = dep_age_panel()
    a2539 = aggregate_ages(d, G2539, "25-39")
    a1524 = aggregate_ages(d, G1524, "15-24")
    log(f"H2 : {d.dep.nunique()} départements, cohortes D3 ≥ 50 % : {sorted(d.cohort.unique())}")
    # H2b (test primaire) : 25-39 agrégé
    r = run_block(col, a2539, "y_log", "H2", "H2b", "log(naissances / 1 000 f. 25-39)", "département, bascule D3 ≥ 50 %", "unit",
                  cluster="dep", boot=args.boot, nboot_cluster=args.nboot, poisson=("births", "women"), notes="test primaire du papier")
    # H2a, H2c : groupes séparés
    fam_c = []
    for g in GROUPS:
        sub = d[d.age_group == g]
        rg = run_block(col, sub, "y_log", "H2", "H2a" if g in G1524 else "H2c", f"log(naissances / 1 000 f. {g})",
                       "département, bascule D3 ≥ 50 %", "unit", cluster="dep", poisson=("births", "women"))
        if "cs" in rg:
            pa = rg["cs"]["post_avg"].iloc[0]
            if g not in G1524:
                fam_c.append((g, float(pa.estimate), float(pa.se)))
    if fam_c:
        ps = [did.p_from_z(e, s) for _, e, s in fam_c]
        adj = did.holm(ps)
        for (g, e, s), p0, pa in zip(fam_c, ps, adj):
            col.add_scalar("H2", "H2c", f"log(naissances / 1 000 f. {g})", "département, bascule D3 ≥ 50 %", "cs", "ATT[1,5] (Holm)", e, s,
                           d.dep.nunique(), len(d[d.age_group == g]), f"p brut {p0:.4f}, p Holm {pa:.4f} (famille 25-29, 30-34, 35-39, 40-49)",
                           aggregation="post_avg_1_5_holm", p_holm=pa)
    # H2d : égalité 15-24 vs 25-39
    r1 = run_block(col, a1524, "y_log", "H2", "H2d", "log(naissances / 1 000 f. 15-24)", "département, bascule D3 ≥ 50 %", "unit",
                   cluster="dep", estimators=("cs",))
    if "cs" in r and "cs" in r1:
        p1, p2 = r1["cs"]["post_avg"].iloc[0], r["cs"]["post_avg"].iloc[0]
        t = did.difference_test(p1.estimate, p1.se, p2.estimate, p2.se)
        col.add_scalar("H2", "H2d", "ATT 15-24 − ATT 25-39", "département, bascule D3 ≥ 50 %", "cs", "différence", t["diff"], t["se"],
                       d.dep.nunique(), len(d), "indépendance supposée entre les deux estimations (même départements : approximation)", aggregation="difference")
    # traitement continu D3 : effets fixes département × âge et année × âge ; et par groupe
    full = pd.concat([d[d.age_group.isin(GROUPS)]], ignore_index=True)
    t = did.continuous_twfe(full.dropna(subset=["y_log"]), "y_log", "d3", "dep^age_group + year^age_group", "dep")
    col.add("H2", "H2 continu", "log(naissances / 1 000 f.), tous âges", "département × âge, D3 continu", t, d.dep.nunique(), len(full),
            "effets fixes département × âge et année × âge ; interprétation sous traitement continu (hypothèses plus fortes)", aggregation="continuous")
    for g, sub in [("25-39", a2539), ("15-24", a1524)] + [(g, d[d.age_group == g]) for g in GROUPS]:
        t = did.continuous_twfe(sub.dropna(subset=["y_log"]), "y_log", "d3", "dep + year", "dep")
        col.add("H2", "H2 continu", f"log(naissances / 1 000 f. {g})", "département, D3 continu", t, sub.dep.nunique(), len(sub),
                "effets fixes département et année", aggregation="continuous")
    # variante bascule 90 %
    d90 = dep_age_panel("cohort_d3_90")
    a90 = aggregate_ages(d90, G2539, "25-39")
    run_block(col, a90, "y_log", "H2", "H2b", "log(naissances / 1 000 f. 25-39)", "département, bascule D3 ≥ 90 %", "unit", cluster="dep", estimators=("cs",))
    col.save()


# ----------------------------------------------------------------------------- H3 : canal

def part_h3(args) -> None:
    col = Collector("h3")
    d = dep_age_panel()
    a2539 = aggregate_ages(d, G2539, "25-39")
    a1524 = aggregate_ages(d, G1524, "15-24")
    a2034 = aggregate_ages(d, ["20-24", "25-29", "30-34"], "20-34")
    # H3a (i) mariages pour 1 000 femmes par âge
    for g, sub in [("25-39", a2539), ("15-24", a1524), ("20-34", a2034)] + [(g, d[d.age_group == g]) for g in GROUPS]:
        run_block(col, sub, "y_mar", "H3", "H3a", f"log(mariages de femmes / 1 000 f. {g})", "département, bascule D3 ≥ 50 %", "unit",
                  cluster="dep", estimators=("cs", "twfe"), poisson=("marriages_f", "women"))
    # H3a (ii) PACS pour 1 000 femmes 15-49, département, 2007-2016
    dp = pd.read_parquet(PROC / "fr_outcomes_dep.parquet")
    dt = pd.read_parquet(PROC / "fr_treatment_dep.parquet").drop_duplicates("dep").set_index("dep")
    dp = dp[dp.dep.isin(dt.index) & dp.year.between(2007, 2016)].copy()
    dp["cohort"] = dp.dep.map(dt.cohort_d3_50).fillna(0).astype(int)
    dp["y_pacs"] = np.log(dp.pacs_per_1000_f1549.where(dp.pacs_per_1000_f1549 > 0))
    dp["unit"] = dp.dep
    run_block(col, dp.dropna(subset=["y_pacs"]), "y_pacs", "H3", "H3a", "log(PACS / 1 000 f. 15-49)", "département, 2007-2016 (série PACS disponible)", "unit",
              cluster="dep", estimators=("cs", "twfe"), notes="fenêtre courte : effets +1..+3 seulement pour les cohortes 2013-2015", min_pre=3)
    # H3a (iii) part des 15-24 et 25-39 ans vivant en couple (commune, millésimes RP interpolés, deux sexes)
    c = commune_panel()
    for v, lab in (("share_couple_1524", "part des 15-24 ans en couple"), ("share_couple_2539", "part des 25-39 ans en couple")):
        sub = c.dropna(subset=[v]).copy()
        run_block(col, sub, v, "H3", "H3a", lab + " (RP, deux sexes, millésimes interpolés)", "commune", "unit", estimators=("cs", "twfe"),
                  notes="résultat lissé par interpolation entre millésimes RP : réponse retardée, borne inférieure de l'effet de calendrier")
    # H3b : naissances de parents mariés pour 1 000 femmes (1998-2021) et part des naissances de parents mariés
    db = d[d.married_available == True]  # noqa: E712
    b2539 = aggregate_ages(db, G2539, "25-39")
    run_block(col, b2539, "y_bmar", "H3", "H3b", "log(naissances de parents mariés / 1 000 f. 25-39)", "département, 1998-2021", "unit",
              cluster="dep", estimators=("cs", "twfe"), poisson=("births_married", "women"))
    b2539["share_married"] = b2539.births_married / b2539.births
    run_block(col, b2539, "share_married", "H3", "H3b", "part des naissances de parents mariés, 25-39", "département, 1998-2021", "unit",
              cluster="dep", estimators=("cs", "twfe"))
    for g in GROUPS:
        sub = db[db.age_group == g].copy()
        run_block(col, sub, "y_bmar", "H3", "H3b", f"log(naissances de parents mariés / 1 000 f. {g})", "département, 1998-2021", "unit",
                  cluster="dep", estimators=("cs",))
    col.save()


# ----------------------------------------------------------------------------- H5 : placebos

def part_h5(args) -> None:
    col = Collector("h5")
    cog = Cog(next(iter(raw_files("fr_insee_cog"))))
    cov = covariates_commune(cog)
    d = commune_panel().merge(cov[["unit"] + COVS], on="unit", how="left")
    # H5a : bascule fictive décalée de −3 ans, estimée sur les seules années antérieures à la vraie bascule
    f = d.copy()
    f["true_cohort"] = f.cohort
    f = f[(f.true_cohort == 0) | (f.year < f.true_cohort)].copy()
    f["cohort"] = np.where(f.true_cohort > 0, f.true_cohort - 3, 0)
    f = f[(f.cohort == 0) | (f.cohort >= COMMUNE_YEARS[0] + MIN_PRE)]
    run_block(col, f, "y_log", "H5", "H5a", "log(naissances+0,5 / 1 000 f. 15-44)", "commune, bascule fictive −3 ans, années pré-traitement seules", "unit",
              estimators=("cs", "twfe"), notes="placebo : aucun effet attendu")
    fc = f.dropna(subset=COVS)
    run_block(col, fc, "y_log", "H5", "H5a", "log(naissances+0,5 / 1 000 f. 15-44)", "commune, bascule fictive −3 ans, covariables", "unit",
              covs=COVS, estimators=("cs",), notes="placebo : aucun effet attendu")
    # H5b : décès pour 1 000 habitants (résultat sans lien attendu), vraie bascule
    run_block(col, d, "y_deaths", "H5", "H5b", "log(décès+0,5 / 1 000 hab.)", "commune", "unit", estimators=("cs", "twfe"),
              notes="placebo : décès totaux (décès des 60 ans et plus non disponibles au niveau commune, addendum A1)")
    # H5a au niveau département × âge (25-39)
    dd = dep_age_panel()
    a = aggregate_ages(dd, G2539, "25-39")
    a["true_cohort"] = a.cohort
    a = a[(a.true_cohort == 0) | (a.year < a.true_cohort)].copy()
    a["cohort"] = np.where(a.true_cohort > 0, a.true_cohort - 3, 0)
    run_block(col, a, "y_log", "H5", "H5a", "log(naissances / 1 000 f. 25-39)", "département, bascule fictive −3 ans, années pré-traitement seules", "unit",
              cluster="dep", estimators=("cs", "twfe"), notes="placebo : aucun effet attendu")
    col.save()


# ----------------------------------------------------------------------------- H6 : hétérogénéité (commune)

def part_h6(args) -> None:
    col = Collector("h6")
    cog = Cog(next(iter(raw_files("fr_insee_cog"))))
    cov = covariates_commune(cog)
    d = commune_panel().merge(cov[["unit"] + COVS + ["med12", "dens_cat"]], on="unit", how="left")
    fam = []

    def sub_block(mask, label):
        sub = d[mask]
        r = run_block(col, sub, "y_log", "H6", "H6", "log(naissances+0,5 / 1 000 f. 15-44)", label, "unit", estimators=("cs",))
        if "cs" in r:
            pa = r["cs"]["post_avg"].iloc[0]
            fam.append((label, float(pa.estimate), float(pa.se), sub.unit.nunique(), len(sub)))

    for k, lab in ((1, "densité : dense"), (2, "densité : intermédiaire"), (3, "densité : rural")):
        sub_block(d.dens_cat == k, lab)
    ter = d.drop_duplicates("unit").dropna(subset=["med12"])
    q = ter.med12.quantile([1 / 3, 2 / 3]).values
    tmap = ter.set_index("unit").med12.map(lambda x: 1 if x <= q[0] else 2 if x <= q[1] else 3)
    d["ter_med"] = d.unit.map(tmap)
    for k in (1, 2, 3):
        sub_block(d.ter_med == k, f"revenu médian 2012 : tercile {k}")
    ter = d.drop_duplicates("unit").dropna(subset=["share_fsup"])
    q = ter.share_fsup.quantile([1 / 3, 2 / 3]).values
    smap = ter.set_index("unit").share_fsup.map(lambda x: 1 if x <= q[0] else 2 if x <= q[1] else 3)
    d["ter_sup"] = d.unit.map(smap)
    for k in (1, 2, 3):
        sub_block(d.ter_sup == k, f"part de diplômées du supérieur 2011 : tercile {k}")
    sub_block(d.zdp == True, "ZDP")  # noqa: E712
    sub_block(d.zdp == False, "hors ZDP")  # noqa: E712
    ps = [did.p_from_z(e, s) for _, e, s, _, _ in fam]
    for (lab, e, s, nu, no), p0, pa in zip(fam, ps, did.holm(ps)):
        col.add_scalar("H6", "H6", "log(naissances+0,5 / 1 000 f. 15-44)", lab, "cs", "ATT[1,5] (Holm)", e, s, nu, no,
                       f"p brut {p0:.4f}, p Holm {pa:.4f} (famille des {len(fam)} sous-groupes)", aggregation="post_avg_1_5_holm", p_holm=pa)
    # rang de naissance (H6) : disponible 1998-2012 seulement, avant toute bascule D3 (2013) → non testable
    col.add_scalar("H6", "H6", "part des naissances de rang 1", "département", "—", "non testable", np.nan, np.nan, 0, 0,
                   "le rang de naissance n'est renseigné que jusqu'en 2012, avant la première bascule départementale (2013)")
    col.save()


# ----------------------------------------------------------------------------- robustesse (commune)

def part_robust(args) -> None:
    col = Collector("robust")
    cog = Cog(next(iter(raw_files("fr_insee_cog"))))
    cov = covariates_commune(cog)
    base = commune_panel().merge(cov[["unit"] + COVS], on="unit", how="left")
    y, lab, hyp = "y_log", "log(naissances+0,5 / 1 000 f. 15-44)", "H1"
    run_block(col, base[base.year <= 2019], y, "robustesse", hyp, lab, "fenêtre 2008-2019", "unit", estimators=("cs", "twfe"))
    run_block(col, base[~base.year.isin([2020, 2021])], y, "robustesse", hyp, lab, "sans 2020-2021", "unit", estimators=("cs",))
    run_block(col, base[~base.cohort.between(2013, 2014)], y, "robustesse", hyp, lab, "hors cohortes 2013-2014 (préreg. : 2012-2014)", "unit", estimators=("cs",))
    run_block(col, base[~base.cohort.between(2013, 2017)], y, "robustesse", hyp, lab, "hors cohortes 2013-2017 (addendum A1)", "unit", estimators=("cs",))
    run_block(col, base[base.densite != 1], y, "robustesse", hyp, lab, "hors grands centres urbains (densité 1)", "unit", estimators=("cs",))
    run_block(col, base, y, "robustesse", hyp, lab, "grappes = département", "unit", cluster="dep", estimators=("cs", "twfe"))
    # définitions alternatives du traitement
    for ccol, lab2 in (("cohort_4g_obs_only", "D1 observatoire seul"), ("cohort_4g_2op", "deuxième opérateur 4G")):
        dd = commune_panel(ccol)
        run_block(col, dd, y, "robustesse", hyp, lab, f"traitement = {lab2}", "unit", estimators=("cs",))
    dd = commune_panel("cohort_4g_arcep")
    dd = dd[(dd.cohort == 0) | (dd.cohort >= 2020)]
    run_block(col, dd, y, "robustesse", hyp, lab, "traitement = premier site 4G commercial ARCEP (cohortes ≥ 2020 ; 4G en 2018-T4 exclues)", "unit", estimators=("cs",),
              notes="composition différente : communes tardives seulement")
    dd = commune_panel("cohort_3g")
    run_block(col, dd, y, "robustesse", "3G", lab, "traitement = premier émetteur UMTS (cohortes 2011+ ; antérieures exclues)", "unit", estimators=("cs",),
              notes="3G en robustesse (préreg.) ; la plupart des cohortes 3G précèdent 2008 et sont exclues")
    # niveau département : fenêtres
    d = dep_age_panel()
    a = aggregate_ages(d, G2539, "25-39")
    run_block(col, a[a.year <= 2019], y, "robustesse", "H2b", "log(naissances / 1 000 f. 25-39)", "département, 1998-2019", "unit", cluster="dep", estimators=("cs",))
    run_block(col, a[~a.year.isin([2020, 2021])], y, "robustesse", "H2b", "log(naissances / 1 000 f. 25-39)", "département, sans 2020-2021", "unit", cluster="dep", estimators=("cs",))
    run_block(col, a[a.year >= 2008], y, "robustesse", "H2b", "log(naissances / 1 000 f. 25-39)", "département, 2008-2024", "unit", cluster="dep", estimators=("cs",))
    col.save()


# ----------------------------------------------------------------------------- IV (secondaire)

ZEAT_OF_AGE = {"20-24": "18-24 ans", "25-39": "25-39 ans"}


def part_iv(args) -> None:
    col = Collector("iv")
    import importlib.util
    spec = importlib.util.spec_from_file_location("fs", Path(__file__).resolve().parent / "04b_firststage.py")
    fs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fs)
    zeat_of_dep = {dep: z for z, deps in fs.ZEAT_DEPS.items() for dep in deps}
    d = dep_age_panel()
    d["zone"] = d.dep.map(zeat_of_dep)
    rows = []
    for g, groups in (("20-24", ["20-24"]), ("25-39", G2539)):
        s = d[d.age_group.isin(groups)].groupby(["zone", "year"]).agg(births=("births", "sum"), women=("women", "sum")).reset_index()
        s["age"] = g
        rows.append(s)
    fert = pd.concat(rows, ignore_index=True)
    fert["y_log"] = np.log(1000 * fert.births / fert.women)
    bar = pd.read_parquet(PROC / "fr_firststage_panel.parquet")
    bar = bar[(bar.panel == "ZEAT") & bar.smartphone.notna()]
    bar["age"] = bar.AGE6FUZ.map({v: k for k, v in ZEAT_OF_AGE.items()})
    bar = bar.dropna(subset=["age"])
    ad = bar.groupby(["zone", "year", "age"]).apply(lambda x: pd.Series({"smart": np.average(x.smartphone, weights=x.w), "d3": x.d3.iloc[0], "n": len(x)}),
                                                     include_groups=False).reset_index()
    p = fert.merge(ad, on=["zone", "year", "age"], how="inner")
    p = p[p.year.between(2011, 2020)]
    log(f"IV : {len(p)} cellules zone × âge × année, {p.zone.nunique()} zones")
    for g in ("20-24", "25-39", "pooled"):
        sub = p if g == "pooled" else p[p.age == g]
        fe = "zone^age + year^age" if g == "pooled" else "zone + year"
        try:
            r = did.iv_2sls(sub, "y_log", "smart", "d3", fe, "zone", weights="women")
            col.add_scalar("IV", "IV", f"log(naissances / 1 000 f. {g})", "ZEAT × année 2011-2020", "2sls", "forme réduite (D3)", *r["reduced_form"], sub.zone.nunique(), r["n"],
                           "effets fixes " + fe + " ; pondéré par les femmes ; 9 grappes", aggregation="iv")
            col.add_scalar("IV", "IV", f"possession de smartphone {g}", "ZEAT × année 2011-2020", "2sls", "premier étage (D3)", *r["first_stage"], sub.zone.nunique(), r["n"],
                           f"F ≈ {r['first_stage_F']:.1f}", aggregation="iv")
            col.add_scalar("IV", "IV", f"log(naissances / 1 000 f. {g})", "ZEAT × année 2011-2020", "2sls", "IV : effet de la possession de smartphone (0→1)", *r["iv"], sub.zone.nunique(), r["n"],
                           "re-normalisation de la forme réduite ; restriction d'exclusion discutée dans le papier", aggregation="iv")
        except Exception as e:  # noqa: BLE001
            log(f"  IV {g} non estimé : {e}")
    col.save()


# ----------------------------------------------------------------------------- synthèse

def part_summary(args) -> None:
    files = sorted(EST.glob("*.csv"))
    if not files:
        log("aucun résultat à synthétiser")
        return
    allr = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    allr.to_csv(ROOT / "tables" / "est_fr_all.csv", index=False)
    key = allr[allr.aggregation.isin(["post_avg_1_5", "post_avg_1_5_boot", "post_avg_1_5_holm", "static", "difference", "continuous", "iv", "pre_test"])]
    lines = ["# Estimations France — synthèse (généré par scripts/05_estimate.py --part summary)", "",
             "Toutes les estimations : `tables/est_fr_all.csv` (une ligne par coefficient, event studies comprises). "
             "ATT[1,5] = moyenne des effets +1 à +5 après la bascule (log-points ≈ %). cs = Callaway & Sant'Anna ; "
             "sunab = Sun & Abraham ; did2s = Gardner ; twfe = effets fixes bidirectionnels ; twfe_poisson = Poisson à effets fixes.", ""]
    for fam, g in key.groupby("family", sort=False):
        lines += [f"## {fam}", "", "| hypothèse | résultat | échantillon | estimateur | terme | estimation | es | IC 95 % | p | n unités | n obs | notes |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in g.iterrows():
            ci = f"[{r.ci_low:+.4f}, {r.ci_high:+.4f}]" if np.isfinite(r.ci_low) else ""
            pv = f"{r.p:.3f}" if np.isfinite(r.p) else ""
            est = f"{r.estimate:+.4f}" if np.isfinite(r.estimate) else ""
            se = f"{r.se:.4f}" if np.isfinite(r.se) else ""
            lines.append(f"| {r.hypothesis} | {r.outcome} | {r['sample']} | {r.estimator} | {r.term} | {est} | {se} | {ci} | {pv} | {r.n_units:,} | {r.n_obs:,} | {str(r.notes)[:160]} |")
        lines.append("")
    (ROOT / "tables" / "t_estimates_fr.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"synthèse : {len(key)} lignes clés, {len(allr)} coefficients au total")


PARTS = {"h1": part_h1, "h2": part_h2, "h3": part_h3, "h5": part_h5, "h6": part_h6, "robust": part_robust, "iv": part_iv, "summary": part_summary}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--part", nargs="+", default=["all"])
    ap.add_argument("--boot", type=int, default=199, help="itérations du bootstrap multiplicateur (bandes simultanées)")
    ap.add_argument("--nboot", type=int, default=100, help="tirages du bootstrap par grappes pour ATT[1,5] des spécifications primaires")
    ap.add_argument("--fast", action="store_true", help="bootstraps réduits (vérification)")
    ap.add_argument("--sample", type=int, default=None, help="sous-échantillon de communes (tests de fonctionnement ; jamais pour le papier)")
    a = ap.parse_args()
    if a.fast:
        a.boot, a.nboot = 19, 5
    if a.sample:
        global SAMPLE_UNITS
        SAMPLE_UNITS = a.sample
        global EST
        EST = ROOT / "tables" / "est_smoke"           # les tests de fonctionnement n'écrivent jamais dans tables/est
    parts = list(PARTS) if a.part == ["all"] else a.part
    for p in parts:
        if p not in PARTS:
            raise SystemExit(f"partie inconnue : {p} (choix : {', '.join(PARTS)})")
    for p in parts:
        log(f"=== partie {p}")
        PARTS[p](a)
    if "summary" not in parts and a.part == ["all"]:
        part_summary(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
