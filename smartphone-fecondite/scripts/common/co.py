"""Colombie — lecteurs communs : projections de population DANE (municipio × área × sexe × âge simple) et microdonnées
des naissances EEVV (fichiers texte tabulés 1998-2007, CSV 2008-2024, dans des archives parfois emboîtées).

Conventions : code municipio DIVIPOLA à 5 chiffres (département 2 + municipio 3) ; groupes d'âge de la préregistration.
"""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

AGE_GROUPS = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-49"]
# EDAD_MADRE (EEVV) : 1 = 10-14, 2 = 15-19, 3 = 20-24, 4 = 25-29, 5 = 30-34, 6 = 35-39, 7 = 40-44, 8 = 45-49, 9 = 50-54, 99 = sans information
EDAD_TO_GROUP = {2: "15-19", 3: "20-24", 4: "25-29", 5: "30-34", 6: "35-39", 7: "40-49", 8: "40-49"}
# EST_CIVM, fichiers 2008+ : 1 = union libre ≥ 2 ans, 2 = union libre < 2 ans, 3 = séparée/divorcée, 4 = veuve, 5 = célibataire,
# 6 = mariée, 9 = sans information. Fichiers 1998-2007 (dictionnaire DANE-DCD-EEVV-1998-2007) : 1 = célibataire, 2 = mariée,
# 3 = veuve, 4 = union libre, 5 = séparée/divorcée, 9 = sans information (vérifié le 04/10/2026, addendum A4).
UNION_CODES = {1, 2, 6}
NOT_UNION_CODES = {3, 4, 5}
UNION_CODES_OLD = {2, 4}
NOT_UNION_CODES_OLD = {1, 3, 5}


def age_group_of_single_age(age: pd.Series) -> pd.Series:
    bins = [15, 20, 25, 30, 35, 40, 50]
    labels = AGE_GROUPS
    return pd.cut(age, bins=bins, right=False, labels=labels).astype(object)


# ----------------------------------------------------------------------------- projections DANE

def load_projections(paths: list[Path]) -> pd.DataFrame:
    """Lit les fichiers « proyecciones de población municipal por área, sexo y edad simple » et renvoie une table longue :
    municipio (5 chiffres), year, area (cabecera / resto / total), sex (h/f), age (int), pop."""
    out = []
    for p in sorted(paths):
        x = pd.ExcelFile(p)
        for sh in x.sheet_names:
            raw = pd.read_excel(p, sheet_name=sh, header=None)
            if raw.shape[1] < 8:
                continue
            hdr = next((i for i in range(min(40, len(raw))) if str(raw.iloc[i, 0]).strip().upper() in ("DP", "COD_DPTO") or
                        str(raw.iloc[i, 3]).strip().upper() in ("MPIO", "COD_MPIO")), None)
            if hdr is None:
                continue
            names = [str(c).strip() for c in raw.iloc[hdr]]
            second = [str(c).strip() for c in raw.iloc[hdr + 1]] if hdr + 1 < len(raw) else []
            # fichier 2018-2042 : deuxième ligne d'en-tête (« Hombres 0 años », « Mujeres 0 años ») sous des groupes HOMBRES / MUJERES
            two_rows = bool(second) and any(re.match(r"(?i)^(hombres|mujeres) \d+", c) for c in second)
            if two_rows:
                names = [b if re.match(r"(?i)^(hombres|mujeres) \d+", b) else a for a, b in zip(names, second)]
                names = [re.sub(r"(?i)^(hombres|mujeres) (\d+).*$", lambda m: f"{m.group(1)}_{m.group(2)}", n) for n in names]
            d = raw.iloc[hdr + (2 if two_rows else 1):].copy()
            d.columns = names
            cols = {c.upper(): c for c in d.columns}
            mp = cols.get("MPIO") or cols.get("COD_MPIO")
            yr = cols.get("AÑO") or cols.get("ANO") or cols.get("AÑO ")
            ar = next((cols[c] for c in cols if "REA" in c), None)
            if not (mp and yr and ar):
                continue
            age_cols = [c for c in d.columns if re.match(r"(?i)^(hombres|mujeres)_\d+$", c)]
            if not age_cols:
                continue
            d["municipio"] = d[mp].astype(str).str.zfill(5)
            d["year"] = pd.to_numeric(d[yr], errors="coerce")
            d = d[d.year.notna()]
            d["year"] = d.year.astype(int)
            a = d[ar].astype(str).str.lower()
            d["area"] = np.where(a.str.contains("cabecera"), "cabecera", np.where(a.str.contains("total"), "total", "resto"))
            long = d.melt(id_vars=["municipio", "year", "area"], value_vars=age_cols, var_name="sa", value_name="pop")
            long["sex"] = np.where(long.sa.str.lower().str.startswith("hombres"), "h", "f")
            long["age"] = long.sa.str.extract(r"_(\d+)$")[0].astype(int)
            long["pop"] = pd.to_numeric(long["pop"], errors="coerce")
            out.append(long.drop(columns="sa"))
    res = pd.concat(out, ignore_index=True)
    return res.drop_duplicates(["municipio", "year", "area", "sex", "age"], keep="last")


