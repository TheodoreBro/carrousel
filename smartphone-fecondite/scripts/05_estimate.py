#!/usr/bin/env python
"""Étape 3 — estimations France, telles que préenregistrées (docs/preregistration.md §3, §5 ; addenda A1, A2).

Usage :
    python scripts/05_estimate.py --part all            # tout (long : plusieurs heures, bootstraps compris)
    python scripts/05_estimate.py --part h1 h2          # familles choisies
    python scripts/05_estimate.py --part h2 --fast      # bootstraps réduits, pour vérifier que tout tourne

Parties : h1 (effet total commune), h2 (effet par âge, département), h3 (canal), h5 (placebos), h6
(hétérogénéité), iv (2SLS ZEAT × âge × année), robust (fenêtres, définitions du traitement, groupage,
pondération, DOM), summary (synthèse et manifeste).

Chaque estimation est une ligne « tidy » dans tables/est/<partie>.csv : famille, hypothèse, résultat,
échantillon, estimateur, terme, estimation, écart-type, IC 95 %, p, n unités, n observations, agrégation,
drapeau « exploratoire » (analyse hors préregistration, consignée dans l'addendum A2), notes, et pour chaque
bloc les effectifs de composition (jamais traitées, cohortes recodées, unités déséquilibrées exclues, années
réellement identifiées par Callaway & Sant'Anna). `tables/t_estimates_fr.md` (synthèse) et
`tables/est/_run.json` (manifeste : commit, versions, durées) sont produits par `--part summary` (ou à la
fin de `--part all`).

Rien dans ce script ne vient d'une autre étude ; aucune valeur n'est imputée. Les résultats sont rapportés
tels quels, y compris nuls ou contraires aux prédictions.
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
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

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
EST = ROOT / "tables" / "est"
GROUPS = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-49"]
G2539 = ["25-29", "30-34", "35-39"]
G1524 = ["15-19", "20-24"]
WINDOW = did.EVENT_WINDOW
COMMUNE_YEARS = (2008, 2024)      # 2025 : naissances disponibles mais aucun dénominateur (addendum A2)
DEP_YEARS = (1998, 2024)
MIN_PRE = 3
RP_MILLESIMES = [2006, 2011, 2016, 2021]       # millésimes RP non chevauchants (enquêtes N−2..N+2)
Y_COMMUNE = "log(naissances+0,5 / 1 000 f. 15-44)"
Y_2539 = "log(naissances / 1 000 f. 25-39)"

# ----------------------------------------------------------------------------- collecte des résultats

STD_COLS = {"term", "estimate", "se", "ci_low", "ci_high", "estimator"}


class Collector:
    def __init__(self, part: str):
        self.part = part
        self.rows: list[dict] = []
        self.t0 = time.time()

    def add(self, family: str, hyp: str, outcome: str, sample: str, tidy: pd.DataFrame, n_units: int, n_obs: int,
            notes: str = "", exploratory: bool = False, **extra) -> None:
        for _, r in tidy.iterrows():
            row = {"part": self.part, "family": family, "hypothesis": hyp, "outcome": outcome, "sample": sample,
                   "estimator": r["estimator"], "term": str(r["term"]), "estimate": float(r["estimate"]),
                   "se": float(r["se"]), "ci_low": float(r["ci_low"]), "ci_high": float(r["ci_high"]),
                   "p": float(r["p"]) if "p" in tidy.columns and np.isfinite(r["p"]) else did.p_from_z(r["estimate"], r["se"]),
                   "n_units": int(n_units), "n_obs": int(n_obs), "exploratory": bool(exploratory), "notes": notes, **extra}
            for c in tidy.columns:                      # colonnes supplémentaires (n_cohorts, cband_low, k_periods…)
                if c not in STD_COLS and c != "p":
                    row[c] = r[c]
            self.rows.append(row)

    def add_scalar(self, family: str, hyp: str, outcome: str, sample: str, estimator: str, term: str, est: float, se: float,
                   n_units: int, n_obs: int, notes: str = "", exploratory: bool = False, p: float | None = None, **extra) -> None:
        z = 1.959964
        est, se = float(est), float(se)
        self.rows.append({"part": self.part, "family": family, "hypothesis": hyp, "outcome": outcome, "sample": sample,
                          "estimator": estimator, "term": term, "estimate": est, "se": se,
                          "ci_low": est - z * se if np.isfinite(se) else np.nan, "ci_high": est + z * se if np.isfinite(se) else np.nan,
                          "p": did.p_from_z(est, se) if p is None else float(p),
                          "n_units": int(n_units), "n_obs": int(n_obs), "exploratory": bool(exploratory), "notes": notes, **extra})

    def save(self) -> pd.DataFrame:
        EST.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(self.rows)
        df.to_csv(EST / f"{self.part}.csv", index=False)
        log(f"partie {self.part} : {len(df)} lignes, {time.time() - self.t0:.0f} s → {EST / (self.part + '.csv')}")
        return df


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ----------------------------------------------------------------------------- covariables et panels

def _codes_sheet(path_or_file, sheet: str) -> pd.DataFrame:
    """Feuille INSEE à deux lignes d'en-tête (libellés puis codes) : la ligne de codes est la dernière commençant par CODGEO."""
    sh = pd.read_excel(path_or_file, sheet_name=sheet, header=None, dtype=str)
    hdr = max(i for i in range(10) if str(sh.iloc[i, 0]).strip().upper() == "CODGEO")
    out = sh.iloc[hdr + 1:].copy()
    out.columns = [str(c).upper() for c in sh.iloc[hdr]]
    return out


def covariates_commune(cog: Cog) -> pd.DataFrame:
    """Contrôles de pré-période par unité (préreg. §4.1) : classe de densité (grille INSEE 2024 : dense = 1,
    intermédiaire = 2-4, rural = 5-7), revenu médian 2012 (Filosofi), part de femmes diplômées du supérieur 2011,
    taux de chômage des 15-24 ans en 2011 (deux sexes, RP), tendance 2008-2011 des naissances (pente MCO de
    log(naissances + 0,5) sur l'année). Sauvegardé dans data/processed/fr_covariates_commune.parquet."""
    out = PROC / "fr_covariates_commune.parquet"
    if out.exists():
        return pd.read_parquet(out)
    z = zipfile.ZipFile(next(p for p in raw_files("fr_insee_filosofi_2012")))
    name = next(n for n in z.namelist() if n.endswith(".xls"))
    filo = _codes_sheet(z.open(name), "COM")
    filo["unit"] = cog.harmonize(filo.CODGEO)
    filo["med12"] = pd.to_numeric(filo.MED12, errors="coerce")
    filo["nmen12"] = pd.to_numeric(filo.NBMENFISC12, errors="coerce")
    f = filo.dropna(subset=["med12"]).groupby("unit").apply(
        lambda g: np.average(g.med12, weights=g.nmen12.fillna(1).clip(lower=1)), include_groups=False).rename("med12")
    # Diplômes 2011 : femmes non scolarisées 15+ diplômées du supérieur (BAC+2 et plus) / femmes non scolarisées 15+
    dip = _codes_sheet(next(p for p in raw_files("fr_insee_rp_diplomes_2011")), "COM_2011")
    dip["unit"] = cog.harmonize(dip.CODGEO)
    for c in ["P11_FNSCOL15P", "P11_FNSCOL15P_BACP2", "P11_FNSCOL15P_SUP"]:
        dip[c] = pd.to_numeric(dip[c], errors="coerce")
    d = dip.groupby("unit")[["P11_FNSCOL15P", "P11_FNSCOL15P_BACP2", "P11_FNSCOL15P_SUP"]].sum(min_count=1)
    d["share_fsup"] = (d.P11_FNSCOL15P_BACP2 + d.P11_FNSCOL15P_SUP) / d.P11_FNSCOL15P
    # Chômage des 15-24 ans en 2011, deux sexes : base Emploi-Population active 2016 (variables P11_)
    p = next(p for p in raw_files("fr_insee_rp_activite") if "2016" in p.name)
    z = zipfile.ZipFile(p)
    name = next(n for n in z.namelist() if n.lower().endswith(".csv") and "meta" not in n.lower())
    act = pd.read_csv(z.open(name), sep=";", dtype={"CODGEO": str}, usecols=["CODGEO", "P11_ACT1524", "P11_HCHOM1524", "P11_FCHOM1524"])
    act["unit"] = cog.harmonize(act.CODGEO)
    a = act.groupby("unit")[["P11_ACT1524", "P11_HCHOM1524", "P11_FCHOM1524"]].sum(min_count=1)
    a["unemp_1524"] = (a.P11_HCHOM1524 + a.P11_FCHOM1524) / a.P11_ACT1524
    # tendance 2008-2011 des naissances : pente MCO de log(naissances + 0,5) sur l'année (4 points, ≥ 3 requis)
    oc = pd.read_parquet(PROC / "fr_outcomes_commune.parquet")
    pre = oc[oc.year.between(2008, 2011)].pivot(index="unit", columns="year", values="births")
    pre = pre.dropna(thresh=3)
    yrs = np.array(pre.columns, float)
    L = np.log(pre.values.astype(float) + 0.5)
    ok = np.isfinite(L)
    X = np.broadcast_to(yrs, L.shape)
    nobs = ok.sum(1)
    xbar = np.where(ok, X, 0.0).sum(1) / nobs
    lbar = np.where(ok, L, 0.0).sum(1) / nobs
    num = np.where(ok, (X - xbar[:, None]) * (L - lbar[:, None]), 0.0).sum(1)
    den = np.where(ok, (X - xbar[:, None]) ** 2, 0.0).sum(1)
    trend = pd.Series(num / den, index=pre.index, name="pretrend_0811")
    tr = pd.read_parquet(PROC / "fr_treatment_commune_static.parquet").set_index("unit")
    cov = pd.concat([f, d.share_fsup, a.unemp_1524, trend, tr.densite, tr.w_f1544], axis=1)
    cov["log_med12"] = np.log(cov.med12)
    cov["dens_cat"] = cov.densite.map(lambda x: 1 if x == 1 else 2 if x in (2, 3, 4) else 3 if x in (5, 6, 7) else np.nan)
    cov["dens_inter"] = (cov.dens_cat == 2).astype(float)
    cov["dens_rural"] = (cov.dens_cat == 3).astype(float)
    cov = cov.reset_index().rename(columns={"index": "unit"})
    cov.to_parquet(out, index=False)
    return cov


COVS = ["log_med12", "share_fsup", "unemp_1524", "pretrend_0811", "dens_inter", "dens_rural"]
COVS_NOPRE = [c for c in COVS if c != "pretrend_0811"]
COVS_DEP = ["log_med12", "share_fsup", "unemp_1524", "dens_inter", "dens_rural", "pretrend_0811"]


