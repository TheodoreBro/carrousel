#!/usr/bin/env python
"""Étape 2b — construction du traitement (France) à partir des fichiers bruts consignés.

Sorties (data/processed/) :
- ``fr_treatment_commune.parquet`` : unité harmonisée (COG courant) × année 2004-2026 avec
  D1 (4G_ct : ≥ 1 émetteur LTE en service au 1er janvier), cohorte 4G, cohorte 3G, nombre d'émetteurs LTE,
  nombre d'opérateurs 4G, cohortes de recoupement (observatoire courant seul, archives, sites ARCEP),
  ZDP, zones blanches, classe de densité, département ;
- ``fr_treatment_dep.parquet`` : département × année avec D3 (part des femmes de 15-44 ans résidant dans une
  commune avec D1 = 1, poids RP 2011 fixes) et les années de bascule à 50 % et 90 % ;
- ``tables/t_treatment_fr.md`` : distribution des cohortes, recodages, accords entre sources.

Décisions de mesure prises à la lecture des fichiers (liste fermée, préregistration §10), toutes
consignées dans ``docs/preregistration_addenda.md`` :
- dates LTE antérieures au 01/01/2012 (avant tout lancement commercial 4G) recodées au 30/06/2012 ;
  dates UMTS antérieures au 01/01/2004 recodées au 01/12/2004 ; comptées ci-dessous ;
- la date de référence d'un émetteur est ``emr_dt`` (observatoire) ou ``EMR_DT_SERVICE`` (archives) ;
  seules les lignes « En service » de l'observatoire sont utilisées ;
- cohorte D1 = première année t telle que la plus ancienne date LTE connue (observatoire courant ∪ archives
  annuelles 2018-2025) est ≤ 1er janvier t.
"""
from __future__ import annotations

import io
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common.download import raw_files, RAW  # noqa: E402
from common.geo import Cog  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "tables"
YEARS = list(range(2004, 2027))
LTE_FLOOR = pd.Timestamp("2012-01-01")
LTE_RECODE = pd.Timestamp("2012-06-30")
UMTS_FLOOR = pd.Timestamp("2004-01-01")
UMTS_RECODE = pd.Timestamp("2004-12-01")

notes: list[str] = []


def log(msg: str) -> None:
    print(msg)
    notes.append(msg)


def _one(src_id: str, pattern: str = ".") -> Path:
    files = [p for p in raw_files(src_id) if re.search(pattern, p.name)]
    if not files:
        raise FileNotFoundError(f"{src_id} : aucun fichier brut consigné (lancer 01_download.py)")
    return files[0]


# ----------------------------------------------------------------------------- observatoire ANFR

def load_observatoire(cog: Cog) -> pd.DataFrame:
    z = zipfile.ZipFile(_one("fr_anfr_observatoire"))
    name = [n for n in z.namelist() if n.endswith(".csv")][0]
    df = pd.read_csv(z.open(name), sep=";", dtype=str,
                     usecols=["adm_lb_nom", "sup_id", "emr_lb_systeme", "emr_dt", "code_insee", "generation", "statut"])
    log(f"Observatoire ANFR : {len(df):,} lignes, fichier {name}")
    log("  statuts : " + ", ".join(f"{k} {v:,}" for k, v in df.statut.value_counts().items()))
    df = df[df.statut == "En service"].copy()
    df["date"] = pd.to_datetime(df.emr_dt, errors="coerce")
    log(f"  en service : {len(df):,} lignes ; dates manquantes : {df.date.isna().sum():,}")
    df = df.dropna(subset=["date"])
    df["unit"] = cog.harmonize(df.code_insee)
    unk = cog.unknown(df.code_insee)
    log(f"  codes commune inconnus du COG {cog.year} : {len(unk)} ({', '.join(unk.head(8))}…)")
    return df


def recode_dates(df: pd.DataFrame, gen: str, floor: pd.Timestamp, recode: pd.Timestamp, label: str) -> pd.DataFrame:
    m = (df.generation == gen) & (df.date < floor)
    n_rows, n_units = int(m.sum()), df.loc[m, "unit"].nunique()
    log(f"  recodage {label} : {n_rows:,} émetteurs ({n_units} communes) datés avant {floor.date()} → {recode.date()}")
    df.loc[m, "date"] = recode
    return df


def first_dates(df: pd.DataFrame, gen: str) -> pd.Series:
    return df.loc[df.generation == gen].groupby("unit").date.min()


# ----------------------------------------------------------------------------- archives ANFR (installations)

