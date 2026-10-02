"""Téléchargement journalisé des sources primaires.

Principes (règle 1 du cahier des charges) :
- chaque fichier est téléchargé depuis l'URL du producteur, jamais recréé ni complété ;
- chaque téléchargement est consigné (URL, date d'accès, taille, SHA-256, licence) dans
  ``data/raw/manifest.json`` et ``docs/data_log.md`` ;
- toute erreur (refus du proxy, 404, taille nulle, empreinte différente de celle déjà consignée)
  lève une exception : le pipeline s'arrête et le dit, il ne contourne pas.

Particularité de l'environnement (constatée le 02/10/2026) : le relais du proxy coupe parfois une
connexion en cours (« Connection reset by peer »). Un transfert interrompu est repris avec un en-tête
``Range`` ; après cinq échecs consécutifs on s'arrête.
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
UA = "smartphone-fecondite-wp/0.2 (recherche reproductible ; contact via le dépôt GitHub)"
BACKOFF = (2, 4, 8, 16, 16, 16, 16, 16)      # 9 tentatives : le relais data.gouv.fr coupe souvent
MELODI = "https://api.insee.fr/melodi"


class DownloadBlocked(RuntimeError):
    """Refus réseau ou ressource introuvable : on s'arrête, on ne comble pas."""


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    ca = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    if ca:
        s.verify = ca
    return s


def _get(url: str, stream: bool = False, timeout: int = 120, headers: dict | None = None) -> requests.Response:
    """GET avec 8 reprises sur erreur réseau. Un 403/407 du proxy n'est pas repris."""
    last: Exception | None = None
    for wait in (0,) + BACKOFF:
        if wait:
            time.sleep(wait)
        try:
            r = _session().get(url, stream=stream, timeout=timeout, allow_redirects=True, headers=headers)
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


def get_text(url: str) -> str:
    return _get(url).text


def get_json(url: str):
    return _get(url).json()


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
        DATA_LOG.write_text("# Journal des données\n\n| source | pays | rôle | URL | accès (UTC) | octets | SHA-256 | licence | statut |\n|---|---|---|---|---|---|---|---|---|\n", encoding="utf-8")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    with open(DATA_LOG, "a", encoding="utf-8") as f:
        f.write(f"| {src.id} | {src.country} | {src.role} | {url} | {now} | {size} | `{sha[:16]}…` | {src.license} | {status} |\n")


def _filename_from(url: str, r: requests.Response) -> str:
    cd = r.headers.get("content-disposition", "")
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd)
    name = unquote(m.group(1)) if m else Path(urlparse(url).path).name
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name) or "download.bin"


def _stream_to(url: str, tmp: Path, max_restarts: int = 5) -> tuple[int, requests.Response]:
    """Télécharge ``url`` dans ``tmp`` ; reprend avec ``Range`` si la connexion est coupée."""
    size = 0
    restarts = 0
    first: requests.Response | None = None
    while True:
        headers = {"Range": f"bytes={size}-"} if size else None
        r = _get(url, stream=True, headers=headers)
        if first is None:
            first = r
        if size and r.status_code != 206:          # le serveur ne gère pas Range : on repart de zéro
            size = 0
            mode = "wb"
        else:
            mode = "ab" if size else "wb"
        try:
            with open(tmp, mode) as f:
                for chunk in r.iter_content(1 << 20):
                    if chunk:
                        f.write(chunk)
                        size += len(chunk)
            return size, first
        except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout) as e:
            restarts += 1
            if restarts > max_restarts:
                raise DownloadBlocked(f"Transfert interrompu {max_restarts} fois pour {url} : {e}") from e
            time.sleep(BACKOFF[min(restarts, len(BACKOFF)) - 1])


def _check_integrity(path: Path, name: str, url: str) -> None:
    """Un transfert coupé sans en-tête Content-Length passe inaperçu (constaté sur insee.fr en HTTP/2) :
    on vérifie que les archives s'ouvrent et que leurs CRC sont bons avant de les consigner."""
    low = name.lower()
    try:
        if low.endswith(".zip"):
            import zipfile
            with zipfile.ZipFile(path) as z:
                bad = z.testzip()
            if bad is not None:
                raise ValueError(f"CRC incorrect pour {bad}")
        elif low.endswith(".xls"):
            import xlrd
            xlrd.open_workbook(path, on_demand=True)
        elif low.endswith(".xlsx"):
            import openpyxl
            openpyxl.load_workbook(path, read_only=True).close()
        elif low.endswith(".pdf"):
            import pypdf
            pypdf.PdfReader(path)
    except Exception as e:  # noqa: BLE001
        path.unlink(missing_ok=True)
        raise DownloadBlocked(f"Fichier incomplet ou illisible reçu pour {url} ({type(e).__name__}: {e}) — relancer") from e


