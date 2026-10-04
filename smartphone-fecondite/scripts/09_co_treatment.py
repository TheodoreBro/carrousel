#!/usr/bin/env python
"""Colombie — traitement (addendum A4) à partir de la couverture mobile MinTIC par centro poblado.

Part de population couverte en 4G par au moins un opérateur, pour chaque municipio et chaque année (dernier trimestre
observé de l'année) : [pop. cabecera × 1(cabecera couverte) + pop. hors cabecera × (part des centros poblados couverts)]
/ pop. totale, avec les populations 2015 des projections DANE. Cohorte = première année avec part ≥ 50 % (variante 90 %) ;
municipios déjà ≥ 50 % au premier trimestre observé (2015-T4) = censurés à gauche (exclus du primaire). Même construction
pour la 3G (robustesse) et pour la seule cabecera.

Sorties : data/processed/co_treatment.parquet (municipio × année), co_treatment_static.parquet (cohortes, censure,
population 2015, part cabecera), tables/t_treatment_co.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common.co import load_projections  # noqa: E402
from common.download import raw_files  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "tables"
BASE_YEAR = 2015


def log(msg: str) -> None:
    print(msg, flush=True)


def coverage() -> pd.DataFrame:
    p = next(iter(raw_files("co_mintic_cobertura")))
    d = pd.read_csv(p, dtype=str, low_memory=False)
    d.columns = [c.strip().lower() for c in d.columns]
    d["year"] = pd.to_numeric(d["a_o"], errors="coerce").astype(int)
    d["q"] = pd.to_numeric(d["trimestre"], errors="coerce").astype(int)
    d["municipio"] = d.cod_municipio.astype(str).str.zfill(5)
    d["cp"] = d.cod_centro_poblado.astype(str)
    d["cab"] = d.cabecera_municipal.str.upper().eq("S")
    d["g4"] = d["cobertuta_4g"].str.upper().eq("S") | d["cobertura_lte"].str.upper().eq("S")
    d["g3"] = d["cobertura_3g"].str.upper().eq("S") | d["cobertura_hspa_hspa_dc"].str.upper().eq("S")
    log(f"couverture : {len(d):,} lignes, {d.municipio.nunique()} municipios, {d.cp.nunique():,} centros poblados, "
        f"{d.year.min()}-T{d[d.year == d.year.min()].q.min()} → {d.year.max()}-T{d[d.year == d.year.max()].q.max()}, {d.proveedor.nunique()} opérateurs")
    # au niveau centro poblado × trimestre : couvert par au moins un opérateur
    cpq = d.groupby(["municipio", "cp", "cab", "year", "q"], as_index=False).agg(g4=("g4", "max"), g3=("g3", "max"))
    # dernier trimestre observé de chaque année
    last_q = cpq.groupby(["municipio", "year"]).q.max().rename("q_last").reset_index()
    cpy = cpq.merge(last_q, on=["municipio", "year"])
    cpy = cpy[cpy.q == cpy.q_last]
    agg = cpy.groupby(["municipio", "year"]).apply(
        lambda g: pd.Series({"cab_g4": float(g.loc[g.cab, "g4"].max()) if g.cab.any() else np.nan,
                             "cab_g3": float(g.loc[g.cab, "g3"].max()) if g.cab.any() else np.nan,
                             "cp_share_g4": float(g.loc[~g.cab, "g4"].mean()) if (~g.cab).any() else np.nan,
                             "cp_share_g3": float(g.loc[~g.cab, "g3"].mean()) if (~g.cab).any() else np.nan,
                             "n_cp": int((~g.cab).sum()), "q_last": int(g.q_last.iloc[0])}), include_groups=False).reset_index()
    return agg


def populations() -> pd.DataFrame:
    proj = load_projections([p for p in raw_files("co_dane_proyecciones") if "2005-2017" in p.name])
    b = proj[proj.year == BASE_YEAR].groupby(["municipio", "area"])["pop"].sum().unstack()
    b = b.rename(columns={"cabecera": "pop_cab", "resto": "pop_resto", "total": "pop_total"})
    if "pop_total" not in b:
        b["pop_total"] = b.pop_cab + b.pop_resto
    b["share_cab"] = b.pop_cab / b.pop_total
    return b.reset_index()


def main() -> int:
    cov = coverage()
    pop = populations()
    d = cov.merge(pop, on="municipio", how="left")
    miss = d[d.pop_total.isna()].municipio.unique()
    log(f"municipios sans population DANE 2015 : {len(miss)} ({', '.join(sorted(miss)[:10])}{'…' if len(miss) > 10 else ''})")
    for tech in ("g4", "g3"):
        cab = d[f"cab_{tech}"].fillna(0.0)
        cps = d[f"cp_share_{tech}"].fillna(cab)                    # sans centro poblado hors cabecera : la cabecera fait foi
        d[f"share_{tech}"] = (d.pop_cab * cab + d.pop_resto * cps) / d.pop_total
    d = d.sort_values(["municipio", "year"])
    first_year = d.groupby("municipio").year.min().rename("first_obs")
    stat = pd.DataFrame({"first_obs": first_year})
    for tech, lab in (("g4", "4g"), ("g3", "3g")):
        for thr, suf in ((0.5, "50"), (0.9, "90")):
            hit = d[d[f"share_{tech}"] >= thr].groupby("municipio").year.min()
            stat[f"cohort_{lab}_{suf}"] = hit.reindex(stat.index).fillna(0).astype(int)
            first_val = d.merge(first_year.reset_index(), on="municipio").query("year == first_obs").set_index("municipio")[f"share_{tech}"]
            stat[f"censored_{lab}_{suf}"] = (first_val.reindex(stat.index) >= thr)
    hit = d[d.cab_g4 >= 1].groupby("municipio").year.min()
    stat["cohort_4g_cab"] = hit.reindex(stat.index).fillna(0).astype(int)
    stat = stat.merge(pop, left_index=True, right_on="municipio", how="left").set_index("municipio")
    stat["dep"] = stat.index.str[:2]
    stat = stat.reset_index()
    d.to_parquet(PROC / "co_treatment.parquet", index=False)
    stat.to_parquet(PROC / "co_treatment_static.parquet", index=False)
    # tableau
    lines = ["# Colombie — traitement (généré par scripts/09_co_treatment.py)", "",
             f"Couverture MinTIC par centro poblado, {d.year.min()}-{d.year.max()} ; populations DANE {BASE_YEAR} ; {stat.shape[0]} municipios "
             f"({stat.pop_total.notna().sum()} avec population). Part de population couverte = cabecera × 1(couverte) + hors cabecera × part des centros poblados couverts.", "",
             "| année | municipios observés | cabecera 4G | part 4G ≥ 50 % | part 4G ≥ 90 % | part 3G ≥ 50 % | médiane part 4G |", "|---|---|---|---|---|---|---|"]
    for y, g in d.groupby("year"):
        lines.append(f"| {y} (T{int(g.q_last.max())}) | {g.municipio.nunique()} | {int(g.cab_g4.fillna(0).sum())} | {int((g.share_g4 >= .5).sum())} | "
                     f"{int((g.share_g4 >= .9).sum())} | {int((g.share_g3 >= .5).sum())} | {100 * g.share_g4.median():.1f} % |")
    lines += ["", "## Cohortes (première année avec part de population couverte ≥ seuil ; 0 = jamais sur la fenêtre)", "",
              "| seuil | censurés au premier trimestre observé (exclus du primaire) | " + " | ".join(str(y) for y in range(2016, 2024)) + " | jamais |",
              "|---|---|" + "---|" * 9]
    for lab, col, cen in (("4G ≥ 50 % (primaire)", "cohort_4g_50", "censored_4g_50"), ("4G ≥ 90 %", "cohort_4g_90", "censored_4g_90"),
                          ("cabecera 4G", "cohort_4g_cab", "censored_4g_50"), ("3G ≥ 50 %", "cohort_3g_50", "censored_3g_50")):
        s = stat[~stat[cen]][col].value_counts()
        lines.append(f"| {lab} | {int(stat[cen].sum())} | " + " | ".join(str(int(s.get(y, 0))) for y in range(2016, 2024)) + f" | {int(s.get(0, 0))} |")
    lines += ["", f"Municipios observés pour la première fois après 2015-T4 : {int((stat.first_obs > 2015).sum())} (première observation = référence de censure).",
              f"Part de population en cabecera en {BASE_YEAR} : médiane {100 * stat.share_cab.median():.1f} %, q25 {100 * stat.share_cab.quantile(.25):.1f} %, q75 {100 * stat.share_cab.quantile(.75):.1f} %."]
    (TABLES / "t_treatment_co.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
