#!/usr/bin/env python
"""Suède — check-list des critères d'inclusion (préregistration §4.3) sur les fichiers PTS consignés.

Calcule, par année, la distribution entre kommuner de la part des ménages ayant accès au haut débit fixe via LTE
(tabellbilaga historiska uppgifter teknik, 2015-2022) et le nombre de kommuner au-dessus des seuils préenregistrés
(50 % ; variante 90 %) ; puis la couverture surfacique 4G ≥ 10 Mbit/s (tabellbilaga mobiltäckning, 2016-2024).
Sorties : tables/t_se_check.md et tables/t_se_check.csv. Aucune estimation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common.download import raw_files  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "tables"


def lte_households() -> pd.DataFrame:
    p = next(p for p in raw_files("se_pts_tackning") if "historiska" in p.name)
    d = pd.read_excel(p, sheet_name="Fast bredband-teknik, totalt", header=None)
    hdr = d.iloc[4:7].ffill(axis=1)
    cols = [" / ".join(str(x) for x in col if str(x) != "nan") for col in zip(hdr.iloc[0], hdr.iloc[1], hdr.iloc[2])]
    body = d.iloc[7:].copy()
    body.columns = cols
    body = body.rename(columns={cols[0]: "kod", cols[1]: "namn"})
    body["kod"] = pd.to_numeric(body.kod, errors="coerce")
    kom = body[body.kod >= 100].copy()                      # codes à 4 chiffres = kommuner ; 2 chiffres = län
    rows = []
    for y in range(2015, 2023):
        c = f"Andel med tillgång till fast bredband via LTE ej 450 MHz / {y} / Hushåll"
        s = pd.to_numeric(kom[c], errors="coerce")
        q = np.nanquantile(s, [0.05, 0.25, 0.5, 0.75, 0.95])
        rows.append({"série": "ménages avec accès LTE (fixe via LTE hors 450 MHz)", "année": y, "kommuner": int(s.notna().sum()),
                     "min": float(np.nanmin(s)), "q05": q[0], "q25": q[1], "médiane": q[2], "q75": q[3], "q95": q[4],
                     "≥ 50 %": int((s >= 0.5).sum()), "≥ 90 %": int((s >= 0.9).sum()), "≥ 99 %": int((s >= 0.99).sum())})
    return pd.DataFrame(rows)


def area_4g() -> pd.DataFrame:
    p = next(p for p in raw_files("se_pts_tackning") if "1-3" in p.name)
    y = pd.read_excel(p, sheet_name="Yttäckning - aggregerad", header=None)
    h = y.iloc[1:4].ffill(axis=1)
    cols = [" / ".join(str(x).replace("\n", " ") for x in col if str(x) != "nan") for col in zip(h.iloc[0], h.iloc[1], h.iloc[2])]
    body = y.iloc[4:].copy()
    body.columns = cols
    body = body.rename(columns={cols[0]: "namn", cols[1]: "kod"})
    body["kod"] = pd.to_numeric(body.kod, errors="coerce")
    kom = body[body.kod >= 100]
    rows = []
    seen = set()
    for i, c in enumerate(cols):
        # colonnes par triplets (terminal de base « Grund », +8 dB, +16 dB) ; on garde la première de chaque (série, année)
        if "4G" in c and "10 Mbit" in c and "exkl" in c and int(c.split(" / ")[-1]) not in seen:
            year = int(c.split(" / ")[-1])
            seen.add(year)
            s = pd.to_numeric(body.iloc[:, i][kom.index].replace({">99,99%": 0.9999}), errors="coerce")
            q = np.nanquantile(s, [0.05, 0.25, 0.5, 0.75, 0.95])
            rows.append({"série": "couverture surfacique 4G ≥ 10 Mbit/s hors 450 MHz (terminal de base)", "année": year, "kommuner": int(s.notna().sum()),
                         "min": float(np.nanmin(s)), "q05": q[0], "q25": q[1], "médiane": q[2], "q75": q[3], "q95": q[4],
                         "≥ 50 %": int((s >= 0.5).sum()), "≥ 90 %": int((s >= 0.9).sum()), "≥ 99 %": int((s >= 0.99).sum())})
    return pd.DataFrame(rows).sort_values("année")


def main() -> int:
    t = pd.concat([lte_households(), area_4g()], ignore_index=True)
    t.to_csv(TABLES / "t_se_check.csv", index=False)
    lines = ["# Suède — vérification des critères d'inclusion (généré par scripts/08_se_check.py)", "",
             "Source : PTS, Mobiltäcknings- och bredbandskartläggning, tabellbilagor consignées dans `docs/data_log.md` (`se_pts_tackning`). "
             "Unités = 290 kommuner. Les colonnes « ≥ 50 % » et « ≥ 90 % » comptent les kommuner au-dessus des seuils de traitement "
             "préenregistrés (§4.2). Aucune donnée par kommun antérieure à 2015 n'est en ligne chez PTS (voir addendum A3).", "",
             "| série | année | kommuner | min | q05 | q25 | médiane | q75 | q95 | ≥ 50 % | ≥ 90 % | ≥ 99 % |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in t.iterrows():
        f = lambda v: "" if pd.isna(v) else f"{100 * v:.1f} %"  # noqa: E731
        lines.append(f"| {r['série']} | {r['année']} | {r['kommuner']} | {f(r['min'])} | {f(r['q05'])} | {f(r['q25'])} | {f(r['médiane'])} | {f(r['q75'])} | {f(r['q95'])} | {r['≥ 50 %']} | {r['≥ 90 %']} | {r['≥ 99 %']} |")
    (TABLES / "t_se_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
