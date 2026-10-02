#!/usr/bin/env python
"""Étape 2a — téléchargement des données brutes depuis les sources primaires.

Usage :
    python scripts/01_download.py --country FR            # toutes les sources France
    python scripts/01_download.py --ids fr_anfr_observatoire eu_demo_r_frate2
    python scripts/01_download.py --all
    python scripts/01_download.py --list                  # affiche le registre sans rien télécharger
    python scripts/01_download.py --check                 # teste la joignabilité des hôtes, sans télécharger
    python scripts/01_download.py --country FR --resolve  # affiche les URL résolues, sans télécharger

Le script s'arrête à la première erreur (refus réseau, 404, fichier vide) et l'affiche. Il ne
remplace jamais un fichier manquant par autre chose (règle 1).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common.sources import SOURCES, select  # noqa: E402
from common.download import DownloadBlocked, download_source, resolve, rebuild_data_log, _get  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--country")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--roles", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--log", action="store_true", help="régénère docs/data_log.md depuis le manifeste")
    ap.add_argument("--skip", nargs="*", default=[], help="identifiants à sauter")
    a = ap.parse_args()

    if a.log:
        rebuild_data_log()
        print("docs/data_log.md régénéré")
        return 0
    srcs = select(a.country, a.ids, a.roles) if (a.country or a.ids or a.roles) else (SOURCES if (a.all or a.list or a.check) else [])
    if not srcs:
        ap.print_help()
        return 2

    if a.list:
        for s in srcs:
            print(f"{s.id:38s} {s.country:5s} {s.role:11s} {s.resolver:12s} {s.title}")
        return 0

    if a.resolve:
        rc = 0
        for s in srcs:
            if s.id in a.skip:
                continue
            try:
                urls = resolve(s)
                print(f"[{s.id}] {len(urls)} fichier(s)")
                for u in urls:
                    print(f"    {u}")
            except DownloadBlocked as e:
                print(f"[{s.id}] ÉCHEC : {e}")
                rc = 1
        return rc

    if a.check:
        hosts = sorted({urlparse(s.ref).netloc for s in srcs if s.ref.startswith("http")}
                       | {"www.data.gouv.fr", "www.insee.fr", "ec.europa.eu", "api.worldbank.org", "ourworldindata.org", "www.datos.gov.co"})
        blocked = []
        for h in hosts:
            try:
                _get(f"https://{h}/", timeout=20)
                print(f"ok       {h}")
            except DownloadBlocked as e:
                print(f"BLOQUÉ   {h}  ({str(e)[:80]})")
                blocked.append(h)
            except Exception as e:  # noqa: BLE001
                print(f"erreur   {h}  ({type(e).__name__})")
                blocked.append(h)
        if blocked:
            print(f"\n{len(blocked)} hôte(s) injoignable(s). Rien n'a été téléchargé.")
            return 1
        return 0

    for s in srcs:
        if s.id in a.skip:
            continue
        print(f"[{s.id}] {s.title}")
        try:
            paths = download_source(s)
        except DownloadBlocked as e:
            print(f"\nARRÊT : {e}\nAucune valeur de remplacement n'est utilisée. Corriger l'accès ou la source, puis relancer.")
            return 1
        print(f"  {len(paths)} fichier(s) consigné(s) dans docs/data_log.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
