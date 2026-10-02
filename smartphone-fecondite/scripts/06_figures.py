#!/usr/bin/env python
"""Étape 3 — figures du papier (PDF dans figures/), toutes produites à partir des sorties des scripts précédents.

- fig_rollout.pdf        : part des communes avec ≥ 1 émetteur 4G en service au 1er janvier, par classe de densité ;
                           distribution de D3 (départements) par année  (02_treatment.py)
- fig_rates_age.pdf      : taux de fécondité par âge 1998-2024, France métropolitaine (03_outcomes.py)
- fig_barometre.pdf      : possession de smartphone et usage des réseaux sociaux par classe d'âge (04b_firststage.py)
- fig_event_<clé>.pdf    : event studies (coefficients et IC 95 %) pour les spécifications clés (05_estimate.py)
- fig_h2_age.pdf         : ATT[1,5] par groupe d'âge, naissances et mariages (05_estimate.py)

Palette catégorielle validée (dataviz, mode clair, paires adjacentes) : bleu, orange, aqua, jaune.
Aucune valeur n'est saisie à la main.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "tables"
FIG = ROOT / "figures"
COLORS = {"cs": "#2a78d6", "sunab": "#eb6834", "did2s": "#1baf7a", "twfe": "#eda100"}
LABELS = {"cs": "Callaway & Sant'Anna", "sunab": "Sun & Abraham", "did2s": "did2s (Gardner)", "twfe": "TWFE"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e2"

plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "legend.frameon": False, "figure.dpi": 150, "pdf.fonttype": 42})


def label_ends(ax, items: list[tuple[float, float, str, str]], min_gap: float | None = None) -> None:
    """Étiquettes directes en fin de courbe, écartées verticalement pour éviter les collisions.
    ``items`` = (x, y, texte, couleur)."""
    if not items:
        return
    ylo, yhi = ax.get_ylim()
    gap = min_gap or 0.05 * (yhi - ylo)
    items = sorted(items, key=lambda it: it[1])
    ys = [it[1] for it in items]
    for i in range(1, len(ys)):
        if ys[i] - ys[i - 1] < gap:
            ys[i] = ys[i - 1] + gap
    if ys[-1] > yhi - 0.3 * gap:                     # on reste dans le cadre : on décale l'ensemble vers le bas
        shift = ys[-1] - (yhi - 0.3 * gap)
        ys = [y - shift for y in ys]
    for (x, _, txt, col), y in zip(items, ys):
        ax.annotate(txt, (x, y), xytext=(4, 0), textcoords="offset points", va="center", fontsize=8, color=INK2)


def int_ticks(ax, nbins: int = 7) -> None:
    from matplotlib.ticker import MaxNLocator
    ax.xaxis.set_major_locator(MaxNLocator(nbins=nbins, integer=True))


def save(fig, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name, bbox_inches="tight")
    fig.savefig(FIG / name.replace(".pdf", ".png"), bbox_inches="tight", dpi=200)
    plt.close(fig)
    print("figure :", name)


# ----------------------------------------------------------------------------- déploiement

def fig_rollout() -> None:
    tr = pd.read_parquet(PROC / "fr_treatment_commune.parquet")
    tr = tr[tr.metro & tr.year.between(2008, 2026)]
    tr["classe"] = tr.densite.map(lambda x: "dense (1)" if x == 1 else "intermédiaire (2-4)" if x in (2, 3, 4) else "rural (5-7)")
    sh = tr.groupby(["year", "classe"]).d1_4g.mean().unstack()
    dep = pd.read_parquet(PROC / "fr_treatment_dep.parquet")
    dep = dep[dep.year.between(2008, 2026)]
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.1))
    ax = axes[0]
    items = []
    for i, c in enumerate(["dense (1)", "intermédiaire (2-4)", "rural (5-7)"]):
        ax.plot(sh.index, 100 * sh[c], color=list(COLORS.values())[i], lw=2, label=c)
        items.append((sh.index[-1], 100 * sh[c].iloc[-1], c, list(COLORS.values())[i]))
    ax.set_ylabel("communes avec ≥ 1 émetteur 4G (%)")
    ax.set_title("Communes (D1), par classe de densité", loc="left", fontsize=9)
    ax.set_xlim(2008, 2031)
    label_ends(ax, items)
    int_ticks(ax)
    ax = axes[1]
    q = dep.groupby("year").d3.quantile([0.1, 0.5, 0.9]).unstack()
    ax.fill_between(q.index, 100 * q[0.1], 100 * q[0.9], color=COLORS["cs"], alpha=0.15, lw=0, label="déciles 1-9")
    ax.plot(q.index, 100 * q[0.5], color=COLORS["cs"], lw=2, label="médiane")
    ax.axhline(50, color=INK2, lw=0.8, ls="--")
    ax.text(2008.3, 52, "seuil de bascule 50 %", fontsize=8, color=INK2)
    ax.set_ylabel("D3 : femmes 15-44 en commune avec 4G (%)")
    ax.set_title("Départements (D3), médiane et déciles", loc="left", fontsize=9)
    ax.legend(loc="lower right", fontsize=8)
    int_ticks(ax)
    fig.subplots_adjust(wspace=0.4)
    save(fig, "fig_rollout.pdf")


# ----------------------------------------------------------------------------- descriptif

def fig_rates_age() -> None:
    da = pd.read_parquet(PROC / "fr_outcomes_dep_age.parquet")
    da = da[da.metro]
    g = da.groupby(["year", "age_group"]).apply(lambda x: 1000 * x.births.sum() / x.women.sum(), include_groups=False).unstack()
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.1))
    groups = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-49"]
    for ax, sel in zip(axes, (["25-29", "30-34", "35-39"], ["15-19", "20-24", "40-49"])):
        items = []
        for i, grp in enumerate(sel):
            ax.plot(g.index, g[grp], color=list(COLORS.values())[i], lw=2)
            items.append((g.index[-1], g[grp].iloc[-1], grp, list(COLORS.values())[i]))
        ax.axvline(2013, color=INK2, lw=0.8, ls="--")
        ax.set_xlim(1998, 2027)
        ax.set_ylabel("naissances pour 1 000 femmes")
        label_ends(ax, items)
        int_ticks(ax)
    axes[0].set_title("25-39 ans (test primaire)", loc="left", fontsize=9)
    axes[1].set_title("15-24 et 40-49 ans", loc="left", fontsize=9)
    axes[0].text(2013.3, axes[0].get_ylim()[1] * 0.97, "premières bascules D3", fontsize=8, color=INK2, va="top")
    fig.subplots_adjust(wspace=0.3)
    save(fig, "fig_rates_age.pdf")


def fig_barometre() -> None:
    p = TABLES / "t_barometre_age_year.csv"
    if not p.exists():
        return
    d = pd.read_csv(p)
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.1), sharey=True)
    order = ["18-24 ans", "25-39 ans", "40-59 ans", "60-69 ans"]
    for ax, var, title in zip(axes, ("smartphone", "social"), ("Possède un smartphone", "A participé à des réseaux sociaux (12 mois)")):
        s = d[(d.variable == var) & d.age.isin(order)].pivot(index="year", columns="age", values="share")
        items = []
        for i, a in enumerate(order):
            if a in s:
                ax.plot(s.index, 100 * s[a], color=list(COLORS.values())[i], lw=2, marker="o", ms=3, label=a)
                items.append((s.index[-1], 100 * s[a].iloc[-1], a, list(COLORS.values())[i]))
        ax.set_title(title, loc="left", fontsize=9)
        ax.set_xlim(s.index.min(), s.index.max() + 4)
        ax.set_ylim(0, 105)
        label_ends(ax, items)
        int_ticks(ax)
    axes[0].set_ylabel("% des individus (pondéré)")
    axes[0].legend(fontsize=8, loc="lower right", title="classe d'âge", title_fontsize=8)
    fig.subplots_adjust(wspace=0.25)
    save(fig, "fig_barometre.pdf")


# ----------------------------------------------------------------------------- event studies

def _event_rows(allr: pd.DataFrame, hyp: str, outcome_re: str, sample_re: str) -> pd.DataFrame:
    e = allr[(allr.aggregation == "event") & (allr.hypothesis == hyp) & allr.outcome.str.contains(outcome_re, regex=True)
             & allr["sample"].str.contains(sample_re, regex=True)]
    e = e.copy()
    e["rel"] = pd.to_numeric(e.term, errors="coerce")
    return e.dropna(subset=["rel"])


def fig_event(allr: pd.DataFrame, key: str, hyp: str, outcome_re: str, sample_re: str, title: str, ylabel: str) -> None:
    e = _event_rows(allr, hyp, outcome_re, sample_re)
    if e.empty:
        return
    ests = [k for k in COLORS if k in set(e.estimator)]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    offs = np.linspace(-0.18, 0.18, len(ests)) if len(ests) > 1 else [0.0]
    for k, off in zip(ests, offs):
        s = e[e.estimator == k].sort_values("rel")
        ax.errorbar(s.rel + off, s.estimate, yerr=[s.estimate - s.ci_low, s.ci_high - s.estimate], fmt="o", ms=3.5, lw=1,
                    color=COLORS[k], ecolor=COLORS[k], capsize=0, label=LABELS[k], alpha=0.95)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.axvline(-0.5, color=INK2, lw=0.8, ls="--")
    ax.set_xlabel("années depuis la bascule (référence : −1)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", fontsize=9)
    ax.legend(fontsize=8, ncol=2, loc="lower left")
    save(fig, f"fig_event_{key}.pdf")


def fig_h2_age(allr: pd.DataFrame) -> None:
    rows = allr[(allr.aggregation == "post_avg_1_5") & (allr.estimator == "cs")]
    groups = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-49"]
    panels = [("H2", r"naissances / 1 000 f\. (\d\d-\d\d)\)$", "département, bascule D3 ≥ 50 %", "Naissances pour 1 000 femmes (H2)"),
              ("H3a", r"mariages de femmes / 1 000 f\. (\d\d-\d\d)\)$", "département, bascule D3 ≥ 50 %", "Mariages de femmes pour 1 000 femmes (H3a)")]
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.2), sharey=False)
    for ax, (fam, pat, samp, title) in zip(axes, panels):
        sub = rows[rows.hypothesis.str.startswith(fam[:2]) & rows.outcome.str.contains(pat, regex=True) & (rows["sample"] == samp)]
        pts = []
        for g in groups:
            r = sub[sub.outcome.str.contains(rf"f\. {g}\)")]
            if len(r):
                r = r.iloc[0]
                pts.append((g, r.estimate, r.ci_low, r.ci_high))
        if not pts:
            continue
        x = np.arange(len(pts))
        ax.errorbar(x, [p[1] for p in pts], yerr=[[p[1] - p[2] for p in pts], [p[3] - p[1] for p in pts]], fmt="o", color=COLORS["cs"], ms=5, lw=1.2, capsize=0)
        ax.axhline(0, color=INK2, lw=0.8)
        ax.set_xticks(x, [p[0] for p in pts])
        ax.set_title(title, loc="left", fontsize=9)
        ax.set_ylabel("ATT[1,5], log-points (≈ %)")
        ax.set_xlabel("groupe d'âge")
    save(fig, "fig_h2_age.pdf")


def main() -> int:
    fig_rollout()
    fig_rates_age()
    fig_barometre()
    p = TABLES / "est_fr_all.csv"
    if p.exists():
        allr = pd.read_csv(p)
        fig_event(allr, "h1", "H1", r"naissances\+0,5 / 1 000 f\. 15-44", "^toutes communes, sans covariables$",
                  "H1 : naissances pour 1 000 femmes 15-44, communes (log)", "effet (log-points)")
        fig_event(allr, "h1_primaire", "H1", r"naissances\+0,5 / 1 000 f\. 15-44", "^primaire", "H1 : spécification primaire (covariables de pré-période)", "effet (log-points)")
        fig_event(allr, "h2b", "H2b", r"f\. 25-39\)", "≥ 50 %$", "H2b : naissances pour 1 000 femmes 25-39, départements (log)", "effet (log-points)")
        fig_event(allr, "h2_1524", "H2d", r"f\. 15-24\)", "≥ 50 %$", "Naissances pour 1 000 femmes 15-24, départements (log)", "effet (log-points)")
        fig_event(allr, "h3a_2539", "H3a", r"mariages de femmes / 1 000 f\. 25-39", "≥ 50 %$", "H3a : mariages de femmes pour 1 000 femmes 25-39 (log)", "effet (log-points)")
        fig_event(allr, "h5a", "H5a", r"15-44", "^commune, bascule fictive −3 ans, années pré-traitement seules$", "H5a : placebo, bascule fictive −3 ans (communes)", "effet (log-points)")
        fig_event(allr, "h5b", "H5b", r"décès", "^commune$", "H5b : placebo, décès pour 1 000 habitants (communes)", "effet (log-points)")
        fig_h2_age(allr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