def covariates_dep(cog: Cog) -> pd.DataFrame:
    """Covariables de pré-période agrégées au département (moyennes des communes pondérées par les femmes 15-44 de 2011) :
    log du revenu médian 2012, part de diplômées du supérieur 2011, chômage 15-24 en 2011, parts des classes de densité
    intermédiaire et rurale. La tendance 2008-2011 est calculée sur le panel département × âge lui-même (``add_dep_pretrend``)."""
    cov = covariates_commune(cog)
    tr = pd.read_parquet(PROC / "fr_treatment_commune_static.parquet")[["unit", "dep"]]
    c = cov.merge(tr, on="unit", how="inner").dropna(subset=["w_f1544"])
    rows = []
    for dep, g in c.groupby("dep"):
        w = g.w_f1544.clip(lower=0)
        rows.append({"dep": dep, **{v: float(np.average(g[v].fillna(g[v].mean()), weights=w)) if w.sum() > 0 else np.nan
                                   for v in ["log_med12", "share_fsup", "unemp_1524", "dens_inter", "dens_rural"]}})
    return pd.DataFrame(rows)


def add_dep_pretrend(d: pd.DataFrame, y: str = "y_log", years: tuple[int, int] = (2008, 2011)) -> pd.DataFrame:
    """Pente MCO de ``y`` sur l'année en 2008-2011, par unité (tendance de pré-période du groupe d'âge)."""
    pre = d[d.year.between(*years)].pivot_table(index="unit", columns="year", values=y)
    X = np.array(pre.columns, float) - np.mean(pre.columns)
    L = pre.values
    ok = np.isfinite(L)
    Lm = np.where(ok, L, np.nan)
    lbar = np.nanmean(Lm, axis=1)
    num = np.nansum((X[None, :]) * (Lm - lbar[:, None]), axis=1)
    den = np.where(ok, X[None, :] ** 2, 0).sum(1)
    tr = pd.Series(num / den, index=pre.index, name="pretrend_0811")
    return d.drop(columns=[c for c in ["pretrend_0811"] if c in d]).merge(tr, left_on="unit", right_index=True, how="left")


def with_dep_covs(d: pd.DataFrame, cog: Cog, y: str = "y_log") -> pd.DataFrame:
    cd = covariates_dep(cog)
    out = d.drop(columns=[c for c in cd.columns if c != "dep" and c in d]).merge(cd, on="dep", how="left")
    return add_dep_pretrend(out, y)


def female_employment_dep(cog: Cog) -> pd.DataFrame:
    """Taux d'emploi des femmes de 25-54 ans (RP : actives occupées / femmes 25-54) par département aux millésimes
    2011, 2016 (base 2016 : P11_, P16_) et 2021 (base 2021 : P21_). Pour le test partiel de la restriction
    d'exclusion de l'IV (préreg. §5 : « effet de D3 sur l'emploi des femmes 25-39 » ; le RP ne donne que 25-54,
    addendum A2)."""
    out = PROC / "fr_femploy_dep.parquet"
    if out.exists():
        return pd.read_parquet(out)
    rows = []
    for base, prefixes in (("2016", ["P11", "P16"]), ("2021", ["P21"])):
        p = next(p for p in raw_files("fr_insee_rp_activite") if base in p.name)
        z = zipfile.ZipFile(p)
        name = next(n for n in z.namelist() if n.lower().endswith(".csv") and "meta" not in n.lower())
        cols = ["CODGEO"] + [f"{pf}_{v}" for pf in prefixes for v in ("FACTOCC2554", "F2554")]
        act = pd.read_csv(z.open(name), sep=";", dtype={"CODGEO": str}, usecols=cols)
        act["dep"] = cog.dep_of(cog.harmonize(act.CODGEO))
        for pf in prefixes:
            g = act.groupby("dep")[[f"{pf}_FACTOCC2554", f"{pf}_F2554"]].sum(min_count=1)
            g["year"] = 2000 + int(pf[1:])
            g["emp_f2554"] = g[f"{pf}_FACTOCC2554"] / g[f"{pf}_F2554"]
            rows.append(g.reset_index()[["dep", "year", "emp_f2554"]])
    res = pd.concat(rows, ignore_index=True)
    res.to_parquet(out, index=False)
    return res


SAMPLE_UNITS: int | None = None     # --sample N : sous-échantillon aléatoire de communes (tests de fonctionnement seulement)


def commune_panel(cohort_col: str = "cohort_4g", years: tuple[int, int] = COMMUNE_YEARS, metro_only: bool = True) -> pd.DataFrame:
    tr = pd.read_parquet(PROC / "fr_treatment_commune.parquet")
    oc = pd.read_parquet(PROC / "fr_outcomes_commune.parquet")
    d = oc.merge(tr.drop(columns=["dep", "metro"]), on=["unit", "year"], how="inner")
    if metro_only:
        d = d[d.metro]
    d = d[d.year.between(*years) & (d.women_1544 > 0)].copy()
    d["cohort"] = d[cohort_col].fillna(0).astype(int)
    d["rate"] = (d.births + 0.5) / d.women_1544 * 1000
    d["y_log"] = np.log(d.rate)
    d["y_rate"] = d.births / d.women_1544 * 1000
    d["y_asinh"] = np.arcsinh(d.y_rate)
    d["y_deaths"] = np.log((d.deaths + 0.5) / d["pop"] * 1000).where(d["pop"] > 0)
    d["unit"] = d.unit.astype(str)
    d["dep"] = d.dep.astype(str)
    if SAMPLE_UNITS:
        keep = np.random.default_rng(0).choice(d.unit.unique(), min(SAMPLE_UNITS, d.unit.nunique()), replace=False)
        d = d[d.unit.isin(keep)]
    return d


def _interp_within(d: pd.DataFrame, by: str, cols: list[str], limit: int = 2) -> pd.DataFrame:
    """Interpolation linéaire entre millésimes à l'intérieur de chaque unité, prolongement à plat limité à ``limit`` ans."""
    d = d.sort_values([by, "year"]).copy()
    for c in cols:
        d[c] = d.groupby(by)[c].transform(lambda s: s.interpolate(limit_area="inside").ffill(limit=limit).bfill(limit=limit))
    return d


COUPLE_COLS = ["p1519_couple", "p2024_couple", "p2539_couple", "p4054_couple", "p1519", "p2024", "p2539", "p4054"]


def dep_age_panel(cohort_col: str = "cohort_d3_50", years: tuple[int, int] = DEP_YEARS, metro_only: bool = True) -> pd.DataFrame:
    da = pd.read_parquet(PROC / "fr_outcomes_dep_age.parquet")
    dt = pd.read_parquet(PROC / "fr_treatment_dep.parquet")
    coh = dt.drop_duplicates("dep").set_index("dep")[["cohort_d3_50", "cohort_d3_90"]]
    keep = da.metro if metro_only else da.dep.isin(coh.index)
    d = da[keep & da.year.between(*years)].merge(dt[["dep", "year", "d3"]], on=["dep", "year"], how="left")
    d = d.merge(coh, left_on="dep", right_index=True, how="left")
    d["d3"] = d.d3.fillna(0.0)                               # avant 2004 : aucune 4G
    d["cohort"] = d[cohort_col].fillna(0).astype(int)
    cols = [c for c in COUPLE_COLS if c in d.columns]
    d["rp_millesime"] = d.year.isin(RP_MILLESIMES) & (d.p2539_couple.notna() if "p2539_couple" in d else False)
    # femmes en couple par âge : personnes en couple (deux sexes) interpolées entre millésimes, puis / 2 (addendum A2) ;
    # l'interpolation se fait par département (valeurs identiques pour les groupes d'âge d'un même département × année)
    if cols:
        key = d[["dep", "year"] + cols].drop_duplicates(["dep", "year"])
        key = _interp_within(key, "dep", cols)
        d = d.drop(columns=cols).merge(key, on=["dep", "year"], how="left")
    d["y_log"] = np.log(d.births_per_1000.where(d.births_per_1000 > 0))
    d["y_mar"] = np.log(d.marriages_per_1000.where(d.marriages_per_1000 > 0))
    d["y_mar_asinh"] = np.arcsinh(d.marriages_per_1000)
    d["y_bmar"] = np.log((1000 * d.births_married / d.women).where(d.births_married > 0))
    d["unit"] = d.dep + "_" + d.age_group
    return d


def aggregate_ages(d: pd.DataFrame, groups: list[str], label: str) -> pd.DataFrame:
    """Taux agrégé sur plusieurs groupes d'âge (pondéré par les effectifs de femmes). Les femmes en couple
    (moitié des personnes en couple des groupes RP correspondants) ne sont définies que pour 15-24 et 25-39."""
    agg = dict(births=("births", "sum"), women=("women", "sum"), marriages_f=("marriages_f", "sum"),
               births_married=("births_married", "sum"), d3=("d3", "first"), rp_millesime=("rp_millesime", "first"))
    for c in COUPLE_COLS:
        if c in d.columns:
            agg[c] = (c, "first")
    s = d[d.age_group.isin(groups)].groupby(["dep", "year", "cohort"]).agg(**agg).reset_index()
    if "metro" in d:
        s = s.merge(d.drop_duplicates("dep")[["dep", "metro"]], on="dep", how="left")
    s["age_group"] = label
    s["births_per_1000"] = 1000 * s.births / s.women
    s["marriages_per_1000"] = 1000 * s.marriages_f / s.women
    s["y_log"] = np.log(s.births_per_1000.where(s.births_per_1000 > 0))
    s["y_mar"] = np.log(s.marriages_per_1000.where(s.marriages_per_1000 > 0))
    s["y_mar_asinh"] = np.arcsinh(s.marriages_per_1000)
    s["y_bmar"] = np.log((1000 * s.births_married / s.women).where(s.births_married > 0))
    if set(groups) == set(G2539) and "p2539_couple" in s:
        s["women_couple"] = s.p2539_couple / 2
    elif set(groups) == set(G1524) and "p1519_couple" in s:
        s["women_couple"] = (s.p1519_couple + s.p2024_couple) / 2
    else:
        s["women_couple"] = np.nan
    s["y_couple"] = np.log((1000 * s.births / s.women_couple).where(s.women_couple > 0))
    s["unit"] = s.dep + "_" + label
    return s


# ----------------------------------------------------------------------------- bloc d'estimation standard

def _prepare(d: pd.DataFrame, y: str, unit: str, min_pre: int, balance: bool) -> tuple[pd.DataFrame, dict]:
    """Échantillon d'un bloc : résultat fini, ≥ ``min_pre`` années de pré-période, cohortes postérieures à la
    dernière année recodées « jamais traitées », panel équilibré (sauf ``balance=False``). Tout est compté."""
    d = d[np.isfinite(d[y].astype(float))].copy()
    d = did.drop_always_treated(d, "year", "cohort", min_pre)
    tmax = int(d.year.max())
    late = d.cohort > tmax
    comp = {"n_late_recoded": int(d.loc[late, unit].nunique()), "year_max": tmax, "year_min": int(d.year.min())}
    d.loc[late, "cohort"] = 0
    counts = d.groupby(unit).year.nunique()
    comp["n_unbalanced"] = int((counts < counts.max()).sum())
    if balance and comp["n_unbalanced"]:
        d = d[d[unit].isin(counts[counts == counts.max()].index)]
    comp["n_never"] = int(d.loc[d.cohort == 0, unit].nunique())
    comp["n_treated"] = int(d.loc[d.cohort > 0, unit].nunique())
    return d, comp


