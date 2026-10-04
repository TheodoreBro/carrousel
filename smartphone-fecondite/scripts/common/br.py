"""Brésil — lecteurs communs : réponses JSON de l'API IBGE « agregados v3 » et table Anatel « Municípios atendidos por SMP ».

Conventions : code município IBGE à 7 chiffres (texte) ; groupes d'âge de la préregistration (15-19 … 40-49).
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

AGE_GROUPS = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-49"]
# table 2609 / 4412 : libellés IBGE des groupes quinquennaux → groupes de la préregistration
IBGE_GROUP_TO_AGE = {"15 a 19 anos": "15-19", "20 a 24 anos": "20-24", "25 a 29 anos": "25-29", "30 a 34 anos": "30-34",
                     "35 a 39 anos": "35-39", "40 a 44 anos": "40-49", "45 a 49 anos": "40-49"}
REGIONS = {"1": "Norte", "2": "Nordeste", "3": "Sudeste", "4": "Sul", "5": "Centro-Oeste"}


def _num(v) -> float:
    """Valeurs IBGE/SIDRA : nombre ; « - » = zéro absolu (converti par l'appelant) ; « ... » = non disponible ; « X » = secret."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return np.nan


def read_ibge(path: Path) -> pd.DataFrame:
    """Table longue : municipio (7 chiffres), year, value, puis une colonne par classification (libellé de la catégorie) et
    ``cat_<id>`` (identifiant de catégorie). Les valeurs non numériques sont NaN et comptées dans la colonne ``raw``."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = []
    for var in data:
        for res in var["resultados"]:
            cls = {c["nome"]: next(iter(c["categoria"].values())) for c in res["classificacoes"]}
            ids = {f"cat_{c['id']}": next(iter(c["categoria"].keys())) for c in res["classificacoes"]}
            for s in res["series"]:
                loc = s["localidade"]
                for per, val in s["serie"].items():
                    rows.append({"municipio": str(loc["id"]).zfill(7), "year": int(per), "raw": val, "value": _num(val), **cls, **ids})
    return pd.DataFrame(rows)


def read_anatel_presence(path: Path) -> pd.DataFrame:
    """« Tabela_Municipios_Atendidos_SMP » : Período (mm/aaaa), Operadora, Município, UF, Código IBGE, Tecnologia, Presença (SIM/NÃO)."""
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        d = pd.read_csv(io.BytesIO(z.read(name)), sep=";", dtype=str, encoding="utf-8-sig")
    d.columns = [c.strip() for c in d.columns]
    d["per"] = pd.to_datetime(d["Período"], format="%m/%Y")
    d["year"] = d.per.dt.year
    d["municipio"] = d["Código IBGE"].astype(str).str.strip().str.zfill(7)
    d["tech"] = d["Tecnologia"].str.strip().str.upper()
    d["present"] = d["Presença"].str.strip().str.upper().str.startswith("S")
    d["operator"] = d["Operadora"].str.strip().str.upper()
    d["uf"] = d["UF"].str.strip().str.upper()
    return d[["municipio", "uf", "operator", "tech", "per", "year", "present"]]
