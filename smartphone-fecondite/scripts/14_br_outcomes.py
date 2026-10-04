#!/usr/bin/env python
"""Brésil — résultats (addendum A5) : nés vivants par município de résidence de la mère × groupe d'âge × année d'occurrence
(IBGE, Registro Civil, table 2609, 2003-2024), mariages homme-femme par groupe d'âge de l'épouse (table 4412, 2013-2024),
femmes par groupe d'âge interpolées entre les recensements 2000, 2010 et 2022 et calées sur la population totale annuelle (table 6579).

Naissances de l'année t = enregistrées en t et nées en t + enregistrées en t+1 et nées en t (2024 : enregistrements de 2025
indisponibles → provisoire). Convention SIDRA : « - » = zéro absolu, « ... » = non disponible, « X » = secret statistique.

Sorties : data/processed/br_outcomes_mun_age.parquet, br_outcomes_mun.parquet (15-49), br_static.parquet (population 2010,
part des femmes 15-49, région), tables/t_outcomes_br.md.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common.br import AGE_GROUPS, IBGE_GROUP_TO_AGE, REGIONS, read_ibge  # noqa: E402
from common.download import raw_files  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "tables"
YEARS = list(range(2003, 2025))
# municípios créés en 2013 (absents du recensement 2000) et municípios d'origine, exclus (A5, §10) ; codes IBGE
CREATED_2013 = {"1504752": "Mojuí dos Campos (PA)", "4212650": "Pescaria Brava (SC)", "4220000": "Balneário Rincão (SC)",
                "4314548": "Pinto Bandeira (RS)", "5006275": "Paraíso das Águas (MS)"}
PARENTS_2013 = {"1506807": "Santarém (PA)", "4209409": "Laguna (SC)", "4207007": "Içara (SC)", "4302105": "Bento Gonçalves (RS)",
                "5003504": "Costa Rica (MS)", "5000203": "Água Clara (MS)", "5002951": "Chapadão do Sul (MS)"}


def log(msg: str) -> None:
    print(msg, flush=True)


def _age_group(label: str) -> str:
    if label in IBGE_GROUP_TO_AGE:
        return IBGE_GROUP_TO_AGE[label]
    if label.startswith("Menos de 15"):
        return "<15"
    if label.startswith("50"):
        return "50+"
    if label.startswith("Ignorad"):
        return "inconnu"
    return "total" if label == "Total" else label


def births() -> tuple[pd.DataFrame, dict]:
    frames = []
    for p in sorted(raw_files("br_ibge_nascidos_vivos")):
        frames.append(read_ibge(p))
    d = pd.concat(frames, ignore_index=True)
    d["age_group"] = d["Idade da mãe na ocasião do parto"].map(_age_group)
    d["born"] = pd.to_numeric(d["Ano de nascimento"], errors="coerce").astype(int)
    d = d.rename(columns={"year": "registered"})
    notes = {"cellules « ... » ou « X » (non disponibles)": int(d.value.isna().sum()), "cellules « - » (zéro)": int((d.raw == "-").sum()),
             "lignes": int(len(d))}
    d["value"] = d.value.where(d.raw != "-", 0.0)
    # année d'occurrence : enregistrées la même année ou l'année suivante
    same = d[d.registered == d.born]
    late = d[d.registered == d.born + 1]
    keys = ["municipio", "born", "age_group"]
    b = same.groupby(keys).value.sum(min_count=1).rename("same").reset_index().merge(
        late.groupby(keys).value.sum(min_count=1).rename("late").reset_index(), on=keys, how="outer")
    b["births"] = b.same.fillna(0) + b.late.fillna(0)
    b.loc[b.same.isna() & b.late.isna(), "births"] = np.nan
    b = b.rename(columns={"born": "year"})
    b = b[b.year >= YEARS[0]]                      # les nés en 2002 enregistrés en 2003 n'ont pas d'enregistrement « même année » lu
    notes["part des enregistrements tardifs (naissances 15-49, 2003-2023)"] = float(
        b[(b.year <= 2023) & b.age_group.isin(AGE_GROUPS)].late.sum() / b[(b.year <= 2023) & b.age_group.isin(AGE_GROUPS)].births.sum())
    return b[["municipio", "year", "age_group", "births"]], notes


def census_women() -> pd.DataFrame:
    """Femmes par groupe d'âge et município aux recensements 2000 (groupes), 2010 et 2022 (âges simples)."""
    rows = []
    for p in sorted(raw_files("br_ibge_censo_mulheres")):
        d = read_ibge(p)
        col = "Grupo de idade" if "Grupo de idade" in d else "Idade"
        if col == "Grupo de idade":
            d["age_group"] = d[col].map(IBGE_GROUP_TO_AGE)
        else:
            age = pd.to_numeric(d[col].str.extract(r"^(\d+) ano")[0], errors="coerce")
            d["age_group"] = pd.cut(age, bins=[15, 20, 25, 30, 35, 40, 50], right=False, labels=AGE_GROUPS).astype(object)
        d["value"] = d.value.where(d.raw != "-", 0.0)
        rows.append(d.dropna(subset=["age_group"]).groupby(["municipio", "year", "age_group"]).value.sum(min_count=1).rename("women").reset_index())
    return pd.concat(rows, ignore_index=True)


