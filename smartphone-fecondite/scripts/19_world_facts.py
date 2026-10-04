#!/usr/bin/env python
"""Faits stylisés (mission, méthode 1 ; section descriptive du papier, sans inférence causale) à partir du panel mondial et européen :

- fig_world_tfr_income.pdf   : indice synthétique de fécondité par groupe de revenu de la Banque mondiale, 1990-2024, et abonnements
                               mobiles / usage d'Internet pour 100 habitants (WB SP.DYN.TFRT.IN, IT.CEL.SETS.P2, IT.NET.USER.ZS)
- fig_world_asfr.pdf          : taux de fécondité par âge (UN WPP 2024) dans les quatre pays d'étude, 1995-2023
- tables/t_world_inflection.md|csv : année du maximum local de l'ISF sur 2000-2015 et baisse jusqu'en 2023 pour les pays à revenu élevé
                               (WB) — datation descriptive des points d'inflexion
- fig_eu_mobile_internet.pdf  : part des individus utilisant un téléphone mobile pour accéder à Internet (Eurostat isoc_ci_im_i, I_IUMP),
                               France, Espagne, UE, 2012-2019 ; et taux de fécondité 25-29 / 30-34 (Eurostat demo_frate)

Aucune valeur n'est saisie à la main ; chaque série vient d'un fichier consigné dans docs/data_log.md.
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common.download import raw_files  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "tables"
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("f6", Path(__file__).resolve().parent / "06_figures.py")
f6 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(f6)
plt = f6.plt
STUDY = {"FRA": "France", "COL": "Colombie", "BRA": "Brésil", "ESP": "Espagne"}
# agrégats par groupe de revenu : code ISO3 vide dans la réponse de l'API, identifiés par leur nom
INCOME = {"High income": "Revenu élevé", "Upper middle income": "Revenu intermédiaire supérieur", "Lower middle income": "Revenu intermédiaire inférieur", "Low income": "Revenu faible"}
COLORS4 = [f6.COLORS["cs"], f6.COLORS["sunab"], f6.COLORS["did2s"], f6.COLORS["twfe"]]


def wb(src: str) -> pd.DataFrame:
    d = json.loads(Path(next(iter(raw_files(src)))).read_text(encoding="utf-8"))[1]
    t = pd.DataFrame([{"iso3": r["countryiso3code"], "name": r["country"]["value"], "year": int(r["date"]), "value": r["value"]} for r in d])
    t["value"] = pd.to_numeric(t.value, errors="coerce")
    return t.dropna(subset=["value"])


def eurostat(src: str) -> pd.DataFrame:
    p = next(iter(raw_files(src)))
    with gzip.open(p, "rt", encoding="utf-8") as f:
        d = pd.read_csv(f, sep="\t")
    key = d.columns[0]
    dims = key.split("\\")[0].split(",")
    keys = d[key].str.split(",", expand=True)
    keys.columns = dims
    vals = d.drop(columns=[key])
    vals.columns = [c.strip() for c in vals.columns]
    out = pd.concat([keys, vals], axis=1).melt(id_vars=dims, var_name="year", value_name="raw")
    out["value"] = pd.to_numeric(out.raw.astype(str).str.replace(r"[a-z: ]", "", regex=True), errors="coerce")
    out["year"] = pd.to_numeric(out.year, errors="coerce")
    return out.dropna(subset=["value", "year"])


def fig_tfr_income() -> None:
    tfr, mob, net = wb("wb_tfr"), wb("wb_mobile"), wb("wb_internet")
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.2))
    for ax, (d, title, ylab) in zip(axes, ((tfr, "Indice synthétique de fécondité", "enfants par femme"), (mob, "Abonnements mobiles", "pour 100 habitants"),
                                           (net, "Individus utilisant Internet", "% de la population"))):
        items = []
        for (code, lab), col in zip(INCOME.items(), COLORS4):
            s = d[(d.name == code) & d.year.between(1990, 2024)].sort_values("year")
            if s.empty:
                continue
            ax.plot(s.year, s.value, color=col, lw=1.8)
            items.append((s.year.iloc[-1], s.value.iloc[-1], lab, col))
        ax.set_xlim(1990, 2033)
        f6.label_ends(ax, items)
        ax.set_title(title, loc="left", fontsize=9)
        ax.set_ylabel(ylab)
        f6.int_ticks(ax, 4)
    fig.suptitle("Groupes de revenu de la Banque mondiale, 1990-2024 (agrégats WB ; descriptif)", fontsize=9, x=0.01, ha="left")
    fig.tight_layout()
    f6.save(fig, "fig_world_tfr_income.pdf")


def fig_asfr() -> None:
    p = next(iter(raw_files("un_wpp_asfr")))
    d = pd.read_csv(p, compression="gzip", encoding="latin-1", usecols=["ISO3_code", "Variant", "Time", "AgeGrp", "ASFR"])
    d = d[(d.Variant == "Medium") & d.ISO3_code.isin(STUDY) & d.Time.between(1995, 2023)]
    groups = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44"]
    cols = [f6.COLORS["cs"], f6.COLORS["sunab"], f6.COLORS["did2s"], f6.COLORS["twfe"], "#8e6bd9", "#b5566e"]
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.0), sharey=True)
    for ax, (iso, name) in zip(axes, STUDY.items()):
        items = []
        for g, col in zip(groups, cols):
            s = d[(d.ISO3_code == iso) & (d.AgeGrp == g)].sort_values("Time")
            ax.plot(s.Time, s.ASFR, color=col, lw=1.6)
            items.append((s.Time.iloc[-1], s.ASFR.iloc[-1], g, col))
        ax.set_xlim(1995, 2031)
        f6.label_ends(ax, items)
        ax.set_title(name, loc="left", fontsize=9)
        f6.int_ticks(ax, 5)
    axes[0].set_ylabel("naissances pour 1 000 femmes")
    fig.suptitle("Taux de fécondité par âge, 1995-2023 (UN WPP 2024, estimations ; descriptif)", fontsize=9, x=0.01, ha="left")
    fig.tight_layout()
    f6.save(fig, "fig_world_asfr.pdf")


def table_inflection() -> None:
    """ISF par pays (UN WPP 2024, estimations, LocTypeName = Country/Area, TFR = 5 × Σ ASFR / 1 000) : année du maximum local sur
    2000-2015 et variation jusqu'en 2023, pour les pays dont l'ISF 2000 est inférieur à 2,5."""
    p = next(iter(raw_files("un_wpp_asfr")))
    d = pd.read_csv(p, compression="gzip", encoding="latin-1", usecols=["ISO3_code", "Location", "LocTypeName", "Variant", "Time", "ASFR"])
    d = d[(d.Variant == "Medium") & (d.LocTypeName == "Country/Area") & d.Time.between(2000, 2023) & d.ISO3_code.notna()]
    tfr = d.groupby(["ISO3_code", "Location", "Time"]).ASFR.sum().mul(5 / 1000).rename("tfr").reset_index()
    rows = []
    for (iso, name), g in tfr.groupby(["ISO3_code", "Location"]):
        g = g.sort_values("Time")
        if len(g) < 24 or g[g.Time == 2000].tfr.iloc[0] >= 2.5:
            continue
        win = g[g.Time.between(2000, 2015)]
        peak = win.loc[win.tfr.idxmax()]
        last = g.iloc[-1]
        rows.append({"iso3": iso, "pays": name, "ISF 2000": g[g.Time == 2000].tfr.iloc[0], "année du maximum 2000-2015": int(peak.Time),
                     "ISF au maximum": peak.tfr, "ISF 2023": last.tfr, "baisse depuis le maximum (%)": 100 * (last.tfr / peak.tfr - 1)})
    t = pd.DataFrame(rows).sort_values(["année du maximum 2000-2015", "pays"])
    t.to_csv(TABLES / "t_world_inflection.csv", index=False)
    dist = t["année du maximum 2000-2015"].value_counts().sort_index()
    lines = ["# Datation descriptive des points d'inflexion de l'ISF (généré par scripts/19_world_facts.py)", "",
             "Pays (UN WPP 2024, estimations ; ISF = 5 × somme des taux par âge / 1 000) dont l'ISF 2000 est inférieur à 2,5 : année du maximum local sur "
             "2000-2015 et variation jusqu'en 2023. Un maximum en 2000 signifie une baisse continue depuis la borne de la fenêtre. Aucune inférence causale.", "",
             f"Nombre de pays : {len(t)} ; distribution de l'année du maximum : " + ", ".join(f"{y} : {n}" for y, n in dist.items()) +
             f" ; maximum entre 2008 et 2015 : {int(dist[(dist.index >= 2008) & (dist.index <= 2015)].sum())} pays ({100 * dist[(dist.index >= 2008) & (dist.index <= 2015)].sum() / len(t):.0f} %) ; "
             f"baisse médiane depuis le maximum : {t['baisse depuis le maximum (%)'].median():+.0f} %.", "",
             "| pays | ISF 2000 | année du maximum | ISF au maximum | ISF 2023 | baisse depuis le maximum |", "|---|---|---|---|---|---|"]
    for _, r in t.iterrows():
        lines.append(f"| {r.pays} | {r['ISF 2000']:.2f} | {r['année du maximum 2000-2015']} | {r['ISF au maximum']:.2f} | {r['ISF 2023']:.2f} | {r['baisse depuis le maximum (%)']:+.0f} % |")
    (TABLES / "t_world_inflection.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:5]))


def fig_eu() -> None:
    im = eurostat("eu_isoc_ci_im_i")
    im = im[(im.indic_is == "I_IUMP") & (im.unit == "PC_IND") & (im.ind_type == "IND_TOTAL") & im.geo.isin(["FR", "ES", "EU27_2020", "EU28"])]
    fr = eurostat("eu_demo_frate")
    fr = fr[(fr.unit == "NR") & (fr.agedef == "COMPLET") & fr.geo.isin(["FR", "ES"]) & fr.age.isin(["Y25-29", "Y30-34", "Y15-19"]) & fr.year.between(2005, 2023)]
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.2))
    fig.subplots_adjust(wspace=0.3)
    ax = axes[0]
    items = []
    for geo, lab, col in (("FR", "France", f6.COLORS["cs"]), ("ES", "Espagne", f6.COLORS["sunab"]), ("EU27_2020", "UE-27", f6.COLORS["twfe"]), ("EU28", "UE-28", f6.COLORS["twfe"])):
        s = im[im.geo == geo].sort_values("year")
        if s.empty:
            continue
        ax.plot(s.year, s.value, color=col, lw=1.8, marker="o", ms=3)
        items.append((s.year.iloc[-1], s.value.iloc[-1], lab, col))
    if items:
        ax.set_xlim(2011, 2021.5)
        f6.label_ends(ax, items)
    ax.set_title("Internet depuis un téléphone mobile (% des individus)", loc="left", fontsize=9)
    f6.int_ticks(ax, 6)
    ax = axes[1]
    items = []
    for geo, lab, col in (("FR", "France", f6.COLORS["cs"]), ("ES", "Espagne", f6.COLORS["sunab"])):
        for age, ls in (("Y25-29", "-"), ("Y30-34", "--"), ("Y15-19", ":")):
            s = fr[(fr.geo == geo) & (fr.age == age)].sort_values("year")
            if s.empty:
                continue
            ax.plot(s.year, s.value, color=col, lw=1.6, ls=ls)
            items.append((s.year.iloc[-1], s.value.iloc[-1], f"{lab} {age[1:]}", col))
    ax.set_xlim(2005, 2027)
    f6.label_ends(ax, items)
    ax.set_title("Taux de fécondité par âge (naissances par femme)", loc="left", fontsize=9)
    f6.int_ticks(ax, 6)
    fig.tight_layout()
    f6.save(fig, "fig_eu_mobile_internet.pdf")


def main() -> int:
    fig_tfr_income()
    fig_asfr()
    table_inflection()
    fig_eu()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