def load_archives(cog: Cog) -> pd.DataFrame:
    """Plus ancienne date LTE / UMTS par commune dans chaque export annuel des installations."""
    out = []
    for p in raw_files("fr_anfr_installations_archives"):
        if not re.search(r"(data|DATA)\.zip$", p.name):
            continue
        z = zipfile.ZipFile(p)
        names = {re.sub(r".*/", "", n).upper(): n for n in z.namelist()}
        em_name = next((names[k] for k in names if k.startswith("SUP_EMETTEUR")), None)
        su_name = next((names[k] for k in names if k.startswith("SUP_SUPPORT")), None)
        if not em_name or not su_name:
            log(f"  archive {p.name} : tables SUP_EMETTEUR/SUP_SUPPORT absentes ({list(names)[:6]}) — ignorée")
            continue
        em = pd.read_csv(z.open(em_name), sep=";", dtype=str, encoding="latin-1",
                         usecols=lambda c: c.upper() in ("EMR_LB_SYSTEME", "STA_NM_ANFR", "EMR_DT_SERVICE"))
        em.columns = [c.upper() for c in em.columns]
        su = pd.read_csv(z.open(su_name), sep=";", dtype=str, encoding="latin-1",
                         usecols=lambda c: c.upper() in ("STA_NM_ANFR", "COM_CD_INSEE"))
        su.columns = [c.upper() for c in su.columns]
        em = em[em.EMR_LB_SYSTEME.fillna("").str.upper().str.match(r"^(LTE|UMTS)")]
        em["gen"] = np.where(em.EMR_LB_SYSTEME.str.upper().str.startswith("LTE"), "4G", "3G")
        snapshot = pd.Timestamp(p.name[:8])
        if "EMR_DT_SERVICE" in em.columns:
            em["date"] = pd.to_datetime(em.EMR_DT_SERVICE, format="%d/%m/%Y", errors="coerce")
            kind = "émetteurs datés (EMR_DT_SERVICE)"
        else:
            # exports 2018 : pas de date d'émetteur ; la présence dans l'instantané borne la date par celle de l'export
            em["date"] = snapshot
            kind = f"émetteurs présents, datés par l'instantané ({snapshot.date()}, borne supérieure)"
        em = em.dropna(subset=["date"]).merge(su.drop_duplicates("STA_NM_ANFR"), on="STA_NM_ANFR", how="inner")
        em["unit"] = cog.harmonize(em.COM_CD_INSEE)
        g = em.groupby(["unit", "gen"]).date.min().reset_index()
        g["archive"] = p.name[:8]
        out.append(g)
        log(f"  archive {p.name} : {len(em):,} {kind}, {g.unit.nunique():,} communes")
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["unit", "gen", "date", "archive"])


# ----------------------------------------------------------------------------- sites ARCEP

def load_arcep_sites(cog: Cog) -> pd.Series:
    """Premier trimestre (≥ 2018-T4) où la commune compte un site 4G ouvert commercialement (ARCEP)."""
    firsts = {}
    for p in sorted(raw_files("fr_arcep_sites")):
        m = re.search(r"(\d{4})_T(\d)", p.name)
        if not m:
            continue
        q = (int(m.group(1)), int(m.group(2)))
        raw = p.read_bytes()
        txt = raw.decode("utf-8", errors="replace")
        lines = txt.splitlines()
        hdr = next((i for i, l in enumerate(lines[:5]) if "site_4g" in l.lower()), None)
        if hdr is None:
            continue                                            # 2017-T3 → 2018-T3 : pas de code commune
        df = pd.read_csv(io.StringIO("\n".join(lines[hdr:])), sep=";", dtype=str)
        df.columns = [c.lower() for c in df.columns]
        if "insee_com" not in df.columns:
            continue
        has4g = df.loc[df.site_4g.astype(str).str.strip() == "1", "insee_com"].dropna()
        units = set(cog.harmonize(has4g))
        for u in units:
            firsts.setdefault(u, q)
    s = pd.Series(firsts, name="first_q_arcep")
    log(f"Sites ARCEP : {len(s):,} communes avec ≥ 1 site 4G entre 2018-T4 et le dernier trimestre")
    return s


# ----------------------------------------------------------------------------- ZDP, zones blanches (PDF ARCEP)

