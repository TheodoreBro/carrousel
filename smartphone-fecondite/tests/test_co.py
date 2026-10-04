"""Colombie — lecteurs communs : recodage de l'état civil par période, groupes d'âge, lecture d'une archive EEVV synthétique."""
import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common.co import AGE_GROUPS, age_group_of_single_age, read_births  # noqa: E402


def _archive(tmp_path: Path, rows: str, name: str, sep: str) -> Path:
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as zi:
        zi.writestr(name, rows.replace(",", sep))
    p = tmp_path / "nacimientos.zip"
    with zipfile.ZipFile(p, "w") as z:            # archive emboîtée, comme certains fichiers DANE
        z.writestr("inner.zip", inner.getvalue())
    return p


def test_age_groups_boundaries():
    g = age_group_of_single_age(pd.Series([14, 15, 19, 20, 39, 40, 49, 50]))
    assert pd.isna(g.iloc[0]) and pd.isna(g.iloc[-1])
    assert list(g.iloc[1:-1]) == ["15-19", "15-19", "20-24", "35-39", "40-49", "40-49"]
    assert set(g.dropna()) <= set(AGE_GROUPS)


def test_union_recoding_by_period(tmp_path):
    # 1998-2007 : 2 = mariée, 4 = union libre, 1 = célibataire ; 2008+ : 1/2 = union libre, 6 = mariée, 5 = célibataire, 9 = inconnu
    rows = "ANO,CODPTORE,CODMUNRE,EDAD_MADRE,EST_CIVM,N_HIJOSV\n2005,5,1,3,2,1\n2005,5,1,3,4,2\n2005,5,1,3,1,1\n2010,5,1,3,1,1\n2010,5,1,3,6,3\n2010,5,1,3,5,1\n2010,5,1,3,9,1\n"
    b = read_births(_archive(tmp_path, rows, "nac2005.txt", "\t"))
    assert list(b.municipio) == ["05001"] * 7
    assert list(b.age_group) == ["20-24"] * 7
    assert b.union.tolist()[:3] == [1.0, 1.0, 0.0]
    assert b.union.tolist()[3:6] == [1.0, 1.0, 0.0] and np.isnan(b.union.iloc[6])
    assert b.rank1.tolist() == [1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0]


def test_csv_archive_with_semicolon(tmp_path):
    rows = "ANO,CODPTORE,CODMUNRE,EDAD_MADRE,EST_CIVM,N_HIJOSV\n2020,11,1,99,1,1\n2020,11,1,8,6,1\n"
    b = read_births(_archive(tmp_path, rows, "nac2020.csv", ";"))
    assert b.age_group.isna().iloc[0] and b.age_group.iloc[1] == "40-49"
