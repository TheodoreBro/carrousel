#!/usr/bin/env python
"""Colombie — figures (figures/fig_co_*.pdf|png) et tableaux LaTeX (tables/tab_co_*.tex), tous produits à partir des sorties
des scripts 09, 10 et 11. Réutilise les fonctions des scripts 06 (fig_event, save, palette) et 07 (write, tab_from, esc).

- fig_co_rollout.pdf      : part des municipios dont la part de population couverte en 4G atteint 50 % / 90 %, cabecera 4G,
                            3G ≥ 50 %, par année (09_co_treatment.py) ; médiane de la part 4G
- fig_co_rates_age.pdf    : taux de fécondité par âge 1998-2024, ensemble des municipios (10_co_outcomes.py)
- fig_event_co_<clé>.pdf  : event studies des spécifications clés (11_co_estimate.py)
- fig_co_h2_age.pdf       : ATT[1,k] par groupe d'âge (H2) et naissances de mères en union (H3b)
- fig_co_h6.pdf           : ATT[1,k] par sous-groupe (H6)
- tab_co_sample.tex, tab_co_mde.tex, tab_co_main.tex, tab_co_h2_age.tex, tab_co_h3.tex, tab_co_placebo.tex, tab_co_h6.tex,
  tab_co_robust.tex, tab_co_exploratory.tex

`--smoke` : lit tables/est_co_smoke/ et écrit dans figures/smoke/ et tables/est_co_smoke/ (jamais pour le papier).
Aucune valeur n'est saisie à la main.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "tables"
HERE = Path(__file__).resolve().parent


def _load(name: str, fname: str):
    spec = importlib.util.spec_from_file_location(name, HERE / fname)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


f6 = _load("f6", "06_figures.py")
t7 = _load("t7", "07_tables.py")
plt = f6.plt
AGE_GROUPS = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-49"]
SAMPLE_PRIM = "^municipios avec covariables, bascule 4G ≥ 50 %$"


# ----------------------------------------------------------------------------- figures descriptives

def fig_rollout() -> None:
    p = PROC / "co_treatment.parquet"
    if not p.exists():
        return
    d = pd.read_parquet(p)
    n = d.groupby("year").municipio.nunique()
    series = [("4G ≥ 50 % pop.", (d.share_g4 >= .5), f6.COLORS["cs"]), ("4G ≥ 90 %", (d.share_g4 >= .9), f6.COLORS["sunab"]),
              ("cabecera 4G", (d.cab_g4 >= 1), f6.COLORS["did2s"]), ("3G ≥ 50 %", (d.share_g3 >= .5), f6.COLORS["twfe"])]
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.2))
    fig.subplots_adjust(wspace=0.3)
    ax = axes[0]
    items = []
    for lab, m, col in series:
        s = 100 * d[m].groupby("year").municipio.nunique().reindex(n.index).fillna(0) / n
        ax.plot(s.index, s.values, color=col, lw=2, marker="o", ms=4)
        items.append((s.index[-1], s.values[-1], lab, col))
    ax.set_ylim(0, 105)
    ax.set_xlim(n.index.min() - 0.3, n.index.max() + 2.6)
    f6.label_ends(ax, items)
    ax.set_title("Municipios atteignant le seuil (%)", loc="left", fontsize=9)
    ax.set_xlabel("année (dernier trimestre observé ; 2015 = T4)")
    f6.int_ticks(ax, 9)
    ax = axes[1]
    q = d.groupby("year").share_g4.quantile([.25, .5, .75]).unstack() * 100
    ax.fill_between(q.index, q[.25], q[.75], color=f6.COLORS["cs"], alpha=0.15, lw=0, label="quartiles")
    ax.plot(q.index, q[.5], color=f6.COLORS["cs"], lw=2, marker="o", ms=4, label="médiane")
    ax.set_ylim(0, 105)
    ax.set_title("Part de population couverte en 4G (%)", loc="left", fontsize=9)
    ax.set_xlabel("année")
    ax.legend(fontsize=7.5, loc="lower right")
    f6.int_ticks(ax, 5)
    f6.save(fig, "fig_co_rollout.pdf")


def fig_rates_age() -> None:
    p = PROC / "co_outcomes_mun_age.parquet"
    if not p.exists():
        return
    d = pd.read_parquet(p)
    g = d.groupby(["year", "age_group"])[["births", "women"]].sum().reset_index()
    g["rate"] = 1000 * g.births / g.women
    cols = [f6.COLORS["cs"], f6.COLORS["sunab"], f6.COLORS["did2s"], f6.COLORS["twfe"], "#8e6bd9", "#b5566e"]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    items = []
    for ag, col in zip(AGE_GROUPS, cols):
        s = g[g.age_group == ag].sort_values("year")
        ax.plot(s.year, s.rate, color=col, lw=1.8)
        items.append((s.year.iloc[-1], s.rate.iloc[-1], ag, col))
    ax.set_xlim(g.year.min() - 0.3, g.year.max() + 2.2)
    f6.label_ends(ax, items)
    ax.set_title("Naissances pour 1 000 femmes par groupe d'âge, ensemble des municipios (2024 provisoire)", loc="left", fontsize=9)
    ax.set_xlabel("année")
    f6.int_ticks(ax, 9)
    f6.save(fig, "fig_co_rates_age.pdf")


# ----------------------------------------------------------------------------- figures d'estimation

def _dots(ax, pts: list[tuple[str, float, float, float]], title: str, ks: list[int], color: str) -> None:
    x = np.arange(len(pts))
    ax.errorbar(x, [p[1] for p in pts], yerr=[[p[1] - p[2] for p in pts], [p[3] - p[1] for p in pts]], fmt="o", color=color, ms=5, lw=1.2, capsize=0)
    ax.axhline(0, color=f6.INK2, lw=0.8)
    ax.set_xticks(x, [p[0] for p in pts], fontsize=7.5)
    ax.set_title(title, loc="left", fontsize=9)
    ax.set_ylabel(f"ATT[1,{','.join(map(str, ks)) if ks else 'k'}], log-points (≈ %) ; IC 95 %")


def _post_rows(allr: pd.DataFrame, hyp_prefix: tuple[str, ...], outcome_re: str, sample_re: str, exploratory: bool = False) -> pd.DataFrame:
    return allr[(allr.aggregation == "post_avg") & (allr.estimator == "cs") & (allr.exploratory == exploratory)  # noqa: E712
                & allr.hypothesis.str.startswith(hyp_prefix) & allr.outcome.str.contains(outcome_re, regex=True)
                & allr["sample"].str.contains(sample_re, regex=True)]


def fig_h2_age(allr: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.2))
    fig.subplots_adjust(wspace=0.35)
    sub = _post_rows(allr, ("H2",), r"^log\(naissances\+0,5 / 1 000 f\. \d\d-\d\d\)$", SAMPLE_PRIM)
    pts = []
    for g in AGE_GROUPS:
        r = sub[sub.outcome.str.contains(rf"f\. {g}\)")]
        if len(r):
            r = r.iloc[0]
            pts.append((g, r.estimate, r.ci_low, r.ci_high))
    ks = sorted(set(int(k) for k in sub.k_post.dropna()))
    if pts:
        _dots(axes[0], pts, "Naissances par groupe d'âge (H2)", ks, f6.COLORS["cs"])
        axes[0].set_xlabel("groupe d'âge")
    sub = _post_rows(allr, ("H3b",), r"^log\(naissances de mères (?:en|hors) union\+0,5 / 1 000 f\. \d\d-\d\d\)$", SAMPLE_PRIM)
    sub2 = _post_rows(allr, ("H3b",), r"^log\(naissances de mères (?:en|hors) union\+0,5 / 1 000 f\. \d\d-\d\d\)$", SAMPLE_PRIM, exploratory=True)
    sub = pd.concat([sub, sub2])
    pts = []
    for lab, pat in (("en union\n15-24", r"en union\+0,5 / 1 000 f\. 15-24"), ("hors union\n15-24", r"hors union\+0,5 / 1 000 f\. 15-24"),
                     ("en union\n25-39", r"en union\+0,5 / 1 000 f\. 25-39"), ("hors union\n25-39", r"hors union\+0,5 / 1 000 f\. 25-39")):
        r = sub[sub.outcome.str.contains(pat, regex=True)]
        if len(r):
            r = r.iloc[0]
            pts.append((lab, r.estimate, r.ci_low, r.ci_high))
    if pts:
        _dots(axes[1], pts, "Mères en union (H3b) et hors union (complément)", ks, f6.COLORS["cs"])
    f6.save(fig, "fig_co_h2_age.pdf")


def fig_h6(allr: pd.DataFrame) -> None:
    sub = allr[(allr.aggregation == "post_avg") & (allr.estimator == "cs") & (allr.hypothesis == "H6")]
    if sub.empty:
        return
    pts = []
    for _, r in sub.iterrows():
        s = str(r["sample"])
        lab = s.replace("part de population en cabecera 2015 (densité) : ", "cabecera\n").replace("population 2015 : ", "population\n") \
               .replace("rang 2 et plus", "rang 2+").replace("tercile ", "T")
        if "rang" in s:
            lab = "naissances\n" + lab
        pts.append((lab, r.estimate, r.ci_low, r.ci_high))
    ks = sorted(set(int(k) for k in sub.k_post.dropna()))
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    _dots(ax, pts, "Hétérogénéité (H6) : terciles de part en cabecera et de population 2015 ; rang de naissance", ks, f6.COLORS["cs"])
    f6.save(fig, "fig_co_h6.pdf")


def figures(allr: pd.DataFrame | None, smoke: bool) -> None:
    if not smoke:
        fig_rollout()
        fig_rates_age()
    if allr is None:
        return
    ev = f6.fig_event
    log49 = r"log\(naissances\+0,5 / 1 000 f\. 15-49\)"
    ev(allr, "co_h1", "H1", log49, "^tous municipios, sans covariables$", "H1 : naissances pour 1 000 femmes 15-49, municipios (log)", "effet (log-points)")
    ev(allr, "co_h1_primaire", "H1", log49, "^primaire : municipios avec covariables$|^municipios avec covariables, comparaisons$",
       "H1 : spécification primaire (covariables de pré-période) et comparaisons", "effet (log-points)")
    ev(allr, "co_h2b", "H2b", r"log\(naissances\+0,5 / 1 000 f\. 25-39\)", SAMPLE_PRIM, "H2b : naissances pour 1 000 femmes 25-39, municipios (log)", "effet (log-points)")
    ev(allr, "co_h2_1524", "H2d", r"f\. 15-24\)", SAMPLE_PRIM, "Naissances pour 1 000 femmes 15-24, municipios (log)", "effet (log-points)")
    ev(allr, "co_h3b_2539", "H3b", r"en union\+0,5 / 1 000 f\. 25-39", SAMPLE_PRIM, "H3b : naissances de mères en union pour 1 000 femmes 25-39 (log)", "effet (log-points)")
    ev(allr, "co_h5a", "H5a", "15-49", "^municipio, bascule fictive −3 ans, années pré-traitement seules$", "H5a : placebo, bascule fictive −3 ans (municipios)", "effet (log-points)")
    fig_h2_age(allr)
    fig_h6(allr)


# ----------------------------------------------------------------------------- tableaux

def tab_sample_mde() -> None:
    esc, fmt, write = t7.esc, t7.fmt, t7.write
    p = TABLES / "t_sample_co.csv"
    if p.exists():
        d = pd.read_csv(p)
        rows = [[esc(r["spécification"]), f"{int(r['unités']):,}".replace(",", "\\,"), esc(r["années"]), f"{int(r['unités-années']):,}".replace(",", "\\,"),
                 f"{int(r['unités traitées']):,}".replace(",", "\\,"), f"{int(r['jamais traitées']):,}".replace(",", "\\,"), esc(r["cohortes"])] for _, r in d.iterrows()]
        write("tab_co_sample.tex", ["Spécification", "Unités", "Années", "Unités-années", "Traitées", "Jamais traitées", "Cohortes"], rows,
              "Échantillons par spécification, Colombie", "tab:co_sample",
              "Source : scripts/11\\_co\\_estimate.py (partie sample). Unités = municipios (DIVIPOLA) avec covariables de pré-période ; municipios censurés à gauche exclus (A4).")
    p = TABLES / "t_mde_co.csv"
    if p.exists():
        d = pd.read_csv(p)
        rows = [[esc(r["hypothèse"]), fmt(r["sd placebo"], 4), fmt(100 * r["MDE (80 %, 5 %) en log ≈ %"], 2), str(int(r["permutations"]))] for _, r in d.iterrows()]
        write("tab_co_mde.tex", ["Hypothèse", "É.-t. des ATT placebo", "MDE (80 %, 5 %), %", "Permutations"], rows,
              "Taille d'effet minimale détectable par permutation des cohortes, Colombie", "tab:co_mde",
              "Source : scripts/11\\_co\\_estimate.py. ATT statique TWFE sur le log du taux, cohortes permutées entre municipios ; MDE = (1,96 + 0,84) $\\times$ écart-type placebo.")


def tables(allr: pd.DataFrame | None) -> None:
    tab_sample_mde()
    if allr is None:
        return
    tf = t7.tab_from
    key_aggs = ["post_avg", "post_avg_boot", "post_avg_balanced", "static"]
    src = "Source : scripts/11\\_co\\_estimate.py."
    tf(allr, "tab_co_main.tex", allr.aggregation.isin(key_aggs) & allr.hypothesis.isin(["H1", "H2b"]) & (allr.family != "robustesse"),
       "Colombie — effet de la bascule 4G ($\\geq$ 50 \\% de la population) sur les naissances : effet total (H1) et 25-39 ans (H2b), municipios", "tab:co_main",
       src + " cs = Callaway \\& Sant'Anna (écart-type avec covariance complète des coefficients).")
    tf(allr, "tab_co_h2_age.tex", (allr.aggregation.isin(["post_avg", "post_avg_holm"]) & (allr.estimator == "cs") | allr.aggregation.isin(["difference"]))
       & allr.hypothesis.str.startswith("H2") & ~allr["sample"].str.contains("anticipation"),
       "Colombie — effet par groupe d'âge (H2), municipios", "tab:co_h2age",
       src + " Familles corrigées par Holm : 15-19, 20-24 (H2a) ; 25-29, 30-34, 35-39, 40-49 (H2c) ; p Holm dans est\\_co\\_all.csv.")
    tf(allr, "tab_co_h3.tex", allr.aggregation.isin(key_aggs + ["decision", "note"]) & allr.hypothesis.str.startswith(("H3", "§6")),
       "Colombie — canal (H3b : naissances de mères en union) et règle de décision §6", "tab:co_h3",
       src + " H3a (mariages) et H3c non testables en Colombie (A4).")
    tf(allr, "tab_co_placebo.tex", (allr.aggregation.isin(key_aggs + ["pre_test"]) & allr.hypothesis.str.startswith("H5"))
       | ((allr.aggregation == "pre_test") & allr.hypothesis.isin(["H1", "H2b"]) & (allr.estimator == "cs") & (allr.family != "robustesse")),
       "Colombie — placebos (H5)", "tab:co_placebo", src + " H5b (décès) non construit (A4). H5c : test de Wald joint des coefficients $-8$ à $-2$.")
    tf(allr, "tab_co_h6.tex", allr.aggregation.isin(["post_avg", "post_avg_holm", "note"]) & allr.hypothesis.str.startswith("H6"),
       "Colombie — hétérogénéité (H6), municipios", "tab:co_h6", src + " p Holm dans la colonne notes de est\\_co\\_all.csv.")
    tf(allr, "tab_co_robust.tex", allr.aggregation.isin(key_aggs + ["note"]) & (allr.family == "robustesse") & allr.estimator.isin(["cs", "—"]),
       "Colombie — robustesse", "tab:co_robust", src)
    tf(allr, "tab_co_exploratory.tex", allr.aggregation.isin(key_aggs), "Colombie — analyses complémentaires hors préregistration (addendum A4)",
       "tab:co_exploratory", src + " Analyses marquées « exploratoire » ; aucune n'entre dans les règles de décision.", exploratory=True)


def main() -> int:
    smoke = "--smoke" in sys.argv
    est_dir = TABLES / ("est_co_smoke" if smoke else "est_co")
    if smoke:
        f6.FIG = ROOT / "figures" / "smoke"
        t7.TABLES = est_dir                      # les .tex de fumée vont dans tables/est_co_smoke/ (ignoré par git)
    t7.SMOKE = False
    p = (est_dir if smoke else TABLES) / "est_co_all.csv"      # la synthèse complète écrit tables/est_co_all.csv (11_co_estimate.py)
    allr = None
    if p.exists():
        allr = pd.read_csv(p)
        if "exploratory" not in allr:
            allr["exploratory"] = False
    else:
        print(f"pas d'estimations dans {p} : figures et tableaux descriptifs seulement")
    figures(allr, smoke)
    tables(allr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