def load_zdp(cog: Cog) -> tuple[set, set]:
    import pypdf
    r = pypdf.PdfReader(_one("fr_arcep_zdp_decision"))
    txt = [p.extract_text() or "" for p in r.pages]
    zb_start = next(i for i, t in enumerate(txt) if re.search(r"zones blanches", t, re.I) and re.search(r"tableau ci-dessous", t, re.I))
    zdp_start = next(i for i, t in enumerate(txt) if re.search(r"ploiement\s+prioritaire", t, re.I) and re.search(r"tableau ci-dessous", t, re.I))
    pat = re.compile(r"^\s*\d{2}\s+(\d{5})\s", re.M)
    zb = {c for t in txt[zb_start:zdp_start] for c in pat.findall(t)}
    zdp = {c for t in txt[zdp_start:] for c in pat.findall(t)}
    zb_u = set(cog.harmonize(pd.Series(sorted(zb))))
    zdp_u = set(cog.harmonize(pd.Series(sorted(zdp))))
    log(f"Décision ARCEP 2012-0039 : {len(zb):,} codes « zones blanches » (p. {zb_start + 1}-{zdp_start}), "
        f"{len(zdp):,} codes ZDP (p. {zdp_start + 1}-{len(txt)}) → {len(zdp_u):,} unités harmonisées")
    return zb_u, zdp_u


# ----------------------------------------------------------------------------- densité, poids RP 2011

def load_density(cog: Cog) -> pd.Series:
    p = _one("fr_insee_grille_densite", r"2024\.xlsx$")
    x = pd.read_excel(p, sheet_name=None, dtype=str)
    sheet = next(df for df in x.values() if df.shape[0] > 30000)
    # en-tête : ligne contenant un code commune de 5 caractères dans la première colonne
    hdr = next(i for i in range(min(10, len(sheet))) if re.fullmatch(r"\d{5}|2[AB]\d{3}", str(sheet.iloc[i, 0]) or ""))
    body = sheet.iloc[hdr:].reset_index(drop=True)
    code, dens = body.iloc[:, 0], pd.to_numeric(body.iloc[:, 2], errors="coerce")
    s = pd.Series(dens.values, index=cog.harmonize(code).values).groupby(level=0).min()
    log(f"Grille de densité 2024 : {s.notna().sum():,} communes, niveaux {sorted(s.dropna().unique().astype(int))}")
    return s.rename("densite")


def load_rp2011_weights(cog: Cog) -> pd.DataFrame:
    p = _one("fr_insee_rp_pop_struct", r"2011")
    z = zipfile.ZipFile(p)
    name = next(n for n in z.namelist() if re.search(r"\.(xls|csv)$", n, re.I) and not re.search(r"meta", n, re.I))
    if name.lower().endswith(".xls"):
        sheets = pd.read_excel(z.open(name), sheet_name=None, header=None, dtype=str)
        sheet = sheets["COM_2011"] if "COM_2011" in sheets else next(v for k, v in sheets.items() if k.upper().startswith("COM"))
        hdr = next(i for i in range(min(12, len(sheet))) if str(sheet.iloc[i, 0]).strip().upper() == "CODGEO")
        df = sheet.iloc[hdr + 1:].copy()
        df.columns = [str(c).upper() for c in sheet.iloc[hdr]]
        for c in df.columns:
            if c != "CODGEO" and c != "LIBGEO":
                df[c] = pd.to_numeric(df[c], errors="coerce")
    else:
        df = pd.read_csv(z.open(name), sep=";", dtype={"CODGEO": str})
    cols = [c for c in df.columns if re.fullmatch(r"P11_F(1529|3044)", c)]
    df["w_f1544"] = df[cols].sum(axis=1)
    df["w_pop"] = df["P11_POP"]
    df["unit"] = cog.harmonize(df.CODGEO)
    w = df.groupby("unit")[["w_f1544", "w_pop"]].sum()
    log(f"RP 2011 (poids fixes D3) : {len(w):,} unités, femmes 15-44 = {w.w_f1544.sum():,.0f}")
    return w


# ----------------------------------------------------------------------------- assemblage