def run_block(col: Collector, d: pd.DataFrame, y: str, family: str, hyp: str, outcome: str, sample: str, unit: str,
              cluster: str | None = None, covs: list[str] | None = None, control: str = "not_yet_treated",
              estimators=("cs", "sunab", "did2s", "twfe"), boot: int = 0, nboot_cluster: int = 0, seed: int = 1,
              notes: str = "", poisson: tuple[str, str] | None = None, min_pre: int = MIN_PRE, extra_fe: str | None = None,
              weights: str | None = None, anticipation: int = 0, exploratory: bool = False, balance: bool = True,
              balanced_post: bool = False, est_method: str = "dr") -> dict:
    """Estime une spécification complète : CS (event study avec bandes sup-t, moyenne +1..+k à covariance complète,
    agrégat simple, test de Wald joint des coefficients pré), puis comparaisons (Sun & Abraham, did2s, TWFE, Poisson
    avec offset). ``extra_fe`` (ex. "year^dens_cat") s'applique aux estimateurs de régression ; pour CS, la classe de
    densité entre par les covariables de l'estimateur doublement robuste. ``balanced_post`` ajoute l'agrégat
    +1..+5 restreint aux cohortes observées jusqu'à +5."""
    d, comp = _prepare(d, y, unit, min_pre, balance)
    if covs:
        const = [c for c in covs if d[c].nunique(dropna=True) <= 1]
        covs = [c for c in covs if c not in const]
        if const:
            notes += f" ; covariables constantes retirées : {', '.join(const)}"
    nu, no = d[unit].nunique(), len(d)
    comp_note = (f" ; fenêtre {comp['year_min']}-{comp['year_max']} ; {comp['n_treated']} traitées, {comp['n_never']} jamais traitées sur la fenêtre"
                 + (f" (dont {comp['n_late_recoded']} traitées après {comp['year_max']})" if comp["n_late_recoded"] else "")
                 + (f" ; {comp['n_unbalanced']} unités incomplètes exclues" if comp["n_unbalanced"] and balance else "")
                 + (f" ; panel déséquilibré par construction ({comp['n_unbalanced']} unités incomplètes gardées)" if comp["n_unbalanced"] and not balance else ""))
    base_extra = dict(aggregation=None, n_never=comp["n_never"], n_treated=comp["n_treated"], n_late_recoded=comp["n_late_recoded"],
                      n_unbalanced=comp["n_unbalanced"], year_min=comp["year_min"], year_max=comp["year_max"])
    out = {"comp": comp, "data": d}
    cs_kw = dict(covariates=covs, control=control, cluster=cluster, weights=weights, anticipation=anticipation, balance=balance, est_method=est_method)
    inv = [c for c in (covs or []) if (d.groupby(unit)[c].nunique() <= 1).all()]
    reg_covs = [c for c in (covs or []) if c not in inv] or None
    if "cs" in estimators:
        t0 = time.time()
        r = did.cs_event_study(d, y, unit, "year", "cohort", boot=boot, seed=seed, **cs_kw)
        info = r["info"]
        note = (notes + (f" ; covariables : {', '.join(covs)} ({'doublement robuste' if est_method == 'dr' else 'régression de résultat seule' if est_method == 'reg' else est_method})" if covs else "")
                + f" ; contrôle = {control}" + comp_note
                + (f" ; ATT(g,t) identifiés jusqu'en {info['years_model'][1]} (sans unité jamais traitée, la dernière cohorte sert de contrôle)"
                   if info["years_model"][1] < info["years"][1] else "")
                + (f" ; référence −{1 + anticipation}" if anticipation else "")
                + (f" ; pondéré par {weights}" if weights else "")
                + (f" ; grappes = {cluster} ({info['n_clusters']})" if cluster and cluster != unit else "")
                + (f" ; bandes simultanées sup-t (bootstrap multiplicateur Rademacher, {boot} tirages, valeur critique {info['cband_crit']:.2f})" if boot else ""))
        ex = dict(base_extra, years_model_min=info["years_model"][0], years_model_max=info["years_model"][1], n_clusters=info["n_clusters"], k_post=info["k_post"],
                  est_method=est_method if covs else "reg")
        col.add(family, hyp, outcome, sample, r["event"], nu, no, note, exploratory, **dict(ex, aggregation="event"))
        col.add(family, hyp, outcome, sample, r["post_avg"], nu, no, note + " ; écart-type avec covariance complète des coefficients (fonctions d'influence)",
                exploratory, **dict(ex, aggregation="post_avg"))
        col.add(family, hyp, outcome, sample, r["simple"], nu, no, note + " ; moyenne de tous les ATT(g,t) post", exploratory, **dict(ex, aggregation="simple"))
        pw = r["pre_wald"]
        col.add_scalar(family, hyp, outcome, sample, "cs", f"Wald pré ({WINDOW[0]}..{info['ref'] - 1})", pw["stat"], np.nan, nu, no,
                       f"H5c : test de Wald joint de nullité des coefficients pré avec covariance des fonctions d'influence, df = {pw['df']}" + comp_note,
                       exploratory, p=pw["p_value"], **dict(ex, aggregation="pre_test", df=pw["df"]))
        out["cs"] = r
        pa = r["post_avg"].iloc[0]
        log(f"  CS {hyp} {outcome} [{sample}] : {pa.term} = {pa.estimate:+.4f} (es {pa.se:.4f}, p {did.p_from_z(pa.estimate, pa.se):.3f}), "
            f"pré-test p = {pw['p_value']:.3f}, {nu:,} unités, {time.time() - t0:.0f} s")
        if nboot_cluster:
            t0 = time.time()
            stat = lambda b: did.cs_post_avg(b, y, unit, "year", "cohort", **cs_kw)  # noqa: E731
            bs = did.cluster_bootstrap(d, unit, stat, n_boot=nboot_cluster, seed=seed, cluster=cluster, strata="cohort")
            col.add_scalar(family, hyp, outcome, sample, "cs", pa.term, pa.estimate, bs["se_boot"], nu, no,
                           f"écart-type par bootstrap par grappes stratifié par cohorte ({bs['n_boot_ok']} tirages, grappe = {cluster or unit}) ; quantiles "
                           f"[{bs['q025']:+.4f}, {bs['q975']:+.4f}]" + comp_note, exploratory, **dict(ex, aggregation="post_avg_boot"))
            log(f"  bootstrap grappes : es = {bs['se_boot']:.4f} ({bs['n_boot_ok']} tirages, {time.time() - t0:.0f} s)")
        if balanced_post:
            kmax = did.POST_AVG[1]
            b = did.cs_balanced_post(r, kmax=kmax)
            if b["tidy"] is not None:
                col.add(family, hyp, outcome, sample + f" ; agrégation à composition constante (cohortes {b['cohorts'][0]}-{b['cohorts'][-1]} observées jusqu'à +{kmax})",
                        b["tidy"], nu, no, note + f" ; même estimation, agrégat +1..+{kmax} restreint aux cohortes {b['cohorts']} (g + {kmax} ≤ {b['t_id']}), "
                        "poids fixes = tailles de cohortes ; par période : " + ", ".join(f"+{k + 1}: {v:+.4f}" for k, v in enumerate(b["by_k"])),
                        exploratory, **dict(ex, aggregation="post_avg_balanced", k_post=b["k"]))
            else:
                col.add_scalar(family, hyp, outcome, sample + " ; agrégation à composition constante", "cs", f"ATT[1,{kmax}] (composition constante)", np.nan, np.nan, nu, no,
                               f"non calculable : aucune cohorte n'est observée jusqu'à +{kmax} parmi les ATT(g,t) identifiés (dernière année identifiée {b['t_id']})",
                               exploratory, **dict(ex, aggregation="post_avg_balanced"))
    reg_kw = dict(cluster=cluster, extra_fe=extra_fe, covariates=reg_covs)
    reg_note = (notes + comp_note + (f" ; effets fixes supplémentaires {extra_fe}" if extra_fe else "") + (f" ; covariables : {', '.join(reg_covs)}" if reg_covs else "")
                + (f" ; covariables invariantes dans le temps absorbées par les effets fixes unité : {', '.join(inv)}" if inv else ""))
    d_full, sample_full, reg_note_full = d, sample, reg_note
    if comp["n_never"] == 0 and any(e in estimators for e in ("sunab", "did2s", "twfe")) or (comp["n_never"] == 0 and poisson):
        # sans unité jamais traitée : même convention que Callaway & Sant'Anna — la dernière cohorte sert de contrôle et la fenêtre
        # s'arrête l'année précédente ; Sun & Abraham, did2s, TWFE et Poisson sont estimés sur cette fenêtre identifiée (A2.5)
        last = int(d.cohort.max())
        d = d[d.year < last].copy()
        d.loc[d.cohort == last, "cohort"] = 0
        sample = sample + f" ; fenêtre identifiée ≤ {last - 1}, cohorte {last} = contrôle"
        reg_note = reg_note + f" ; comparaisons sur la fenêtre identifiée (années < {last}, cohorte {last} recodée contrôle, {int((d.cohort == 0).sum() / max(d.groupby(unit).size().max(), 1))} unités de contrôle)"
    for est in ("sunab", "did2s", "twfe"):
        if est not in estimators:
            continue
        try:
            fn = {"sunab": did.sunab_event_study, "did2s": did.did2s_event_study, "twfe": did.twfe_event_study}[est]
            kw = dict(reg_kw)
            if est != "did2s":
                kw["weights"] = weights
            else:
                # did2s : un effet fixe année × classe de densité n'est pas estimable quand une classe est entièrement traitée
                # certaines années (niveau absent du premier étage, estimé sur les seules observations non traitées)
                kw["extra_fe"] = None
            t = fn(d, y, unit, "year", "cohort", **kw)
            rn = (reg_note + " ; cellules −8 et +8 bornées" + (f" ; covariables invariantes retirées du premier étage : {', '.join(t['dropped_covariates'])}" if t.get("dropped_covariates") else "")
                  + (f" ; sans les effets fixes {extra_fe} (non estimables dans did2s)" if est == "did2s" and extra_fe else ""))
            col.add(family, hyp, outcome, sample, t["event"], nu, no, rn, exploratory, **dict(base_extra, aggregation="event"))
            col.add(family, hyp, outcome, sample, t["post_avg"], nu, no, reg_note + " ; écart-type avec covariance complète (w'Vw)", exploratory,
                    **dict(base_extra, aggregation="post_avg"))
            pw = t["pre_wald"]
            col.add_scalar(family, hyp, outcome, sample, est, f"Wald pré ({WINDOW[0]}..−2)", pw["stat"], np.nan, nu, no,
                           f"test de Wald joint, covariance groupée, df = {pw['df']}" + comp_note, exploratory, p=pw["p_value"], **dict(base_extra, aggregation="pre_test", df=pw["df"]))
            out[est] = t
        except Exception as e:  # noqa: BLE001
            log(f"  {est} non estimé : {e}")
            col.add_scalar(family, hyp, outcome, sample, est, "non estimé", np.nan, np.nan, nu, no, f"erreur : {str(e)[:200]}", exploratory, **dict(base_extra, aggregation="note"))
    if "twfe" in estimators:
        try:
            col.add(family, hyp, outcome, sample, did.twfe_att(d, y, unit, "year", "cohort", weights=weights, **reg_kw), nu, no, reg_note, exploratory,
                    **dict(base_extra, aggregation="static"))
            if d is not d_full:      # complément : TWFE statique sur la fenêtre complète (toutes les cohortes traitées, pas de contrôle jamais traité)
                col.add(family, hyp, outcome, sample_full + " ; fenêtre complète", did.twfe_att(d_full, y, unit, "year", "cohort", weights=weights, **reg_kw), nu, no,
                        reg_note_full + " ; TWFE sur toutes les années (identification par le calendrier des bascules seulement)", True, **dict(base_extra, aggregation="static"))
        except Exception as e:  # noqa: BLE001
            log(f"  TWFE statique non estimé : {e}")
    if poisson:
        count, expo = poisson
        try:
            t = did.twfe_att(d, count, unit, "year", "cohort", poisson=True, exposure=expo, **reg_kw)
            t.loc[0, "term"] = "ATT (log du taux contrefactuel)"
            col.add(family, hyp, outcome, sample, t, nu, no, reg_note + f" ; Poisson à effets fixes, offset = log({expo})", exploratory,
                    **dict(base_extra, aggregation="static"))
        except Exception as e:  # noqa: BLE001
            log(f"  Poisson non estimé : {e}")
            col.add_scalar(family, hyp, outcome, sample, "twfe_poisson", "non estimé", np.nan, np.nan, nu, no, f"erreur : {str(e)[:200]}", exploratory,
                           **dict(base_extra, aggregation="note"))
    return out


