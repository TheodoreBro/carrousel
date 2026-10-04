#!/usr/bin/env python
"""Synthèse entre pays (préregistration §5, addendum A7) : méta-analyse à effets aléatoires (REML) des ATT[1,k] primaires par groupe
d'âge, exprimés en % du taux contrefactuel, sur les pays inclus (France, Colombie, Brésil, Espagne). Test primaire = poolé 25-39 (H2b).
Sensibilité (A7, exploratoire) : sans les pays dont le pré-test de Wald de la spécification primaire H2b rejette à 5 % ; variante avec
les écarts-types bootstrap. Règle de décision §6 imprimée condition par condition.

Sorties : tables/t_meta.md, tables/t_meta.csv, figures/fig_meta.pdf|png.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import did  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "tables"
FIG = ROOT / "figures"
COUNTRIES = {
    "France": dict(file="est_fr_all.csv", sample="département, bascule D3 ≥ 50 %", outcome=lambda g: f"log(naissances / 1 000 f. {g})"),
    "Colombie": dict(file="est_co_all.csv", sample="municipios avec covariables, bascule 4G ≥ 50 %", outcome=lambda g: f"log(naissances+0,5 / 1 000 f. {g})"),
    "Brésil": dict(file="est_br_all.csv", sample="unités avec covariables, bascule 4G", outcome=lambda g: f"log(naissances+0,5 / 1 000 f. {g})"),
    "Espagne": dict(file="est_es_all.csv", sample="unités avec covariables, bascule 4G", outcome=lambda g: f"log(naissances+0,5 / 1 000 f. {g})"),
}
GROUPS = ["25-39", "15-19", "20-24", "25-29", "30-34", "35-39", "40-49", "15-24"]


def log(msg: str) -> None:
    print(msg, flush=True)


def rows() -> pd.DataFrame:
    out = []
    for name, c in COUNTRIES.items():
        p = TABLES / c["file"]
        if not p.exists():
            log(f"  {name} : {p.name} absent — pays non inclus dans la synthèse (dit)")
            continue
        d = pd.read_csv(p)
        d = d[(d.estimator == "cs") & (d.exploratory == False) & (d["sample"] == c["sample"])]  # noqa: E712
        for g in GROUPS:
            sub = d[d.outcome == c["outcome"](g)]
            pa = sub[sub.aggregation == "post_avg"]
            pb = sub[sub.aggregation == "post_avg_boot"]
            pt = sub[sub.aggregation == "pre_test"]
            if pa.empty:
                continue
            r = pa.iloc[0]
            out.append({"pays": name, "groupe": g, "hyp": r.hypothesis, "att_log": r.estimate, "se_log": r.se, "k": int(r.k_post) if np.isfinite(r.k_post) else np.nan,
                        "p": r.p, "se_boot_log": pb.iloc[0].se if len(pb) else np.nan, "p_pre": pt.iloc[0].p if len(pt) else np.nan, "n_units": int(r.n_units)})
    t = pd.DataFrame(out)
    t["att_pct"] = 100 * (np.exp(t.att_log) - 1)
    t["se_pct"] = 100 * np.exp(t.att_log) * t.se_log
    t["se_boot_pct"] = 100 * np.exp(t.att_log) * t.se_boot_log
    return t


def pool(t: pd.DataFrame, g: str, se_col: str = "se_pct", exclude: set | None = None) -> dict | None:
    s = t[(t.groupe == g) & t[se_col].notna()]
    if exclude:
        s = s[~s.pays.isin(exclude)]
    if len(s) < 2:
        return None
    r = did.meta_random_effects(s.att_pct.values, (s[se_col].values) ** 2, names=list(s.pays))
    k = len(s)
    # intervalle de prédiction à 95 % (t à k − 2 degrés de liberté) : sqrt(tau² + var(poolé))
    se_pool = (r["ci_upp"] - r["ci_low"]) / (2 * stats.norm.ppf(0.975))
    tcrit = stats.t.ppf(0.975, max(k - 2, 1))
    half = tcrit * np.sqrt(r["tau2"] + se_pool ** 2)
    z = r["estimate"] / se_pool if se_pool > 0 else np.nan
    return {"groupe": g, "pays": ", ".join(s.pays), "k_pays": k, "poolé %": r["estimate"], "es": se_pool, "IC bas": r["ci_low"], "IC haut": r["ci_upp"],
            "p": 2 * (1 - stats.norm.cdf(abs(z))), "PI bas": r["estimate"] - half, "PI haut": r["estimate"] + half, "tau2": r["tau2"], "I2": max(0.0, float(r["i2"])), "es_col": se_col}


def main() -> int:
    t = rows()
    if t.empty:
        raise SystemExit("aucune estimation nationale trouvée")
    t.to_csv(TABLES / "t_meta.csv", index=False)
    log(t.to_string())
    rejected = set(t[(t.groupe == "25-39") & (t.p_pre < 0.05)].pays)
    res = []
    for g in GROUPS:
        for se_col, lab, exc in (("se_pct", "primaire (es analytique, tous pays)", None), ("se_boot_pct", "es bootstrap", None),
                                 ("se_pct", "sans pays au pré-test rejeté (A7, exploratoire)", rejected)):
            r = pool(t, g, se_col, exc)
            if r:
                r["variante"] = lab
                res.append(r)
    R = pd.DataFrame(res)
    R.to_csv(TABLES / "t_meta.csv", index=False, mode="a")
    prim = R[(R.groupe == "25-39") & (R.variante.str.startswith("primaire"))]
    lines = ["# Synthèse entre pays — méta-analyse à effets aléatoires (généré par scripts/18_meta.py ; règles A7)", "",
             f"Pays inclus avec estimation : {', '.join(sorted(set(t.pays)))}. ATT[1,k] primaires par pays, Callaway & Sant'Anna, en % du taux contrefactuel "
             "(100 × (exp(ATT) − 1), écart-type delta). Pré-test rejeté à 5 % sur la spécification primaire H2b : " + (", ".join(sorted(rejected)) or "aucun") + ".", "",
             "## Estimations nationales retenues", "",
             "| pays | groupe | hyp. | ATT (log) | es | k | p | es bootstrap | p pré-test | unités | ATT % | es % |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in t.iterrows():
        lines.append(f"| {r.pays} | {r.groupe} | {r.hyp} | {r.att_log:+.4f} | {r.se_log:.4f} | {r.k} | {r.p:.3f} | "
                     f"{'' if pd.isna(r.se_boot_log) else f'{r.se_boot_log:.4f}'} | {'' if pd.isna(r.p_pre) else f'{r.p_pre:.3f}'} | {r.n_units} | {r.att_pct:+.2f} | {r.se_pct:.2f} |")
    lines += ["", "## Estimations poolées (REML)", "",
              "| groupe | variante | pays | poolé % | es | IC 95 % | p | intervalle de prédiction 95 % | τ² | I² |", "|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in R.iterrows():
        lines.append(f"| {r.groupe} | {r.variante} | {r.pays} | {r['poolé %']:+.2f} | {r.es:.2f} | [{r['IC bas']:+.2f}, {r['IC haut']:+.2f}] | {r.p:.3f} | "
                     f"[{r['PI bas']:+.2f}, {r['PI haut']:+.2f}] | {r.tau2:.2f} | {100 * r.I2:.0f} % |")
    # règle §6
    lines += ["", "## Règle de décision §6 (effet net sur les 25 ans et plus)", ""]
    h2b = t[t.groupe == "25-39"]
    sig = h2b[h2b.p < 0.05]
    same = sig[np.sign(sig.att_log) == np.sign(sig.att_log.iloc[0])] if len(sig) else sig
    cond1 = len(same) >= 2
    cond2 = bool(len(prim)) and float(prim.p.iloc[0]) < 0.05
    cond3 = all(p >= 0.05 for p in same.p_pre.dropna()) if len(same) else False
    lines += [f"- H2b rejetée (p < 0,05) de même signe dans ≥ 2 pays : {'oui' if cond1 else 'non'} ({', '.join(f'{r.pays} {r.att_pct:+.1f} % (p = {r.p:.3f})' for _, r in h2b.iterrows())})",
              f"- estimation poolée 25-39 significative : {'oui' if cond2 else 'non'} ({prim['poolé %'].iloc[0]:+.2f} %, p = {prim.p.iloc[0]:.3f})" if len(prim) else "- estimation poolée : non calculable",
              f"- H5c (pré-test) non rejeté dans les pays où H2b est rejetée : {'oui' if cond3 else 'non'} ; H5a et H5b : voir les tableaux nationaux (H5b non construit hors France)",
              f"- **Conclusion §6 : {'effet net sur les 25 ans et plus établi' if (cond1 and cond2 and cond3) else 'effet net sur les 25 ans et plus non établi'}** "
              "(les conditions H5a/H5b doivent être vérifiées à la main dans les tableaux nationaux avant de reporter cette conclusion)"]
    (TABLES / "t_meta.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("\n".join(lines[-12:]))
    # forêt
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    groups = [g for g in GROUPS if g in set(t.groupe)]
    fig, axes = plt.subplots(1, len(groups), figsize=(2.1 * len(groups), 3.6), sharey=False)
    axes = np.atleast_1d(axes)
    for ax, g in zip(axes, groups):
        s = t[t.groupe == g].reset_index(drop=True)
        y = np.arange(len(s))[::-1]
        ax.errorbar(s.att_pct, y, xerr=1.96 * s.se_pct, fmt="o", color="#2a78d6", ms=4, lw=1, capsize=0)
        pr = R[(R.groupe == g) & R.variante.str.startswith("primaire")]
        if len(pr):
            ax.errorbar([pr["poolé %"].iloc[0]], [-1], xerr=[[pr["poolé %"].iloc[0] - pr["IC bas"].iloc[0]], [pr["IC haut"].iloc[0] - pr["poolé %"].iloc[0]]],
                        fmt="D", color="#eb6834", ms=5, lw=1.4)
        ax.axvline(0, color="#52514e", lw=0.8)
        ax.set_yticks(list(y) + [-1], list(s.pays) + ["poolé"], fontsize=7)
        ax.set_title(g, fontsize=9, loc="left")
        ax.set_xlabel("ATT, % ; IC 95 %", fontsize=7)
        ax.tick_params(axis="x", labelsize=7)
    fig.suptitle("Effet de la bascule 4G sur les naissances pour 1 000 femmes, par pays et poolé (REML)", fontsize=9, x=0.01, ha="left")
    fig.tight_layout()
    FIG.mkdir(exist_ok=True)
    fig.savefig(FIG / "fig_meta.pdf", bbox_inches="tight")
    fig.savefig(FIG / "fig_meta.png", bbox_inches="tight", dpi=200)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
