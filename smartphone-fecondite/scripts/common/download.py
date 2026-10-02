"""Téléchargement journalisé des sources primaires.

Principes (règle 1 du cahier des charges) :
- chaque fichier est téléchargé depuis l'URL du producteur, jamais recréé ni complété ;
- chaque téléchargement est consigné (URL, date d'accès, taille, SHA-256, licence) dans
  ``data/raw/manifest.json`` et ``docs/data_log.md`` ;
- toute erreur (refus du proxy, 404, taille nulle, empreinte différente de celle déjà consignée)
  lève une exception : le pipeline s'arrête et le dit, il ne contourne pas.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

import requests

from .sources import Source

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "manifest.json"
DATA_LOG = ROOT / "docs" / "data_log.md"
UA = "smartphone-fecondite-wp/0.1 (recherche reproductible ; contact via le dépôt GitHub)"
BACKOFF = (2, 4, 8, 16)


class DownloadBlocked(RuntimeError):
    """Refus réseau ou ressource introuvable : on s'arrête, on ne comble pas."""


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    ca = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    if ca:
        s.verify = ca
    return s


def _get(url: str, stream: bool = False, timeout: int = 120) -> requests.Response:
    """GET avec 4 reprises (2, 4, 8, 16 s) sur erreur réseau. Un 403/407 du proxy n'est pas repris."""
    last: Exception | None = None
    for i, wait in enumerate((0,) + BACKOFF):
        if wait:
            time.sleep(wait)
        try:
            r = _session().get(url, stream=stream, timeout=timeout, allow_redirects=True)
        except requests.exceptions.ProxyError as e:
            raise DownloadBlocked(f"Proxy : accès refusé à {urlparse(url).netloc} ({e})") from e
        except requests.exceptions.RequestException as e:
            last = e
            continue
        if r.status_code in (403, 407):
            raise DownloadBlocked(f"HTTP {r.status_code} pour {url} (politique réseau ou accès refusé)")
        if r.status_code == 404:
            raise DownloadBlocked(f"HTTP 404 : ressource introuvable {url} — URL à corriger dans sources.py")
        if r.status_code >= 500:
            last = RuntimeError(f"HTTP {r.status_code}")
            continue
        r.raise_for_status()
        return r
    raise DownloadBlocked(f"Échec réseau après {len(BACKOFF) + 1} tentatives pour {url} : {last}")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}


def _save_manifest(m: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _append_log(src: Source, url: str, path: Path, sha: str, size: int, status: str) -> None:
    DATA_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_LOG.exists():
        DATA_LOG.write_text(
            "# Journal des données\n\n"
            "Une ligne par fichier téléchargé, écrite automatiquement par `scripts/01_download.py`.\n"
            "Colonnes : identifiant de source, pays, rôle, URL exacte, date d'accès (UTC), taille, SHA-256, licence, statut.\n"
            "Les trous, limites et décisions de mesure par source sont documentés sous le tableau, à la main.\n\n"
            "| source | pays | rôle | URL | accès (UTC) | octets | SHA-256 | licence | statut |\n"
            "|---|---|---|---|---|---|---|---|---|\n",
            encoding="utf-8",
        )
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    with open(DATA_LOG, "a", encoding="utf-8") as f:
        f.write(f"| {src.id} | {src.country} | {src.role} | {url} | {now} | {size} | `{sha[:16]}…` | {src.license} | {status} |\n")


def _filename_from(url: str, r: requests.Response) -> str:
    cd = r.headers.get("content-disposition", "")
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd)
    name = unquote(m.group(1)) if m else Path(urlparse(url).path).name
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name) or "download.bin"