def population_total() -> pd.DataFrame:
    rows = []
    for key in ("br_ibge_censo_total", "br_ibge_populacao_estimada"):
        for p in sorted(raw_files(key)):
            d = read_ibge(p)
            d["value"] = d.value.where(d.raw != "-", 0.0)
            rows.append(d.groupby(["municipio", "year"]).value.first().rename("pop_total").reset_index().assign(src="censo" if "censo" in key else "estimativa"))
    return pd.concat(rows, ignore_index=True)


def women_by_year(cw: pd.DataFrame, pt: pd.DataFrame) -> pd.DataFrame:
    """Part de chaque groupe d'âge dans la population totale, interpolée linéairement entre recensements (constante au-delà),
    × population totale de l'année (recensement ou estimation ; années manquantes interpolées log-linéairement)."""
    tot = pt.pivot_table(index="municipio", columns="year", values="pop_total", aggfunc="first")
    tot = tot.reindex(columns=range(2000, 2025))
    ltot = np.log(tot.where(tot > 0))
    ltot = ltot.interpolate(axis=1, limit_direction="both")
    tot_y = np.exp(ltot)
    cens = cw.pivot_table(index=["municipio", "age_group"], columns="year", values="women", aggfunc="first")
    share = cens.copy()
    for y in share.columns:
        share[y] = share[y] / tot[y].reindex(share.index.get_level_values(0)).values
    share = share.reindex(columns=range(2000, 2025)).interpolate(axis=1, limit_direction="both")
    w = share.stack().rename("share").reset_index().rename(columns={"level_2": "year"})
    w["pop_total"] = tot_y.stack().reindex(pd.MultiIndex.from_frame(w[["municipio", "year"]])).values
    w["women"] = w.share * w.pop_total
    return w[["municipio", "year", "age_group", "women", "pop_total"]]


def marriages() -> pd.DataFrame:
    rows = []
    for p in sorted(raw_files("br_ibge_casamentos")):
        d = read_ibge(p)
        d["age_group"] = d["Grupo de idade do segundo cônjuge"].map(_age_group)
        d["value"] = d.value.where(d.raw != "-", 0.0)
        rows.append(d.groupby(["municipio", "year", "age_group"]).value.sum(min_count=1).rename("marriages").reset_index())
    return pd.concat(rows, ignore_index=True)