def holm_family(col: Collector, family: str, hyp: str, sample: str, members: list[tuple], label: str) -> None:
    """``members`` = (outcome, est, se, n_units, n_obs, term, info) ; ajoute une ligne par membre avec la p corrigée de Holm."""
    if not members:
        return
    ps = [did.p_from_z(m[1], m[2]) for m in members]
    ks = sorted(set(m[6]["k_post"] for m in members))
    for (outcome, e, s, nu, no, term, info), p0, pa in zip(members, ps, did.holm(ps)):
        col.add_scalar(family, hyp, outcome, sample, "cs", f"{term} (Holm)", e, s, nu, no,
                       f"p brut {p0:.4f}, p Holm {pa:.4f} (famille : {label}, {len(members)} tests" + (f" ; k diffère dans la famille : {ks}" if len(ks) > 1 else "") + ")",
                       aggregation="post_avg_holm", p_holm=pa, k_post=info["k_post"], years_model_min=info["years_model"][0], years_model_max=info["years_model"][1],
                       n_clusters=info["n_clusters"])


def _member(rg: dict, outcome: str, sub: pd.DataFrame, unit_col: str = "dep") -> tuple:
    pa = rg["cs"]["post_avg"].iloc[0]
    return (outcome, float(pa.estimate), float(pa.se), sub[unit_col].nunique(), len(sub), pa.term, rg["cs"]["info"])


def long_difference(d: pd.DataFrame, y: str, unit: str, y0: int, y1: int, x: str, covs: list[str] | None = None,
                    cluster: str | None = None, weights: str | None = None) -> tuple[pd.DataFrame, int]:
    """Différence longue y(y1) − y(y0) régressée sur ``x`` (indicatrice de bascule avant y1, ou années d'exposition)
    avec covariables ; erreurs groupées par ``cluster`` (ou robustes). Pour les résultats observés aux seuls millésimes RP."""
    import pyfixest as pf

    w = d[d.year.isin([y0, y1])].pivot_table(index=unit, columns="year", values=y)
    w = w.dropna()
    w["dy"] = w[y1] - w[y0]
    stat = d.drop_duplicates(unit).set_index(unit)
    w[x] = stat[x].reindex(w.index)
    cols = [x]
    if covs:
        for c in covs:
            w[c] = stat[c].reindex(w.index)
        cols += covs
    if cluster and cluster != unit:
        w[cluster] = stat[cluster].reindex(w.index)
    if weights:
        w[weights] = stat[weights].reindex(w.index)
    w = w.dropna(subset=cols + ([cluster] if cluster and cluster != unit else []) + ([weights] if weights else [])).reset_index()
    vc = {"CRV1": cluster} if cluster and cluster != unit else "hetero"
    m = pf.feols(f"dy ~ {' + '.join(cols)}", data=w, vcov=vc, weights=weights)
    t = m.tidy().reset_index()
    t = t[t["Coefficient"] == x]
    return did._tidy([f"Δ{y0}→{y1} sur {x}"], t["Estimate"], t["Std. Error"], "long_diff"), len(w)


# ----------------------------------------------------------------------------- H1 : effet total, commune

def part_h1(args) -> None:
    col = Collector("h1")
    cog = Cog(next(iter(raw_files("fr_insee_cog"))))
    cov = covariates_commune(cog)
    d = commune_panel().merge(cov[["unit"] + COVS + ["dens_cat"]], on="unit", how="left")
    dc = d.dropna(subset=COVS)
    nev_all, nev_c = d[d.cohort == 0].unit.nunique(), dc[dc.cohort == 0].unit.nunique()
    share_w = dc.drop_duplicates("unit").w_f1544.sum() / d.drop_duplicates("unit").w_f1544.sum()
    log(f"H1 : {d.unit.nunique():,} unités, {len(d):,} obs ; avec covariables : {dc.unit.nunique():,} unités ({share_w:.1%} des femmes 15-44 de 2011 ; "
        f"jamais traitées {nev_c:,} sur {nev_all:,})")
    cov_note = (f"spécification primaire préenregistrée ; communes avec les 5 covariables : {dc.unit.nunique():,} sur {d.unit.nunique():,} "
                f"({share_w:.1%} des femmes 15-44 RP 2011), jamais traitées {nev_c:,} sur {nev_all:,} ; moyenne non pondérée entre communes")
    # primaire : CS doublement robuste avec contrôles de pré-période, pas-encore-traités, grappes commune, bandes sup-t
    run_block(col, dc, "y_log", "H1", "H1", Y_COMMUNE, "primaire : communes avec covariables", "unit",
              covs=COVS, boot=args.boot, nboot_cluster=args.nboot_commune, estimators=("cs",), notes=cov_note, balanced_post=True)
    # comparaisons (préreg. §5 : toujours rapportées) sur la même spécification : SA, did2s, TWFE avec covariables et
    # effets fixes année × classe de densité (chocs concurrents §4.1), Poisson avec offset
    run_block(col, dc, "y_log", "H1", "H1", Y_COMMUNE, "communes avec covariables, comparaisons", "unit",
              covs=COVS, estimators=("sunab", "did2s", "twfe"), extra_fe="year^dens_cat",
              poisson=("births", "women_1544"), notes="comparaisons de la spécification primaire")
    # sans covariables, toutes les communes ; CS et comparaisons
    run_block(col, d, "y_log", "H1", "H1", Y_COMMUNE, "toutes communes, sans covariables", "unit",
              boot=args.boot, extra_fe="year^dens_cat", poisson=("births", "women_1544"))
    # contrôle = jamais traitées
    run_block(col, dc, "y_log", "H1", "H1", Y_COMMUNE, "covariables, contrôle = jamais traitées", "unit",
              covs=COVS, control="never_treated", estimators=("cs",))
    # covariables par régression de résultat seule (sans pondération par le score de propension : les covariables des très
    # petites communes — chômage 15-24 à 0 ou 1, tendance ±1 — rendent les poids IPW instables ; constaté au test de fonctionnement, A2)
    run_block(col, dc, "y_log", "H1", "H1", Y_COMMUNE, "communes avec covariables, régression de résultat seule (est_method = reg)", "unit",
              covs=COVS, estimators=("cs",), est_method="reg", exploratory=True, notes="complément A2 : sensibilité à la composante IPW de l'estimateur doublement robuste")
    # sensibilité à la transformation
    for y, lab in (("y_rate", "naissances / 1 000 f. 15-44 (taux brut)"), ("y_asinh", "asinh(taux)")):
        run_block(col, dc, y, "H1", "H1", lab, "communes avec covariables", "unit", covs=COVS, estimators=("cs",))
    # complément (A2) : référence −2 (année −1 partiellement exposée : 4G en service en médiane 5 mois avant le 1er janvier,
    # et délai de gestation)
    run_block(col, dc, "y_log", "H1", "H1", Y_COMMUNE, "communes avec covariables, référence −2 (anticipation = 1)", "unit",
              covs=COVS, estimators=("cs",), anticipation=1, exploratory=True,
              notes="complément A2 : l'année −1 est partiellement exposée ; le primaire (référence −1) est une borne basse en valeur absolue si l'effet commence avec l'exposition")
    # pondéré par les femmes 15-44 de 2011 (effet moyen par femme plutôt que par commune) : CS sans covariables (l'estimateur
    # doublement robuste pondéré de ``differences`` n'est pas invariant à l'échelle des poids et donne des écarts-types
    # aberrants sur ce panel : constaté au test de fonctionnement, A2) ; TWFE pondéré avec covariables en comparaison
    run_block(col, dc, "y_log", "H1", "H1", Y_COMMUNE, "communes avec covariables, pondéré par les femmes 15-44 (RP 2011), CS sans covariables", "unit",
              estimators=("cs",), weights="w_f1544", exploratory=True, notes="complément A2 : pondération ; CS sans covariables (voir A2)")
    run_block(col, dc, "y_log", "H1", "H1", Y_COMMUNE, "communes avec covariables, pondéré par les femmes 15-44 (RP 2011)", "unit",
              covs=COVS, estimators=("twfe",), extra_fe="year^dens_cat", weights="w_f1544", exploratory=True, notes="complément A2 : pondération")
    col.save()


# ----------------------------------------------------------------------------- H2 : effet par âge, département

