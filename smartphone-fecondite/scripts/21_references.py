#!/usr/bin/env python
"""Références du papier (règle 2 de la mission) : chaque entrée est vérifiée avant d'entrer dans paper/references.bib —
métadonnées lues dans le registre DOI (API Crossref) et page éditeur consultée quand le proxy la laisse passer. Le journal de
vérification est écrit dans docs/references_check.md ; une référence dont les métadonnées Crossref ne correspondent pas à la
citation attendue (auteur, année) est écartée et signalée.

Usage : python scripts/21_references.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
UA = "smartphone-fecondite-wp/0.2 (recherche reproductible ; contact via le depot GitHub)"
# clé bib, DOI, (premier auteur attendu, année attendue), rôle dans le papier
REFS = [
    ("billari2019", "10.1080/00324728.2019.1584327", ("Billari", 2019), "positionnement : haut débit fixe et fécondité des 25-45 ans (Allemagne)"),
    ("guldi2017", "10.1007/s00148-016-0605-0", ("Guldi", 2016), "positionnement : haut débit fixe et fécondité adolescente (États-Unis)"),
    ("bellou2015", "10.1007/s00148-014-0527-7", ("Bellou", 2014), "positionnement : haut débit fixe et mariages (États-Unis)"),
    ("rosenfeld2019", "10.1073/pnas.1908630116", ("Rosenfeld", 2019), "positionnement : la rencontre en ligne devient le premier mode de rencontre"),
    ("potarca2020", "10.1371/journal.pone.0243733", ("Potarca", 2020), "positionnement : couples formés via applications (Suisse)"),
    ("myers2026", "10.3386/w35310", ("Myers", 2025), "positionnement : smartphone et fécondité des 15-24 ans (États-Unis, NBER)"),
    ("ershov2026", "10.3386/w34757", ("Ershov", 2026), "positionnement : rencontre en ligne et marchés matrimoniaux (États-Unis, NBER)"),
    ("hudson2026", "10.2139/ssrn.6676839", ("Hudson", 2026), "positionnement : fécondité adolescente et ère numérique (SSRN)"),
    ("si2025", "10.1016/j.asieco.2025.101962", ("Si", 2025), "positionnement : haut débit et décisions de fécondité (Chine)"),
    ("jung2026", "10.1016/j.econlet.2026.112873", ("Jung", 2026), "positionnement : applications de rencontre et taux de mariage"),
    ("liu2026", "10.2139/ssrn.6257058", ("Liu", 2026), "positionnement : Internet mobile et fécondité en Afrique subsaharienne (SSRN)"),
    ("churchill2026", "10.3386/w34614", ("Churchill", 2026), "mécanismes : haut débit et santé mentale des adolescents (NBER)"),
    ("callaway2021", "10.1016/j.jeconom.2020.12.001", ("Callaway", 2021), "méthode : estimateur primaire"),
    ("sun2021", "10.1016/j.jeconom.2020.09.006", ("Sun", 2021), "méthode : comparaison"),
    ("gardner2022", "10.48550/arXiv.2207.05943", ("Gardner", 2022), "méthode : comparaison (did2s)"),
    ("dechaisemartin2020", "10.1257/aer.20181169", ("de Chaisemartin", 2020), "méthode : biais du TWFE"),
    ("roth2023", "10.1016/j.jeconom.2023.03.008", ("Roth", 2023), "méthode : synthèse des estimateurs échelonnés"),
]


def crossref(doi: str) -> dict | None:
    """Registre Crossref ; les DOI arXiv (10.48550) sont enregistrés chez DataCite : lecture au même format minimal."""
    for _ in range(3):
        r = requests.get(f"https://api.crossref.org/works/{doi}", headers={"User-Agent": UA}, timeout=60)
        if r.status_code == 200:
            return r.json()["message"]
        if r.status_code != 404:
            time.sleep(3)
            continue
        break
    if doi.lower().startswith("10.48550/"):
        r = requests.get(f"https://api.datacite.org/dois/{doi}", headers={"User-Agent": UA}, timeout=60)
        if r.status_code != 200:
            return None
        a = r.json()["data"]["attributes"]
        return {"DOI": doi, "type": "posted-content", "title": [t["title"] for t in a.get("titles", [])][:1] or [""],
                "author": [{"family": c.get("familyName", c.get("name", "")), "given": c.get("givenName", "")} for c in a.get("creators", [])],
                "issued": {"date-parts": [[a.get("publicationYear")]]}, "publisher": a.get("publisher", "arXiv"),
                "resource": {"primary": {"URL": a.get("url", f"https://arxiv.org/abs/{doi.split('arXiv.')[-1]}")}}}
    return None


def probe(url: str) -> int:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=40, allow_redirects=True, stream=True)
        return r.status_code
    except requests.RequestException:
        return 0


def tex(s: str) -> str:
    return s.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("#", r"\#")


def entry(key: str, m: dict) -> str:
    authors = " and ".join(f"{a.get('family', '')}, {a.get('given', '')}".strip(", ") for a in m.get("author", []))
    year = (m.get("issued") or {}).get("date-parts", [[None]])[0][0] or (m.get("published-print") or {}).get("date-parts", [[None]])[0][0]
    title = tex(re.sub(r"\s+", " ", m["title"][0]).strip())
    container = tex(m["container-title"][0]) if m.get("container-title") else ""
    typ = m.get("type", "")
    fields = [f"  author = {{{tex(authors)}}}", f"  title = {{{{{title}}}}}", f"  year = {{{year}}}", f"  doi = {{{m['DOI']}}}"]
    if typ == "journal-article":
        kind = "article"
        fields.append(f"  journal = {{{container}}}")
        for k in ("volume", "issue", "page"):
            if m.get(k):
                fields.append(f"  {'number' if k == 'issue' else 'pages' if k == 'page' else k} = {{{m[k]}}}")
    elif typ in ("report", "posted-content"):
        kind = "techreport" if typ == "report" else "unpublished"
        inst = tex(m.get("institution", [{}])[0].get("name", "")) if m.get("institution") else tex((m.get("publisher") or ""))
        if m["DOI"].startswith("10.3386/"):
            fields.append(f"  institution = {{National Bureau of Economic Research}}")
            fields.append(f"  number = {{Working Paper {m['DOI'].split('/w')[-1]}}}")
        elif m["DOI"].startswith("10.2139/"):
            fields.append("  note = {SSRN, document de travail}")
        elif m["DOI"].startswith("10.48550/"):
            fields.append("  note = {arXiv, document de travail}")
        elif inst:
            fields.append(f"  institution = {{{inst}}}")
    else:
        kind = "misc"
        if container:
            fields.append(f"  howpublished = {{{container}}}")
    return f"@{kind}{{{key},\n" + ",\n".join(fields) + "\n}\n"


def main() -> int:
    bib, log = [], ["# Vérification des références (généré par scripts/21_references.py)", "",
                    f"Date : {time.strftime('%Y-%m-%d')}. Chaque DOI est lu dans le registre Crossref (titre, auteurs, revue, année) et comparé à la citation "
                    "attendue ; la page éditeur est ensuite consultée (code HTTP ; 403 = refus du proxy, la référence reste vérifiée par le registre DOI). "
                    "Une référence absente du registre ou ne correspondant pas est écartée.", "",
                    "| clé | DOI | registre DOI | premier auteur / année | revue ou série | page éditeur (HTTP) | rôle | verdict |", "|---|---|---|---|---|---|---|---|"]
    for key, doi, (fam, year), role in REFS:
        m = crossref(doi)
        if not m:
            log.append(f"| {key} | {doi} | **absent** | | | | {role} | écartée |")
            continue
        got_fam = (m.get("author") or [{}])[0].get("family", "")
        got_year = (m.get("issued") or {}).get("date-parts", [[None]])[0][0]
        ok = fam.split()[-1].lower() in got_fam.lower() and got_year is not None and abs(int(got_year) - year) <= 1
        url = (m.get("resource") or {}).get("primary", {}).get("URL") or f"https://doi.org/{doi}"
        code = probe(url)
        container = (m.get("container-title") or [m.get("publisher", "")])[0]
        verdict = "retenue" if ok else "écartée (métadonnées ≠ citation)"
        log.append(f"| {key} | {doi} | oui | {got_fam} / {got_year} | {container} | {code} ({url.split('/')[2]}) | {role} | {verdict} |")
        print(f"{key:20s} {doi:36s} {got_fam:16s} {got_year} {container[:40]:40s} HTTP {code} → {verdict}")
        if ok:
            bib.append(entry(key, m))
        time.sleep(1)
    (ROOT / "paper" / "references.bib").write_text("% Généré par scripts/21_references.py — ne pas éditer à la main (journal : docs/references_check.md).\n\n" + "\n".join(bib), encoding="utf-8")
    (ROOT / "docs" / "references_check.md").write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"{len(bib)} références retenues sur {len(REFS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