def main() -> int:
    b, notes = births()
    log(f"naissances : {len(b):,} cellules, {b.municipio.nunique()} municípios, {b.year.min()}-{b.year.max()} ; {notes}")
    cw = census_women()
    pt = population_total()
    w = women_by_year(cw, pt)
    log(f"femmes : recensements {sorted(cw.year.unique())}, {cw.municipio.nunique()} municípios ; population totale {pt.groupby('src').year.unique().to_dict()}")
    m = marriages()
    log(f"mariages : {m.year.min()}-{m.year.max()}, {m.municipio.nunique()} municípios")
    excl = set(CREATED_2013) | set(PARENTS_2013)
    muns = sorted((set(b.municipio) & set(w.municipio)) - excl)
    full = pd.MultiIndex.from_product([muns, YEARS, AGE_GROUPS], names=["municipio", "year", "age_group"]).to_frame(index=False)
    d = full.merge(b, on=["municipio", "year", "age_group"], how="left").merge(w, on=["municipio", "year", "age_group"], how="left") \
            .merge(m, on=["municipio", "year", "age_group"], how="left")
    # cellule absente de la table (município sans naissance dans la cellule) = zéro : la table 2609 ne renvoie pas de « - » pour toutes
    # les combinaisons ; les cellules « ... »/« X » restent manquantes (comptées)
    d["births"] = d.births.fillna(0.0)
    years_m = set(m.year.unique())                 # zéro seulement pour les années effectivement lues (2017+ absentes si l'API n'a pas répondu)
    d.loc[d.year.isin(years_m), "marriages"] = d.loc[d.year.isin(years_m), "marriages"].fillna(0.0)
    oth = b[b.age_group.isin(["<15", "50+", "inconnu"])].groupby(["year", "age_group"]).births.sum().unstack()
    d["births_per_1000"] = 1000 * d.births / d.women
    d["uf"] = d.municipio.str[:2]
    d["region"] = d.municipio.str[0].map(REGIONS)
    d.to_parquet(PROC / "br_outcomes_mun_age.parquet", index=False)
    mm = d.groupby(["municipio", "year"], as_index=False).agg(births=("births", "sum"), women=("women", "sum"), marriages=("marriages", "sum"), pop_total=("pop_total", "first"))
    mm["births_per_1000"] = 1000 * mm.births / mm.women
    mm.to_parquet(PROC / "br_outcomes_mun.parquet", index=False)
    st = d[d.year == 2010].groupby("municipio").agg(pop_2010=("pop_total", "first"), women_1549_2010=("women", "sum")).reset_index()
    st["share_women_1549_2010"] = st.women_1549_2010 / st.pop_2010
    st["region"] = st.municipio.str[0].map(REGIONS)
    st.to_parquet(PROC / "br_static.parquet", index=False)
    lines = ["# Brésil — résultats (généré par scripts/14_br_outcomes.py)", "",
             "Nés vivants (IBGE, Registro Civil, table 2609) par município de résidence de la mère et groupe d'âge, année d'occurrence "
             "(enregistrés l'année même ou la suivante ; 2024 provisoire) ; femmes interpolées entre les recensements 2000, 2010, 2022 et "
             "calées sur la population totale annuelle (A5). Mariages homme-femme par âge de l'épouse (table 4412) à partir de 2013.", "",
             f"Lecture : {notes}. Municípios exclus (créés en 2013 et municípios d'origine, A5) : {', '.join(sorted(CREATED_2013.values()))} ; "
             f"{', '.join(sorted(PARENTS_2013.values()))}.", "",
             "| année | municípios | naissances 15-49 | dont < 15 / 50+ / âge inconnu | femmes 15-49 | taux p. 1 000 | mariages (épouse 15-49) |", "|---|---|---|---|---|---|---|"]
    for y, g in d.groupby("year"):
        o = oth.loc[y] if y in oth.index else {}
        lines.append(f"| {y} | {g.municipio.nunique()} | {g.births.sum():,.0f} | {o.get('<15', 0):,.0f} / {o.get('50+', 0):,.0f} / {o.get('inconnu', 0):,.0f} | "
                     f"{g.women.sum():,.0f} | {1000 * g.births.sum() / g.women.sum():.1f} | {g.marriages.sum():,.0f} |")
    (TABLES / "t_outcomes_br.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("\n".join(lines[-26:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
