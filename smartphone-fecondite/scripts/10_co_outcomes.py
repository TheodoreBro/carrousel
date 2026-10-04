#!/usr/bin/env python
"""Colombie — résultats (addendum A4) : naissances par municipio de résidence de la mère × groupe d'âge × année
(EEVV 1998-2024), naissances de mères en union (mariées ou en union libre) et de rang 1, femmes par groupe d'âge
(projections DANE), taux pour 1 000 femmes.

Sorties : data/processed/co_outcomes_mun_age.parquet, co_outcomes_mun.parquet (15-49 agrégé), tables/t_outcomes_co.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common.co import AGE_GROUPS, age_group_of_single_age, load_projections, read_births  # noqa: E402
from common.download import raw_files  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "tables"


def log(msg: str) -> None:
    print(msg, flush=True)


def births() -> tuple[pd.DataFrame, list[dict]]:
    cache = PROC / "co_births_agg_cache.parquet"
    if cache.exists() and (PROC / "co_births_notes_cache.json").exists():
        import json
        return pd.read_parquet(cache), json.load(open(PROC / "co_births_notes_cache.json"))
    rows, notes = [], []
    for p in sorted(raw_files("co_dane_eevv_nacimientos")):
        b = read_births(p)
        n = len(b)
        yrs = sorted(b.year.dropna().astype(int).unique())
        excl = {"âge manquant ou hors 15-49": int(b.age_group.isna().sum()), "municipio invalide": int((~b.municipio.str.match(r"^\d{5}$")).sum()),
                "état civil inconnu": int(b.union.isna().sum())}
        notes.append({"fichier": p.name, "naissances": n, "années": f"{yrs[0]}-{yrs[-1]}" if yrs else "?", **excl})
        log(f"  {p.name} : {n:,} naissances, années {yrs}, exclues : {excl}")
        ok = b[b.age_group.notna() & b.year.notna() & b.municipio.str.match(r"^\d{5}$")].copy()
        # niveau d'éducation de la mère (NIV_EDUM, codage 2008+ : 7-12 = supérieur ; 99 = inconnu) — covariable de pré-période (A4)
        edu = pd.to_numeric(ok.get("niv_edum"), errors="coerce")
        ok["edu_sup"] = np.where(ok.year >= 2008, np.where(edu.between(7, 12), 1.0, np.where(edu.between(1, 13), 0.0, np.nan)), np.nan)
        g = ok.groupby(["municipio", "year", "age_group"]).agg(births=("edad", "size"), births_union=("union", "sum"),
                                                                 births_civ_known=("union", "count"), births_rank1=("rank1", "sum"),
                                                                 births_rank_known=("rank1", "count"), births_edu_sup=("edu_sup", "sum"),
                                                                 births_edu_known=("edu_sup", "count")).reset_index()
        rows.append(g)
    d = pd.concat(rows, ignore_index=True)
    d["year"] = d.year.astype(int)
    d = d.groupby(["municipio", "year", "age_group"], as_index=False).sum()
    import json
    d.to_parquet(cache, index=False)                                      # cache (≈ 10 min de lecture) ; supprimer pour recalculer
    json.dump(notes, open(PROC / "co_births_notes_cache.json", "w"), ensure_ascii=False, default=int)
    return d, notes


def women() -> pd.DataFrame:
    proj = load_projections(list(raw_files("co_dane_proyecciones")))
    f = proj[(proj.sex == "f") & (proj.area == "total")].copy()
    f["age_group"] = age_group_of_single_age(f.age)
    w = f.dropna(subset=["age_group"]).groupby(["municipio", "year", "age_group"])["pop"].sum().rename("women").reset_index()
    return w


def main() -> int:
    b, notes = births()
    w = women()
    years = sorted(b.year.unique())
    log(f"naissances : {len(b):,} cellules, {b.municipio.nunique()} municipios, {years[0]}-{years[-1]} ; femmes : {w.year.min()}-{w.year.max()}")
    full = pd.MultiIndex.from_product([sorted(set(b.municipio) | set(w.municipio)), years, AGE_GROUPS], names=["municipio", "year", "age_group"]).to_frame(index=False)
    d = full.merge(b, on=["municipio", "year", "age_group"], how="left").merge(w, on=["municipio", "year", "age_group"], how="left")
    # cellule absente des fichiers d'une année lue = zéro naissance (même règle qu'en France, A2.5)
    for c in ["births", "births_union", "births_civ_known", "births_rank1", "births_rank_known", "births_edu_sup", "births_edu_known"]:
        d[c] = d[c].fillna(0.0)
    d["births_per_1000"] = 1000 * d.births / d.women
    d["share_union"] = d.births_union / d.births_civ_known.where(d.births_civ_known > 0)
    d["share_rank1"] = d.births_rank1 / d.births_rank_known.where(d.births_rank_known > 0)
    d["dep"] = d.municipio.str[:2]
    d.to_parquet(PROC / "co_outcomes_mun_age.parquet", index=False)
    m = d.groupby(["municipio", "year"], as_index=False).agg(births=("births", "sum"), births_union=("births_union", "sum"), births_civ_known=("births_civ_known", "sum"),
                                                              births_rank1=("births_rank1", "sum"), births_rank_known=("births_rank_known", "sum"),
                                                              births_edu_sup=("births_edu_sup", "sum"), births_edu_known=("births_edu_known", "sum"), women=("women", "sum"))
    m["births_per_1000"] = 1000 * m.births / m.women
    m["dep"] = m.municipio.str[:2]
    m.to_parquet(PROC / "co_outcomes_mun.parquet", index=False)
    # tableau
    lines = ["# Colombie — résultats (généré par scripts/10_co_outcomes.py)", "",
             "Naissances EEVV par municipio de résidence de la mère et groupe d'âge ; femmes des projections DANE (área total, 30 juin). "
             "Mères de moins de 15 ans, de 50 ans et plus et d'âge inconnu hors périmètre (comptées ci-dessous).", "",
             "| fichier | naissances | années | âge manquant ou hors 15-49 | municipio invalide | état civil inconnu |", "|---|---|---|---|---|---|"]
    for n in notes:
        lines.append(f"| {n['fichier']} | {n['naissances']:,} | {n['années']} | {n['âge manquant ou hors 15-49']:,} | {n['municipio invalide']:,} | {n['état civil inconnu']:,} |")
    lines += ["", "| année | municipios | naissances 15-49 | femmes 15-49 | taux p. 1 000 | part en union | part rang 1 |", "|---|---|---|---|---|---|---|"]
    for y, g in d.groupby("year"):
        lines.append(f"| {y} | {g.municipio.nunique()} | {g.births.sum():,.0f} | {g.women.sum():,.0f} | {1000 * g.births.sum() / g.women.sum():.1f} | "
                     f"{g.births_union.sum() / max(g.births_civ_known.sum(), 1):.1%} | {g.births_rank1.sum() / max(g.births_rank_known.sum(), 1):.1%} |")
    (TABLES / "t_outcomes_co.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("\n".join(lines[-30:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