def part_h2(args) -> None:
    col = Collector("h2")
    d = dep_age_panel()
    a2539 = aggregate_ages(d, G2539, "25-39")
    a1524 = aggregate_ages(d, G1524, "15-24")
    samp = "département, bascule D3 ≥ 50 %"
    log(f"H2 : {d.dep.nunique()} départements, cohortes D3 ≥ 50 % : {sorted(d.cohort.unique())}")
    # H2b (test primaire) : 25-39 agrégé
    r = run_block(col, a2539, "y_log", "H2", "H2b", Y_2539, samp, "unit", cluster="dep", boot=args.boot, nboot_cluster=args.nboot,
                  poisson=("births", "women"), notes="test primaire du papier", balanced_post=True)
    run_block(col, a2539, "y_log", "H2", "H2b", Y_2539, samp + ", référence −2 (anticipation = 1)", "unit", cluster="dep",
              estimators=("cs",), anticipation=1, exploratory=True, notes="complément A2 : année −1 partiellement exposée")
    # H2a, H2c : groupes séparés ; familles de Holm (A2 : H2a corrigée aussi)
    # sensibilité à la transformation (préreg. §5) pour H2b
    for yv, lab in (("births_per_1000", "naissances / 1 000 f. 25-39 (taux brut)"), ("y_asinh", "asinh(naissances / 1 000 f. 25-39)")):
        a2539["y_asinh"] = np.arcsinh(a2539.births_per_1000)
        run_block(col, a2539, yv, "H2", "H2b", lab, samp, "unit", cluster="dep", estimators=("cs",))
    # forme préenregistrée (§5) : doublement robuste avec les covariables de pré-période agrégées au département (A2.5)
    cog = Cog(next(iter(raw_files("fr_insee_cog"))))
    sampc = samp + ", covariables de pré-période agrégées"
    rc = run_block(col, with_dep_covs(a2539, cog), "y_log", "H2", "H2b", Y_2539, sampc, "unit", cluster="dep", covs=COVS_DEP, boot=args.boot,
                   estimators=("cs",), notes="forme préenregistrée (doublement robuste avec covariables) ; voir A2.5 sur l'ordre d'ajout", balanced_post=True)
    fam_a, fam_c, fam_ac, fam_cc = [], [], [], []
    for g in GROUPS:
        sub = d[d.age_group == g]
        hyp_g = "H2a" if g in G1524 else "H2c"
        rg = run_block(col, sub, "y_log", "H2", hyp_g, f"log(naissances / 1 000 f. {g})", samp, "unit", cluster="dep", poisson=("births", "women"))
        if "cs" in rg:
            (fam_a if g in G1524 else fam_c).append(_member(rg, f"log(naissances / 1 000 f. {g})", sub))
        rgc = run_block(col, with_dep_covs(sub, cog), "y_log", "H2", hyp_g, f"log(naissances / 1 000 f. {g})", sampc, "unit", cluster="dep", covs=COVS_DEP, estimators=("cs",))
        if "cs" in rgc:
            (fam_ac if g in G1524 else fam_cc).append(_member(rgc, f"log(naissances / 1 000 f. {g})", sub))
    holm_family(col, "H2", "H2c", samp, fam_c, "25-29, 30-34, 35-39, 40-49")
    holm_family(col, "H2", "H2a", samp, fam_a, "15-19, 20-24")
    holm_family(col, "H2", "H2c", sampc, fam_cc, "25-29, 30-34, 35-39, 40-49 (avec covariables)")
    holm_family(col, "H2", "H2a", sampc, fam_ac, "15-19, 20-24 (avec covariables)")
    # H2d : égalité 15-24 vs 25-39 — différence des ATT[1,k] avec bootstrap conjoint par département (stratifié par cohorte)
    r1 = run_block(col, a1524, "y_log", "H2", "H2d", "log(naissances / 1 000 f. 15-24)", samp, "unit", cluster="dep", estimators=("cs",))
    if "cs" in r and "cs" in r1:
        p1, p2 = r1["cs"]["post_avg"].iloc[0], r["cs"]["post_avg"].iloc[0]
        base = d[d.age_group.isin(G1524 + G2539)].dropna(subset=["y_log"])

        def stat(b):
            x1 = aggregate_ages(b, G1524, "15-24")
            x2 = aggregate_ages(b, G2539, "25-39")
            return did.cs_post_avg(x1, "y_log", "unit", "year", "cohort") - did.cs_post_avg(x2, "y_log", "unit", "year", "cohort")

        bs = did.cluster_bootstrap(base, "dep", stat, n_boot=args.nboot, seed=1, strata="cohort")
        diff = float(p1.estimate - p2.estimate)
        col.add_scalar("H2", "H2d", "ATT 15-24 − ATT 25-39", samp, "cs", "différence (bootstrap conjoint)", diff, bs["se_boot"], d.dep.nunique(), len(base),
                       f"bootstrap par département stratifié par cohorte, {bs['n_boot_ok']} tirages, les deux ATT recalculés sur chaque tirage ; "
                       f"quantiles [{bs['q025']:+.4f}, {bs['q975']:+.4f}]", aggregation="difference")
        t = did.difference_test(p1.estimate, p1.se, p2.estimate, p2.se)
        col.add_scalar("H2", "H2d", "ATT 15-24 − ATT 25-39", samp, "cs", "différence (indépendance supposée)", t["diff"], t["se"], d.dep.nunique(), len(base),
                       "pour mémoire : écart-type sous indépendance des deux estimations (mêmes départements : approximation)", aggregation="difference_indep")
    # traitement continu D3 : effets fixes département × âge et année × âge ; et par groupe
    full = d[d.age_group.isin(GROUPS)].dropna(subset=["y_log"])
    t = did.continuous_twfe(full, "y_log", "d3", "dep^age_group + year^age_group", "dep")
    col.add("H2", "H2 continu", "log(naissances / 1 000 f.), tous âges", "département × âge, D3 continu", t, d.dep.nunique(), len(full),
            "effets fixes département × âge et année × âge ; interprétation sous traitement continu (hypothèses plus fortes)", aggregation="continuous")
    for g, sub in [("25-39", a2539), ("15-24", a1524)] + [(g, d[d.age_group == g]) for g in GROUPS]:
        sub = sub.dropna(subset=["y_log"])
        t = did.continuous_twfe(sub, "y_log", "d3", "dep + year", "dep")
        col.add("H2", "H2 continu", f"log(naissances / 1 000 f. {g})", "département, D3 continu", t, sub.dep.nunique(), len(sub),
                "effets fixes département et année (par groupe : complément, hors préregistration)", True, aggregation="continuous")
    # variante bascule 90 %
    d90 = dep_age_panel("cohort_d3_90")
    a90 = aggregate_ages(d90, G2539, "25-39")
    run_block(col, a90, "y_log", "H2", "H2b", Y_2539, "département, bascule D3 ≥ 90 %", "unit", cluster="dep", estimators=("cs",))
    col.save()


# ----------------------------------------------------------------------------- H3 : canal

def _first_negative(ev: pd.DataFrame) -> int | None:
    post = ev[ev.term.astype(int) >= 0].sort_values("term")
    hit = post[(post.estimate < 0) & (post.ci_high < 0)]
    return int(hit.term.iloc[0]) if len(hit) else None


