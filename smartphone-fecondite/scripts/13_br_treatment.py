#!/usr/bin/env python
"""Brésil — traitement (addendum A5) à partir de la table Anatel « Municípios atendidos por SMP ».

Présence de la 4G (et de la 3G) par au moins un opérateur dans le município : instantanés de décembre 2013-2016, puis mensuels
2017 → ; l'instantané 2013-12 ne contient aucune présence 4G (artefact de la source, A5) et n'est utilisé que pour la 3G.
Cohorte = première année de présence (décembre pour 2014-2016, premier mois de présence ensuite) ; variante ≥ 2 opérateurs ;
3G : municípios déjà couverts au 2013-12 = censurés à gauche.

Sorties : data/processed/br_treatment.parquet (município × année : nombre d'opérateurs 4G et 3G en fin d'année),
br_treatment_static.parquet (cohortes, censure, UF, région), tables/t_treatment_br.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common.br import REGIONS, read_anatel_presence  # noqa: E402
from common.download import raw_files  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "tables"


def log(msg: str) -> None:
    print(msg, flush=True)


def main() -> int:
    p = next(iter(raw_files("br_anatel_municipios_atendidos")))
    d = read_anatel_presence(p)
    log(f"Anatel : {len(d):,} lignes, {d.municipio.nunique()} municípios, {d.per.min():%Y-%m} → {d.per.max():%Y-%m}, "
        f"{d.per.nunique()} périodes, technologies {sorted(d.tech.unique())}, {d.operator.nunique()} opérateurs")
    d = d[d.tech.isin(["3G", "4G"])]
    # nombre d'opérateurs présents par município × technologie × période, puis fin d'année (dernière période de l'année)
    n = d[d.present].groupby(["municipio", "tech", "per"]).operator.nunique().rename("n_op").reset_index()
    grid = d.groupby(["municipio", "tech", "per"]).size().reset_index()[["municipio", "tech", "per"]]
    n = grid.merge(n, on=["municipio", "tech", "per"], how="left").fillna({"n_op": 0})
    n["year"] = n.per.dt.year
    last = n.groupby(["municipio", "tech", "year"]).per.max().rename("per_last").reset_index()
    ye = n.merge(last, on=["municipio", "tech", "year"]).query("per == per_last")
    wide = ye.pivot_table(index=["municipio", "year"], columns="tech", values="n_op", aggfunc="first").rename(columns={"3G": "n_op_3g", "4G": "n_op_4g"}).reset_index()
    wide["n_op_3g"] = wide.n_op_3g.fillna(0).astype(int)
    wide["n_op_4g"] = wide.n_op_4g.fillna(0).astype(int)
    # cohortes : première année de présence (toutes périodes de l'année, pas seulement la dernière)
    first4 = n[(n.tech == "4G") & (n.n_op >= 1) & (n.year >= 2014)].groupby("municipio").year.min()
    first4_2 = n[(n.tech == "4G") & (n.n_op >= 2) & (n.year >= 2014)].groupby("municipio").year.min()
    first3 = n[(n.tech == "3G") & (n.n_op >= 1)].groupby("municipio").year.min()
    cens3 = n[(n.tech == "3G") & (n.per == n.per.min())].set_index("municipio").n_op >= 1
    uf = d.groupby("municipio").uf.first()
    stat = pd.DataFrame({"uf": uf})
    stat["cohort_4g_1"] = first4.reindex(stat.index).fillna(0).astype(int)
    stat["cohort_4g_2"] = first4_2.reindex(stat.index).fillna(0).astype(int)
    stat["cohort_3g_1"] = first3.reindex(stat.index).fillna(0).astype(int)
    stat["censored_3g_1"] = cens3.reindex(stat.index).fillna(False).astype(bool)
    stat["censored_4g_1"] = False                      # aucune présence 4G au 2013-12 dans la source (A5) : pas de censure mesurable
    stat["region"] = stat.index.str[0].map(REGIONS)
    stat = stat.reset_index()
    wide.to_parquet(PROC / "br_treatment.parquet", index=False)
    stat.to_parquet(PROC / "br_treatment_static.parquet", index=False)
    years = sorted(wide.year.unique())
    lines = ["# Brésil — traitement (généré par scripts/13_br_treatment.py)", "",
             f"Anatel, « Municípios atendidos por SMP » : présence par opérateur et technologie, {d.per.min():%Y-%m} → {d.per.max():%Y-%m} "
             f"(instantanés de décembre 2013-2016, mensuels ensuite) ; {stat.shape[0]} municípios. Au 2013-12 aucune ligne 4G n'est « SIM » (A5).", "",
             "| année (fin) | municípios | 4G ≥ 1 opérateur | 4G ≥ 2 opérateurs | 3G ≥ 1 opérateur | médiane opérateurs 4G |", "|---|---|---|---|---|---|"]
    for y in years:
        g = wide[wide.year == y]
        lines.append(f"| {y} | {g.municipio.nunique()} | {int((g.n_op_4g >= 1).sum())} | {int((g.n_op_4g >= 2).sum())} | {int((g.n_op_3g >= 1).sum())} | {g.n_op_4g.median():.0f} |")
    lines += ["", "## Cohortes (première année de présence ; 0 = jamais sur la fenêtre)", "",
              "| définition | censurés | " + " | ".join(str(y) for y in range(2014, 2024)) + " | jamais |", "|---|---|" + "---|" * 11]
    for lab, col, cen in (("4G ≥ 1 opérateur (primaire)", "cohort_4g_1", "censored_4g_1"), ("4G ≥ 2 opérateurs", "cohort_4g_2", "censored_4g_1"),
                          ("3G ≥ 1 opérateur (censure au 2013-12)", "cohort_3g_1", "censored_3g_1")):
        s = stat[~stat[cen]][col].value_counts()
        lines.append(f"| {lab} | {int(stat[cen].sum())} | " + " | ".join(str(int(s.get(y, 0))) for y in range(2014, 2024)) + f" | {int(s.get(0, 0))} |")
    lines += ["", "Par grande région, cohorte 4G ≥ 1 opérateur (médiane) : " + " ; ".join(f"{r} {stat[(stat.region == r) & (stat.cohort_4g_1 > 0)].cohort_4g_1.median():.0f}"
                                                                                       for r in REGIONS.values())]
    (TABLES / "t_treatment_br.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