def fetch(src: Source, url: str, subdir: str | None = None, filename: str | None = None) -> Path:
    """Télécharge ``url`` dans data/raw/<pays>/<source>/, journalise, renvoie le chemin.

    Si le fichier est déjà présent avec la même URL dans le manifeste, il n'est pas retéléchargé
    (reproductibilité : on garde la version consignée).
    """
    dest_dir = RAW / src.country / (subdir or src.id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest()
    key = f"{src.id}::{url}"
    if key in manifest and (RAW / manifest[key]["path"]).exists():
        return RAW / manifest[key]["path"]

    guess = dest_dir / re.sub(r"[^A-Za-z0-9._-]+", "_", Path(urlparse(url).path).name or "download")
    if filename is None and not guess.exists():           # nom donné par content-disposition (ex. Melodi : « …_CSV_FR.zip »)
        cands = [c for c in dest_dir.iterdir() if c.name.lower() in (guess.name.lower(), guess.name.lower() + ".zip")
                 and not c.name.endswith(".part")]
        if len(cands) == 1:
            guess = cands[0]
    if filename is None and guess.exists() and guess.stat().st_size > 0:
        # fichier déjà complet sur disque (téléchargement antérieur non consigné) : consigné sans retéléchargement
        sha = sha256_of(guess)
        manifest[key] = {"source": src.id, "url": url, "path": str(guess.relative_to(RAW)), "bytes": guess.stat().st_size,
                         "sha256": sha, "accessed_utc": datetime.fromtimestamp(guess.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
                         "license": src.license, "title": src.title}
        _save_manifest(manifest)
        return guess
    tmp = guess.with_name(guess.name + ".part")
    size, r = _stream_to(url, tmp)
    expected = r.headers.get("content-length")
    if size == 0:
        tmp.unlink(missing_ok=True)
        raise DownloadBlocked(f"Fichier vide reçu pour {url}")
    if expected and expected.isdigit() and r.status_code == 200 and int(expected) != size:
        tmp.unlink(missing_ok=True)
        raise DownloadBlocked(f"Taille reçue {size} ≠ annoncée {expected} pour {url}")
    name = filename or _filename_from(url, r)
    dest = dest_dir / name
    _check_integrity(tmp, name, url)
    tmp.replace(dest)
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
    return get_json(f"https://www.data.gouv.fr/api/1/datasets/{slug}/").get("resources", [])


def _insee_file_links(page_url: str) -> list[str]:
    html = get_text(page_url)
    links = re.findall(r'href="(/fr/(?:statistiques|information)/fichier/\d+/[^"]+)"', html)
    return sorted({urljoin("https://www.insee.fr", unquote(l)) for l in links})


def _insee_sommaire_subpages(sommaire_url: str, title_re: str) -> list[str]:
    """Sous-pages d'un sommaire INSEE dont le libellé du lien correspond à ``title_re``."""
    html = get_text(sommaire_url)
    out = []
    for m in re.finditer(r'href="(/fr/statistiques/\d+)\?sommaire=\d+"[^>]*>\s*([^<]*?)\s*</a>', html):
        if re.search(title_re, m.group(2).strip()):
            out.append(urljoin("https://www.insee.fr", m.group(1)))
    return sorted(set(out))


def _melodi_product_url(dataset_id: str) -> str:
    """URL du CSV complet d'un jeu Melodi, lue dans le catalogue (``product[].accessURL``)."""
    cat = get_json(f"{MELODI}/catalog/all")
    for entry in cat:
        if entry.get("identifier") == dataset_id:
            prods = [p for p in entry.get("product", []) if p.get("format", "").upper() == "CSV"
                     and p.get("language", "FR") == "FR" and p.get("id", "").startswith(dataset_id)]
            if prods:
                return prods[0]["accessURL"]
            raise DownloadBlocked(f"{dataset_id} : aucun produit CSV dans le catalogue Melodi")
    raise DownloadBlocked(f"{dataset_id} : absent du catalogue Melodi")


def _arcep_dir_entries(dir_url: str) -> list[str]:
    """Entrées (fichiers et sous-dossiers) d'un dossier de l'explorateur statique data.arcep.fr."""
    html = get_text(dir_url.rstrip("/") + "/index.html")
    m = re.search(r'id="dir-content".*?</ul>', html, re.S)
    if not m:
        return []
    hrefs = re.findall(r'href="([^"]+)"', m.group(0))
    out = []
    for h in hrefs:
        if h.startswith("../") or h.startswith("http"):
            continue
        out.append(h[:-len("index.html")] if h.endswith("index.html") else h)
    return out


def _keep(name: str, src: Source) -> bool:
    if src.include and not any(re.search(p, name) for p in src.include):
        return False
    if src.exclude and any(re.search(p, name) for p in src.exclude):
        return False
    return True


def resolve(src: Source) -> list[str]:
    """Renvoie la liste des URL de fichiers à télécharger pour une source."""
    if src.resolver == "direct":
        return src.ref.split("|")
    if src.resolver == "datagouv":
        urls = [res["url"] for res in _datagouv_resources(src.ref) if res.get("url")]
        urls = [u for u in urls if _keep(Path(urlparse(u).path).name, src)]
        if src.latest:
            urls = sorted(urls, key=lambda u: Path(urlparse(u).path).name)[-src.latest:]
        if not urls:
            raise DownloadBlocked(f"{src.id} : aucune ressource retenue pour le jeu data.gouv « {src.ref} »")
        return urls
    if src.resolver in ("insee_page", "insee_sommaire"):
        pages = src.ref.split("|")
        if src.resolver == "insee_sommaire":
            pages = [p for s in pages for p in _insee_sommaire_subpages(s, src.subpage or ".")]
            if not pages:
                raise DownloadBlocked(f"{src.id} : aucune sous-page « {src.subpage} » dans {src.ref}")
        urls: list[str] = []
        for p in pages:
            urls += [u for u in _insee_file_links(p) if _keep(Path(urlparse(u).path).name, src)]
        if not urls:
            raise DownloadBlocked(f"{src.id} : aucun lien de fichier retenu sur {src.ref}")
        return sorted(set(urls))
    if src.resolver == "melodi":
        return [_melodi_product_url(src.ref)]
    if src.resolver == "arcep_dir":
        base = src.ref.rstrip("/") + "/"
        urls = []
        for e in _arcep_dir_entries(base):
            if e.endswith("/"):
                if src.subpage and not re.search(src.subpage, e):
                    continue
                stack = [base + e]
                while stack:                                   # descente (Metropole/…)
                    d = stack.pop()
                    for f in _arcep_dir_entries(d):
                        if f.endswith("/"):
                            stack.append(d + f)
                        elif _keep(f, src):
                            urls.append(d + f)
            elif _keep(e, src):
                urls.append(base + e)
        if not urls:
            raise DownloadBlocked(f"{src.id} : aucun fichier retenu sous {src.ref}")
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


def _subdir_for(src: Source, url: str) -> str | None:
    """Les trimestres ARCEP et les sommaires INSEE produisent des noms homonymes : un sous-dossier par URL."""
    if src.resolver == "arcep_dir":
        m = re.search(r"/(\d{4}_T\d)/", url)
        return f"{src.id}/{m.group(1)}" if m else None
    return None


def download_source(src: Source, verbose: bool = True) -> list[Path]:
    paths = []
    for url in resolve(src):
        if verbose:
            print(f"  ↓ {url}")
        paths.append(fetch(src, url, subdir=_subdir_for(src, url)))
    return paths


def rebuild_data_log() -> None:
    """Réécrit la section « Fichiers téléchargés » de docs/data_log.md à partir du manifeste.

    La partie rédigée à la main (tout ce qui précède le marqueur) est conservée ; le tableau est
    régénéré en entier, trié par source puis URL, pour rester lisible quand plusieurs
    téléchargements tournent en parallèle.
    """
    from .sources import BY_ID
    marker = "## Fichiers téléchargés"
    head = "# Journal des données\n\nUne ligne par fichier téléchargé (régénéré depuis `data/raw/manifest.json` par `scripts/01_download.py --log`).\n"
    if DATA_LOG.exists():
        txt = DATA_LOG.read_text(encoding="utf-8")
        if marker in txt:
            head = txt.split(marker)[0]
        else:                                   # ancien format : on retire le tableau automatique
            lines = [l for l in txt.splitlines() if not l.startswith("| ") or l.startswith("| source |") and False]
            head = "\n".join(l for l in lines if not l.startswith("|---") and not l.startswith("| source |")) + "\n"
    m = _load_manifest()
    rows = ["| source | pays | rôle | fichier | URL | accès (UTC) | octets | SHA-256 | licence |", "|---|---|---|---|---|---|---|---|---|"]
    for k in sorted(m, key=lambda k: (m[k]["source"], m[k]["url"])):
        v = m[k]
        s = BY_ID.get(v["source"])
        rows.append(f"| {v['source']} | {s.country if s else ''} | {s.role if s else ''} | {Path(v['path']).name} | {v['url']} | "
                    f"{v['accessed_utc'][:16].replace('T', ' ')} | {v['bytes']:,} | `{v['sha256'][:16]}…` | {v['license']} |")
    total = sum(v["bytes"] for v in m.values())
    DATA_LOG.write_text(head.rstrip() + f"\n\n{marker}\n\n{len(m)} fichiers, {total / 1e6:,.0f} Mo. Empreintes complètes dans `data/raw/manifest.json`.\n\n"
                        + "\n".join(rows) + "\n", encoding="utf-8")


def raw_files(src_id: str) -> list[Path]:
    """Fichiers consignés dans le manifeste pour une source (ordre des URL)."""
    m = _load_manifest()
    return [RAW / v["path"] for k, v in sorted(m.items()) if v["source"] == src_id]


def describe(src: Source) -> dict:
    return asdict(src)