def part_h3(args) -> None:
    col = Collector("h3")
    d = dep_age_panel()
    a2539 = aggregate_ages(d, G2539, "25-39")
    a1524 = aggregate_ages(d, G1524, "15-24")
    a2034 = aggregate_ages(d, ["20-24", "25-29", "30-34"], "20-34")
    samp = "département, bascule D3 ≥ 50 %"
    res = {}
    # H3a (i) mariages pour 1 000 femmes par âge (log ; asinh + Poisson pour les groupes avec cellules nulles, A2)
    cog = Cog(next(iter(raw_files("fr_insee_cog"))))
    for g, sub in [("25-39", a2539), ("15-24", a1524), ("20-34", a2034)] + [(g, d[d.age_group == g]) for g in GROUPS]:
        zeros = int((sub.marriages_f == 0).sum())
        if zeros == 0:
            res[f"mar_{g}"] = run_block(col, sub, "y_mar", "H3", "H3a", f"log(mariages de femmes / 1 000 f. {g})", samp, "unit", cluster="dep",
                                        estimators=("cs", "twfe"), poisson=("marriages_f", "women"), boot=args.boot if g == "25-39" else 0,
                                        exploratory=(g == "20-34"), notes="test H3a entrant dans la règle §6" if g == "25-39" else ("agrégat 20-34 : complément" if g == "20-34" else ""))
            if g == "25-39":
                run_block(col, with_dep_covs(sub, cog, "y_mar"), "y_mar", "H3", "H3a", f"log(mariages de femmes / 1 000 f. {g})", samp + ", covariables de pré-période agrégées",
                          "unit", cluster="dep", covs=COVS_DEP, estimators=("cs",), notes="forme préenregistrée (doublement robuste), A2.5")
        else:
            res[f"mar_{g}"] = run_block(col, sub, "y_mar_asinh", "H3", "H3a", f"asinh(mariages de femmes / 1 000 f. {g})", samp, "unit", cluster="dep",
                                        estimators=("cs", "twfe"), poisson=("marriages_f", "women"),
                                        notes=f"{zeros} cellules à zéro mariage (codées 0, A2) : asinh au lieu du log, Poisson en comparaison")
    # H3a (ii) PACS pour 1 000 femmes 15-49, département, 2007-2016
    dp = pd.read_parquet(PROC / "fr_outcomes_dep.parquet")
    dt = pd.read_parquet(PROC / "fr_treatment_dep.parquet").drop_duplicates("dep").set_index("dep")
    dp = dp[dp.dep.isin(d.dep.unique()) & dp.year.between(2007, 2016)].copy()      # départements métropolitains du panel
    dp["cohort"] = dp.dep.map(dt.cohort_d3_50).fillna(0).astype(int)
    dp["y_pacs"] = np.log(dp.pacs_per_1000_f1549.where(dp.pacs_per_1000_f1549 > 0))
    dp["unit"] = dp.dep
    run_block(col, dp, "y_pacs", "H3", "H3a", "log(PACS / 1 000 f. 15-49)", "département, 2007-2016 (série PACS disponible)", "unit",
              cluster="dep", estimators=("cs", "twfe"), notes="fenêtre courte : effets +1..+3 seulement pour les cohortes 2013-2015")
    # H3a (iii) part des 15-24 et 25-39 ans vivant en couple : (a) millésimes RP seuls, différences longues ; (b) interpolation (lissée, A2)
    cov = covariates_commune(cog)
    c = commune_panel().merge(cov[["unit"] + COVS], on="unit", how="left")
    c["treated_by_2016"] = ((c.cohort > 0) & (c.cohort <= 2016)).astype(float)
    c["exposure_2021"] = np.clip(2021 - c.cohort + 1, 0, None).where(c.cohort > 0, 0.0)
    for v, lab in (("share_couple_1524", "part des 15-24 ans en couple"), ("share_couple_2539", "part des 25-39 ans en couple")):
        sub = c.dropna(subset=[v]).copy()
        for (y0, y1, x, xl) in ((2011, 2016, "treated_by_2016", "bascule 4G ≤ 2016"), (2011, 2021, "exposure_2021", "années d'exposition à la 4G en 2021")):
            t, n = long_difference(sub, v, "unit", y0, y1, x, covs=COVS, cluster="dep")
            col.add("H3", "H3a", lab + f" (RP {y0} → {y1}, deux sexes)", "commune, différence longue entre millésimes", t, n, n,
                    f"Δ régressée sur {xl} et les covariables de pré-période ; erreurs groupées par département ; observé aux seuls millésimes RP (A2)",
                    aggregation="long_diff")
        run_block(col, sub, v, "H3", "H3a", lab + " (RP, deux sexes, millésimes interpolés)", "commune", "unit", estimators=("cs", "twfe"), exploratory=True,
                  notes="résultat interpolé linéairement entre millésimes RP : coefficients pré mécaniquement contaminés et effet lissé ; lecture descriptive seulement (A2)")
    # H3a (iii) au département (préreg. §4.1 : « commune et département ») : part en couple aux millésimes, différences longues
    for g, cols_c, cols_p in (("15-24", ["p1519_couple", "p2024_couple"], ["p1519", "p2024"]), ("25-39", ["p2539_couple"], ["p2539"])):
        sd = a2539.copy() if g == "25-39" else a1524.copy()
        sd["share_couple"] = sd[cols_c].sum(axis=1) / sd[cols_p].sum(axis=1)
        sd["treated_by_2016"] = ((sd.cohort > 0) & (sd.cohort <= 2016)).astype(float)
        sd["exposure_2021"] = np.clip(2021 - sd.cohort + 1, 0, None).where(sd.cohort > 0, 0.0)
        for (y0, y1, x, xl) in ((2011, 2016, "treated_by_2016", "bascule D3 ≥ 50 % ≤ 2016"), (2011, 2021, "exposure_2021", "années d'exposition en 2021")):
            t, n = long_difference(sd[sd.rp_millesime | sd.year.isin([y0, y1])], "share_couple", "dep", y0, y1, x)
            col.add("H3", "H3a", f"part des {g} ans en couple (RP {y0} → {y1}, deux sexes)", "département, différence longue entre millésimes", t, n, n,
                    f"Δ régressée sur {xl} ; erreurs robustes ; millésimes RP seuls (A2)", aggregation="long_diff")
    # H3b : naissances pour 1 000 femmes en couple (dénominateur = moitié des personnes en couple du groupe, RP interpolé ; A2)
    for g, sub in (("25-39", a2539), ("15-24", a1524)):
        sub = sub.copy()
        res[f"cpl_{g}"] = run_block(col, sub, "y_couple", "H3", "H3b", f"log(naissances / 1 000 f. en couple {g})", samp + ", femmes en couple interpolées entre millésimes",
                                    "unit", cluster="dep", estimators=("cs", "twfe"), boot=args.boot if g == "25-39" else 0,
                                    notes=("test H3b entrant dans la règle §6 ; " if g == "25-39" else "") + "dénominateur interpolé entre millésimes RP (2006-2022), prolongé 2 ans")
        if g == "25-39":
            run_block(col, with_dep_covs(sub, cog, "y_couple"), "y_couple", "H3", "H3b", f"log(naissances / 1 000 f. en couple {g})",
                      samp + ", femmes en couple interpolées, covariables de pré-période agrégées", "unit", cluster="dep", covs=COVS_DEP, estimators=("cs",),
                      notes="forme préenregistrée (doublement robuste), A2.5")
        sub["treated_by_2016"] = ((sub.cohort > 0) & (sub.cohort <= 2016)).astype(float)
        sub["exposure_2021"] = np.clip(2021 - sub.cohort + 1, 0, None).where(sub.cohort > 0, 0.0)
        for (y0, y1, x, xl) in ((2011, 2016, "treated_by_2016", "bascule D3 ≥ 50 % ≤ 2016"), (2011, 2021, "exposure_2021", "années d'exposition en 2021")):
            t, n = long_difference(sub[sub.rp_millesime | sub.year.isin([y0, y1])], "y_couple", "dep", y0, y1, x)
            col.add("H3", "H3b", f"log(naissances / 1 000 f. en couple {g}) (RP {y0} → {y1})", "département, différence longue entre millésimes", t, n, n,
                    f"Δ régressée sur {xl} ; erreurs robustes ; millésimes RP seuls (A2)", aggregation="long_diff")
    # complément : naissances de parents mariés pour 1 000 femmes (1998-2021) — pas le H3b préenregistré (dénominateur = toutes les femmes)
    db = d[d.married_available == True]  # noqa: E712
    b2539 = aggregate_ages(db, G2539, "25-39")
    run_block(col, b2539, "y_bmar", "H3", "H3b complément", "log(naissances de parents mariés / 1 000 f. 25-39)", "département, 1998-2021", "unit",
              cluster="dep", estimators=("cs", "twfe"), poisson=("births_married", "women"),
              notes="complément : dénominateur = toutes les femmes (les femmes mariées par âge ne sont pas disponibles au département)")
    b2539["share_married"] = b2539.births_married / b2539.births
    run_block(col, b2539, "share_married", "H3", "H3b complément", "part des naissances de parents mariés, 25-39", "département, 1998-2021", "unit",
              cluster="dep", estimators=("cs", "twfe"), exploratory=True)
    for g in GROUPS:
        sub = db[db.age_group == g].copy()
        zeros = int((sub.births_married == 0).sum())
        if zeros:
            run_block(col, sub, "births_married", "H3", "H3b complément", f"naissances de parents mariés {g} (Poisson)", "département, 1998-2021", "unit",
                      cluster="dep", estimators=(), poisson=("births_married", "women"), exploratory=True, notes=f"{zeros} cellules nulles : Poisson avec offset seulement")
        else:
            run_block(col, sub, "y_bmar", "H3", "H3b complément", f"log(naissances de parents mariés / 1 000 f. {g})", "département, 1998-2021", "unit",
                      cluster="dep", estimators=("cs",), exploratory=True)
    # H3c (calendrier) : première période relative ≥ 0 où l'event study CS est négative avec IC excluant 0, pour les unions
    # (mariages 25-39), les naissances par femme en couple 25-39 et les naissances 25-39 (H2b, ré-estimée ici à l'identique)
    res["births_25-39"] = {"cs": did.cs_event_study(did.drop_always_treated(a2539.dropna(subset=["y_log"]), "year", "cohort", MIN_PRE), "y_log", "unit", "year", "cohort", cluster="dep")}
    for key, lab in (("mar_25-39", "mariages 25-39"), ("cpl_25-39", "naissances / f. en couple 25-39"), ("births_25-39", "naissances 25-39 (H2b)")):
        if key in res and "cs" in res[key]:
            k = _first_negative(res[key]["cs"]["event"])
            col.add_scalar("H3", "H3c", lab, samp, "cs", "première période négative (IC 95 % < 0)", np.nan if k is None else k, np.nan, 0, 0,
                           "aucune période post avec coefficient négatif et IC ponctuel excluant 0" if k is None else f"période relative +{k}", aggregation="timing")
    # règle de décision §6 : H3a (mariages 25-39) vs H3b (naissances / femmes en couple 25-39), différence des ATT[1,k]
    # (deux résultats en log : effets standardisés = log-points), bootstrap conjoint par département stratifié par cohorte
    if "cs" in res.get("mar_25-39", {}) and "cs" in res.get("cpl_25-39", {}):
        pa, pb = res["mar_25-39"]["cs"]["post_avg"].iloc[0], res["cpl_25-39"]["cs"]["post_avg"].iloc[0]
        base = d[d.age_group.isin(G2539)].copy()

        def stat(b):
            x = aggregate_ages(b, G2539, "25-39")
            return did.cs_post_avg(x, "y_mar", "unit", "year", "cohort") - did.cs_post_avg(x, "y_couple", "unit", "year", "cohort")

        bs = did.cluster_bootstrap(base, "dep", stat, n_boot=args.nboot, seed=1, strata="cohort")
        col.add_scalar("H3", "§6 canal", "ATT mariages 25-39 − ATT naissances / f. en couple 25-39", samp, "cs", "différence (bootstrap conjoint)",
                       float(pa.estimate - pb.estimate), bs["se_boot"], d.dep.nunique(), len(base),
                       f"règle §6 : H3a = {pa.term} mariages 25-39 = {pa.estimate:+.4f} (p {did.p_from_z(pa.estimate, pa.se):.3f}) ; H3b = {pb.term} naissances "
                       f"/ femmes en couple 25-39 = {pb.estimate:+.4f} (p {did.p_from_z(pb.estimate, pb.se):.3f}) ; {bs['n_boot_ok']} tirages, "
                       f"quantiles [{bs['q025']:+.4f}, {bs['q975']:+.4f}]", aggregation="decision")
    col.add_scalar("H3", "H3", "famille H3", samp, "—", "note", np.nan, np.nan, 0, 0,
                   "H3 présentée sans correction de tests multiples ; seuls les deux tests nommés dans la ligne « §6 canal » entrent dans la règle de décision (A2)",
                   aggregation="note")
    col.save()


# ----------------------------------------------------------------------------- H5 : placebos

def part_h5(args) -> None:
    col = Collector("h5")
    cog = Cog(next(iter(raw_files("fr_insee_cog"))))
    cov = covariates_commune(cog)
    d = commune_panel().merge(cov[["unit"] + COVS + ["dens_cat"]], on="unit", how="left")
    # H5a : bascule fictive décalée de −3 ans, estimée sur les seules années antérieures à la vraie bascule
    f = d.copy()
    f["true_cohort"] = f.cohort
    f = f[(f.true_cohort == 0) | (f.year < f.true_cohort)].copy()
    f["cohort"] = np.where(f.true_cohort > 0, f.true_cohort - 3, 0)
    f = f[(f.cohort == 0) | (f.cohort >= COMMUNE_YEARS[0] + MIN_PRE)]
    pl_note = "placebo : aucun effet attendu ; périodes relatives fictives ≤ +2 ; H5a et H5c testent la même hypothèse de tendances parallèles sous deux normalisations"
    run_block(col, f, "y_log", "H5", "H5a", Y_COMMUNE, "commune, bascule fictive −3 ans, années pré-traitement seules", "unit",
              estimators=("cs", "twfe"), extra_fe="year^dens_cat", notes=pl_note, balance=False)
    fc = f.dropna(subset=COVS)
    run_block(col, fc, "y_log", "H5", "H5a", Y_COMMUNE, "commune, bascule fictive −3 ans, covariables", "unit", covs=COVS, estimators=("cs",),
              notes=pl_note, balance=False)
    # H5b : décès pour 1 000 habitants (résultat sans lien attendu), vraie bascule
    run_block(col, d, "y_deaths", "H5", "H5b", "log(décès+0,5 / 1 000 hab.)", "commune", "unit", estimators=("cs", "twfe"), extra_fe="year^dens_cat",
              notes="placebo : décès totaux (décès des 60 ans et plus non disponibles au niveau commune, addendum A1)")
    run_block(col, d.dropna(subset=COVS), "y_deaths", "H5", "H5b", "log(décès+0,5 / 1 000 hab.)", "commune, covariables", "unit", covs=COVS, estimators=("cs",),
              notes="placebo : décès totaux")
    # H5c : test de Wald pré (−8..−2) de la spécification primaire, et sans la tendance 2008-2011 (A2 : cette covariable est
    # construite sur les résultats 2008-2011, ce qui contamine mécaniquement les coefficients pré de ces années)
    dc = d.dropna(subset=COVS)
    run_block(col, dc, "y_log", "H5", "H5c", Y_COMMUNE, "primaire : communes avec covariables", "unit", covs=COVS, estimators=("cs",),
              notes="H5c sur la spécification primaire (même estimation que H1, répétée ici)")
    run_block(col, dc, "y_log", "H5", "H5c", Y_COMMUNE, "communes avec covariables sans la tendance 2008-2011", "unit", covs=COVS_NOPRE, estimators=("cs",),
              notes="H5c sans pretrend_0811 (A2)")
    # H5a au niveau département × âge (25-39)
    dd = dep_age_panel()
    a = aggregate_ages(dd, G2539, "25-39")
    a["true_cohort"] = a.cohort
    a = a[(a.true_cohort == 0) | (a.year < a.true_cohort)].copy()
    a["cohort"] = np.where(a.true_cohort > 0, a.true_cohort - 3, 0)
    run_block(col, a, "y_log", "H5", "H5a", Y_2539, "département, bascule fictive −3 ans, années pré-traitement seules", "unit",
              cluster="dep", estimators=("cs", "twfe"), notes=pl_note, balance=False)
    # H5c au niveau département (même estimation que H2b, répétée ici pour la famille H5)
    a = aggregate_ages(dd, G2539, "25-39")
    run_block(col, a, "y_log", "H5", "H5c", Y_2539, "département, bascule D3 ≥ 50 %", "unit", cluster="dep", estimators=("cs",),
              notes="H5c sur la spécification H2b (même estimation, répétée ici)")
    col.save()


