"""Registre des sources de données.

Chaque source est décrite par un identifiant stable, un pays, un rôle (traitement, résultat,
exposition, contrôle, panel), une licence, et une méthode de résolution des URL de fichiers :

- ``direct``       : liste d'URL de fichiers connues ;
- ``datagouv``     : jeu de données data.gouv.fr (slug) → ressources via l'API ;
- ``insee_page``   : page insee.fr → liens ``/fr/statistiques/fichier/<id>/<nom>`` ;
- ``eurostat_tsv`` : code de table Eurostat → export TSV compressé via l'API de diffusion ;
- ``worldbank``    : indicateur Banque mondiale → API v2 JSON, tous pays ;
- ``owid``         : identifiant de graphique Our World in Data → CSV ;
- ``socrata``      : identifiant Socrata (datos.gov.co) → CSV complet ;
- ``manual``       : aucune résolution automatique connue → le téléchargement s'arrête et le dit.

Rien n'est téléchargé ici. ``verified`` passe à True seulement après un téléchargement réussi
consigné dans ``docs/data_log.md`` (règle 1 du cahier des charges). Les URL marquées « à vérifier »
proviennent de la recherche documentaire de l'Étape 0 et peuvent être fausses : le téléchargeur
s'arrête à la première erreur.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Source:
    id: str
    country: str          # code ISO-2, ou "EU", "WORLD"
    role: str             # traitement | resultat | exposition | controle | panel | geo
    title: str
    resolver: str         # direct | datagouv | insee_page | eurostat_tsv | worldbank | owid | socrata | manual
    ref: str              # URL, slug, code de table ou identifiant selon le resolver
    license: str
    years: str = ""
    granularity: str = ""
    notes: str = ""
    include: tuple = field(default_factory=tuple)   # motifs (regex) de noms de fichiers à garder
    exclude: tuple = field(default_factory=tuple)


SOURCES: list[Source] = [
    # ------------------------------------------------------------------ France : traitement
    Source("fr_anfr_observatoire", "FR", "traitement",
           "ANFR — Observatoire 2G, 3G, 4G, 5G (supports × opérateur × génération, statut, date, code INSEE)",
           "datagouv", "observatoire-2g-3g-4g-5g", "Licence Ouverte 2.0",
           years="instantané courant + archives mensuelles 2015+", granularity="support → commune",
           notes="Export courant ~516 Mo ; les archives mensuelles sont sur anfr.fr (à résoudre).",
           include=(r"\.csv$", r"\.zip$")),
    Source("fr_anfr_installations", "FR", "traitement",
           "ANFR — Données sur les installations radioélectriques de plus de 5 watts (SUP_EMETTEUR : EMR_LB_SYSTEME, EMR_DT_SERVICE)",
           "datagouv", "donnees-sur-les-installations-radioelectriques-de-plus-de-5-watts-1", "Licence Ouverte 2.0",
           years="instantané courant, dates de service historiques", granularity="émetteur → commune",
           include=(r"\.zip$",)),
    Source("fr_arcep_couverture", "FR", "traitement",
           "ARCEP — Mon réseau mobile : couvertures théoriques par commune et opérateur",
           "datagouv", "mon-reseau-mobile", "Licence Ouverte 2.0",
           years="2017-T4 →", granularity="commune × opérateur, trimestriel",
           notes="Les millésimes sont aussi listés sur https://data.arcep.fr/mobile/couvertures_theoriques/ (à vérifier)."),
    Source("fr_arcep_zdp", "FR", "traitement",
           "ARCEP — Décision 2011-0600, liste des communes de la zone de déploiement prioritaire (800 MHz)",
           "manual", "https://www.legifrance.gouv.fr/jorf/article_jo/JORFARTI000024170018", "Légifrance (réutilisation libre)",
           years="2011", granularity="commune",
           notes="Annexe à extraire ; chercher aussi un fichier xls sur arcep.fr."),
    # ------------------------------------------------------------------ France : résultats
    Source("fr_insee_naissances_detail_1998_2013", "FR", "resultat",
           "INSEE — Fichiers détail naissances 1998-2013 (AGEMERE, DEPDOM, TUDOM, AMAR, NBENF)",
           "insee_page", "https://www.insee.fr/fr/statistiques/2117120", "Licence Ouverte 2.0",
           years="1998-2013", granularity="naissance individuelle, département de domicile",
           notes="Sommaire « Naissances, décès et mariages de 1998 à 2013 » ; une page par année (à vérifier).",
           include=(r"(?i)nais.*\.(zip|csv|dbf)$",)),
    Source("fr_insee_naissances_detail_2023", "FR", "resultat",
           "INSEE — Les naissances en 2023, fichier détail", "insee_page",
           "https://www.insee.fr/fr/statistiques/8285987", "Licence Ouverte 2.0", years="2023",
           granularity="naissance individuelle", include=(r"\.zip$",)),
    Source("fr_insee_naissances_detail_autres", "FR", "resultat",
           "INSEE — Fichiers détail naissances 2014-2022, 2024, 2025 (pages à découvrir via la recherche INSEE)",
           "insee_page", "https://www.insee.fr/fr/statistiques?debut=0&q=naissances+fichier+d%C3%A9tail&categorie=5",
           "Licence Ouverte 2.0", years="2014-2025", granularity="naissance individuelle",
           notes="Résolution en deux temps : la page de recherche liste les pages annuelles, puis chaque page donne le zip. À vérifier.",
           include=(r"\.zip$",)),
    Source("fr_insee_mariages_detail", "FR", "resultat",
           "INSEE — Fichiers détail mariages (âge des époux, DEPDOM), 1998-2013 et pages annuelles 2014-2024",
           "insee_page", "https://www.insee.fr/fr/statistiques/2117120", "Licence Ouverte 2.0",
           years="1998-2024", granularity="mariage individuel, département",
           notes="Pages connues : 2021 → 7453878, 2022 → 7759252, 2023 → 8603939 (à vérifier).",
           include=(r"(?i)mar.*\.(zip|csv|dbf)$",)),
    Source("fr_insee_naissances_communes_2014_2023", "FR", "resultat",
           "INSEE — Naissances et décès domiciliés 2014-2023, résultats pour toutes les communes",
           "insee_page", "https://www.insee.fr/fr/statistiques/zones/8311958", "Licence Ouverte 2.0",
           years="2014-2023", granularity="commune", include=(r"\.(zip|csv|xlsx)$",)),
    Source("fr_insee_naissances_communes_2004_2015", "FR", "resultat",
           "INSEE via data.gouv.fr — Naissances de 2004 à 2015 par commune", "datagouv",
           "naissances-de-2004-a-2015-par-commune", "Licence Ouverte 2.0", years="2004-2015", granularity="commune"),
    Source("fr_insee_naissances_communes_annuel", "FR", "resultat",
           "INSEE via data.gouv.fr — Nombre de naissances annuelles par commune", "datagouv",
           "nombre-de-naissances-annuelles-par-commune", "Licence Ouverte 2.0", years="2014 →", granularity="commune"),
    Source("fr_justice_pacs", "FR", "resultat",
           "Ministère de la Justice — PACS conclus par tribunal d'instance / département", "manual",
           "http://www.stats.justice.gouv.fr/chiffres_cles/html/C-VM_CUBE_PACS_CON_TI", "Licence Ouverte 2.0",
           years="1999-2016 (tribunaux), 2017+ via INSEE", granularity="département",
           notes="Cube interactif ; export à résoudre. Complément INSEE bilan démographique départemental."),
    Source("fr_insee_rp_cfm", "FR", "resultat",
           "INSEE RP — Base Couples-Familles-Ménages par commune (population 15+ par sexe, âge, vie en couple), millésimes 2006-2022",
           "insee_page", "https://www.insee.fr/fr/statistiques?debut=0&q=couples+familles+m%C3%A9nages+base&categorie=5",
           "Licence Ouverte 2.0", years="RP2006-RP2022", granularity="commune",
           notes="Pages connues : 2021 → 8268828, 2022 → 8647008, 2020 → 7704086, 2019 → 6454116 (à vérifier).",
           include=(r"(?i)cc.*(coupl|fam|men).*\.(zip|csv|xlsx)$",)),
    Source("fr_insee_estim_pop_dep", "FR", "resultat",
           "INSEE — Estimations de population par département, sexe et âge quinquennal, 1975-2025",
           "insee_page", "https://www.insee.fr/fr/statistiques/1893198", "Licence Ouverte 2.0",
           years="1975-2025", granularity="département × sexe × âge", include=(r"estim-pop.*\.xlsx?$",)),
    Source("fr_insee_rp_pop_struct", "FR", "resultat",
           "INSEE RP — Base Évolution et structure de la population par commune (sexe × âge), millésimes",
           "insee_page", "https://www.insee.fr/fr/statistiques?debut=0&q=evolution+et+structure+de+la+population+base&categorie=5",
           "Licence Ouverte 2.0", years="RP2006-RP2022", granularity="commune × sexe × âge",
           include=(r"(?i)cc.*(evol|struct).*\.(zip|csv|xlsx)$",)),
    # ------------------------------------------------------------------ France : exposition, contrôles, géo
    Source("fr_barometre_numerique", "FR", "exposition",
           "CREDOC / ARCEP / CGE — Baromètre du numérique, microdonnées depuis 2007", "datagouv",
           "barometre-du-numerique", "Licence Ouverte 2.0", years="2007-2025", granularity="individu",
           notes="Slug à vérifier (recherche data.gouv « baromètre du numérique »)."),
    Source("fr_insee_filosofi", "FR", "controle",
           "INSEE — Filosofi, revenu disponible médian par commune", "insee_page",
           "https://www.insee.fr/fr/statistiques?debut=0&q=filosofi+base+communale&categorie=5",
           "Licence Ouverte 2.0", years="2012-2021", granularity="commune", include=(r"(?i)filo.*\.(zip|csv|xlsx)$",)),
    Source("fr_insee_rp_activite", "FR", "controle",
           "INSEE RP — Base Activité des résidents par commune (chômage par âge, diplômes)", "insee_page",
           "https://www.insee.fr/fr/statistiques?debut=0&q=activite+des+residents+base&categorie=5",
           "Licence Ouverte 2.0", years="RP2006-RP2022", granularity="commune", include=(r"(?i)cc.*act.*\.(zip|csv|xlsx)$",)),
    Source("fr_insee_grille_densite", "FR", "controle",
           "INSEE — Grille communale de densité", "insee_page",
           "https://www.insee.fr/fr/information/6439600", "Licence Ouverte 2.0", granularity="commune",
           notes="Identifiant de page à vérifier.", include=(r"\.(zip|xlsx|csv)$",)),
    Source("fr_dvf_statistiques", "FR", "controle",
           "Cerema / Etalab — Statistiques DVF agrégées par commune (prix, volumes)", "datagouv",
           "statistiques-dvf", "Licence Ouverte 2.0", years="2014-2024", granularity="commune"),
    Source("fr_insee_cog", "FR", "geo",
           "INSEE — Code officiel géographique 2024 et table de passage des communes fusionnées", "insee_page",
           "https://www.insee.fr/fr/information/7766585", "Licence Ouverte 2.0", years="2024",
           notes="Identifiant de page à vérifier.", include=(r"\.(zip|csv|xlsx)$",)),
    # ------------------------------------------------------------------ Europe
    Source("eu_demo_r_frate2", "EU", "resultat", "Eurostat — Taux de fécondité par âge, NUTS 2", "eurostat_tsv",
           "demo_r_frate2", "Eurostat (réutilisation libre avec mention)", years="1990-2024", granularity="NUTS 2 × âge"),
    Source("eu_demo_frate", "EU", "resultat", "Eurostat — Taux de fécondité par âge, pays", "eurostat_tsv",
           "demo_frate", "Eurostat", years="1960-2024", granularity="pays × âge"),
    Source("eu_demo_nind", "EU", "resultat", "Eurostat — Indicateurs de nuptialité", "eurostat_tsv",
           "demo_nind", "Eurostat", granularity="pays"),
    Source("eu_isoc_r_iuse_i", "EU", "exposition", "Eurostat — Usage régulier d'Internet, régions", "eurostat_tsv",
           "isoc_r_iuse_i", "Eurostat", years="2006-2025", granularity="NUTS 1/2"),
    Source("eu_isoc_ci_im_i", "EU", "exposition", "Eurostat — Internet mobile hors domicile, par âge", "eurostat_tsv",
           "isoc_ci_im_i", "Eurostat", years="2012-2023", granularity="pays × âge"),
    Source("eu_isoc_ci_ac_i", "EU", "exposition", "Eurostat — Activités Internet dont réseaux sociaux, par âge", "eurostat_tsv",
           "isoc_ci_ac_i", "Eurostat", years="2011-2025", granularity="pays × âge"),
    # ------------------------------------------------------------------ Panel international (descriptif)
    Source("wb_tfr", "WORLD", "panel", "Banque mondiale — ISF (SP.DYN.TFRT.IN)", "worldbank", "SP.DYN.TFRT.IN", "CC BY 4.0"),
    Source("wb_mobile", "WORLD", "panel", "Banque mondiale — Abonnements mobiles pour 100 hab. (IT.CEL.SETS.P2)", "worldbank", "IT.CEL.SETS.P2", "CC BY 4.0"),
    Source("wb_internet", "WORLD", "panel", "Banque mondiale — Usagers d'Internet, % (IT.NET.USER.ZS)", "worldbank", "IT.NET.USER.ZS", "CC BY 4.0"),
    Source("wb_gdp", "WORLD", "panel", "Banque mondiale — PIB/hab. PPA constant (NY.GDP.PCAP.PP.KD)", "worldbank", "NY.GDP.PCAP.PP.KD", "CC BY 4.0"),
    Source("owid_mobile_broadband", "WORLD", "panel", "ITU via OWID — Abonnements haut débit mobile pour 100 hab.", "owid",
           "mobile-broadband-subscriptions-per-100-people", "CC BY 4.0", notes="Slug OWID à vérifier."),
    Source("un_wpp_asfr", "WORLD", "panel", "UN WPP 2024 — Taux de fécondité par groupe d'âge quinquennal, tous pays", "direct",
           "https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/WPP2024_Fertility_by_Age5.csv.gz",
           "CC BY 3.0 IGO", years="1950-2023", granularity="pays × âge",
           notes="Nom de fichier non confirmé ; repli : API dataportalapi, indicateur ASFR5."),
    Source("itu_coverage", "WORLD", "panel", "ITU DataHub — Population couverte par au moins un réseau 3G / LTE (indicateur 100095)", "manual",
           "https://datahub.itu.int/data/?i=100095", "ITU (conditions à vérifier)", years="≈2010-2023", granularity="pays",
           notes="Point de téléchargement CSV/API non confirmé."),
    # ------------------------------------------------------------------ Pays de niveau 1 (addendum requis avant estimation)
    Source("es_cobertura_2013_2021", "ES", "traitement",
           "MINECO/SETID — Base de datos histórica 2013-2021 de cobertura de banda ancha fija y móvil (LTE par entidad singular)",
           "manual", "https://datos.gob.es/en/catalogo/e05068901-base-de-datos-historica-desde-2013-a2020-de-cobertura-banda-ancha-fija-y-movil",
           "datos.gob.es (licence du jeu à vérifier)", years="2013-2021", granularity="entidad singular de población",
           notes="Résolution via l'API datos.gob.es à écrire ; un seul XLSX (~5 Mo)."),
    Source("es_ine_nacimientos", "ES", "resultat", "INE — Estadística de nacimientos, microdonnées", "manual",
           "https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736177007&menu=resultados&secc=1254736195443&idp=1254735573002",
           "INE (réutilisation libre avec mention)", granularity="naissance, commune de résidence (seuil de taille)"),
    Source("se_pts_tackning", "SE", "traitement", "PTS — Mobiltäcknings- och bredbandskartläggning, par kommun, 2013+", "manual",
           "https://statistik.pts.se/mobiltacknings-och-bredbandskartlaggning", "PTS", years="2013 →", granularity="kommun"),
    Source("se_scb_fodda", "SE", "resultat", "SCB — Födda efter region, moderns ålder och barnets kön (FoddaK), API PxWeb", "manual",
           "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/BE/BE0101/BE0101H/FoddaK", "SCB (CC0)", years="1968-2024", granularity="kommun × âge",
           notes="Requête POST PxWeb à écrire."),
    Source("br_anatel_acessos", "BR", "traitement", "Anatel — Acessos SMP por município e tecnologia (mensuel)", "manual",
           "https://www.anatel.gov.br/dadosabertos/PDA/Acessos/", "Dados abertos (licence à vérifier)", years="2007 →", granularity="município",
           notes="Arborescence de fichiers à lister."),
    Source("br_anatel_cobertura", "BR", "traitement", "Anatel — Cobertura da telefonia móvel por setor censitário", "manual",
           "https://www.anatel.gov.br/dadosabertos/PDA/Cobertura_Movel/", "Dados abertos", granularity="secteur censitaire → município"),
    Source("br_sinasc", "BR", "resultat", "DATASUS — SINASC microdonnées (DN{UF}{AAAA}.dbc)", "manual",
           "ftp://ftp.datasus.gov.br/dissemin/publicos/SINASC/NOV/DNRES/", "DATASUS (ouvert)", years="1996 →", granularity="naissance, município",
           notes="FTP : peut ne pas passer par le proxy HTTPS ; repli PCDaS/Fiocruz."),
    Source("br_sidra_casamentos", "BR", "resultat", "IBGE SIDRA — Tabela 4412, casamentos por idade dos cônjuges, município", "manual",
           "https://apisidra.ibge.gov.br/values/t/4412/n6/all", "IBGE", granularity="município × âge",
           notes="API REST ; pagination par UF à écrire."),
    Source("co_mintic_cobertura", "CO", "traitement", "MinTIC — Cobertura móvil por tecnología, departamento y municipio por proveedor", "socrata",
           "9mey-c8s8", "datos.gov.co (CC BY)", years="≈2013 →", granularity="municipio × opérateur × technologie, trimestriel"),
    Source("co_dane_nacimientos", "CO", "resultat", "DANE — EEVV nacimientos, microdonnées", "manual",
           "https://microdatos.dane.gov.co/index.php/catalog/843", "DANE (usage public)", years="1998-2024", granularity="naissance, municipio"),
]

BY_ID = {s.id: s for s in SOURCES}


def select(country: str | None = None, ids: list[str] | None = None, roles: list[str] | None = None) -> list[Source]:
    out = SOURCES
    if country:
        out = [s for s in out if s.country == country]
    if ids:
        out = [s for s in out if s.id in ids]
    if roles:
        out = [s for s in out if s.role in roles]
    return out
