"""Espagne — lecteurs communs : couverture municipale (MINECO/SETELECO, xlsx), microdonnées INE des naissances et des mariages
(largeur fixe 2007-2015 d'après les dessins d'enregistrement, parquet 2016+), Padrón continuo (PC-Axis).

Conventions : code municipio INE à 5 chiffres (province 2 + municipio 3) ; dans les microdonnées le municipio n'est codé que pour les
municipios de plus de 10 000 habitants (sinon blanc) ; groupes d'âge de la préregistration.
"""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

AGE_GROUPS = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-49"]
# positions (début, fin ; 1-based, inclus) dans les fichiers à largeur fixe 2007-2015 : dessins « Diseñoanonimizadonacimientos_07_15.xls »
# et « Diseñoanonimizadomatrimonios_08_15.xls » (INE, lus le 04/10/2026 ; mêmes positions pour 2016+ en txt, mais on lit le parquet)
BIRTH_FIELDS_0715 = {"PROI": (1, 2), "MUNI": (3, 5), "ANOPAR": (8, 11), "PAISNXM": (42, 44), "PROREM": (45, 46), "MUNREM": (47, 49), "ECIVM": (57, 57),
                     "NUMHV": (75, 76), "TMUNRM": (133, 133), "EDADM": (144, 145), "NACVN": (173, 173), "CLASIF": (180, 180)}
MARRIAGE_FIELDS_0815 = {"ANOCM": (8, 11), "CPROMA": (13, 14), "CMUMA": (15, 17), "SEXOCA": (41, 41), "SEXOCB": (89, 89), "EDADCA": (129, 130), "EDADCB": (131, 132)}
SPAIN = "108"          # PAISNXM : pays de naissance de la mère (108 = Espagne)
WOMAN, MAN = "6", "1"  # codes sexe INE (TSEXO)


def age_group_of(age: pd.Series) -> pd.Series:
    return pd.cut(pd.to_numeric(age, errors="coerce"), bins=[15, 20, 25, 30, 35, 40, 50], right=False, labels=AGE_GROUPS).astype(object)


# ----------------------------------------------------------------------------- microdonnées

def _fixed_width(raw: bytes, fields: dict) -> pd.DataFrame:
    names = list(fields)
    colspecs = [(a - 1, b) for a, b in fields.values()]
    return pd.read_fwf(io.BytesIO(raw), colspecs=colspecs, names=names, dtype=str, encoding="latin-1", header=None)


def _members(z: zipfile.ZipFile, suffixes: tuple[str, ...]) -> list[str]:
    return [n for n in z.namelist() if n.lower().endswith(suffixes) and not n.endswith("/")]


def read_births(path: Path) -> pd.DataFrame:
    """Une ligne par naissance : year, municipio (résidence de la mère ; NaN si non codé), age, married, rank1, foreign_born, live."""
    with zipfile.ZipFile(path) as z:
        pq = _members(z, (".parquet",))
        if pq:
            d = pd.read_parquet(io.BytesIO(z.read(pq[0])))
            d = d[["ANOPAR", "PROREM", "MUNREM", "EDADM", "ECIVM", "NUMHV", "PAISNXM", "CLASIF"]].copy()
        else:
            txt = [n for n in _members(z, (".txt", ".a2007", ".a2008", ".a2009", ".a2010", ".a2011", ".a2012", ".a2013", ".a2014", ".a2015"))
                   if "dise" not in n.lower()]
            if not txt:
                txt = [n for n in z.namelist() if not n.endswith("/")]
            d = _fixed_width(z.read(txt[0]), BIRTH_FIELDS_0715)
    for c in d.columns:
        d[c] = d[c].fillna("").astype(str).str.strip()
    out = pd.DataFrame({"year": pd.to_numeric(d.ANOPAR, errors="coerce")})
    mun = d.MUNREM.str.zfill(3).where(d.MUNREM.str.match(r"^\d{1,3}$") & (d.MUNREM != "") & (d.MUNREM != "000"), np.nan)
    out["municipio"] = (d.PROREM.str.zfill(2) + mun).where(mun.notna(), np.nan)
    out["age"] = pd.to_numeric(d.EDADM, errors="coerce")
    out["married"] = np.where(d.ECIVM == "1", 1.0, np.where(d.ECIVM.isin(["2", "3", "4"]), 0.0, np.nan))
    nh = pd.to_numeric(d.NUMHV, errors="coerce")
    out["rank1"] = np.where(nh == 0, 1.0, np.where(nh > 0, 0.0, np.nan))
    # pays de naissance de la mère : 108 = Espagne ; dans les fichiers 2007-2009 le champ est blanc pour les mères nées en Espagne
    out["foreign_born"] = np.where((d.PAISNXM == SPAIN) | (d.PAISNXM == ""), 0.0, np.where(d.PAISNXM.str.match(r"^\d{3}$"), 1.0, np.nan))
    out["live"] = d.CLASIF.isin(["1", "3"]) | (d.CLASIF == "")
    return out


