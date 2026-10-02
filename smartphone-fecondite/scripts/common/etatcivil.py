"""Lecture des fichiers détail de l'état civil INSEE (naissances, mariages), dBase ou csv.

Les noms de variables diffèrent selon les millésimes (minuscules/majuscules, ``nbenfpre`` jusqu'en 2012,
``naiss2010``…). Cette couche renvoie des DataFrames aux colonnes normalisées en minuscules, lues en
chaînes, sans aucune imputation.
"""
from __future__ import annotations

import os
import re
import tempfile
import zipfile
from pathlib import Path

import pandas as pd


def _extract(zip_path: Path, pattern: str) -> Path:
    z = zipfile.ZipFile(zip_path)
    name = next(n for n in z.namelist() if re.search(pattern, n, re.I))
    d = Path(tempfile.mkdtemp(prefix="etatcivil_"))
    z.extract(name, d)
    return d / name


def read_detail(zip_path: Path, kind: str, usecols: list[str] | None = None) -> pd.DataFrame:
    """``kind`` = 'nais' ou 'mar'. Lit la table principale (dbf ou csv) ; colonnes en minuscules."""
    z = zipfile.ZipFile(zip_path)
    names = z.namelist()
    main_csv = [n for n in names if re.search(rf"{kind}\w*\d{{4}}\w*\.csv$", n, re.I)
                and not re.search(r"varmod|varlist|contenu", n, re.I)]
    main_dbf = [n for n in names if re.search(rf"{kind}\w*\.dbf$", n, re.I)
                and not re.search(r"varmod|varlist", n, re.I)]
    if main_csv:
        with z.open(main_csv[0]) as f:
            head = f.readline().decode("utf-8", "replace")
        sep = ";" if head.count(";") >= head.count(",") else ","
        cols = [c.strip().strip('"').lower() for c in head.strip().split(sep)]
        want = None if usecols is None else [cols.index(c) for c in usecols if c in cols]
        df = pd.read_csv(z.open(main_csv[0]), sep=sep, dtype=str, usecols=want, encoding="utf-8",
                         encoding_errors="replace", keep_default_na=False)
        df.columns = [c.lower() for c in df.columns]
        return df
    if main_dbf:
        from dbfread import DBF
        p = _extract(zip_path, re.escape(main_dbf[0]))
        t = DBF(p, load=False, encoding="latin-1", char_decode_errors="replace")
        fields = [f for f in t.field_names if usecols is None or f.lower() in usecols]
        rows = ([r[f] for f in fields] for r in t)
        df = pd.DataFrame(rows, columns=[f.lower() for f in fields]).astype(str)
        os.remove(p)
        return df
    raise FileNotFoundError(f"{zip_path.name} : aucune table {kind} (contenu : {names})")


def year_of(zip_path: Path) -> int:
    m = re.search(r"(19|20)\d{2}", zip_path.name)
    return int(m.group(0))


AGE_GROUPS = [(15, 19, "15-19"), (20, 24, "20-24"), (25, 29, "25-29"), (30, 34, "30-34"), (35, 39, "35-39"), (40, 49, "40-49")]


def age_group(age: pd.Series) -> pd.Series:
    a = pd.to_numeric(age, errors="coerce")
    out = pd.Series(pd.NA, index=age.index, dtype="object")
    for lo, hi, lab in AGE_GROUPS:
        out[(a >= lo) & (a <= hi)] = lab
    out[a < 15] = "15-19"           # < 15 ans : rattachées au premier groupe (effectifs infimes), compté
    out[a >= 50] = "40-49"          # ≥ 50 ans : rattachées au dernier groupe (effectifs infimes), compté
    return out
