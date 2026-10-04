#!/usr/bin/env python
"""Étape 2e — first stage (H4, France) : la couverture 4G se traduit-elle en adoption du smartphone et en usage
des réseaux sociaux ? Baromètre du numérique (microdonnées 2007-2025) × exposition D3 agrégée par zone.

Niveau : ZEAT (9 zones d'études et d'aménagement du territoire, disponibles 2007-2020) × année × classe d'âge,
puis région (13, disponibles 2020-2025). Régression individuelle pondérée (POND) : y = β·D3 + effets fixes zone,
année, classe d'âge ; erreurs groupées par zone (9 ou 13 groupes : inférence fragile, dite telle quelle).
Interaction D3 × (moins de 40 ans) pour la prédiction « davantage chez les moins de 40 ans ».

Sorties : tables/t_firststage_fr.md|csv ; tables/t_barometre_age_year.csv (parts par classe d'âge × année,
descriptif) ; data/processed/fr_firststage_panel.parquet.
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import did  # noqa: E402
from common.download import raw_files  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "tables"

# ZEAT (INSEE) : composition par anciennes régions → départements. Libellés = modalités du Baromètre.
ZEAT_DEPS = {
    "Région parisienne": ["75", "77", "78", "91", "92", "93", "94", "95"],
    "Bassin parisien Est": ["08", "10", "51", "52", "02", "60", "80", "21", "58", "71", "89"],
    "Bassin parisien Ouest": ["27", "76", "14", "50", "61", "18", "28", "36", "37", "41", "45"],
    "Nord": ["59", "62"],
    "Est": ["54", "55", "57", "88", "67", "68", "25", "39", "70", "90"],
    "Ouest": ["44", "49", "53", "72", "85", "22", "29", "35", "56", "16", "17", "79", "86"],
    "Sud-Ouest": ["24", "33", "40", "47", "64", "09", "12", "31", "32", "46", "65", "81", "82", "19", "23", "87"],
    "Centre Est": ["01", "07", "26", "38", "42", "69", "73", "74", "03", "15", "43", "63"],
    "Méditerranée": ["11", "30", "34", "48", "66", "04", "05", "06", "13", "83", "84", "2A", "2B"],
}
# Régions 2016 (code COG → libellé du Baromètre)
REGION_LABELS = {"11": "Ile de France", "24": "Centre Val de Loire", "27": "Bourgogne Franche Comté", "28": "Normandie",
                 "32": "Hauts de France", "44": "Grand Est", "52": "Pays de la Loire", "53": "Bretagne",
                 "75": "Nouvelle Aquitaine", "76": "Occitanie", "84": "Auvergne - Rhône Alpes", "93": "PACA", "94": "Corse"}


def load_barometre() -> pd.DataFrame:
    p = next(f for f in raw_files("fr_barometre_numerique") if f.suffix == ".csv")
    cols = ["ANNEE", "POND", "AGE6FUZ", "ZEAT", "REGION", "AGGLO5", "SMARTPHO", "US_FACEB", "SEXE", "DIPL5"]
    df = pd.read_csv(p, usecols=cols, dtype=str, keep_default_na=False)
    df["year"] = df.ANNEE.astype(int)
    df["w"] = pd.to_numeric(df.POND, errors="coerce")
    df["smartphone"] = df.SMARTPHO.map({"Oui": 1.0, "Non": 0.0})
    df["social"] = df.US_FACEB.map({"Oui": 1.0, "Non": 0.0})
    df["age"] = df.AGE6FUZ
    df["under40"] = df.AGE6FUZ.isin(["12-17 ans", "18-24 ans", "25-39 ans"]).astype(int)
    df["female"] = (df.SEXE == "Femme").astype(int)
    return df


def zone_d3(dep_treat: pd.DataFrame, mapping: dict[str, list[str]]) -> pd.DataFrame:
    rows = []
    for zone, deps in mapping.items():
        sub = dep_treat[dep_treat.dep.isin(deps)]
        g = sub.groupby("year").agg(w=("w", "sum"), wd=("wd", "sum"), n=("dep", "nunique")).reset_index()
        g["zone"] = zone
        g["d3"] = g.wd / g.w
        rows.append(g)
    return pd.concat(rows, ignore_index=True)


def fit(df: pd.DataFrame, y: str, label: str) -> list[dict]:
    import pyfixest as pf
    d = df.dropna(subset=[y, "d3", "w"]).copy()
    out = []
    m = pf.feols(f"{y} ~ d3 | zone + year + age", data=d, weights="w", vcov={"CRV1": "zone"})
    t = m.tidy().reset_index()
    r = t[t.Coefficient == "d3"].iloc[0]
    # p du wild cluster bootstrap (Webb, 9 999 tirages ; 9 ou 13 grappes) sur le modèle non pondéré : pyfixest refuse le
    # bootstrap sauvage avec pondération (A2.5) ; le modèle non pondéré est aussi rapporté
    d["zone_id"] = pd.factorize(d.zone)[0]                      # codes entiers : exigés par wildboottest
    mu = pf.feols(f"{y} ~ d3 | zone + year + age", data=d, vcov={"CRV1": "zone_id"})
    p_wild = did.wild_p(mu, "d3", reps=9999)
    out.append({"échantillon": label, "résultat": y, "terme": "D3", "coef": r.Estimate, "se": r["Std. Error"],
                "p": r["Pr(>|t|)"], "p_wild": p_wild, "coef non pondéré": float(mu.coef().loc["d3"]), "n": int(m._N),
                "zones": d.zone.nunique(), "années": f"{d.year.min()}-{d.year.max()}", "moyenne y": float(np.average(d[y], weights=d.w))})
    d["d3_u40"] = d.d3 * d.under40
    m2 = pf.feols(f"{y} ~ d3 + d3_u40 | zone + year + age", data=d, weights="w", vcov={"CRV1": "zone"})
    m2u = pf.feols(f"{y} ~ d3 + d3_u40 | zone + year + age", data=d, vcov={"CRV1": "zone_id"})
    t2 = m2.tidy().reset_index()
    for term, lab in (("d3", "D3 (40 ans et plus)"), ("d3_u40", "D3 × moins de 40 ans")):
        r = t2[t2.Coefficient == term].iloc[0]
        out.append({"échantillon": label, "résultat": y, "terme": lab, "coef": r.Estimate, "se": r["Std. Error"],
                    "p": r["Pr(>|t|)"], "p_wild": did.wild_p(m2u, term, reps=9999), "coef non pondéré": float(m2u.coef().loc[term]),
                    "n": int(m2._N), "zones": d.zone.nunique(), "années": f"{d.year.min()}-{d.year.max()}",
                    "moyenne y": float(np.average(d[y], weights=d.w))})
    return out


def main() -> int:
    TABLES.mkdir(parents=True, exist_ok=True)
    bar = load_barometre()
    dep = pd.read_parquet(PROC / "fr_treatment_dep.parquet")

    # descriptif : parts pondérées par classe d'âge × année
    desc = []
    for y in ("smartphone", "social"):
        sub = bar.dropna(subset=[y, "w"])
        g = sub.groupby(["year", "age"]).apply(lambda x: np.average(x[y], weights=x.w), include_groups=False).rename("share").reset_index()
        g["variable"] = y
        g["n"] = sub.groupby(["year", "age"]).size().values
        desc.append(g)
    desc = pd.concat(desc, ignore_index=True)
    desc.to_csv(TABLES / "t_barometre_age_year.csv", index=False)

    # panels zone × année
    z1 = zone_d3(dep, ZEAT_DEPS).rename(columns={"zone": "ZEAT"})
    p1 = bar[(bar.ZEAT != "NA") & (bar.year >= 2011)].merge(z1[["ZEAT", "year", "d3"]], on=["ZEAT", "year"], how="inner").rename(columns={"ZEAT": "zone"})
    reg_map = {lab: [] for lab in REGION_LABELS.values()}
    cog = zipfile.ZipFile(next(iter(raw_files("fr_insee_cog"))))
    vdep = pd.read_csv(cog.open(next(n for n in cog.namelist() if re.match(r"v_departement_\d{4}\.csv$", n))), dtype=str)
    for _, r in vdep.iterrows():
        if r.REG in REGION_LABELS:
            reg_map[REGION_LABELS[r.REG]].append(r.DEP)
    z2 = zone_d3(dep, reg_map).rename(columns={"zone": "REGION"})
    p2 = bar[(bar.REGION != "NA")].merge(z2[["REGION", "year", "d3"]], on=["REGION", "year"], how="inner").rename(columns={"REGION": "zone"})
    pd.concat([p1.assign(panel="ZEAT"), p2.assign(panel="REGION")], ignore_index=True).to_parquet(PROC / "fr_firststage_panel.parquet", index=False)

    rows = []
    rows += fit(p1, "smartphone", "ZEAT × année, 2011-2020")
    rows += fit(p1, "social", "ZEAT × année, 2011-2020")
    rows += fit(p2, "smartphone", "Région × année, 2020-2025")
    if p2.social.notna().sum() > 100:
        rows += fit(p2, "social", "Région × année, 2020-2022")
    res = pd.DataFrame(rows)
    res.to_csv(TABLES / "t_firststage_fr.csv", index=False)
    d3_range = z1.groupby("year").d3.agg(["min", "max"]).round(2)
    md = ["# First stage France (H4) — généré par scripts/04b_firststage.py", "",
          "Baromètre du numérique (ARCEP/CGE/ANCT/Arcom, CREDOC) : individus ≥ 12 ans, pondérés (POND). D3 = part des femmes de 15-44 ans "
          "(RP 2011) de la zone résidant dans une commune avec ≥ 1 émetteur LTE en service au 1er janvier (02_treatment.py), "
          "agrégée des départements à la zone. Effets fixes zone, année, classe d'âge (6 classes). Erreurs groupées par zone "
          "(9 ZEAT ou 13 régions : peu de groupes, inférence indicative).", "",
          "Étendue de D3 entre ZEAT par année (min-max) : " + "; ".join(f"{y}: {r['min']:.2f}-{r['max']:.2f}" for y, r in d3_range.iterrows()), "",
          res.to_markdown(index=False, floatfmt=".3f"), "",
          "Lecture : un coefficient de 0,10 sur D3 signifie que passer de 0 à 100 % de couverture 4G de la zone est associé à "
          "+10 points de la probabilité de posséder un smartphone (resp. d'avoir participé à des réseaux sociaux dans l'année), "
          "à année, zone et classe d'âge donnés. Corrélation conditionnelle ; la variation de D3 entre ZEAT est faible après 2016."]
    (TABLES / "t_firststage_fr.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
