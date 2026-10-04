#!/usr/bin/env python
"""Étape 3 — tableaux LaTeX du papier (tables/*.tex), à partir des csv produits par les scripts 04, 04b et 05.

- tab_sample.tex       : unités-années par spécification (04_sample_mde.py)
- tab_mde.tex          : tailles d'effet minimales détectables (04_sample_mde.py)
- tab_firststage.tex   : first stage Baromètre (04b_firststage.py)
- tab_main.tex         : H1 et H2b, tous estimateurs (05_estimate.py)
- tab_h2_age.tex       : H2 par groupe d'âge (CS, Holm) et D3 continu
- tab_h3.tex           : canal (mariages, PACS, couples, naissances par femme en couple, différences longues, règle §6)
- tab_placebo.tex      : H5a-c
- tab_h6.tex           : hétérogénéité
- tab_robust.tex       : robustesse
- tab_iv.tex           : IV (secondaire) et test d'exclusion
- tab_exploratory.tex  : analyses complémentaires hors préregistration (addendum A2)

Aucune valeur n'est saisie à la main ; chaque cellule vient d'un csv. `--smoke` : lit tables/est_smoke/est_fr_all.csv et écrit
dans tables/est_smoke/tex/ (tests de fonctionnement ; jamais pour le papier).
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


def stars(p, p_type=None) -> str:
    if p is None or not np.isfinite(p):
        return ""
    st = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""
    return st + ("$^{w}$" if st and isinstance(p_type, str) and p_type.startswith("wild") else "")


def _visible_len(cell: str) -> int:
    """Longueur approximative du texte affiché (commandes LaTeX et espaces fines retirés)."""
    import re
    t = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", "", cell)
    return len(t.replace("\\,", "").replace("$", "").replace("{", "").replace("}", ""))


def auto_align(header: list[str], rows: list[list[str]], align: str, landscape: bool) -> str:
    """Convertit en colonnes `p{}` (texte renvoyé à la ligne) les colonnes dont une cellule dépasse 30 caractères, en répartissant la
    largeur disponible (16 cm en portrait, 24 cm en paysage) entre elles ; les alignements déjà explicites (`p{}`) sont conservés."""
    import re
    cols = re.findall(r"[lcr]|p\{[^}]*\}", align)
    if len(cols) != len(header) or any(c.startswith("p") for c in cols):
        return align
    maxlen = [max([_visible_len(h)] + [_visible_len(r[i]) for r in rows if i < len(r)]) for i, h in enumerate(header)]
    long_idx = [i for i, m in enumerate(maxlen) if m > 30]
    if not long_idx:
        return align
    char_cm = 0.13 if landscape else 0.16           # largeur moyenne d'un caractère (scriptsize / footnotesize), avec marge
    total = 24.0 if landscape else 16.0
    short = sum(char_cm * maxlen[i] + 0.35 for i in range(len(header)) if i not in long_idx)
    avail = max(total - short, 3.5 * len(long_idx))
    weights = [min(maxlen[i], 120) ** 0.5 for i in long_idx]
    widths = {i: max(3.5, min(7.5, avail * w / sum(weights))) for i, w in zip(long_idx, weights)}
    return "".join(f"p{{{widths[i]:.1f}cm}}" if i in widths else c for i, c in enumerate(cols))


def write(name: str, header: list[str], rows: list[list[str]], caption: str, label: str, note: str = "", align: str | None = None) -> None:
    """Tableau LaTeX (threeparttable). Au-delà de 8 colonnes le tableau est tourné (sidewaystable, scriptsize) ; les colonnes de texte long
    sont renvoyées à la ligne (auto_align) pour tenir dans la page."""
    align = align or "l" + "r" * (len(header) - 1)
    landscape = len(header) >= 9
    align = auto_align(header, rows, align, landscape)
    has_p = "p{" in align
    env = "sidewaystable" if landscape else "table"
    size = r"\scriptsize" if landscape else (r"\footnotesize" if has_p else r"\small")
    lines = [rf"\begin{{{env}}}[htbp]\centering", r"\begin{threeparttable}", rf"\caption{{{caption}}}\label{{{label}}}", size,
             rf"\begin{{tabular}}{{{align}}}", r"\toprule", " & ".join(esc(h) for h in header) + r" \\", r"\midrule"]
    lines += [" & ".join(r) + r" \\" for r in rows]
    lines += [r"\bottomrule", r"\end{tabular}"]
    if note:
        lines += [r"\begin{tablenotes}\footnotesize", rf"\item {note}", r"\end{tablenotes}"]
    lines += [r"\end{threeparttable}", rf"\end{{{env}}}", ""]
    out = (TABLES / "est_smoke" / "tex") if SMOKE else TABLES
    out.mkdir(parents=True, exist_ok=True)
    (out / name).write_text("\n".join(lines), encoding="utf-8")
    print("tableau :", out / name)


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


SMOKE = False


def _load_est() -> pd.DataFrame | None:
    p = (TABLES / "est_smoke" / "est_fr_all.csv") if SMOKE else (TABLES / "est_fr_all.csv")
    if not p.exists():
        return None
    d = pd.read_csv(p)
    if "exploratory" not in d:
        d["exploratory"] = False
    return d


def _row(r, with_sample=True) -> list[str]:
    cells = [esc(r.hypothesis), esc(r.outcome)]
    if with_sample:
        cells.append(esc(r["sample"]))
    ptype = r.get("p_type", None) if hasattr(r, "get") else None
    est = fmt(r.estimate, 4) + stars(r.p, ptype) if np.isfinite(r.se) else (fmt(r.estimate, 2) if np.isfinite(r.estimate) else "")
    se = f"({fmt(r.se, 4)})" if np.isfinite(r.se) else (f"p = {fmt(r.p, 3)}" if np.isfinite(r.p) else "")
    if str(r.get("aggregation", "")) == "timing":
        est, se = ("aucune" if not np.isfinite(r.estimate) else f"+{int(r.estimate)}"), ""
    k = r.get("k_post", np.nan)
    ym = r.get("years_model_max", np.nan)
    kcol = (f"{int(k)}" if np.isfinite(k) else "") + (f" ($\\leq$ {int(ym)})" if np.isfinite(ym) and np.isfinite(k) else "")
    cells += [esc(r.estimator), esc(r.term), est, se, kcol, f"{int(r.n_units):,}".replace(",", "\\,"), f"{int(r.n_obs):,}".replace(",", "\\,")]
    return cells


def tab_from(allr: pd.DataFrame, name: str, mask, caption: str, label: str, note: str, exploratory: bool = False) -> None:
    sub = allr[mask & (allr.exploratory == exploratory)]  # noqa: E712
    if sub.empty:
        return
    rows = [_row(r) for _, r in sub.iterrows()]
    write(name, ["Hyp.", "Résultat", "Échantillon", "Estimateur", "Terme", "Estimation", "É.-t.", "k (années id.)", "Unités", "Obs."], rows, caption, label,
          note + " ATT[1,k] = moyenne des effets +1 à +k (k = dernière période disponible $\\leq$ 5 ; colonne k, avec la dernière année où les ATT(g,t) "
          "sont identifiés pour Callaway \\& Sant'Anna). * p<0,10, ** p<0,05, *** p<0,01 (p d'un test z sur l'écart-type indiqué ; $^{w}$ : p du wild cluster "
          "bootstrap ; pour les tests de Wald, la p est donnée à la place de l'écart-type).", align="llllrrrrrr")


def main() -> int:
    tab_sample()
    tab_mde()
    tab_firststage()
    allr = _load_est()
    if allr is None:
        return 0
    key_aggs = ["post_avg", "post_avg_boot", "post_avg_balanced", "static"]
    tab_from(allr, "tab_main.tex",
             allr.aggregation.isin(key_aggs) & allr.hypothesis.isin(["H1", "H2b"]) & ~allr["sample"].str.contains("90 %") & (allr.family != "robustesse"),
             "Effet de la bascule 4G sur les naissances : effet total (H1, communes) et 25-39 ans (H2b, départements)", "tab:main",
             "Source : scripts/05\\_estimate.py. cs = Callaway \\& Sant'Anna (écart-type avec covariance complète des coefficients).")
    tab_from(allr, "tab_h2_age.tex",
             ((allr.aggregation.isin(["post_avg", "post_avg_holm"]) & (allr.estimator == "cs")) | allr.aggregation.isin(["continuous", "difference"]))
             & allr.hypothesis.str.startswith("H2") & ~allr["sample"].str.contains("90 %|anticipation"),
             "Effet par groupe d'âge (H2), départements", "tab:h2age",
             "Source : scripts/05\\_estimate.py. Familles corrigées par Holm : 15-19, 20-24 (H2a) ; 25-29, 30-34, 35-39, 40-49 (H2c) ; p Holm dans est\\_fr\\_all.csv.")
    tab_from(allr, "tab_h3.tex", allr.aggregation.isin(key_aggs + ["long_diff", "decision", "timing", "note"]) & allr.hypothesis.str.startswith(("H3", "§6")),
             "Décomposition du canal (H3) et règle de décision §6", "tab:h3", "Source : scripts/05\\_estimate.py.")
    tab_from(allr, "tab_placebo.tex", (allr.aggregation.isin(key_aggs + ["pre_test"]) & allr.hypothesis.str.startswith("H5"))
             | ((allr.aggregation == "pre_test") & allr.hypothesis.isin(["H1", "H2b"]) & (allr.estimator == "cs") & (allr.family != "robustesse")),
             "Placebos (H5)", "tab:placebo", "Source : scripts/05\\_estimate.py. H5c : test de Wald joint des coefficients $-8$ à $-2$ (covariance des fonctions d'influence) ; "
             "la p est reportée pour chaque spécification dans est\\_fr\\_all.csv.")
    tab_from(allr, "tab_h6.tex", allr.aggregation.isin(["post_avg", "post_avg_holm", "note"]) & allr.hypothesis.str.startswith("H6"),
             "Hétérogénéité (H6), communes", "tab:h6", "Source : scripts/05\\_estimate.py. p Holm dans la colonne notes de est\\_fr\\_all.csv.")
    tab_from(allr, "tab_robust.tex", allr.aggregation.isin(key_aggs + ["note"]) & (allr.family == "robustesse") & allr.estimator.isin(["cs", "—"]),
             "Robustesse", "tab:robust", "Source : scripts/05\\_estimate.py.")
    tab_from(allr, "tab_iv.tex", allr.aggregation.isin(["iv", "exclusion"]), "Variables instrumentales (secondaire), ZEAT × âge × année, et test d'exclusion", "tab:iv",
             "Source : scripts/05\\_estimate.py. 9 grappes : p du wild cluster bootstrap et intervalle d'Anderson-Rubin dans est\\_fr\\_all.csv.")
    tab_from(allr, "tab_exploratory.tex", allr.aggregation.isin(key_aggs), "Analyses complémentaires hors préregistration (addendum A2)", "tab:exploratory",
             "Source : scripts/05\\_estimate.py. Analyses ajoutées à la relecture, marquées « exploratoire » ; aucune n'entre dans les règles de décision.", exploratory=True)
    return 0


if __name__ == "__main__":
    import sys
    SMOKE = "--smoke" in sys.argv
    raise SystemExit(main())
