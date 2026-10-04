#!/usr/bin/env python
"""Statut du smartphone comme facteur de la baisse de fécondité (préregistration §6, addendum A9) — tables/t_status.md|csv.

Part de la baisse observée du taux de naissances des 25-39 ans (entre la première cohorte 4G et la dernière année du panel)
qu'explique l'effet poolé primaire sur les 25-39 ans (A7, tables/t_meta.md). Règle : premier ordre ≥ 25 %, second ordre 5-25 %,
négligeable < 5 % ou non détecté avec puissance suffisante (A9), indéterminé sinon. Usage : python scripts/23_status.py
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC, TABLES = ROOT / "data" / "processed", ROOT / "tables"
AGES = ["25-29", "30-34", "35-39"]
COUNTRIES = {  # pays : (fichier résultats × âge, filtre, tag du tableau d'échantillon)
    "France": ("fr_outcomes_dep_age.parquet", lambda d: d[d.metro], "fr"),
    "Colombie": ("co_outcomes_mun_age.parquet", lambda d: d, "co"),
    "Brésil": ("br_outcomes_mun_age.parquet", lambda d: d, "br"),
    "Espagne": ("es_outcomes_mun_age.parquet", lambda d: d, "es"),
}


def years(tag: str) -> tuple[int, int]:
    """Année de lancement (première cohorte de H2b) et dernière année du panel, lues dans t_sample_<tag>.csv."""
    t = pd.read_csv(TABLES / f"t_sample_{tag}.csv")
    sel = t[t["spécification"].str.contains("25-39|25-29")]  # H2b (25-39) ; en France la ligne départementale 25-29 porte les mêmes cohortes (2013-2018) et années
    r = sel.iloc[0]
    return int(str(r["cohortes"]).split("-")[0]), int(str(r["années"]).split("-")[1])


def meta() -> tuple[pd.DataFrame, pd.DataFrame]:
    txt = (TABLES / "t_meta.csv").read_text(encoding="utf-8")
    i = txt.index("groupe,pays,k_pays")  # t_meta.csv = tableau national puis tableau poolé (18_meta.py, mode append)
    return pd.read_csv(io.StringIO(txt[:i])), pd.read_csv(io.StringIO(txt[i:]))


def main() -> int:
    nat, pooled = meta()
    rows = []
    for pays, (f, flt, tag) in COUNTRIES.items():
        d = flt(pd.read_parquet(PROC / f))
        d = d[d.age_group.isin(AGES)].dropna(subset=["births", "women"])
        g = d.groupby("year")[["births", "women"]].sum()
        g["rate"] = 1000 * g.births / g.women
        y0, y1 = years(tag)
        r0, r1 = g.loc[y0, "rate"], g.loc[y1, "rate"]
        att = nat[(nat.pays == pays) & (nat.groupe == "25-39")].iloc[0]
        change = 100 * (r1 / r0 - 1)
        rows.append({"pays": pays, "année lancement": y0, "dernière année": y1, "taux 25-39 lancement": r0, "taux 25-39 dernière": r1,
                     "variation observée %": change, "naissances 25-39 lancement": g.loc[y0, "births"], "ATT pays %": att.att_pct,
                     "part expliquée par l'ATT du pays %": 100 * att.att_pct / change if change < 0 else float("nan")})
    t = pd.DataFrame(rows)
    w = t["naissances 25-39 lancement"]
    mean_change = (t["variation observée %"] * w).sum() / w.sum()
    out = []
    for _, p in pooled[pooled.groupe == "25-39"].iterrows():
        lo, hi, est = float(p["IC bas"]), float(p["IC haut"]), float(p["poolé %"])
        if mean_change >= 0:
            share, share_lo, share_hi, verdict = float("nan"), float("nan"), float("nan"), "indéterminé (baisse observée nulle ou positive)"
        else:
            share, s_lo, s_hi = 100 * est / mean_change, 100 * hi / mean_change, 100 * lo / mean_change  # une baisse est négative : la borne basse de l'effet explique le plus
            share_lo, share_hi = min(s_lo, s_hi), max(s_lo, s_hi)
            if p.p < 0.05 and share >= 25:
                verdict = "premier ordre"
            elif p.p < 0.05 and 5 <= share < 25:
                verdict = "second ordre"
            elif p.p < 0.05 and share < 5:
                verdict = "négligeable (effet détecté < 5 %)"
            elif share_hi < 5:
                verdict = "négligeable (non détecté, IC sous 5 % de la baisse)"
            else:
                verdict = "indéterminé (IC couvrant une part ≥ 5 %)"
        out.append({"variante": p.variante, "pays": p.pays, "poolé %": est, "IC 95 %": f"[{lo:+.2f}, {hi:+.2f}]", "p": p.p, "baisse observée moyenne %": mean_change,
                    "part expliquée %": share, "part expliquée, IC 95 %": f"[{share_lo:+.0f}, {share_hi:+.0f}]" if share == share else "", "statut (§6, A9)": verdict})
    s = pd.DataFrame(out)
    t.to_csv(TABLES / "t_status.csv", index=False)
    s.to_csv(TABLES / "t_status_pooled.csv", index=False)
    lines = ["# Statut du smartphone comme facteur (préregistration §6, addendum A9) — généré par scripts/23_status.py", "",
             "Taux = naissances des 25-39 ans pour 1 000 femmes de 25-39 ans, agrégé sur les unités du panel de chaque pays ; variation entre la première "
             "cohorte de H2b et la dernière année du panel. ATT en % du taux contrefactuel (`t_meta.md`). Part expliquée = ATT / variation observée.", "",
             t.to_markdown(index=False, floatfmt=".2f"), "",
             f"Baisse observée moyenne (pondérée par les naissances à l'année de lancement) : {mean_change:+.2f} %.", "",
             "## Effet poolé 25-39 (A7) et statut", "", s.to_markdown(index=False, floatfmt=".2f"), "",
             "Règle (§6) : premier ordre si la part expliquée ≥ 25 %, second ordre 5-25 %, négligeable < 5 % ou non détecté avec puissance suffisante "
             "(A9 : effet non significatif et IC sous 5 % de la baisse), indéterminé sinon. Le statut du papier est celui de la variante « primaire »."]
    (TABLES / "t_status.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