def fetch(src: Source, url: str, subdir: str | None = None, filename: str | None = None) -> Path:
    """Télécharge ``url`` dans data/raw/<pays>/<source>/, journalise, renvoie le chemin.

    Si le fichier est déjà présent avec la même URL dans le manifeste, il n'est pas retéléchargé
    (reproductibilité : on garde la version consignée). Une empreinte différente d'un fichier déjà
    consigné pour la même URL est signalée comme erreur : la source a changé, il faut le documenter.
    """
    dest_dir = RAW / src.country / (subdir or src.id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest()
    key = f"{src.id}::{url}"
    if key in manifest and (RAW / manifest[key]["path"]).exists():
        return RAW / manifest[key]["path"]

    r = _get(url, stream=True)
    name = filename or _filename_from(url, r)
    dest = dest_dir / name
    tmp = dest.with_suffix(dest.suffix + ".part")
    size = 0
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            if chunk:
                f.write(chunk)
                size += len(chunk)
    if size == 0:
        tmp.unlink(missing_ok=True)
        raise DownloadBlocked(f"Fichier vide reçu pour {url}")
    tmp.rename(dest)
    sha = sha256_of(dest)
    manifest[key] = {
        "source": src.id, "url": url, "path": str(dest.relative_to(RAW)), "bytes": size,
        "sha256": sha, "accessed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "license": src.license, "title": src.title,
    }
    _save_manifest(manifest)
    _append_log(src, url, dest, sha, size, "ok")
    return dest


# ---------------------------------------------------------------------------- résolution des URL

def _datagouv_resources(slug: str) -> list[dict]:
    r = _get(f"https://www.data.gouv.fr/api/1/datasets/{slug}/")
    return r.json().get("resources", [])


def _insee_file_links(page_url: str) -> list[str]:
    r = _get(page_url)
    links = re.findall(r'href="(/fr/statistiques/fichier/\d+/[^"]+)"', r.text)
    return sorted({urljoin("https://www.insee.fr", unquote(l)) for l in links})


def _insee_result_pages(search_url: str) -> list[str]:
    r = _get(search_url)
    pages = re.findall(r'href="(/fr/statistiques/\d+)(?:\?sommaire=\d+)?"', r.text)
    return sorted({urljoin("https://www.insee.fr", p) for p in pages})


def _keep(name: str, src: Source) -> bool:
    if src.include and not any(re.search(p, name) for p in src.include):
        return False
    if src.exclude and any(re.search(p, name) for p in src.exclude):
        return False
    return True


def resolve(src: Source) -> list[str]:
    """Renvoie la liste des URL de fichiers à télécharger pour une source."""
    if src.resolver == "direct":
        return [src.ref]
    if src.resolver == "datagouv":
        urls = [res["url"] for res in _datagouv_resources(src.ref) if res.get("url")]
        urls = [u for u in urls if _keep(Path(urlparse(u).path).name, src)]
        if not urls:
            raise DownloadBlocked(f"{src.id} : aucune ressource retenue pour le jeu data.gouv « {src.ref} »")
        return urls
    if src.resolver == "insee_page":
        pages = [src.ref]
        if "statistiques?" in src.ref:                      # page de recherche → pages de résultats
            pages = _insee_result_pages(src.ref)
        urls: list[str] = []
        for p in pages:
            urls += [u for u in _insee_file_links(p) if _keep(Path(urlparse(u).path).name, src)]
        if not urls:
            raise DownloadBlocked(f"{src.id} : aucun lien de fichier trouvé sur {src.ref}")
        return sorted(set(urls))
    if src.resolver == "eurostat_tsv":
        return [f"https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{src.ref}?format=TSV&compressed=true"]
    if src.resolver == "worldbank":
        return [f"https://api.worldbank.org/v2/country/all/indicator/{src.ref}?format=json&per_page=20000&date=1960:2025"]
    if src.resolver == "owid":
        return [f"https://ourworldindata.org/grapher/{src.ref}.csv?v=1&csvType=full&useColumnShortNames=true"]
    if src.resolver == "socrata":
        return [f"https://www.datos.gov.co/resource/{src.ref}.csv?$limit=5000000"]
    raise DownloadBlocked(
        f"{src.id} : résolution « {src.resolver} » non automatisée ({src.ref}). "
        "Écrire le résolveur ou documenter la raison dans data_log.md avant de continuer."
    )


def download_source(src: Source, verbose: bool = True) -> list[Path]:
    paths = []
    for url in resolve(src):
        if verbose:
            print(f"  ↓ {url}")
        paths.append(fetch(src, url))
    return paths


def describe(src: Source) -> dict:
    return asdict(src)
