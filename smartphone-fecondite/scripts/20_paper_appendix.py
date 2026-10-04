#!/usr/bin/env python
"""Annexes du papier générées depuis les fichiers du dépôt (rien n'est saisi à la main dans paper.tex) :

- tables/tab_sources.tex      : sources exactes (registre scripts/common/sources.py + manifeste data/raw/manifest.json : fichiers, octets, date)
- tables/tab_countries.tex    : pays examinés (docs/etape0_pays.md §1) et verdicts fichiers en main (docs/data_log.md, addenda A3-A6)
- tables/tab_meta.tex         : synthèse entre pays (tables/t_meta.csv, règles A7)
- tables/tab_dictionary.tex   : dictionnaire des variables (définitions des scripts 02-17, écrites ici une fois)
- tables/tab_design.tex       : résumé du dessin par pays (unité, traitement, fenêtre, cohortes, unités) lu dans les t_sample_*.csv et
                                les parquet de traitement
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common.sources import SOURCES  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "tables"
PROC = ROOT / "data" / "processed"
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("t7", Path(__file__).resolve().parent / "07_tables.py")
t7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(t7)
esc = t7.esc


def longtab(name: str, header: list[str], rows: list[list[str]], caption: str, label: str, note: str, align: str, note_width: str = "15cm") -> None:
    lines = [rf"\begin{{longtable}}{{{align}}}", rf"\caption{{{caption}}}\label{{{label}}}\\", r"\toprule", " & ".join(esc(h) for h in header) + r" \\", r"\midrule", r"\endfirsthead",
             r"\toprule", " & ".join(esc(h) for h in header) + r" \\", r"\midrule", r"\endhead", r"\bottomrule", r"\endfoot"]
    lines += [" & ".join(r) + r" \\" for r in rows]
    lines += [r"\bottomrule", rf"\multicolumn{{{len(header)}}}{{p{{{note_width}}}}}{{\footnotesize {note}}}", r"\end{longtable}", ""]
    (TABLES / name).write_text("\n".join(lines), encoding="utf-8")
    print("annexe :", name, len(rows), "lignes")


def tab_sources() -> None:
    m = json.loads((ROOT / "data" / "raw" / "manifest.json").read_text(encoding="utf-8"))
    by = {}
    for v in m.values():
        s = by.setdefault(v["source"], {"n": 0, "bytes": 0, "first": "9999", "last": "0000"})
        s["n"] += 1
        s["bytes"] += int(v.get("bytes", 0))
        acc = str(v.get("accessed_utc", v.get("accessed", "")))[:10]
        s["first"], s["last"] = min(s["first"], acc), max(s["last"], acc)
    rows = []
    for src in SOURCES:
        st = by.get(src.id)
        if not st and src.country in ("SE",):
            continue
        n = f"{st['n']} ({st['bytes'] / 1e6:,.0f} Mo)".replace(",", "\\,") if st else "non téléchargée"
        acc = (st["first"] if st and st["first"] == st["last"] else f"{st['first']} – {st['last']}") if st else ""
        rows.append([esc(src.country), r"\texttt{" + esc(src.id).replace(r"\_", r"\_\allowbreak{}") + "}", esc(src.title).replace(r"\_", r"\_\allowbreak{}"), esc(src.years), esc(src.license), esc(n), esc(acc)])
    longtab("tab_sources.tex", ["Pays", "Identifiant", "Source", "Années", "Licence", "Fichiers", "Accès"], rows,
            "Sources exactes : registre des sources et fichiers téléchargés", "tab:sources",
            "Source : scripts/common/sources.py et data/raw/manifest.json (empreintes SHA-256 et URL de chaque fichier dans docs/data\\_log.md). "
            "Les sources vérifiées mais non téléchargées (Suède, SCB) sont dans docs/data\\_log.md.", r"lp{2.2cm}p{3.9cm}p{2.1cm}p{1.9cm}p{1.4cm}p{1.6cm}", note_width="14.8cm")


def tab_countries() -> None:
    txt = (ROOT / "docs" / "etape0_pays.md").read_text(encoding="utf-8")
    sec = txt.split("## 1. Classement")[1].split("## 2.")[0]
    lvl1 = re.findall(r"^\| \*\*([^*]+)\*\*", sec.split("### Niveau 2")[0], re.M)
    lvl2 = re.findall(r"^\| \*\*([^*]+)\*\*", sec.split("### Niveau 2")[1].split("### Niveau 3")[0], re.M)
    lvl3 = [c.strip() for c in re.sub(r"\(.*?\)", "", sec.split("### Niveau 3 — descriptif seulement")[1].replace("\n", " ")).split(",") if c.strip() and "voir" not in c]
    verdict = {"France": "incluse (A1-A2) ; estimée", "Espagne": "incluse (A6) ; estimée, identification échouée (A8)", "Suède": "exclue, critère 1 (A3)",
               "Brésil": "inclus (A5) ; estimé (H3a non estimé, API IBGE)", "Colombie": "incluse (A4) ; estimée"}
    rows = [[esc(c.strip()), "1", esc(verdict.get(c.strip().replace(" (conditionnel)", ""), ""))] for c in lvl1]
    rows += [[esc(c.strip()), "2", "non vérifié fichiers en main (hors périmètre de cette version)"] for c in lvl2]
    rows += [[esc(c.strip(" .")), "3", "descriptif seulement"] for c in lvl3]
    longtab("tab_countries.tex", ["Pays", "Niveau (Étape 0)", "Statut (préregistration §4.3, addenda)"], rows,
            "Pays examinés et statut", "tab:countries",
            "Source : docs/etape0\\_pays.md (classement du 18/09/2026, par recherche web) ; verdicts fichiers en main dans docs/data\\_log.md et docs/preregistration\\_addenda.md. "
            "Niveau 1 = réplication causale, 2 = possible sous conditions, 3 = descriptif.", r"lcp{7.5cm}", note_width="12.2cm")


def tab_meta() -> None:
    p = TABLES / "t_meta.csv"
    if not p.exists():
        return
    raw = p.read_text(encoding="utf-8").split("\n")
    # deux tableaux concaténés dans le csv : estimations nationales puis poolées (séparés par la ligne d'en-tête « groupe,pays,… »)
    idx = next(i for i, l in enumerate(raw) if l.startswith("groupe,"))
    import io
    nat = pd.read_csv(io.StringIO("\n".join(raw[:idx])))
    pooled = pd.read_csv(io.StringIO("\n".join(raw[idx:])))
    rows = []
    for _, r in nat.iterrows():
        rows.append([esc(r.pays), esc(r.groupe), f"{r.att_pct:+.2f}", f"{r.se_pct:.2f}", str(int(r.k)) if pd.notna(r.k) else "", f"{r.p:.3f}", f"{r.p_pre:.3f}" if pd.notna(r.p_pre) else ""])
    t7.write("tab_meta_national.tex", ["Pays", "Groupe", "ATT (%)", "É.-t. (%)", "k", "p", "p pré-test"], rows,
             "Estimations nationales entrant dans la synthèse (ATT[1,k] primaires, en \\% du taux contrefactuel)", "tab:meta_national",
             "Source : scripts/18\\_meta.py (règles A7). ATT = 100 (exp(ATT log) $-$ 1) ; écart-type delta.", align="llrrrrr")
    rows = []
    for _, r in pooled.iterrows():
        rows.append([esc(r.groupe), esc(r.variante), esc(r.pays), f"{r['poolé %']:+.2f}", f"[{r['IC bas']:+.2f}, {r['IC haut']:+.2f}]", f"{r.p:.3f}",
                     f"[{r['PI bas']:+.2f}, {r['PI haut']:+.2f}]", f"{100 * r.I2:.0f}"])
    t7.write("tab_meta.tex", ["Groupe", "Variante", "Pays", "Poolé (%)", "IC 95 %", "p", "Intervalle de prédiction", "I$^2$ (%)"], rows,
             "Synthèse entre pays : estimations poolées (effets aléatoires, REML)", "tab:meta",
             "Source : scripts/18\\_meta.py. Primaire = tous les pays inclus, écarts-types analytiques ; « es bootstrap » = écarts-types du bootstrap par grappes ; "
             "« sans pays au pré-test rejeté » = sensibilité exploratoire (A7), hors règle de décision.", align="p{1.4cm}p{2.4cm}p{2.6cm}rp{2.3cm}rp{2.3cm}r")


def tab_design() -> None:
    rows = []
    spec = {"France (département)": ("t_sample_fr.csv", "H2b département 25-39", "département × âge", "D3 : part de la population couverte en 4G $\\geq$ 50 \\% (ARCEP/ANFR)", "1998-2024"),
            "France (commune)": ("t_sample_fr.csv", "H1 commune 15-44", "commune", "D1 : premier émetteur 4G en service (ANFR)", "2008-2024"),
            "Colombie": ("t_sample_co.csv", "H1 municipio 15-49", "municipio × âge", "part de population couverte en 4G $\\geq$ 50 \\% (MinTIC), censure 2015-T4", "1998-2024"),
            "Brésil": ("t_sample_br.csv", "H1 município 15-49", "município × âge", "présence 4G d'au moins un opérateur (Anatel)", "2003-2024"),
            "Espagne": ("t_sample_es.csv", "H1 municipio 15-49", "municipio ($>$ 10 000 hab.) × âge", "part de population couverte en LTE $\\geq$ 50 \\% (MINECO)", "2007-2022")}
    for name, (f, row, unit, treat, win) in spec.items():
        p = TABLES / f
        if not p.exists():
            continue
        d = pd.read_csv(p)
        r = d[d["spécification"].str.startswith(row.split(" ")[0]) & d["spécification"].str.contains(row.split(" ", 1)[1].split(" ")[0])]
        r = r.iloc[0] if len(r) else None
        if r is None:
            continue
        rows.append([esc(name), unit, treat, esc(win), f"{int(r['unités']):,}".replace(",", "\\,"), esc(str(r["cohortes"])), f"{int(r['jamais traitées']):,}".replace(",", "\\,")])
    t7.write("tab_design.tex", ["Pays", "Unité", "Traitement", "Fenêtre", "Unités", "Cohortes", "Jamais traitées"], rows,
             "Dessin par pays : unité, traitement, fenêtre et échantillon de la spécification H1", "tab:design",
             "Source : tables/t\\_sample\\_*.csv (scripts 04, 11, 15) ; addenda A1-A6.", align="lp{2.6cm}p{4.6cm}lrlr")


def tab_dictionary() -> None:
    rows = [
        ("cohort", "année de bascule de l'unité (0 = jamais sur la fenêtre)", "02, 09, 13, 16"),
        ("y\\_log", "log(naissances + 0,5 pour 1 000 femmes du groupe d'âge) ; France : log(naissances pour 1 000 femmes) au département", "03, 10, 14, 17"),
        ("y\\_rate, y\\_asinh", "taux brut pour 1 000 femmes ; asinh du taux", "05, 11, 15"),
        ("y\\_marr", "log(mariages de femmes + 0,5 pour 1 000 femmes du groupe)", "03, 14, 17"),
        ("y\\_union, y\\_married", "log(naissances de mères en union (Colombie) ou mariées (Espagne) + 0,5 pour 1 000 femmes)", "10, 17"),
        ("y\\_rank1, y\\_rank2", "idem pour les naissances de rang 1 et de rang 2 et plus", "10, 17"),
        ("women", "femmes du groupe d'âge : RP/estimations INSEE (France), projections DANE (Colombie), interpolation entre recensements IBGE (Brésil), Padrón au 1er janvier (Espagne)", "03, 10, 14, 17"),
        ("covariables", "France : 5 covariables de pré-période (A2) ; Colombie : part cabecera, log population, part de mères diplômées, tendance 2010-2014 ; Brésil : log population 2010, part des femmes 15-49, niveau et tendance 2008-2013 ; Espagne : log population 2013, part des femmes 15-49, part de mères nées à l'étranger 2010-2012, tendance 2008-2012", "05, 11, 15"),
        ("ATT[1,k]", "moyenne des effets +1 à +k (k = dernière période identifiée $\\leq$ 5), covariance complète des coefficients", "common/did.py"),
        ("post\\_avg\\_balanced", "même agrégat à composition constante (cohortes observées jusqu'à +k)", "common/did.py"),
        ("pre\\_test", "test de Wald joint des coefficients $-8$ à $-2$ (covariance des fonctions d'influence)", "common/did.py"),
        ("p\\_holm", "p corrigée de Holm dans la famille indiquée", "05, 11, 15"),
    ]
    t7.write("tab_dictionary.tex", ["Variable", "Définition", "Script"], [[rf"\texttt{{{a}}}", b, c] for a, b, c in rows],
             "Dictionnaire des variables", "tab:dictionary", "Les définitions complètes sont dans les en-têtes des scripts cités et dans docs/preregistration\\_addenda.md.", align="lp{9.5cm}l")


def tab_status() -> None:
    t = pd.read_csv(TABLES / "t_status.csv")
    s = pd.read_csv(TABLES / "t_status_pooled.csv")
    rows = []
    for _, r in t.iterrows():
        share = r["part expliquée par l'ATT du pays %"]
        rows.append([esc(r.pays), f"{int(r['année lancement'])}-{int(r['dernière année'])}", f"{r['taux 25-39 lancement']:.1f}", f"{r['taux 25-39 dernière']:.1f}",
                     f"{r['variation observée %']:+.1f}", f"{r['ATT pays %']:+.2f}", "" if share != share else f"{share:+.0f}"])
    rows.append([r"\midrule \emph{Effet poolé 25-39}", "", "", "", "", "", ""])
    for _, r in s.iterrows():
        rows.append([esc(r.variante), "", "", "", f"{r['baisse observée moyenne %']:+.1f}", f"{r['poolé %']:+.2f} {esc(r['IC 95 %'])}", f"{r['part expliquée %']:+.0f} {esc(r['part expliquée, IC 95 %'])} : {esc(r['statut (§6, A9)'])}"])
    t7.write("tab_status.tex", ["Pays / variante", "Années", "Taux au lancement", "Taux dernière année", "Variation (%)", "ATT (%)", "Part expliquée (%)"], rows,
             "Statut du smartphone comme facteur de la baisse du taux de naissances des 25-39 ans (préregistration §6, addendum A9)", "tab:status",
             "Source : scripts/23\\_status.py. Taux = naissances des 25-39 ans pour 1\\,000 femmes de 25-39 ans, agrégé sur les unités du panel ; variation entre la première cohorte "
             "de H2b et la dernière année du panel ; moyenne pondérée par les naissances à l'année de lancement. Part expliquée = ATT / variation observée (définie seulement si la variation est négative). "
             "Règle : premier ordre $\\geq$ 25 \\%, second ordre 5-25 \\%, négligeable $<$ 5 \\% ou non détecté avec puissance suffisante (A9), indéterminé sinon.",
             align="p{2.9cm}lrrrp{2.3cm}p{3.2cm}")


def main() -> int:
    tab_sources()
    tab_countries()
    tab_meta()
    tab_design()
    tab_dictionary()
    tab_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
