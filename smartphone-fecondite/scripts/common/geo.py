"""Harmonisation des codes communes sur une géographie de référence (COG INSEE).

Règle (préregistration §4.1 et §10) : agrégation à la géographie la plus récente. Toute paire de codes
reliée par une fusion (MOD 31, 32, 33, 34), un rétablissement (21), un changement de code (41) ou de
département (50) depuis ``since`` appartient à la même **unité harmonisée**. L'identifiant de l'unité est
le plus petit code de commune actuelle (TYPECOM = COM) de la composante. Une composante contenant plusieurs
communes actuelles (commune rétablie après fusion) est donc agrégée sur toute la période : ces cas sont
comptés et rapportés.

Les arrondissements municipaux (ARM) et les communes déléguées/associées (COMD, COMA) sont rattachés à
leur commune parente (COMPARENT).
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pandas as pd

LINK_MODS = {"21", "31", "32", "33", "34", "41", "50"}


class Cog:
    def __init__(self, zip_path: Path, since: str = "1998-01-01"):
        z = zipfile.ZipFile(zip_path)
        names = z.namelist()
        com_name = next(n for n in names if re.match(r"v_commune_\d{4}\.csv$", n))
        mvt_name = next(n for n in names if re.match(r"v_mvt_commune_\d{4}\.csv$", n))
        self.year = int(re.search(r"(\d{4})", com_name).group(1))
        self.communes = pd.read_csv(z.open(com_name), dtype=str)
        self.mvt = pd.read_csv(z.open(mvt_name), dtype=str)
        self.since = since
        self._build()

    def _build(self) -> None:
        com = self.communes
        self.current = set(com.loc[com.TYPECOM == "COM", "COM"])
        parent = com.loc[com.TYPECOM.isin(["ARM", "COMD", "COMA"]), ["COM", "COMPARENT"]].dropna()
        self.parent = dict(zip(parent.COM, parent.COMPARENT))
        dep = com.loc[com.TYPECOM == "COM", ["COM", "DEP"]]
        self.dep = dict(zip(dep.COM, dep.DEP))

        # union-find sur les codes reliés par un mouvement depuis `since`
        par: dict[str, str] = {}

        def find(x: str) -> str:
            par.setdefault(x, x)
            while par[x] != x:
                par[x] = par[par[x]]
                x = par[x]
            return x

        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                par[ra] = rb

        m = self.mvt
        m = m[(m.MOD.isin(LINK_MODS)) & (m.DATE_EFF >= self.since)]
        for a, b in zip(m.COM_AV, m.COM_AP):
            if isinstance(a, str) and isinstance(b, str):
                union(a, b)
        # composantes → identifiant = plus petit code de commune actuelle de la composante
        comp: dict[str, list[str]] = {}
        for x in list(par):
            comp.setdefault(find(x), []).append(x)
        self.mapping: dict[str, str] = {}
        self.multi_current: list[tuple[str, ...]] = []
        for members in comp.values():
            cur = sorted(c for c in members if c in self.current)
            cur_parents = sorted({self.parent.get(c, c) for c in members if c in self.parent} - set(cur))
            if not cur:
                cur = cur_parents
            if not cur:
                continue                                   # codes supprimés sans successeur actuel : laissés tels quels
            if len(cur) > 1:
                self.multi_current.append(tuple(cur))
            for c in members:
                self.mapping[c] = cur[0]
            for c in cur:
                self.mapping[c] = cur[0]
        # communes actuelles non touchées → elles-mêmes ; ARM/COMD/COMA → parent (puis composante)
        for c in self.current:
            self.mapping.setdefault(c, c)
        for c, p in self.parent.items():
            self.mapping.setdefault(c, self.mapping.get(p, p))
        self.units = sorted(set(self.mapping[c] for c in self.current))

    def harmonize(self, codes: pd.Series) -> pd.Series:
        """Code historique → unité harmonisée. Les codes inconnus du COG sont renvoyés tels quels."""
        s = codes.astype(str).str.strip().str.upper().str.zfill(5)
        return s.map(self.mapping).fillna(s)

    def unknown(self, codes: pd.Series) -> pd.Series:
        s = codes.astype(str).str.strip().str.upper().str.zfill(5)
        return s[~s.isin(self.mapping)].drop_duplicates()

    def dep_of(self, units: pd.Series) -> pd.Series:
        return units.map(self.dep).fillna(units.str[:2])

    def is_metro(self, units: pd.Series) -> pd.Series:
        d = self.dep_of(units)
        return ~d.str.startswith("97") & ~d.str.startswith("98")
