#!/usr/bin/env python
"""Étape 2d — tableau d'échantillon et taille d'effet minimale détectable (France), AVANT toute estimation.

Produit :
- ``tables/t_sample_fr.md`` / ``.csv`` : unités-années par spécification (préregistration §7) ;
- ``tables/t_mde_fr.md`` / ``.csv`` : MDE (80 %, 5 %) par permutation des cohortes (200 permutations) pour H1
  (commune, log du taux de naissances pour 1 000 femmes 15-44) et H2b (département × 25-39, log du taux),
  préregistration §5 « Puissance ».

Aucun ATT réel n'est calculé ici : l'estimateur ne tourne que sur des cohortes permutées.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import did  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "tables"
N_PERM = 200
MIN_PRE = 3


def commune_panel() -> pd.DataFrame:
    tr = pd.read_parquet(PROC / "fr_treatment_commune.parquet")
    oc = pd.read_parquet(PROC / "fr_outcomes_commune.parquet")
    d = oc.merge(tr.drop(columns=["dep", "metro"]), on=["unit", "year"], how="inner")
    d = d[d.metro].copy()
    d["cohort"] = d.cohort_4g
    d["log_rate"] = np.log((d.births + 0.5) / d.women_1544 * 1000)
    return d


def dep_age_panel() -> pd.DataFrame:
    da = pd.read_parquet(PROC / "fr_outcomes_dep_age.parquet")
    dt = pd.read_parquet(PROC / "fr_treatment_dep.parquet")
    d = da[da.metro].merge(dt[["dep", "year", "d3", "cohort_d3_50", "cohort_d3_90"]], on=["dep", "year"], how="left")
    d["cohort"] = d.cohort_d3_50.fillna(0).astype(int)
    d["log_rate"] = np.log(d.births_per_1000)
    return d


def sample_rows(name: str, d: pd.DataFrame, unit: str) -> dict:
    treated = d[d.cohort > 0]
    never = d[d.cohort == 0]
    return {"spécification": name, "unités": d[unit].nunique(), "années": f"{d.year.min()}-{d.year.max()}",
            "unités-années": len(d), "unités traitées": treated[unit].nunique(), "jamais traitées": never[unit].nunique(),
            "cohortes": f"{int(treated.cohort.min())}-{int(treated.cohort.max())}" if len(treated) else "—",
            "pré-période médiane (années)": float((treated.groupby(unit).cohort.first() - d.year.min()).median()) if len(treated) else np.nan}


def main() -> int:
    TABLES.mkdir(parents=True, exist_ok=True)
    com = commune_panel()
    da = dep_age_panel()
    rows = []
    # H1 : commune × année, toutes communes puis règle « ≥ 3 ans de pré-période »
    c_all = com.dropna(subset=["log_rate"])
    c_pre = did.drop_always_treated(c_all, "year", "cohort", MIN_PRE)
    rows.append(sample_rows("H1 commune × année, naissances/1 000 femmes 15-44 (toutes)", c_all, "unit"))
    rows.append(sample_rows(f"H1 idem, cohortes avec ≥ {MIN_PRE} années de pré-période (primaire)", c_pre, "unit"))
    rows.append(sample_rows("H1 robustesse 2008-2019", c_pre[c_pre.year <= 2019], "unit"))
    rows.append(sample_rows("H1 robustesse hors cohortes 2013-2017", c_pre[~c_pre.cohort.between(2013, 2017)], "unit"))
    for dens, lab in ((1, "dense"), (2, "intermédiaire"), (3, "rural")):
        sub = c_pre[c_pre.densite.map(lambda x: 1 if x in (1, 2) else 2 if x in (3, 4) else 3 if x in (5, 6, 7) else np.nan) == dens]
        rows.append(sample_rows(f"H6 densité {lab}", sub, "unit"))
    rows.append(sample_rows("H6 ZDP", c_pre[c_pre.zdp], "unit"))
    # H2 : département × âge
    for g in ["15-19", "20-24", "25-29", "30-34", "35-39", "40-49"]:
        sub = da[(da.age_group == g)].dropna(subset=["log_rate"])
        rows.append(sample_rows(f"H2 département × année, naissances/1 000 femmes {g} (D3 ≥ 50 %)", sub, "dep"))
    m = da.dropna(subset=["marriages_per_1000"])
    rows.append(sample_rows("H3a département × âge × année, mariages/1 000 femmes", m, "dep"))
    df = pd.DataFrame(rows)
    df.to_csv(TABLES / "t_sample_fr.csv", index=False)
    md = ["# Échantillons France par spécification (généré par scripts/04_sample_mde.py)", "", df.to_markdown(index=False)]
    (TABLES / "t_sample_fr.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(df.to_string())

    # MDE par permutation (TWFE statique sur log du taux, erreurs groupées à l'unité)
    mde_rows = []
    c_mde = c_pre[["unit", "year", "cohort", "log_rate"]].dropna()
    r = did.mde_permutation(c_mde, "log_rate", "unit", "year", "cohort", n_perm=N_PERM, seed=1)
    mde_rows.append({"hypothèse": "H1 commune, log(naissances/1 000 f. 15-44)", "sd placebo": r["sd_placebo"],
                     "MDE (80 %, 5 %) en log ≈ %": r["mde"], "permutations": r["n_perm_ok"], "moyenne placebo": r["placebo_mean"]})
    # H2b : taux agrégé 25-39 (pondéré par les effectifs de femmes)
    d2 = da[da.age_group.isin(["25-29", "30-34", "35-39"])].groupby(["dep", "year", "cohort"]).agg(births=("births", "sum"), women=("women", "sum")).reset_index()
    d2["log_rate"] = np.log(1000 * d2.births / d2.women)
    d2 = d2.dropna(subset=["log_rate"])
    d2 = d2[np.isfinite(d2.log_rate)]
    r2 = did.mde_permutation(d2[["dep", "year", "cohort", "log_rate"]], "log_rate", "dep", "year", "cohort", n_perm=N_PERM, seed=1)
    mde_rows.append({"hypothèse": "H2b département, log(naissances/1 000 f. 25-39), bascule D3 ≥ 50 %", "sd placebo": r2["sd_placebo"],
                     "MDE (80 %, 5 %) en log ≈ %": r2["mde"], "permutations": r2["n_perm_ok"], "moyenne placebo": r2["placebo_mean"]})
    for g in ["15-19", "20-24", "25-29", "30-34", "35-39"]:
        sub = da[da.age_group == g][["dep", "year", "cohort", "log_rate"]].dropna()
        sub = sub[np.isfinite(sub.log_rate)]
        rg = did.mde_permutation(sub, "log_rate", "dep", "year", "cohort", n_perm=N_PERM, seed=1)
        mde_rows.append({"hypothèse": f"H2 département, log(naissances/1 000 f. {g})", "sd placebo": rg["sd_placebo"],
                         "MDE (80 %, 5 %) en log ≈ %": rg["mde"], "permutations": rg["n_perm_ok"], "moyenne placebo": rg["placebo_mean"]})
    mde = pd.DataFrame(mde_rows)
    mde.to_csv(TABLES / "t_mde_fr.csv", index=False)
    md = ["# Taille d'effet minimale détectable, France (généré par scripts/04_sample_mde.py)", "",
          f"Permutation des cohortes observées entre unités ({N_PERM} tirages), ATT statique TWFE sur le log du taux, "
          "erreurs groupées à l'unité ; MDE = (1,96 + 0,84) × écart-type des ATT placebo. Un log-point ≈ 1 %.", "",
          mde.to_markdown(index=False, floatfmt=".4f")]
    (TABLES / "t_mde_fr.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(mde.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
