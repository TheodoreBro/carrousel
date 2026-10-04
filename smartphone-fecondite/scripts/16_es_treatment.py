#!/usr/bin/env python
"""Espagne — traitement (addendum A6) : part de la population couverte en LTE par municipio (MINECO/SETELECO), instantanés de
décembre 2013-2015 puis de juin 2016-2020 ; cohorte = année du premier instantané avec part ≥ 50 % (variante 90 %) ; le premier
instantané (déc. 2013) marque les municipios « premier instantané » (gardés en primaire, exclus en robustesse : A6). Les
instantanés 4G 2023-2025 (part des foyers) ne servent qu'à documenter les municipios encore sous le seuil en 2020.

Sorties : data/processed/es_treatment.parquet (municipio × instantané), es_treatment_static.parquet (cohortes, habitants, province),
tables/t_treatment_es.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common.download import raw_files  # noqa: E402
from common.es import read_coverage_2013_2020, read_coverage_2021_2025  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "tables"


def log(msg: str) -> None:
    print(msg, flush=True)


def main() -> int:
    cov, pop = read_coverage_2013_2020(next(iter(raw_files("es_cobertura_municipios_2013_2020"))))
    cov2 = read_coverage_2021_2025(next(iter(raw_files("es_cobertura_municipios_2021_2025"))))
    lte = cov[cov.tech == "LTE"].sort_values(["municipio", "year", "month"])
    log(f"couverture : {lte.municipio.nunique()} municipios, instantanés {sorted(set(zip(lte.year, lte.month)))}")
    snaps = lte.groupby(["year", "month"]).size().reset_index()[["year", "month"]]
    first = snaps.iloc[0]
    stat = pd.DataFrame({"municipio": sorted(lte.municipio.unique())}).set_index("municipio")
    for thr, suf in ((0.5, "50"), (0.9, "90")):
        hit = lte[lte.share >= thr].groupby("municipio").year.min()
        stat[f"cohort_lte_{suf}"] = hit.reindex(stat.index).fillna(0).astype(int)
        f0 = lte[(lte.year == first.year) & (lte.month == first.month)].set_index("municipio").share
        stat[f"first_snapshot_{suf}"] = (f0.reindex(stat.index) >= thr).fillna(False)
        stat[f"censored_lte_{suf}"] = False          # cohorte 2013 gardée en primaire (A6) ; exclue en robustesse via first_snapshot_*
    hsp = cov[cov.tech == "HSPA"]
    hit = hsp[hsp.share >= 0.5].groupby("municipio").year.min()
    stat["cohort_hspa_50"] = hit.reindex(stat.index).fillna(0).astype(int)
    stat = stat.merge(pop.set_index("municipio"), left_index=True, right_index=True, how="left")
    stat["prov"] = stat.index.str[:2]
    stat = stat.reset_index()
    cov.to_parquet(PROC / "es_treatment.parquet", index=False)
    stat.to_parquet(PROC / "es_treatment_static.parquet", index=False)
    g4 = cov2.pivot_table(index="municipio", columns="year", values="share", aggfunc="first")
    lines = ["# Espagne — traitement (généré par scripts/16_es_treatment.py)", "",
             f"MINECO/SETELECO, part de population couverte en LTE par municipio ({stat.shape[0]} municipios) ; instantanés de décembre 2013-2015 et de juin 2016-2020 ; "
             "4G (part des foyers) en juin 2023-2025.", "",
             "| instantané | municipios | LTE ≥ 50 % | LTE ≥ 90 % | médiane | ≥ 50 % parmi > 10 000 hab. |", "|---|---|---|---|---|---|"]
    big = set(stat[stat.habitantes > 10000].municipio)
    for (y, m), g in lte.groupby(["year", "month"]):
        lab = f"{'déc.' if m == 12 else 'juin'} {y}"
        lines.append(f"| {lab} | {g.share.notna().sum()} | {int((g.share >= .5).sum())} | {int((g.share >= .9).sum())} | {100 * g.share.median():.1f} % | "
                     f"{int((g[g.municipio.isin(big)].share >= .5).sum())} / {len(big)} |")
    for y in sorted(g4.columns):
        lines.append(f"| juin {y} (4G, foyers) | {g4[y].notna().sum()} | {int((g4[y] >= .5).sum())} | {int((g4[y] >= .9).sum())} | {100 * g4[y].median():.1f} % | |")
    lines += ["", "## Cohortes (année du premier instantané ≥ seuil ; 0 = jamais sur 2013-2020)", "",
              "| seuil | échantillon | " + " | ".join(str(y) for y in range(2013, 2021)) + " | jamais |", "|---|---|" + "---|" * 9]
    for suf in ("50", "90"):
        for lab, sub in (("tous municipios", stat), ("> 10 000 habitants", stat[stat.habitantes > 10000])):
            s = sub[f"cohort_lte_{suf}"].value_counts()
            lines.append(f"| LTE ≥ {suf} % | {lab} | " + " | ".join(str(int(s.get(y, 0))) for y in range(2013, 2021)) + f" | {int(s.get(0, 0))} |")
    (TABLES / "t_treatment_es.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