# ----------------------------------------------------------------------------- H6 : hétérogénéité (commune)

def part_h6(args) -> None:
    col = Collector("h6")
    cog = Cog(next(iter(raw_files("fr_insee_cog"))))
    cov = covariates_commune(cog)
    d = commune_panel().merge(cov[["unit"] + COVS + ["med12", "dens_cat"]], on="unit", how="left").dropna(subset=COVS)
    fam = []

    def sub_block(mask, label):
        sub = d[mask]
        r = run_block(col, sub, "y_log", "H6", "H6", Y_COMMUNE, label, "unit", covs=COVS, estimators=("cs",),
                      notes="spécification primaire (covariables, pas-encore-traités) sur le sous-groupe")
        if "cs" in r:
            fam.append(_member(r, Y_COMMUNE + " — " + label, sub, "unit"))
        run_block(col, sub, "y_log", "H6", "H6", Y_COMMUNE, label + " (régression de résultat seule)", "unit", covs=COVS, estimators=("cs",),
                  est_method="reg", exploratory=True, notes="complément A2 : sans la composante IPW (poids instables sur les petits sous-groupes)")

    for k, lab in ((1, "densité : dense (grille 1)"), (2, "densité : intermédiaire (grille 2-4)"), (3, "densité : rural (grille 5-7)")):
        sub_block(d.dens_cat == k, lab)
    for var, name in (("med12", "revenu médian 2012"), ("share_fsup", "part de diplômées du supérieur 2011")):
        ter = d.drop_duplicates("unit").dropna(subset=[var])
        q = ter[var].quantile([1 / 3, 2 / 3]).values
        tmap = ter.set_index("unit")[var].map(lambda x: 1 if x <= q[0] else 2 if x <= q[1] else 3)
        d["_ter"] = d.unit.map(tmap)
        for k in (1, 2, 3):
            sub_block(d._ter == k, f"{name} : tercile {k}")
    sub_block(d.zdp == True, "ZDP")  # noqa: E712
    sub_block(d.zdp == False, "hors ZDP")  # noqa: E712
    holm_family(col, "H6", "H6", "communes avec covariables", fam, f"les {len(fam)} sous-groupes H6")
    # rang de naissance (H6) : disponible 1998-2012 seulement, avant toute bascule D3 (2013) → non testable
    col.add_scalar("H6", "H6", "part des naissances de rang 1", "département", "—", "non testable", np.nan, np.nan, 0, 0,
                   "le rang de naissance n'est renseigné que jusqu'en 2012, avant la première bascule départementale (2013)", aggregation="note")
    col.save()


# ----------------------------------------------------------------------------- robustesse (commune)

def part_robust(args) -> None:
    col = Collector("robust")
    cog = Cog(next(iter(raw_files("fr_insee_cog"))))
    cov = covariates_commune(cog)
    cc = ["unit"] + COVS + ["dens_cat"]
    base = commune_panel().merge(cov[cc], on="unit", how="left").dropna(subset=COVS)
    y, lab, hyp = "y_log", Y_COMMUNE, "H1"
    kw = dict(covs=COVS, estimators=("cs",))
    run_block(col, base[base.year <= 2019], y, "robustesse", hyp, lab, "fenêtre 2008-2019 (préreg.) ; cohortes 2020-2024 = contrôle", "unit", **kw)
    run_block(col, base[base.year <= 2022], y, "robustesse", hyp, lab, "fenêtre 2008-2022 (dernier millésime du dénominateur)", "unit", exploratory=True, **kw)
    run_block(col, base[~base.year.isin([2020, 2021])], y, "robustesse", hyp, lab, "sans 2020-2021", "unit", **kw)
    run_block(col, base[~base.cohort.between(2013, 2014)], y, "robustesse", hyp, lab, "hors cohortes 2013-2014 (préreg. : 2012-2014)", "unit", **kw)
    run_block(col, base[~base.cohort.between(2013, 2017)], y, "robustesse", hyp, lab, "hors cohortes 2013-2017 (addendum A1)", "unit", **kw)
    run_block(col, base[base.dens_cat != 1], y, "robustesse", hyp, lab, "hors grands centres urbains (densité 1)", "unit", exploratory=True, **kw)
    run_block(col, base, y, "robustesse", hyp, lab, "grappes = département", "unit", cluster="dep", covs=COVS, estimators=("cs", "twfe"))
    run_block(col, base[base.w_f1544 >= 20], y, "robustesse", hyp, lab, "communes d'au moins 20 femmes 15-44 en 2011", "unit", exploratory=True, **kw)
    strict = base[~base.cohort.between(2025, 2027)]
    run_block(col, strict, y, "robustesse", hyp, lab, "contrôle = jamais traitées strictes (cohortes 2025-2027 exclues)", "unit",
              covs=COVS, control="never_treated", estimators=("cs",), exploratory=True)
    # DOM inclus (préreg. §4.1 : DOM en robustesse) ; Filosofi 2012 ne couvre pas les DOM → covariables sans le revenu (A2.5)
    covs_dom = [c for c in COVS if c != "log_med12"]
    dom = commune_panel(metro_only=False).merge(cov[cc], on="unit", how="left").dropna(subset=covs_dom)
    n_dom = dom[~dom.metro].unit.nunique()
    if n_dom:
        run_block(col, dom, y, "robustesse", hyp, lab, f"France entière, DOM inclus ({n_dom} communes d'outre-mer) ; covariables sans le revenu médian", "unit",
                  covs=covs_dom, estimators=("cs",), notes="Filosofi 2012 ne couvre pas les DOM : revenu médian retiré des covariables (A2.5)")
    else:
        col.add_scalar("robustesse", hyp, lab, "France entière, DOM inclus", "—", "non estimable", np.nan, np.nan, 0, 0, "aucune commune d'outre-mer avec covariables", aggregation="note")
    # définitions alternatives du traitement
    for ccol, lab2 in (("cohort_4g_obs_only", "D1 observatoire seul"), ("cohort_4g_2op", "deuxième opérateur 4G")):
        dd = commune_panel(ccol).merge(cov[cc], on="unit", how="left").dropna(subset=COVS)
        run_block(col, dd, y, "robustesse", hyp, lab, f"traitement = {lab2}", "unit", **kw)
    dd = commune_panel("cohort_4g_arcep").merge(cov[cc], on="unit", how="left").dropna(subset=COVS)
    n_cens = dd[dd.cohort == 2019].unit.nunique()        # cohorte ARCEP 2019 = site déjà présent au premier trimestre observé (2018-T4) : censure à gauche
    dd = dd[(dd.cohort == 0) | (dd.cohort >= 2020)]
    run_block(col, dd, y, "robustesse", hyp, lab, f"traitement = premier site 4G commercial ARCEP, cohortes datées ≥ 2020 ({n_cens} communes censurées à gauche exclues)", "unit",
              notes="composition différente : communes tardives seulement ; la cohorte ARCEP 2019 (site déjà présent au 2018-T4, premier trimestre disponible) est exclue, pas recodée (A2.5)", **kw)
    dd = commune_panel("cohort_3g").merge(cov[cc], on="unit", how="left").dropna(subset=COVS)
    dd = dd[(dd.cohort == 0) | dd.cohort.between(2011, 2012)]
    run_block(col, dd, y, "robustesse", "3G", lab, "traitement = premier émetteur UMTS, cohortes 2011-2012 (préreg. : 2008-2012 ; 2008-2010 < 3 ans de pré-période)", "unit",
              notes="3G en robustesse (préreg.) ; cohortes 3G ≥ 2013 exclues ; cohortes antérieures à 2011 exclues par la règle « ≥ 3 ans »", **kw)
    col.add_scalar("robustesse", hyp, lab, "traitement = D2 (couverture ARCEP ≥ 90 % de la population)", "—", "non construit", np.nan, np.nan, 0, 0,
                   "D2 demande un croisement SIG des cartes ARCEP avec les contours communaux (non téléchargés) ; non construit (addendum A1)", aggregation="note")
    col.add_scalar("robustesse", hyp, lab, "contrôle variable : couverture très haut débit fixe (ARCEP)", "—", "non construit", np.nan, np.nan, 0, 0,
                   "préreg. §4.1 : couverture THD fixe en contrôle variable dans le temps ; données non téléchargées à l'Étape 2 ; non estimé (A2)", aggregation="note")
    # niveau département : fenêtres (sans unité jamais traitée, CS n'est identifié que jusqu'en 2017 : les fenêtres qui ne touchent
    # que les années ≥ 2018 donnent par construction la même estimation que le primaire, dit dans la note)
    d = dep_age_panel()
    a = aggregate_ages(d, G2539, "25-39")
    same = "fenêtre sans effet par construction sur les ATT(g,t) identifiés (≤ 2017) : estimation identique au primaire"
    for sub, lab2, nt in ((a[a.year <= 2019], "département, 1998-2019", same), (a[~a.year.isin([2020, 2021])], "département, sans 2020-2021", same),
                          (a[a.year.between(2008, 2019)], "département, 2008-2019 (préreg.)", ""), (a[a.year >= 2008], "département, 2008-2024", "")):
        run_block(col, sub, y, "robustesse", "H2b", Y_2539, lab2, "unit", cluster="dep", estimators=("cs",), notes=nt)
    # DOM au département (préreg. §4.1)
    ddom = dep_age_panel(metro_only=False)
    adom = aggregate_ages(ddom, G2539, "25-39")
    n_dd = adom[~adom.metro].dep.nunique()
    run_block(col, adom, y, "robustesse", "H2b", Y_2539, f"département, DOM inclus ({n_dd} départements d'outre-mer)", "unit", cluster="dep", estimators=("cs",))
    col.save()


