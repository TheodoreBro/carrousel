#!/usr/bin/env python
"""Étape 3 — tableaux LaTeX du papier (tables/*.tex), à partir des csv produits par les scripts 04, 04b et 05.

- tab_sample.tex       : unités-années par spécification (04_sample_mde.py)
- tab_mde.tex          : tailles d'effet minimales détectables (04_sample_mde.py)
- tab_firststage.tex   : first stage Baromètre (04b_firststage.py)
- tab_main.tex         : H1 et H2b, tous estimateurs (05_estimate.py)
- tab_h2_age.tex       : H2 par groupe d'âge (CS, Holm) et D3 continu
- tab_h3.tex           : canal (mariages, PACS, couples, parents mariés)
- tab_placebo.tex      : H5a-c
- tab_h6.tex           : hétérogénéité
- tab_robust.tex       : robustesse
- tab_iv.tex           : IV (secondaire)

Aucune valeur n'est saisie à la main ; chaque cellule vient d'un csv.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "tables"


def esc(s) -> str:
    return str(s).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("≥", r"$\geq$").replace("−", "$-$").replace("≈", r"$\approx$")


def fmt(x, nd=3) -> str:
    return "" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{nd}f}"


def stars(p) -> str:
    if p is None or not np.isfinite(p):
        return ""
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


def write(name: str, header: list[str], rows: list[list[str]], caption: str, label: str, note: str = "", align: str | None = None) -> None:
    align = align or "l" + "r" * (len(header) - 1)
    lines = [r"\begin{table}[htbp]\centering", r"\begin{threeparttable}", rf"\caption{{{caption}}}\label{{{label}}}", r"\small",
             rf"\begin{{tabular}}{{{align}}}", r"\toprule", " & ".join(esc(h) for h in header) + r" \\", r"\midrule"]
    lines += [" & ".join(r) + r" \\" for r in rows]
    lines += [r"\bottomrule", r"\end{tabular}"]
    if note:
        lines += [r"\begin{tablenotes}\footnotesize", rf"\item {note}", r"\end{tablenotes}"]
    lines += [r"\end{threeparttable}", r"\end{table}", ""]
    (TABLES / name).write_text("\n".join(lines), encoding="utf-8")
    print("tableau :", name)


def tab_sample() -> None:
    p = TABLES / "t_sample_fr.csv"
    if not p.exists():
        return
    d = pd.read_csv(p)
    rows = [[esc(r["spécification"]), f"{int(r['unités']):,}".replace(",", "\\,"), esc(r["années"]), f"{int(r['unités-années']):,}".replace(",", "\\,"),
             f"{int(r['unités traitées']):,}".replace(",", "\\,"), f"{int(r['jamais traitées']):,}".replace(",", "\\,"), esc(r["cohortes"])] for _, r in d.iterrows()]
    write("tab_sample.tex", ["Spécification", "Unités", "Années", "Unités-années", "Traitées", "Jamais traitées", "Cohortes"], rows,
          "Échantillons par spécification, France", "tab:sample", "Source : scripts/04\\_sample\\_mde.py. Unités = communes harmonisées (COG 2026) ou départements.")


def tab_mde() -> None:
    p = TABLES / "t_mde_fr.csv"
    if not p.exists():
        return
    d = pd.read_csv(p)
    rows = [[esc(r["hypothèse"]), fmt(r["sd placebo"], 4), fmt(100 * r["MDE (80 %, 5 %) en log ≈ %"], 2), str(int(r["permutations"]))] for _, r in d.iterrows()]
    write("tab_mde.tex", ["Hypothèse", "É.-t. des ATT placebo", "MDE (80 %, 5 %), %", "Permutations"], rows,
          "Taille d'effet minimale détectable par permutation des cohortes", "tab:mde",
          "Source : scripts/04\\_sample\\_mde.py. ATT statique TWFE sur le log du taux, cohortes permutées entre unités ; MDE = (1,96 + 0,84) $\\times$ écart-type placebo.")


def tab_firststage() -> None:
    p = TABLES / "t_firststage_fr.csv"
    if not p.exists():
        return
    d = pd.read_csv(p)
    rows = [[esc(r["échantillon"]), esc(r["résultat"]), esc(r["terme"]), fmt(r["coef"]) + stars(r["p"]), f"({fmt(r['se'])})", f"{int(r['n']):,}".replace(",", "\\,"), str(int(r["zones"]))]
            for _, r in d.iterrows()]
    write("tab_firststage.tex", ["Échantillon", "Résultat", "Terme", "Coef.", "É.-t.", "N", "Zones"], rows,
          "First stage : couverture 4G (D3) et adoption, Baromètre du numérique", "tab:firststage",
          "Source : scripts/04b\\_firststage.py. Effets fixes zone, année, classe d'âge ; pondération POND ; erreurs groupées par zone (9 ou 13 groupes). * p<0,10, ** p<0,05, *** p<0,01.")


def _load_est() -> pd.DataFrame | None:
    p = TABLES / "est_fr_all.csv"
    return pd.read_csv(p) if p.exists() else None


def _row(r, with_sample=True) -> list[str]:
    cells = [esc(r.hypothesis), esc(r.outcome)]
    if with_sample:
        cells.append(esc(r["sample"]))
    cells += [esc(r.estimator), esc(r.term), fmt(r.estimate, 4) + stars(r.p), f"({fmt(r.se, 4)})", f"{int(r.n_units):,}".replace(",", "\\,"), f"{int(r.n_obs):,}".replace(",", "\\,")]
    return cells


def tab_from(allr: pd.DataFrame, name: str, mask, caption: str, label: str, note: str) -> None:
    sub = allr[mask]
    if sub.empty:
        return
    rows = [_row(r) for _, r in sub.iterrows()]
    write(name, ["Hyp.", "Résultat", "Échantillon", "Estimateur", "Terme", "Estimation", "É.-t.", "Unités", "Obs."], rows, caption, label,
          note + " * p<0,10, ** p<0,05, *** p<0,01 (p d'un test z sur l'écart-type indiqué).", align="llllrrrrr")


def main() -> int:
    tab_sample()
    tab_mde()
    tab_firststage()
    allr = _load_est()
    if allr is None:
        return 0
    key_aggs = ["post_avg_1_5", "post_avg_1_5_boot", "static"]
    tab_from(allr, "tab_main.tex",
             allr.aggregation.isin(key_aggs) & allr.hypothesis.isin(["H1", "H2b"]) & ~allr["sample"].str.contains("90 %"),
             "Effet de la bascule 4G sur les naissances : effet total (H1, communes) et 25-39 ans (H2b, départements)", "tab:main",
             "Source : scripts/05\\_estimate.py. ATT[1,5] = moyenne des effets +1 à +5 (log-points). cs = Callaway \\& Sant'Anna.")
    tab_from(allr, "tab_h2_age.tex",
             ((allr.aggregation.isin(["post_avg_1_5", "post_avg_1_5_holm"]) & (allr.estimator == "cs")) | (allr.aggregation == "continuous") | (allr.aggregation == "difference"))
             & allr.hypothesis.str.startswith("H2"),
             "Effet par groupe d'âge (H2), départements", "tab:h2age", "Source : scripts/05\\_estimate.py. Familles corrigées par Holm : 25-29, 30-34, 35-39, 40-49.")
    tab_from(allr, "tab_h3.tex", allr.aggregation.isin(key_aggs + ["note"]) & allr.hypothesis.str.startswith("H3"),
             "Décomposition du canal (H3)", "tab:h3", "Source : scripts/05\\_estimate.py.")
    tab_from(allr, "tab_placebo.tex", allr.aggregation.isin(key_aggs + ["pre_test"]) & allr.hypothesis.str.startswith("H5"),
             "Placebos (H5)", "tab:placebo", "Source : scripts/05\\_estimate.py. H5c : p du test de Wald approché sur les coefficients $-8$ à $-2$, reporté pour chaque spécification dans est\\_fr\\_all.csv.")
    tab_from(allr, "tab_h6.tex", allr.aggregation.isin(["post_avg_1_5", "post_avg_1_5_holm"]) & allr.hypothesis.str.startswith("H6"),
             "Hétérogénéité (H6), communes", "tab:h6", "Source : scripts/05\\_estimate.py. p Holm dans la colonne notes de est\\_fr\\_all.csv.")
    tab_from(allr, "tab_robust.tex", allr.aggregation.isin(key_aggs) & (allr.family == "robustesse") & (allr.estimator == "cs"),
             "Robustesse", "tab:robust", "Source : scripts/05\\_estimate.py.")
    tab_from(allr, "tab_iv.tex", allr.aggregation == "iv", "Variables instrumentales (secondaire), ZEAT × âge × année", "tab:iv",
             "Source : scripts/05\\_estimate.py. 9 grappes : inférence indicative.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