# ----------------------------------------------------------------------------- naissances EEVV

NEEDED = ["ano", "codptore", "codmunre", "edad_madre", "est_civm", "n_hijosv", "niv_edum", "area_res"]


def _iter_members(z: zipfile.ZipFile):
    """Parcourt une archive (et ses archives emboîtées) ; renvoie (nom, octets) des fichiers de données texte/CSV."""
    for n in z.namelist():
        low = n.lower()
        if low.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(z.read(n))) as zi:
                yield from _iter_members(zi)
        elif low.endswith((".csv", ".txt")) and "fetal" not in low and "defun" not in low:
            yield n, z.read(n)


def read_births(path: Path) -> pd.DataFrame:
    """Naissances d'une archive EEVV : une ligne par naissance avec les variables utiles (minuscules), ``year`` tiré de
    ``ano`` et ``municipio`` = résidence de la mère (codptore + codmunre). Les fichiers .sav/.dta ne sont pas lus."""
    frames = []
    with zipfile.ZipFile(path) as z:
        for name, raw in _iter_members(z):
            head = raw[:4096].decode("latin-1", errors="replace")
            sep = "\t" if head.count("\t") > head.count(",") else ("," if head.count(",") >= head.count(";") else ";")
            df = pd.read_csv(io.BytesIO(raw), sep=sep, encoding="latin-1", dtype=str, low_memory=False)
            df.columns = [c.strip().lower() for c in df.columns]
            keep = [c for c in NEEDED if c in df.columns]
            if "codmunre" not in keep or "edad_madre" not in keep:
                continue
            frames.append(df[keep].assign(_file=name))
    if not frames:
        raise ValueError(f"{path.name} : aucun fichier de naissances lisible")
    d = pd.concat(frames, ignore_index=True)
    d["year"] = pd.to_numeric(d.get("ano"), errors="coerce")
    d["municipio"] = d.codptore.astype(str).str.strip().str.zfill(2) + d.codmunre.astype(str).str.strip().str.zfill(3)
    d["edad"] = pd.to_numeric(d.edad_madre, errors="coerce")
    d["age_group"] = d.edad.map(EDAD_TO_GROUP)
    d["civ"] = pd.to_numeric(d.get("est_civm"), errors="coerce")
    old = d.year <= 2007
    d["union"] = np.where(old, np.where(d.civ.isin(UNION_CODES_OLD), 1.0, np.where(d.civ.isin(NOT_UNION_CODES_OLD), 0.0, np.nan)),
                          np.where(d.civ.isin(UNION_CODES), 1.0, np.where(d.civ.isin(NOT_UNION_CODES), 0.0, np.nan)))
    d["rank1"] = (pd.to_numeric(d.get("n_hijosv"), errors="coerce") == 1).astype(float).where(d.get("n_hijosv").notna(), np.nan) if "n_hijosv" in d else np.nan
    return d