# ----------------------------------------------------------------------------- IV (secondaire)

ZEAT_OF_AGE = {"20-24": "18-24 ans", "25-39": "25-39 ans"}     # fécondité 20-24 ↔ classe Baromètre 18-24 ans (seule classe recouvrant 20-24, A2.5)


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
    p = p[p.year.between(2011, 2020)].copy()
    p["zone_id"] = pd.factorize(p.zone)[0]                 # codes entiers : wildboottest et les formules « ^ » de pyfixest l'exigent
    p["age_id"] = (p.age == "25-39").astype(int)
    reps = 999 if args.fast else 9999
    log(f"IV : {len(p)} cellules zone × âge × année, {p.zone.nunique()} zones")
    samp = "ZEAT × année 2011-2020"
    for g in ("20-24", "25-39", "pooled"):
        sub = p if g == "pooled" else p[p.age == g]
        fe = "zone_id^age_id + year^age_id" if g == "pooled" else "zone_id + year"
        try:
            r = did.iv_2sls(sub, "y_log", "smart", "d3", fe, "zone_id", weights="women")
            ru = did.iv_2sls(sub, "y_log", "smart", "d3", fe, "zone_id")          # non pondéré : le wild bootstrap de pyfixest refuse les MCP
            nz = sub.zone.nunique()
            if g != "pooled":
                p_rf = did.wild_p(ru["models"]["reduced_form"], "d3", reps=reps)
                p_fs = did.wild_p(ru["models"]["first_stage"], "d3", reps=reps)
                ar = did.iv_anderson_rubin(sub, "y_log", "smart", "d3", fe, "zone_id", grid=np.linspace(-2, 2, 161), reps=reps // 10)
                n9 = (f" ; {nz} grappes : p du wild cluster bootstrap (Webb, {reps} tirages) sur le modèle non pondéré "
                      f"(forme réduite non pondérée {ru['reduced_form'][0]:+.4f}, premier étage {ru['first_stage'][0]:+.4f})")
            else:   # effets fixes multiples interagis : wild bootstrap et Anderson-Rubin non calculés (comportement non vérifié de wildboottest)
                p_rf, p_fs = did.p_from_z(*r["reduced_form"]), did.p_from_z(*r["first_stage"])
                ar = None
                n9 = f" ; {nz} grappes : p CRV1 seulement (wild bootstrap non calculé avec effets fixes interagis)"
            ptype = "wild_webb" if g != "pooled" else "crv1"
            glab = "18-24 (Baromètre) → naissances 20-24" if g == "20-24" else g
            col.add_scalar("IV", "IV", f"log(naissances / 1 000 f. {g})", samp, "2sls", "forme réduite (D3)", *r["reduced_form"], nz, r["n"],
                           f"effets fixes {fe} ; pondéré par les femmes" + n9 + f" = {p_rf:.3f} (p CRV1 = {did.p_from_z(*r['reduced_form']):.3f})", p=p_rf,
                           aggregation="iv", p_crv1=did.p_from_z(*r["reduced_form"]), p_type=ptype)
            col.add_scalar("IV", "IV", f"possession de smartphone {glab}", samp, "2sls", "premier étage (D3)", *r["first_stage"], nz, r["n"],
                           f"t² CRV1 = {r['first_stage_F']:.1f} (non interprétable selon les seuils usuels à {nz} grappes)" + n9 + f" = {p_fs:.3f}"
                           + (" ; adoption mesurée sur la classe 18-24 ans du Baromètre, seule classe recouvrant 20-24 (A2.5)" if g == "20-24" else ""), p=p_fs, aggregation="iv", p_type=ptype)
            ar_txt = ("non calculé (effets fixes interagis)" if ar is None else "vide (rejet pour tout β de la grille)" if ar["ar_empty"]
                      else f"[{ar['ar_low']:+.2f}, {ar['ar_high']:+.2f}]" + (" (non borné sur la grille)" if ar.get("ar_unbounded") else ""))
            col.add_scalar("IV", "IV", f"log(naissances / 1 000 f. {g})", samp, "2sls", "IV : effet de la possession de smartphone (0→1)", *r["iv"], nz, r["n"],
                           "re-normalisation de la forme réduite ; IC de Wald indicatif (p CRV1) ; intervalle d'Anderson-Rubin (inversion du test wild bootstrap de la forme "
                           f"réduite non pondérée, IV non pondérée {ru['iv'][0]:+.4f}" + (f", grille [{ar['grid'][0]}, {ar['grid'][1]}]" if ar else "") + f") : {ar_txt}",
                           aggregation="iv", ar_low=(ar or {}).get("ar_low", np.nan), ar_high=(ar or {}).get("ar_high", np.nan), iv_unweighted=ru["iv"][0], p_type="crv1")
        except Exception as e:  # noqa: BLE001
            log(f"  IV {g} non estimé : {e}")
            col.add_scalar("IV", "IV", f"log(naissances / 1 000 f. {g})", samp, "2sls", "non estimé", np.nan, np.nan, 0, 0, f"erreur : {str(e)[:200]}", aggregation="note")
    # test partiel de la restriction d'exclusion (préreg. §5) : D3 → taux d'emploi des femmes 25-54 (RP, millésimes 2011, 2016, 2021)
    cog = Cog(next(iter(raw_files("fr_insee_cog"))))
    emp = female_employment_dep(cog)
    dt = pd.read_parquet(PROC / "fr_treatment_dep.parquet")
    coh = dt.drop_duplicates("dep").set_index("dep").cohort_d3_50
    e = emp.merge(dt[["dep", "year", "d3"]], on=["dep", "year"], how="left")
    e = e[e.dep.isin(d.dep.unique())].copy()                    # 96 départements métropolitains du panel
    e["d3"] = e.d3.fillna(0.0)
    e["cohort"] = e.dep.map(coh).fillna(0).astype(int)
    e["treated"] = ((e.cohort > 0) & (e.year >= e.cohort)).astype(float)
    e["unit"] = e.dep
    t = did.continuous_twfe(e, "emp_f2554", "d3", "dep + year", "dep")
    col.add("IV", "exclusion", "taux d'emploi des femmes 25-54 (RP)", "département × millésime RP 2011, 2016, 2021", t, e.dep.nunique(), len(e),
            "test partiel de la restriction d'exclusion : effets fixes département et année, D3 continu ; le RP ne donne pas 25-39 (A2)", aggregation="exclusion")
    t = did.continuous_twfe(e, "emp_f2554", "treated", "dep + year", "dep")
    col.add("IV", "exclusion", "taux d'emploi des femmes 25-54 (RP)", "département × millésime RP 2011, 2016, 2021", t, e.dep.nunique(), len(e),
            "test partiel de la restriction d'exclusion : indicatrice « bascule D3 ≥ 50 % atteinte au millésime »", aggregation="exclusion")
    col.save()


# ----------------------------------------------------------------------------- synthèse

KEY_AGGS = ["post_avg", "post_avg_boot", "post_avg_balanced", "post_avg_holm", "static", "difference", "continuous", "iv", "exclusion", "pre_test",
            "long_diff", "decision", "timing", "note"]


def _git_rev() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        return "n. d."


def part_summary(args) -> None:
    files = sorted(p for p in EST.glob("*.csv") if not p.name.startswith("_"))
    if not files:
        log("aucun résultat à synthétiser")
        return
    allr = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    out_dir = EST if EST.name == "est_smoke" else ROOT / "tables"          # les tests de fonctionnement restent dans est_smoke
    allr.to_csv(out_dir / "est_fr_all.csv", index=False)
    key = allr[allr.aggregation.isin(KEY_AGGS)]
    lines = ["# Estimations France — synthèse (généré par scripts/05_estimate.py --part summary)", "",
             "Toutes les estimations : `tables/est_fr_all.csv` (une ligne par coefficient, event studies comprises). "
             "ATT[1,k] = moyenne des effets +1 à +k après la bascule (k = dernière période disponible ≤ 5 ; log-points ≈ %). "
             "cs = Callaway & Sant'Anna ; sunab = Sun & Abraham ; did2s = Gardner ; twfe = effets fixes bidirectionnels ; "
             "twfe_poisson = Poisson à effets fixes avec offset ; long_diff = différence longue entre millésimes RP. "
             "Colonne « expl. » : analyse complémentaire hors préregistration (addendum A2). Les notes de chaque ligne donnent la composition "
             "(jamais traitées, cohortes recodées, unités exclues, années identifiées).", ""]
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
    (out_dir / "t_estimates_fr.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    import differences, pyfixest  # noqa: E401
    manifest = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "commit": _git_rev(), "python": platform.python_version(),
                "packages": {"differences": differences.__version__, "pyfixest": pyfixest.__version__, "pandas": pd.__version__, "numpy": np.__version__},
                "parts": {f.stem: {"rows": int(len(pd.read_csv(f))), "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.stat().st_mtime))} for f in files},
                "args": {k: v for k, v in vars(args).items()}, "n_rows": int(len(allr)), "n_key_rows": int(len(key)),
                "inputs": {p.name: time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime)) for p in sorted(PROC.glob("fr_*.parquet"))}}
    (EST / "_run.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"synthèse : {len(key)} lignes clés, {len(allr)} coefficients au total ; manifeste {EST / '_run.json'}")


PARTS = {"h1": part_h1, "h2": part_h2, "h3": part_h3, "h5": part_h5, "h6": part_h6, "robust": part_robust, "iv": part_iv, "summary": part_summary}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--part", nargs="+", default=["all"])
    ap.add_argument("--boot", type=int, default=999, help="tirages du bootstrap multiplicateur (bandes simultanées sup-t)")
    ap.add_argument("--nboot", type=int, default=200, help="tirages du bootstrap par grappes (département) pour ATT[1,k], H2d et §6")
    ap.add_argument("--nboot-commune", type=int, default=50, dest="nboot_commune", help="tirages du bootstrap par grappes (commune) pour la spécification primaire H1")
    ap.add_argument("--fast", action="store_true", help="bootstraps réduits (vérification)")
    ap.add_argument("--sample", type=int, default=None, help="sous-échantillon de communes (tests de fonctionnement ; jamais pour le papier)")
    a = ap.parse_args()
    if a.fast:
        a.boot, a.nboot, a.nboot_commune = 49, 5, 2
    if a.sample or a.fast:
        global SAMPLE_UNITS
        SAMPLE_UNITS = a.sample
        global EST
        EST = ROOT / "tables" / "est_smoke"           # les tests de fonctionnement (--sample, --fast) n'écrivent jamais dans tables/est
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