def read_marriages(path: Path) -> pd.DataFrame:
    """Mariages homme-femme : year, municipio (résidence du couple ; NaN si non codé), wife_age."""
    with zipfile.ZipFile(path) as z:
        pq = _members(z, (".parquet",))
        if pq:
            d = pd.read_parquet(io.BytesIO(z.read(pq[0])))
            d = d[["ANOCM", "CPROMA", "CMUMA", "SEXOCA", "SEXOCB", "EDADCA", "EDADCB"]].copy()
        else:
            txt = [n for n in z.namelist() if not n.endswith("/") and "dise" not in n.lower() and not n.lower().endswith((".xls", ".xlsx", ".doc", ".pdf"))]
            d = _fixed_width(z.read(txt[0]), MARRIAGE_FIELDS_0815)
    for c in d.columns:
        d[c] = d[c].fillna("").astype(str).str.strip()
    hetero = ((d.SEXOCA == WOMAN) & (d.SEXOCB == MAN)) | ((d.SEXOCA == MAN) & (d.SEXOCB == WOMAN))
    out = pd.DataFrame({"year": pd.to_numeric(d.ANOCM, errors="coerce")})
    mun = d.CMUMA.str.zfill(3).where(d.CMUMA.str.match(r"^\d{1,3}$") & (d.CMUMA != "") & (d.CMUMA != "000"), np.nan)
    out["municipio"] = (d.CPROMA.str.zfill(2) + mun).where(mun.notna(), np.nan)
    out["wife_age"] = np.where(d.SEXOCA == WOMAN, pd.to_numeric(d.EDADCA, errors="coerce"), pd.to_numeric(d.EDADCB, errors="coerce"))
    out["hetero"] = hetero.values
    return out


# ----------------------------------------------------------------------------- Padrón (PC-Axis)

def read_padron_px(path: Path) -> pd.DataFrame:
    """Table 33570 : population par sexe × municipio × période (1er janvier) × groupe d'âge quinquennal. Renvoie municipio, year,
    sex (total/h/f), age_group (libellé INE), pop (NaN pour « .. »)."""
    raw = Path(path).read_bytes().decode("iso-8859-15")
    head, data = raw.split("DATA=", 1)

    def vals(kind, key):
        m = re.search(kind + r'\("' + re.escape(key) + r'"\)=(.*?);\s*\n', head, re.S)
        return re.findall(r'"([^"]*)"', m.group(1))

    stub = [s.strip('"') for s in re.search(r"STUB=(.*?);", head).group(1).split(",")]
    heading = [s.strip('"') for s in re.search(r"HEADING=(.*?);", head).group(1).split(",")]
    assert stub == ["Sexo", "Municipios", "Periodo"] and heading == ["Edad (grupos quinquenales)"], (stub, heading)
    sexo, per, edad = vals("VALUES", "Sexo"), vals("VALUES", "Periodo"), vals("VALUES", "Edad (grupos quinquenales)")
    codes = vals("CODES", "Municipios")
    nums = data.replace(";", "").split()
    assert len(nums) == len(sexo) * len(codes) * len(per) * len(edad), (len(nums), len(sexo), len(codes), len(per), len(edad))
    v = pd.to_numeric(pd.Series(nums).str.strip('"'), errors="coerce").values.reshape(len(sexo), len(codes), len(per), len(edad))
    idx = pd.MultiIndex.from_product([sexo, codes, per, edad], names=["sex", "municipio", "period", "age_group"])
    d = pd.DataFrame({"pop": v.ravel()}, index=idx).reset_index()
    d["year"] = d.period.str.extract(r"(\d{4})")[0].astype(int)
    d["sex"] = d.sex.map({"Total": "total", "Hombres": "h", "Mujeres": "f"})
    return d[d.municipio.str.match(r"^\d{5}$")][["municipio", "year", "sex", "age_group", "pop"]]


def padron_age_group(label: str) -> str | None:
    m = re.match(r"De (\d+) a (\d+) años", label)
    if not m:
        return None
    a = int(m.group(1))
    if 15 <= a <= 35:
        return f"{a}-{a + 4}"
    if a in (40, 45):
        return "40-49"
    return None


# ----------------------------------------------------------------------------- couverture

def read_coverage_2013_2020(path: Path) -> pd.DataFrame:
    """Feuille « Municipio » : CMUN, Habitantes, colonnes « LTE  (dic 2013) » … « LTE  (junio 2020) » (parts de population)."""
    d = pd.read_excel(path, sheet_name="Municipio", header=0)
    d.columns = [str(c).replace("\n", " ").strip() for c in d.columns]
    d["municipio"] = d["CMUN"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(5)
    rows = []
    for c in d.columns:
        m = re.match(r"^(LTE|HSPA)\s+\((dic|junio)\.?\s*(\d{4})\)$", c)
        if m:
            rows.append(pd.DataFrame({"municipio": d.municipio, "tech": m.group(1), "month": 12 if m.group(2) == "dic" else 6, "year": int(m.group(3)),
                                      "share": pd.to_numeric(d[c], errors="coerce")}))
    cov = pd.concat(rows, ignore_index=True)
    pop = d[["municipio", "Habitantes"]].rename(columns={"Habitantes": "habitantes"})
    pop["habitantes"] = pd.to_numeric(pop.habitantes, errors="coerce")
    return cov, pop


def read_coverage_2021_2025(path: Path) -> pd.DataFrame:
    d = pd.read_excel(path, sheet_name="Municipio_%hogar", header=0)
    d.columns = [str(c).replace("\n", " ").strip() for c in d.columns]
    d["municipio"] = d["CMUN"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(5)
    rows = []
    for c in d.columns:
        m = re.match(r"^4G \(junio (\d{4})\)$", c)
        if m:
            rows.append(pd.DataFrame({"municipio": d.municipio, "tech": "4G_hogares", "month": 6, "year": int(m.group(1)), "share": pd.to_numeric(d[c], errors="coerce")}))
    return pd.concat(rows, ignore_index=True)
