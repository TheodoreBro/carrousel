#!/usr/bin/env python
"""Espagne — résultats (addendum A6) : naissances par municipio de résidence de la mère × groupe d'âge × année (microdonnées INE
2007-2024 ; municipio codé seulement si > 10 000 habitants), naissances de mères mariées, de rang 1, de mères nées à l'étranger ;
mariages homme-femme par municipio de résidence du couple et âge de l'épouse (2008-2024) ; femmes par groupe d'âge au 1er janvier
(Padrón continuo 2003-2022).

Sorties : data/processed/es_outcomes_mun_age.parquet, es_outcomes_mun.parquet (15-49), es_static.parquet (population 2013, part des
femmes 15-49, part des mères nées à l'étranger 2010-2012, province), tables/t_outcomes_es.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common.download import raw_files  # noqa: E402
from common.es import AGE_GROUPS, age_group_of, padron_age_group, read_births, read_marriages, read_padron_px  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "tables"


def log(msg: str) -> None:
    print(msg, flush=True)


def births() -> tuple[pd.DataFrame, list[dict]]:
    rows, notes = [], []
    for p in sorted(x for x in raw_files("es_ine_nacimientos_microdatos") if x.name.startswith("datos_nacimientos")):
        b = read_births(p)
        n = len(b)
        b = b[b.live]
        b["age_group"] = age_group_of(b.age)
        excl = {"mort-nés / < 24 h exclus": int(n - len(b)), "municipio non codé (≤ 10 000 hab.)": int(b.municipio.isna().sum()),
                "âge manquant ou hors 15-49": int(b.age_group.isna().sum())}
        notes.append({"fichier": p.name, "naissances": n, "année": int(b.year.mode().iloc[0]), **excl})
        log(f"  {p.name} : {n:,} naissances ; {excl}")
        ok = b[b.municipio.notna() & b.age_group.notna()]
        g = ok.groupby(["municipio", "year", "age_group"]).agg(births=("age", "size"), births_married=("married", "sum"), births_civ_known=("married", "count"),
                                                              births_rank1=("rank1", "sum"), births_rank_known=("rank1", "count"),
                                                              births_foreign=("foreign_born", "sum"), births_foreign_known=("foreign_born", "count")).reset_index()
        rows.append(g)
    d = pd.concat(rows, ignore_index=True)
    d["year"] = d.year.astype(int)
    return d, notes


def marriages() -> pd.DataFrame:
    rows = []
    for p in sorted(x for x in raw_files("es_ine_matrimonios_microdatos") if x.name.startswith("datos_matrimonios")):
        m = read_marriages(p)
        m = m[m.hetero & m.municipio.notna()]
        m["age_group"] = age_group_of(m.wife_age)
        rows.append(m.dropna(subset=["age_group"]).groupby(["municipio", "year", "age_group"]).size().rename("marriages").reset_index())
        log(f"  {p.name} : {len(m):,} mariages homme-femme avec municipio codé")
    d = pd.concat(rows, ignore_index=True)
    d["year"] = d.year.astype(int)
    return d


def women() -> tuple[pd.DataFrame, pd.DataFrame]:
    p = next(iter(raw_files("es_ine_padron_municipios_edad")))
    px = read_padron_px(p)
    f = px[px.sex == "f"].copy()
    f["age_group"] = f.age_group.map(padron_age_group)
    w = f.dropna(subset=["age_group"]).groupby(["municipio", "year", "age_group"])["pop"].sum(min_count=1).rename("women").reset_index()
    tot = px[(px.sex == "total") & (px.age_group == "Todas las edades")][["municipio", "year", "pop"]].rename(columns={"pop": "pop_total"})
    return w, tot


def main() -> int:
    b, notes = births()
    m = marriages()
    w, tot = women()
    log(f"naissances : {b.municipio.nunique()} municipios codés, {b.year.min()}-{b.year.max()} ; mariages {m.year.min()}-{m.year.max()} ; "
        f"padrón {w.year.min()}-{w.year.max()}, {w.municipio.nunique()} municipios")
    years = list(range(2007, 2025))
    # municipios codés chaque année de la fenêtre d'estimation 2007-2022 (A6 : panel équilibré de municipios > 10 000 habitants)
    coded = b.groupby("municipio").year.nunique()
    muns = sorted(set(coded[coded >= len([y for y in years if y <= 2022])].index) & set(w.municipio))
    full = pd.MultiIndex.from_product([muns, years, AGE_GROUPS], names=["municipio", "year", "age_group"]).to_frame(index=False)
    d = full.merge(b, on=["municipio", "year", "age_group"], how="left").merge(w, on=["municipio", "year", "age_group"], how="left") \
            .merge(m, on=["municipio", "year", "age_group"], how="left").merge(tot, on=["municipio", "year"], how="left")
    for c in ["births", "births_married", "births_civ_known", "births_rank1", "births_rank_known", "births_foreign", "births_foreign_known"]:
        d[c] = d[c].fillna(0.0)
    d.loc[d.year >= 2008, "marriages"] = d.loc[d.year >= 2008, "marriages"].fillna(0.0)
    d["births_per_1000"] = 1000 * d.births / d.women
    d["prov"] = d.municipio.str[:2]
    d.to_parquet(PROC / "es_outcomes_mun_age.parquet", index=False)
    mm = d.groupby(["municipio", "year"], as_index=False).agg(births=("births", "sum"), women=("women", "sum"), marriages=("marriages", "sum"), pop_total=("pop_total", "first"))
    mm["births_per_1000"] = 1000 * mm.births / mm.women
    mm.to_parquet(PROC / "es_outcomes_mun.parquet", index=False)
    st = d[d.year == 2013].groupby("municipio").agg(pop_2013=("pop_total", "first"), women_1549_2013=("women", "sum")).reset_index()
    st["share_women_1549_2013"] = st.women_1549_2013 / st.pop_2013
    fb = d[d.year.between(2010, 2012)].groupby("municipio")[["births_foreign", "births_foreign_known"]].sum()
    st["share_foreign_1012"] = (fb.births_foreign / fb.births_foreign_known.where(fb.births_foreign_known > 0)).reindex(st.municipio).values
    st["prov"] = st.municipio.str[:2]
    st.to_parquet(PROC / "es_static.parquet", index=False)
    lines = ["# Espagne — résultats (généré par scripts/17_es_outcomes.py)", "",
             "Naissances INE (microdonnées) par municipio de résidence de la mère (codé si > 10 000 habitants) et groupe d'âge ; femmes au 1er janvier "
             "(Padrón continuo, 2003-2022) ; mariages homme-femme par âge de l'épouse (2008 →). Panel = municipios codés toutes les années 2007-2022.", "",
             "| fichier | naissances | année | mort-nés / < 24 h exclus | municipio non codé | âge manquant ou hors 15-49 |", "|---|---|---|---|---|---|"]
    for n in notes:
        lines.append(f"| {n['fichier']} | {n['naissances']:,} | {n['année']} | {n['mort-nés / < 24 h exclus']:,} | {n['municipio non codé (≤ 10 000 hab.)']:,} | {n['âge manquant ou hors 15-49']:,} |")
    lines += ["", "| année | municipios | naissances 15-49 | femmes 15-49 | taux p. 1 000 | part mères mariées | part rang 1 | part mères nées à l'étranger | mariages (épouse 15-49) |",
              "|---|---|---|---|---|---|---|---|---|"]
    for y, g in d.groupby("year"):
        wsum = g.women.sum()
        lines.append(f"| {y} | {g.municipio.nunique()} | {g.births.sum():,.0f} | {wsum:,.0f} | {(1000 * g.births.sum() / wsum) if wsum > 0 else float('nan'):.1f} | "
                     f"{g.births_married.sum() / max(g.births_civ_known.sum(), 1):.1%} | {g.births_rank1.sum() / max(g.births_rank_known.sum(), 1):.1%} | "
                     f"{g.births_foreign.sum() / max(g.births_foreign_known.sum(), 1):.1%} | {g.marriages.sum():,.0f} |")
    (TABLES / "t_outcomes_es.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("\n".join(lines[-22:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
