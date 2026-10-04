#!/usr/bin/env python
"""Étape 2c — construction des résultats (France) à partir des fichiers bruts consignés.

Sorties (data/processed/) :
- ``fr_outcomes_commune.parquet`` : unité harmonisée × année 2008-2025 : naissances domiciliées, décès,
  population municipale (interpolée entre millésimes), femmes 15-44 (RP, millésimes interpolés), part des
  femmes 15-24 / 25-39 en couple (RP, millésimes) ;
- ``fr_outcomes_dep_age.parquet`` : département × groupe d'âge × année 1998-2024 : naissances (total, de
  parents mariés, rang 1 jusqu'en 2012), femmes au 1er janvier, mariages de femmes par âge, femmes en couple
  (millésimes RP) ; taux pour 1 000 ;
- ``fr_outcomes_dep.parquet`` : département × année : mariages domiciliés, PACS (2007-2016), femmes 15-49 ;
- ``tables/t_outcomes_fr.md`` : couverture par source et par année, contrôles de cohérence.

Décisions de mesure (liste fermée §10) consignées dans ``docs/preregistration_addenda.md`` :
- âge de la mère = ``agemere`` (âge atteint dans l'année ; censuré à 17 et 46 dans les fichiers détail) ;
- âge de l'épouse = année du mariage − année de naissance ; à partir de 2013, « femme » = conjoint de sexe F
  (les mariages de deux femmes comptent deux femmes) ;
- département de domicile : ``depdom`` ; les codes « 97 » (DOM agrégés avant 2014) et « 99 » (étranger) sont
  conservés dans des lignes à part et exclus du panel métropolitain ;
- dénominateurs : population féminine au 1er janvier par département et âge quinquennal (Melodi) ;
  40-49 = somme de 40-44 et 45-49.
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common.download import raw_files  # noqa: E402
from common.etatcivil import read_detail, year_of, age_group, AGE_GROUPS  # noqa: E402
from common.geo import Cog  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "tables"
GROUPS = [g[2] for g in AGE_GROUPS]
METRO_DEPS = {f"{i:02d}" for i in range(1, 96) if i != 20} | {"2A", "2B"}
notes: list[str] = []


def log(msg: str) -> None:
    print(msg)
    notes.append(msg)


def _one(src_id: str, pattern: str = ".") -> Path:
    files = [p for p in raw_files(src_id) if re.search(pattern, p.name)]
    if not files:
        raise FileNotFoundError(f"{src_id} : aucun fichier brut consigné (lancer 01_download.py)")
    return files[0]


def _melodi_csv(src_id: str) -> pd.DataFrame:
    z = zipfile.ZipFile(_one(src_id))
    name = next(n for n in z.namelist() if n.endswith("_data.csv"))
    return pd.read_csv(z.open(name), sep=";", dtype=str)


def norm_dep(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.upper()
    return s.where(~s.str.fullmatch(r"\d"), "0" + s)


# ----------------------------------------------------------------------------- naissances par département × âge

def births_dep_age() -> pd.DataFrame:
    files = [p for sid in ("fr_insee_naissances_detail_1998_2013", "fr_insee_naissances_detail_2014_2021",
                           "fr_insee_naissances_detail_2022_2024") for p in raw_files(sid)]
    out = []
    for p in sorted(files, key=year_of):
        y = year_of(p)
        df = read_detail(p, "nais", usecols=["agemere", "depdom", "depdomm", "amar", "nbenfpre", "anais"])
        if "anais" in df and (df.anais != str(y)).mean() > 0.01:
            log(f"  naissances {y} : {(df.anais != str(y)).mean():.1%} des lignes d'une autre année (anais)")
        if "depdom" not in df and "depdomm" in df:          # format réduit (2024) : depdomm
            df["depdom"] = df["depdomm"]
        df["dep"] = norm_dep(df.depdom)
        df["age_group"] = age_group(df.agemere)
        df["married"] = (~df.amar.isin(["", "0000", "9999"])).astype(float) if "amar" in df else np.nan
        df["rank1"] = (df.nbenfpre == "0").astype(float) if "nbenfpre" in df else np.nan
        g = df.groupby(["dep", "age_group"], dropna=False).agg(births=("dep", "size"), births_married=("married", "sum"),
                                                                 births_rank1=("rank1", "sum")).reset_index()
        g["year"] = y
        g["rank_available"] = "nbenfpre" in df
        g["married_available"] = "amar" in df
        if "amar" not in df:
            g["births_married"] = np.nan
        if "nbenfpre" not in df:
            g["births_rank1"] = np.nan
        out.append(g)
        log(f"  naissances {y} : {len(df):,} lignes, {df.dep.nunique()} codes département, "
            f"âge manquant {df.age_group.isna().mean():.2%}")
    return pd.concat(out, ignore_index=True)


# ----------------------------------------------------------------------------- mariages par département × âge de l'épouse

def marriages_dep_age() -> pd.DataFrame:
    files = [p for sid in ("fr_insee_mariages_detail_1998_2013", "fr_insee_mariages_detail_2014_2021",
                           "fr_insee_mariages_detail_2022_2024") for p in raw_files(sid)]
    out = []
    for p in sorted(files, key=year_of):
        y = year_of(p)
        df = read_detail(p, "mar")
        cols = set(df.columns)
        if {"sexe1", "anais1", "sexe2", "anais2"} <= cols:
            w1 = df.loc[df.sexe1.str.upper() == "F", ["depdom", "anais1"]].rename(columns={"anais1": "anaisf"})
            w2 = df.loc[df.sexe2.str.upper() == "F", ["depdom", "anais2"]].rename(columns={"anais2": "anaisf"})
            women = pd.concat([w1, w2], ignore_index=True)
            mode = "sexe1/sexe2"
        elif "anaisf" in cols:
            women = df[["depdom", "anaisf"]].copy()
            mode = "anaisf"
        else:
            raise KeyError(f"mariages {y} : colonnes d'âge introuvables ({sorted(cols)})")
        women["age"] = y - pd.to_numeric(women.anaisf, errors="coerce")
        women["dep"] = norm_dep(women.depdom)
        women["age_group"] = age_group(women.age)
        g = women.groupby(["dep", "age_group"], dropna=False).size().rename("marriages_f").reset_index()
        g["year"] = y
        out.append(g)
        log(f"  mariages {y} : {len(df):,} mariages, {len(women):,} épouses ({mode}), âge manquant {women.age_group.isna().mean():.2%}")
    return pd.concat(out, ignore_index=True)


# ----------------------------------------------------------------------------- dénominateurs département × âge

def women_dep_age() -> pd.DataFrame:
    d = _melodi_csv("fr_insee_estim_pop")
    d = d[(d.EP_MEASURE == "POP_JAN_1ST") & (d.SEX == "F") & (d.GEO_OBJECT.isin(["DEP"]) if "GEO_OBJECT" in d else True)]
    d = d[d.GEO.str.len() <= 3]
    amap = {"Y15T19": "15-19", "Y20T24": "20-24", "Y25T29": "25-29", "Y30T34": "30-34", "Y35T39": "35-39",
            "Y40T44": "40-49", "Y45T49": "40-49"}
    d = d[d.AGE.isin(amap)].copy()
    d["age_group"] = d.AGE.map(amap)
    d["dep"] = norm_dep(d.GEO)
    d["year"] = d.TIME_PERIOD.astype(int)
    d["women"] = pd.to_numeric(d.OBS_VALUE, errors="coerce")
    g = d.groupby(["dep", "age_group", "year"]).women.sum().reset_index()
    log(f"Femmes par département × âge (Melodi) : {g.dep.nunique()} départements, {g.year.min()}-{g.year.max()}")
    return g


# ----------------------------------------------------------------------------- mariages / PACS départementaux (séries)

def dep_series() -> pd.DataFrame:
    d = _melodi_csv("fr_insee_mar_pacs_series")
    d = d[(d.FREQ == "A") & (d.GEO_OBJECT == "DEP")]
    d["dep"] = norm_dep(d.GEO)
    d["year"] = d.TIME_PERIOD.str[:4].astype(int)
    d["v"] = pd.to_numeric(d.OBS_VALUE, errors="coerce")
    mar = d[(d.EC_MEASURE == "MAR_DOM") & (d.MARSTA == "MAR")].groupby(["dep", "year"]).v.sum().rename("marriages_dom")
    pacs = d[d.EC_MEASURE == "PACS"].groupby(["dep", "year"]).v.sum().rename("pacs")
    out = pd.concat([mar, pacs], axis=1).reset_index()
    log(f"Séries départementales : mariages domiciliés {out.dropna(subset=['marriages_dom']).year.min()}-"
        f"{out.dropna(subset=['marriages_dom']).year.max()}, PACS {out.dropna(subset=['pacs']).year.min()}-{out.dropna(subset=['pacs']).year.max()}")
    return out


# ----------------------------------------------------------------------------- RP : femmes en couple par âge (commune)

def _sheet_to_df(sheet: pd.DataFrame) -> pd.DataFrame:
    hdr = next(i for i in range(min(12, len(sheet))) if str(sheet.iloc[i, 0]).strip().upper() == "CODGEO")
    df = sheet.iloc[hdr + 1:].copy()
    df.columns = [str(c).upper() for c in sheet.iloc[hdr]]
    return df.reset_index(drop=True)


def _read_rp_zip(p: Path) -> pd.DataFrame:
    """Base RP communale (csv dans un zip, ou xls avec une feuille COM_<millésime> par millésime).

    Les feuilles COM_* d'un xls (ex. COM_2011 et COM_2006) sont empilées : chaque millésime a ses propres
    colonnes (P06_…, P11_…) et sa propre géographie, harmonisée ensuite par le COG."""
    if p.suffix.lower() == ".xls":
        x = pd.read_excel(p, sheet_name=None, header=None, dtype=str)
    else:
        z = zipfile.ZipFile(p)
        name = next(n for n in z.namelist() if re.search(r"\.(csv|xls|xlsx)$", n, re.I) and not re.search(r"meta|doc", n, re.I))
        if name.lower().endswith(".csv"):
            df = pd.read_csv(z.open(name), sep=";", dtype=str, encoding="utf-8", encoding_errors="replace")
            df.columns = [c.upper() for c in df.columns]
            return df
        x = pd.read_excel(z.open(name), sheet_name=None, header=None, dtype=str)
    parts = [_sheet_to_df(v) for k, v in x.items() if k.upper().startswith("COM")]
    if not parts:
        parts = [_sheet_to_df(next(v for v in x.values() if v.shape[0] > 30000))]
    return pd.concat(parts, ignore_index=True, sort=False)


def couples_rp(cog: Cog) -> pd.DataFrame:
    """Personnes vivant en couple par groupe d'âge RP (15-19, 20-24, 25-39, 40-54), deux sexes confondus, par unité
    harmonisée et millésime. Les bases communales Couples-Familles-Ménages ne ventilent pas la vie en couple par sexe
    (variables P<yy>_POP<grp>_COUPLE et P<yy>_POP<grp>) : décision de mesure consignée dans preregistration_addenda.md."""
    out = []
    groups = ("1519", "2024", "2539", "4054")
    for p in raw_files("fr_insee_rp_cfm"):
        df = _read_rp_zip(p)
        cols = [c for c in df.columns if re.fullmatch(r"P\d{2}_POP(1519|2024|2539|4054)_COUPLE", c)]
        if not cols:
            log(f"  RP CFM {p.name} : aucune colonne de couple reconnue ({list(df.columns)[:12]})")
            continue
        df["unit"] = cog.harmonize(df.CODGEO)
        for yy in sorted({c[1:3] for c in cols}):
            year = 2000 + int(yy) if int(yy) < 50 else 1900 + int(yy)
            rec = {"unit": df.unit}
            for grp in groups:
                tot, cpl = f"P{yy}_POP{grp}", f"P{yy}_POP{grp}_COUPLE"
                if tot in df and cpl in df:
                    rec[f"p{grp}"] = pd.to_numeric(df[tot], errors="coerce")
                    rec[f"p{grp}_couple"] = pd.to_numeric(df[cpl], errors="coerce")
            if len(rec) == 1:
                continue
            g = pd.DataFrame(rec).groupby("unit").sum(min_count=1).reset_index()
            g["rp_year"] = year
            g["source_file"] = p.name
            out.append(g)
            log(f"  RP CFM {p.name} → millésime {year} : {len(g):,} unités, colonnes {[c for c in rec if c != 'unit']}")
    if not out:
        return pd.DataFrame(columns=["unit", "rp_year"])
    res = pd.concat(out, ignore_index=True)
    return res.sort_values(["unit", "rp_year", "source_file"]).drop_duplicates(["unit", "rp_year"], keep="last")


def women_rp(cog: Cog) -> pd.DataFrame:
    """Femmes 15-29, 30-44 (RP) par unité et millésime (dénominateur communal)."""
    out = []
    for p in raw_files("fr_insee_rp_pop_struct"):
        df = _read_rp_zip(p)
        cols = [c for c in df.columns if re.fullmatch(r"P\d{2}_F(1529|3044|4559)", c)]
        if not cols:
            log(f"  RP pop {p.name} : colonnes F1529/F3044 absentes ({list(df.columns)[:12]})")
            continue
        df["unit"] = cog.harmonize(df.CODGEO)
        for yy in sorted({c[1:3] for c in cols}):
            year = 2000 + int(yy)
            c1, c2, cp = f"P{yy}_F1529", f"P{yy}_F3044", f"P{yy}_POP"
            if c1 not in df or c2 not in df:
                continue
            g = pd.DataFrame({"unit": df.unit, "f1529": pd.to_numeric(df[c1], errors="coerce"),
                              "f3044": pd.to_numeric(df[c2], errors="coerce"),
                              "pop": pd.to_numeric(df[cp], errors="coerce") if cp in df else np.nan})
            g = g.groupby("unit").sum(min_count=1).reset_index()
            g["rp_year"] = year
            g["source_file"] = p.name
            out.append(g)
            log(f"  RP pop {p.name} → millésime {year} : {len(g):,} unités")
    res = pd.concat(out, ignore_index=True)
    return res.sort_values(["unit", "rp_year", "source_file"]).drop_duplicates(["unit", "rp_year"], keep="last")


def interpolate_years(df: pd.DataFrame, value_cols: list[str], years: list[int]) -> pd.DataFrame:
    """Interpolation linéaire entre millésimes par unité ; pas d'extrapolation au-delà de 2 ans (§4.2)."""
    wide = df.pivot(index="unit", columns="rp_year", values=value_cols)
    out = {}
    for c in value_cols:
        # grille d'années contiguë avant d'interpoler : DataFrame.interpolate(method="linear") traite les colonnes comme
        # équidistantes, et sans l'année 2007 le segment 2006 → 2011 était interpolé en positions, pas en années (A2.5)
        full = list(range(min(set(wide[c].columns) | set(years)), max(set(wide[c].columns) | set(years)) + 1))
        w = wide[c].reindex(columns=full)
        w = w.interpolate(axis=1, limit_area="inside")
        w = w.ffill(axis=1, limit=2).bfill(axis=1, limit=2)
        out[c] = w[years].stack(future_stack=True)
    res = pd.DataFrame(out).reset_index().rename(columns={"level_1": "year", "rp_year": "year"})
    return res