def main() -> int:
    PROC.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    cog = Cog(_one("fr_insee_cog"))
    log(f"COG {cog.year} : {len(cog.current):,} communes, {len(cog.units):,} unités harmonisées "
        f"({len(cog.multi_current)} composantes regroupant plusieurs communes actuelles)")

    obs = load_observatoire(cog)
    obs = recode_dates(obs, "4G", LTE_FLOOR, LTE_RECODE, "LTE")
    obs = recode_dates(obs, "3G", UMTS_FLOOR, UMTS_RECODE, "UMTS")
    first_lte_obs = first_dates(obs, "4G")
    first_umts_obs = first_dates(obs, "3G")
    n_op = obs[obs.generation == "4G"].groupby("unit").adm_lb_nom.nunique()
    second_op_date = (obs[obs.generation == "4G"].groupby(["unit", "adm_lb_nom"]).date.min()
                      .groupby("unit").apply(lambda s: s.nsmallest(2).iloc[-1] if len(s) >= 2 else pd.NaT))

    arch = load_archives(cog)
    arch_lte = arch[arch.gen == "4G"].groupby("unit").date.min().clip(lower=LTE_RECODE)
    arch_umts = arch[arch.gen == "3G"].groupby("unit").date.min().clip(lower=UMTS_RECODE)
    first_lte = pd.concat([first_lte_obs, arch_lte], axis=1).min(axis=1)
    first_umts = pd.concat([first_umts_obs, arch_umts], axis=1).min(axis=1)
    arcep_q = load_arcep_sites(cog)
    zb, zdp = load_zdp(cog)
    dens = load_density(cog)
    w = load_rp2011_weights(cog)

    units = pd.Index(cog.units, name="unit")
    base = pd.DataFrame(index=units)
    base["dep"] = cog.dep_of(units.to_series())
    base["metro"] = cog.is_metro(units.to_series()).values
    base["first_lte"] = first_lte.reindex(units)
    base["first_lte_obs_only"] = first_lte_obs.reindex(units)
    base["first_lte_archives_only"] = arch_lte.reindex(units)
    base["first_umts"] = first_umts.reindex(units)
    base["first_lte_2nd_operator"] = pd.to_datetime(second_op_date.reindex(units))
    base["n_operators_4g"] = n_op.reindex(units).fillna(0).astype(int)
    base["first_q_arcep"] = arcep_q.reindex(units)
    base["zdp"] = units.isin(zdp)
    base["zone_blanche"] = units.isin(zb)
    base["densite"] = dens.reindex(units)
    base = base.join(w)

    def cohort_from(date: pd.Series) -> pd.Series:
        """Première année t telle que date ≤ 1er janvier t ; 0 si jamais."""
        y = date.dt.year + (~((date.dt.month == 1) & (date.dt.day == 1))).astype(int)
        return y.fillna(0).astype(int)

    base["cohort_4g"] = cohort_from(base.first_lte)
    base["cohort_4g_obs_only"] = cohort_from(base.first_lte_obs_only)
    base["cohort_4g_2op"] = cohort_from(base.first_lte_2nd_operator)
    base["cohort_3g"] = cohort_from(base.first_umts)
    base["cohort_4g_arcep"] = base.first_q_arcep.map(lambda q: q[0] + 1 if isinstance(q, tuple) else 0).astype(int)

    # panel commune × année
    rows = []
    lte = obs[obs.generation == "4G"]
    for t in YEARS:
        jan1 = pd.Timestamp(year=t, month=1, day=1)
        n_sites = lte[lte.date <= jan1].groupby("unit").sup_id.nunique().reindex(units).fillna(0).astype(int)
        d = pd.DataFrame({"unit": units, "year": t,
                          "d1_4g": (base.first_lte <= jan1).astype(int).values,
                          "d_3g": (base.first_umts <= jan1).astype(int).values,
                          "n_lte_sites": n_sites.values})
        rows.append(d)
    panel = pd.concat(rows, ignore_index=True).merge(
        base.reset_index()[["unit", "dep", "metro", "cohort_4g", "cohort_4g_obs_only", "cohort_4g_2op", "cohort_3g",
                            "cohort_4g_arcep", "n_operators_4g", "zdp", "zone_blanche", "densite", "w_f1544", "w_pop"]],
        on="unit", how="left")
    panel.to_parquet(PROC / "fr_treatment_commune.parquet", index=False)
    base.reset_index().to_parquet(PROC / "fr_treatment_commune_static.parquet", index=False)

    # D3 département × année (poids RP 2011 fixes, femmes 15-44)
    pw = panel[panel.w_f1544.notna()].copy()
    pw["wd"] = pw.w_f1544 * pw.d1_4g
    d3 = pw.groupby(["dep", "year"]).agg(w=("w_f1544", "sum"), wd=("wd", "sum"),
                                         n_units=("unit", "size"), n_treated=("d1_4g", "sum")).reset_index()
    d3["d3"] = d3.wd / d3.w
    bascule = {}
    for thr in (0.5, 0.9):
        b = d3[d3.d3 >= thr].groupby("dep").year.min()
        bascule[thr] = b
        d3[f"cohort_d3_{int(thr * 100)}"] = d3.dep.map(b).fillna(0).astype(int)
    d3.to_parquet(PROC / "fr_treatment_dep.parquet", index=False)

    # ---- tableau de synthèse
    st = base[base.metro]
    lines = ["# Traitement France — synthèse (généré par scripts/02_treatment.py)", ""]
    lines += ["## Journal de construction", ""] + [f"- {n}" for n in notes] + [""]
    lines += ["## Cohortes 4G (D1), France métropolitaine, unités harmonisées", "",
              "| cohorte | observatoire ∪ archives | observatoire seul | 2e opérateur | sites ARCEP (≥ 2019 datés) |",
              "|---|---|---|---|---|"]
    allc = sorted(set(st.cohort_4g.unique()) | set(st.cohort_4g_obs_only.unique()) | set(st.cohort_4g_arcep.unique()))
    for c in allc:
        lines.append(f"| {c if c else 'jamais'} | {(st.cohort_4g == c).sum():,} | {(st.cohort_4g_obs_only == c).sum():,} | "
                     f"{(st.cohort_4g_2op == c).sum():,} | {(st.cohort_4g_arcep == c).sum():,} |")
    lines += ["", "## Cohortes 3G (UMTS)", "", "| cohorte | unités |", "|---|---|"]
    for c, n in st.cohort_3g.value_counts().sort_index().items():
        lines.append(f"| {c if c else 'jamais'} | {n:,} |")
    both = st[(st.cohort_4g_obs_only > 0) & (st.first_lte_archives_only.notna())]
    diff = (both.cohort_4g_obs_only - cohort_from(both.first_lte_archives_only))
    lines += ["", "## Accord entre sources de datation", "",
              f"- Unités avec LTE dans l'observatoire courant : {(st.cohort_4g_obs_only > 0).sum():,} ; "
              f"dans les archives 2018-2025 : {st.first_lte_archives_only.notna().sum():,} ; dans l'union : {(st.cohort_4g > 0).sum():,}.",
              f"- Parmi les {len(both):,} unités présentes dans les deux : écart de cohorte nul {(diff == 0).sum():,}, "
              f"1 an {(diff.abs() == 1).sum():,}, > 1 an {(diff.abs() > 1).sum():,} (archives plus anciennes dans {(diff > 0).sum():,} cas).",
              f"- Unités où la cohorte retenue diffère de l'observatoire seul : {(st.cohort_4g != st.cohort_4g_obs_only).sum():,}."]
    ar = st[(st.cohort_4g_arcep >= 2020) & (st.cohort_4g > 0)]
    if len(ar):
        da = ar.cohort_4g_arcep - ar.cohort_4g
        lines += [f"- Sites ARCEP : {len(ar):,} unités avec un premier site 4G commercial daté 2019-T1 ou après ; écart (ARCEP − D1) "
                  f"médian {da.median():.0f} an(s), ≤ 1 an dans {(da.abs() <= 1).mean():.0%} des cas, ARCEP postérieur de > 2 ans dans {(da > 2).mean():.0%}.",
                  f"- Unités avec D1 = 1 au 1/1/2019 mais aucun site 4G ARCEP au 2018-T4 : "
                  f"{((st.cohort_4g <= 2019) & (st.cohort_4g > 0) & (st.cohort_4g_arcep != 2019)).sum():,}."]
    lines += ["", "## ZDP, zones blanches, densité", "",
              f"- ZDP : {st.zdp.sum():,} unités métropolitaines ({st.zdp.mean():.1%}) ; zones blanches : {st.zone_blanche.sum():,}.",
              "- Cohorte 4G médiane : ZDP " + f"{st[st.zdp & (st.cohort_4g > 0)].cohort_4g.median():.0f}" +
              f", hors ZDP {st[~st.zdp & (st.cohort_4g > 0)].cohort_4g.median():.0f} ; jamais traitées : ZDP "
              f"{(st[st.zdp].cohort_4g == 0).mean():.1%}, hors ZDP {(st[~st.zdp].cohort_4g == 0).mean():.1%}.",
              "", "| densité (1 = dense … 7 = très peu dense) | unités | cohorte 4G médiane | jamais 4G |", "|---|---|---|---|"]
    for k, g in st.groupby("densite"):
        lines.append(f"| {int(k)} | {len(g):,} | {g[g.cohort_4g > 0].cohort_4g.median():.0f} | {(g.cohort_4g == 0).mean():.1%} |")
    lines += ["", "## D3 (exposition départementale, poids RP 2011 femmes 15-44)", "",
              "| seuil | départements basculés | année médiane | min | max |", "|---|---|---|---|---|"]
    for thr, b in bascule.items():
        bm = b[b.index.isin(st.dep.unique())]
        lines.append(f"| {int(thr * 100)} % | {len(bm)} / {st.dep.nunique()} | {bm.median():.0f} | {bm.min()} | {bm.max()} |")
    (TABLES / "t_treatment_fr.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[-40:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