# ----------------------------------------------------------------------------- assemblage

def main() -> int:
    PROC.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    cog = Cog(_one("fr_insee_cog"))

    # --- commune × année
    nais = _melodi_csv("fr_insee_naissances_communes")
    nais = nais[nais.GEO_OBJECT == "COM"]
    nais["unit"] = cog.harmonize(nais.GEO)
    nais["year"] = nais.TIME_PERIOD.astype(int)
    nais["births"] = pd.to_numeric(nais.OBS_VALUE, errors="coerce")
    nais["births_status"] = nais.OBS_STATUS
    com = nais.groupby(["unit", "year"]).agg(births=("births", "sum"), n_status_non_a=("births_status", lambda s: (s != "A").sum())).reset_index()
    log(f"Naissances communales (Melodi) : {nais.GEO.nunique():,} communes → {com.unit.nunique():,} unités, {com.year.min()}-{com.year.max()}")
    dec = _melodi_csv("fr_insee_deces_communes")
    dec = dec[dec.GEO_OBJECT == "COM"]
    dec["unit"] = cog.harmonize(dec.GEO)
    dec["year"] = dec.TIME_PERIOD.astype(int)
    dec["deaths"] = pd.to_numeric(dec.OBS_VALUE, errors="coerce")
    com = com.merge(dec.groupby(["unit", "year"]).deaths.sum().reset_index(), on=["unit", "year"], how="left")
    years = sorted(com.year.unique())
    wrp = women_rp(cog)
    wi = interpolate_years(wrp, ["f1529", "f3044", "pop"], years)
    wi["women_1544"] = wi.f1529 + wi.f3044
    com = com.merge(wi[["unit", "year", "women_1544", "pop"]], on=["unit", "year"], how="left")
    cpl = couples_rp(cog)
    if len(cpl):
        cols = [c for c in cpl.columns if c.startswith("p")]
        ci = interpolate_years(cpl, cols, years)
        for grp in ("1519", "2024", "2539", "4054"):
            if f"p{grp}_couple" in ci and f"p{grp}" in ci:
                ci[f"share_couple_{grp}"] = ci[f"p{grp}_couple"] / ci[f"p{grp}"]
        if {"p1519_couple", "p2024_couple"} <= set(ci.columns):
            ci["share_couple_1524"] = (ci.p1519_couple + ci.p2024_couple) / (ci.p1519 + ci.p2024)
        com = com.merge(ci[["unit", "year"] + [c for c in ci.columns if c.startswith("share_couple")]], on=["unit", "year"], how="left")
    com["births_per_1000_f1544"] = 1000 * com.births / com.women_1544
    com["deaths_per_1000"] = 1000 * com.deaths / com["pop"]
    com["dep"] = cog.dep_of(com.unit)
    com["metro"] = cog.is_metro(com.unit)
    com.to_parquet(PROC / "fr_outcomes_commune.parquet", index=False)

    # --- département × âge × année
    b = births_dep_age()
    m = marriages_dep_age()
    w = women_dep_age()
    da = b.merge(m, on=["dep", "age_group", "year"], how="outer").merge(w, on=["dep", "age_group", "year"], how="left")
    da = da[da.age_group.notna()]
    # une cellule département × âge absente du fichier mariages d'une année lue est un zéro, pas une valeur manquante
    # (addendum A2) ; même règle pour les naissances d'une année lue
    years_m, years_b = set(m.year.unique()), set(b.year.unique())
    n0 = int((da.marriages_f.isna() & da.year.isin(years_m)).sum())
    da.loc[da.marriages_f.isna() & da.year.isin(years_m), "marriages_f"] = 0.0
    n0b = int((da.births.isna() & da.year.isin(years_b)).sum())
    da.loc[da.births.isna() & da.year.isin(years_b), "births"] = 0.0
    log(f"  cellules département × âge sans ligne de mariage codées 0 : {n0} ; sans ligne de naissance : {n0b}")
    da["metro"] = da.dep.isin(METRO_DEPS)          # 01-95 (sans 20), 2A, 2B ; « 97 », « 98 », « 99 » et DOM exclus
    da["births_per_1000"] = 1000 * da.births / da.women
    da["marriages_per_1000"] = 1000 * da.marriages_f / da.women
    da["share_births_married"] = da.births_married / da.births
    da["share_births_rank1"] = np.where(da.rank_available == True, da.births_rank1 / da.births, np.nan)  # noqa: E712
    # femmes en couple par âge au département (millésimes RP agrégés ; 15-24 et 25-39 seulement)
    if len(cpl):
        cpl["dep"] = cog.dep_of(cpl.unit)
        cd = cpl.groupby(["dep", "rp_year"])[[c for c in cpl.columns if c.startswith("p")]].sum(min_count=1).reset_index()
        cd = cd.rename(columns={"rp_year": "year"})
        da = da.merge(cd, on=["dep", "year"], how="left")
    da.to_parquet(PROC / "fr_outcomes_dep_age.parquet", index=False)

    # contrôle de cohérence : naissances des fichiers détail vs série officielle départementale (Melodi)
    try:
        off = _melodi_csv("fr_insee_naissances_fecondite_series")
        off = off[(off.FREQ == "A") & (off.GEO_OBJECT == "DEP")]
        meas = [c for c in off.columns if c.endswith("MEASURE")][0]
        nb = off[off[meas].str.contains("NAIS|LVB|BIRTH", regex=True, na=False) & (off.get("UNIT_MEASURE", "NR") == "NR")]
        nb = nb.assign(dep=norm_dep(nb.GEO), year=nb.TIME_PERIOD.str[:4].astype(int),
                       v=pd.to_numeric(nb.OBS_VALUE, errors="coerce")).groupby(["dep", "year"]).v.max().rename("births_official")
        chk = da.groupby(["dep", "year"]).births.sum().to_frame().join(nb, how="inner")
        chk["ratio"] = chk.births / chk.births_official
        chk.reset_index().to_parquet(PROC / "fr_check_births_vs_official.parquet", index=False)
        byy = chk.groupby("year").ratio.agg(["median", "min", "max"])
        log("Contrôle naissances fichiers détail / série officielle départementale (ratio médian, min, max par année) : " +
            "; ".join(f"{y}: {r['median']:.3f} [{r['min']:.3f}, {r['max']:.3f}]" for y, r in byy.iterrows()))
    except Exception as e:  # noqa: BLE001
        log(f"Contrôle vs série officielle non réalisé : {e}")

    ds = dep_series()
    w1549 = w.groupby(["dep", "year"]).women.sum().rename("women_1549").reset_index()
    ds = ds.merge(w1549, on=["dep", "year"], how="left")
    ds["marriages_per_1000_f1549"] = 1000 * ds.marriages_dom / ds.women_1549
    ds["pacs_per_1000_f1549"] = 1000 * ds.pacs / ds.women_1549
    ds.to_parquet(PROC / "fr_outcomes_dep.parquet", index=False)

    # --- synthèse
    met = da[da.metro]
    lines = ["# Résultats France — couverture (généré par scripts/03_outcomes.py)", "", "## Journal", ""] + [f"- {n}" for n in notes]
    lines += ["", "## Département × âge × année (France métropolitaine)", "",
              "| année | départements | naissances | mariages (épouses) | femmes 15-49 | naissances/1 000 f. 15-49 | part parents mariés | rang 1 dispo |",
              "|---|---|---|---|---|---|---|---|"]
    for y, g in met.groupby("year"):
        married = f"{g.births_married.sum() / g.births.sum():.1%}" if g.married_available.any() else "n. d."
        lines.append(f"| {y} | {g.dep.nunique()} | {g.births.sum():,.0f} | {g.marriages_f.sum():,.0f} | {g.women.sum():,.0f} | "
                     f"{1000 * g.births.sum() / g.women.sum():.1f} | {married} | "
                     f"{'oui' if g.rank_available.any() else 'non'} |")
    lines += ["", "## Taux de fécondité par âge pour 1 000 femmes (métropole, naissances/femmes au 1er janvier)", "",
              "| année | " + " | ".join(GROUPS) + " |", "|---|" + "---|" * len(GROUPS)]
    for y, g in met.groupby("year"):
        r = g.groupby("age_group").apply(lambda x: 1000 * x.births.sum() / x.women.sum(), include_groups=False)
        lines.append(f"| {y} | " + " | ".join(f"{r.get(a, float('nan')):.1f}" for a in GROUPS) + " |")
    cm = com[com.metro]
    lines += ["", "## Commune × année (métropole)", "",
              "| année | unités | naissances | femmes 15-44 (RP interp.) | unités sans dénominateur |", "|---|---|---|---|---|"]
    for y, g in cm.groupby("year"):
        lines.append(f"| {y} | {g.unit.nunique():,} | {g.births.sum():,.0f} | {g.women_1544.sum():,.0f} | {g.women_1544.isna().sum():,} |")
    (TABLES / "t_outcomes_fr.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[-45:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
