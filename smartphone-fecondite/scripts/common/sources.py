"""Registre des sources de données.

Chaque source est décrite par un identifiant stable, un pays, un rôle (traitement, résultat,
exposition, contrôle, panel, géo), une licence, et une méthode de résolution des URL de fichiers :

- ``direct``         : liste d'URL de fichiers connues (``ref`` = URL, ou plusieurs séparées par « | ») ;
- ``datagouv``       : jeu de données data.gouv.fr (slug) → ressources via l'API ``/api/1/datasets/<slug>/``,
                       filtrées par ``include``/``exclude`` (regex sur le nom de fichier) ; ``latest`` = n ne
                       garde que les n derniers noms (ordre lexicographique, les noms ANFR sont datés) ;
- ``insee_page``     : page insee.fr → liens ``/fr/statistiques/fichier/<id>/<nom>`` ;
- ``insee_sommaire`` : page « sommaire » insee.fr → sous-pages dont le titre du lien correspond à
                       ``subpage`` (regex) → liens de fichiers ;
- ``melodi``         : identifiant de jeu de l'API Melodi (api.insee.fr/melodi) → fichier CSV complet
                       (``product`` → ``accessURL`` du catalogue) ;
- ``arcep_dir``      : dossier de data.arcep.fr (explorateur statique) → sous-dossiers correspondant à
                       ``subpage`` → fichiers correspondant à ``include`` ;
- ``eurostat_tsv``   : code de table Eurostat → export TSV compressé via l'API de diffusion ;
- ``worldbank``      : indicateur Banque mondiale → API v2 JSON, tous pays ;
- ``owid``           : identifiant de graphique Our World in Data → CSV ;
- ``socrata``        : identifiant Socrata (datos.gov.co) → CSV complet ;
- ``manual``         : aucune résolution automatique connue → le téléchargement s'arrête et le dit.

Rien n'est téléchargé ici. Historique des corrections d'URL : ``docs/data_log.md`` (section « Corrections
du registre »). Les URL « à vérifier » proviennent de la recherche documentaire de l'Étape 0 ; celles marquées
« constaté le 02/10/2026 » ont été lues sur la page réelle du producteur.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Source:
    id: str
    country: str          # code ISO-2, ou "EU", "WORLD"
    role: str             # traitement | resultat | exposition | controle | panel | geo
    title: str
    resolver: str
    ref: str              # URL, slug, code de table ou identifiant selon le resolver
    license: str
    years: str = ""
    granularity: str = ""
    notes: str = ""
    include: tuple = field(default_factory=tuple)   # motifs (regex) de noms de fichiers à garder
    exclude: tuple = field(default_factory=tuple)
    subpage: str = ""                               # insee_sommaire / arcep_dir : regex sur les sous-pages
    latest: int = 0                                 # datagouv : ne garder que les n derniers fichiers


# Pages annuelles INSEE des fichiers détail (constatées le 02/10/2026 sur insee.fr).
# 1998-2013 : un seul sommaire (2117120) avec 48 sous-pages « Les naissances / Les mariages / Les décès ».
INSEE_ETAT_CIVIL_SOMMAIRES = {
    2014: 2114983, 2015: 2406457, 2016: 3051496, 2017: 3596198, 2018: 4215184, 2019: 4768339,
    2020: 5419788, 2021: 6652160,
}
INSEE_NAIS_PAGES = {2022: 7708070, 2023: 8285987, 2024: 8610295}      # pages sans sommaire
INSEE_MAR_PAGES = {2022: 7759252, 2023: 8603939, 2024: 8899385}

SOURCES: list[Source] = [
    # ================================================================== France : traitement
    Source("fr_anfr_observatoire", "FR", "traitement",
           "ANFR — Données sur les réseaux mobiles (observatoire 2G/3G/4G/5G) : stations × opérateur × système, "
           "date (emr_dt), statut, code INSEE ; dernier export hebdomadaire",
           "datagouv", "donnees-sur-les-reseaux-mobiles", "Licence Ouverte 2.0",
           years="instantané courant ; dates emr_dt 1990-2027", granularity="support × système → commune",
           notes="Constaté le 02/10/2026 : 10 zips hebdomadaires (~20 Mo, csv ';' de ~830 000 lignes). "
                 "On ne garde que le plus récent. Colonnes : adm_lb_nom, sup_id, emr_lb_systeme, emr_dt, code_insee, "
                 "generation, statut (En service / Techniquement opérationnel / Projet approuvé).",
           include=(r"\.zip$",), latest=1),
    Source("fr_anfr_installations_archives", "FR", "traitement",
           "ANFR — Installations radioélectriques de plus de 5 W : exports mensuels (SUP_EMETTEUR : EMR_LB_SYSTEME, "
           "EMR_DT_SERVICE ; SUP_SUPPORT : commune) — un export par an, 2018-2025, pour recouper les dates",
           "datagouv", "donnees-sur-les-installations-radioelectriques-de-plus-de-5-watts-1", "Licence Ouverte 2.0",
           years="exports 2018-01 → 2026-08 (mensuels)", granularity="émetteur → commune",
           notes="Constaté le 02/10/2026 : exports mensuels (33-68 Mo) nommés AAAAMMJJ_DATA.zip (janv. 2018), "
                 "AAAAMMJJ_Export_Etalab_Data.zip (2018) puis AAAAMMJJ-export-etalab-data.zip. On garde un export par an "
                 "(janvier 2018 = le plus ancien, puis le dernier de chaque année 2018-2025) + tables de référence.",
           include=(r"^(20180131_(DATA|Tables_de_reference)|20181231-export-etalab-(data|ref)|2019123\d-export-etalab-(data|ref)|"
                    r"20201201-export-etalab-(data|ref)|20211223-export-etalab-(data|ref)|20221223-export-etalab-(data|ref)|"
                    r"20231222-export-etalab-(data|ref)|20241231-export-etalab-(data|ref)|20251231-export-etalab-(data|ref))",)),
    Source("fr_arcep_sites", "FR", "traitement",
           "ARCEP — Sites mobiles ouverts commercialement par opérateur et technologie, trimestriel, France métropolitaine",
           "arcep_dir", "https://data.arcep.fr/mobile/sites/", "Licence Ouverte 2.0",
           years="2018-T4 → 2026-T2 (avec code commune ; 2017-T3 à 2018-T3 : coordonnées seulement)",
           granularity="site → commune, trimestriel",
           notes="Constaté le 02/10/2026 : dossiers <AAAA>_T<n>/Metropole/<AAAA>_T<n>_sites_Metropole.csv puis "
                 "<AAAA>_T<n>/<AAAA>_T<n>_sites_Metropole.csv à partir de 2022-T3 ; insee_com présent depuis 2018-T4.",
           subpage=r"^(20(1[89]|2[0-6]))_T[1-4]/$", include=(r"_sites_Metropole\.csv$",)),
    Source("fr_arcep_couverture_doc", "FR", "traitement",
           "ARCEP — Documentation des cartes de couverture théorique (Mon réseau mobile)",
           "direct", "https://data.arcep.fr/mobile/couvertures_theoriques/documentation_couverture.md", "Licence Ouverte 2.0",
           notes="Constaté le 02/10/2026 : les couvertures sont des géopackages/shapefiles par opérateur et trimestre "
                 "(2018-T1 →), pas des tableaux par commune. D2 (part de population couverte par commune) exige un "
                 "croisement SIG : voir docs/data_log.md."),
    Source("fr_arcep_zdp_decision", "FR", "traitement",
           "ARCEP — Décision n° 2012-0039 (autorisation 800 MHz de SFR) : annexes listant les communes du programme "
           "« zones blanches » et les communes de la zone de déploiement prioritaire (ZDP)",
           "direct", "https://www.arcep.fr/uploads/tx_gsavis/12-0039.pdf", "ARCEP (document public)",
           years="2012 (liste fixée par la décision 2011-0600)", granularity="commune",
           notes="Constaté le 02/10/2026 : la décision 2011-0600 (11-0600.pdf) renvoie la liste à « un fichier séparé » "
                 "introuvable sur arcep.fr ; les décisions d'autorisation 2012-0037/0038/0039 (275 pages) reproduisent les "
                 "deux listes en annexe (zones blanches p. 18-56, ZDP p. 57-275, colonnes DPT INSEE COMMUNE, 22 389 codes "
                 "extraits par pypdf). Extraction dans 02_treatment.py."),
    # ================================================================== France : résultats
    Source("fr_insee_naissances_detail_1998_2013", "FR", "resultat",
           "INSEE — Fichiers détail naissances 1998-2013 (dBase : AGEMERE, DEPDOM, TUDOM, AMAR, NBENF)",
           "insee_sommaire", "https://www.insee.fr/fr/statistiques/2117120", "Licence Ouverte 2.0",
           years="1998-2013", granularity="naissance individuelle, département de domicile",
           notes="Constaté le 02/10/2026 : 16 sous-pages « Les naissances », fichiers etatcivil<AAAA>_nais<AAAA>_dbase.zip "
                 "(2010 : naiss2010).",
           subpage=r"^Les naissances", include=(r"(?i)naiss?\d{4}_dbase\.zip$",)),
    Source("fr_insee_naissances_detail_2014_2021", "FR", "resultat",
           "INSEE — Fichiers détail naissances 2014-2021 (sommaires annuels)",
           "insee_sommaire", "|".join(f"https://www.insee.fr/fr/statistiques/{p}" for p in INSEE_ETAT_CIVIL_SOMMAIRES.values()),
           "Licence Ouverte 2.0", years="2014-2021", granularity="naissance individuelle",
           notes="Constaté le 02/10/2026 : sommaires " + ", ".join(f"{y} → {p}" for y, p in INSEE_ETAT_CIVIL_SOMMAIRES.items()) + ".",
           subpage=r"^Les naissances", include=(r"(?i)(nais201[4-7]_dbase|nais201[89]_csv|FD_NAIS_\d{4}_csv)\.zip$",),
           exclude=(r"(?i)beyond",)),
    Source("fr_insee_naissances_detail_2022_2024", "FR", "resultat",
           "INSEE — Fichiers détail naissances 2022, 2023, 2024 (pages sans sommaire)",
           "insee_page", "|".join(f"https://www.insee.fr/fr/statistiques/{p}" for p in INSEE_NAIS_PAGES.values()),
           "Licence Ouverte 2.0", years="2022-2024", granularity="naissance individuelle",
           notes="Constaté le 02/10/2026 : 2022 → 7708070, 2023 → 8285987, 2024 → 8610295 ; FD_NAIS_<AAAA>_csv.zip. "
                 "Les naissances 2025 ne sont pas encore publiées en fichier détail (dernière année : 2024).",
           include=(r"FD_NAIS_\d{4}_csv\.zip$",)),
    Source("fr_insee_mariages_detail_1998_2013", "FR", "resultat",
           "INSEE — Fichiers détail mariages 1998-2013 (dBase)",
           "insee_sommaire", "https://www.insee.fr/fr/statistiques/2117120", "Licence Ouverte 2.0",
           years="1998-2013", granularity="mariage individuel, département de domicile",
           subpage=r"^Les mariages", include=(r"(?i)mar\d{4}_dbase\.zip$",)),
    Source("fr_insee_mariages_detail_2014_2021", "FR", "resultat",
           "INSEE — Fichiers détail mariages 2014-2021 (sommaires annuels)",
           "insee_sommaire", "|".join(f"https://www.insee.fr/fr/statistiques/{p}" for p in INSEE_ETAT_CIVIL_SOMMAIRES.values()),
           "Licence Ouverte 2.0", years="2014-2021", granularity="mariage individuel",
           subpage=r"^Les mariages", include=(r"(?i)(mar201[4-6]_dbase|mar20(1[7-9]|2[01])_csv)\.zip$",),
           exclude=(r"(?i)beyond",)),
    Source("fr_insee_mariages_detail_2022_2024", "FR", "resultat",
           "INSEE — Fichiers détail mariages 2022, 2023, 2024",
           "insee_page", "|".join(f"https://www.insee.fr/fr/statistiques/{p}" for p in INSEE_MAR_PAGES.values()),
           "Licence Ouverte 2.0", years="2022-2024", granularity="mariage individuel",
           notes="Constaté le 02/10/2026 : 2022 → 7759252 (etatcivil2022_mar2022_csv.zip), 2023 → 8603939, 2024 → 8899385 (FD_MAR_2024_csv.zip).",
           include=(r"(?i)(mar\d{4}_csv|FD_MAR_\d{4}_csv)\.zip$",)),
    Source("fr_insee_naissances_communes", "FR", "resultat",
           "INSEE (API Melodi) — Nombre de naissances domiciliées annuelles par commune, 2008-2025 (DS_ETAT_CIVIL_NAIS_COMMUNES)",
           "melodi", "DS_ETAT_CIVIL_NAIS_COMMUNES", "Licence Ouverte 2.0",
           years="2008-2025", granularity="commune (géographie courante), 34 875 communes",
           notes="Constaté le 02/10/2026 : CSV ';' (FREQ, GEO, GEO_OBJECT, EC_MEASURE, OBS_STATUS, TIME_PERIOD, OBS_VALUE). "
                 "Aucune série communale INSEE scriptable avant 2008 : la fenêtre communale commence en 2008 "
                 "(décision de mesure §10, consignée dans preregistration_addenda.md)."),
    Source("fr_insee_deces_communes", "FR", "resultat",
           "INSEE (API Melodi) — Nombre de décès annuels par commune, 2008-2025 (résultat placebo H5b)",
           "melodi", "DS_ETAT_CIVIL_DECES_COMMUNES", "Licence Ouverte 2.0", years="2008-2025", granularity="commune"),
    Source("fr_insee_estim_pop", "FR", "resultat",
           "INSEE (API Melodi) — Estimations localisées de population au 1er janvier par département, sexe et âge quinquennal, 1975-2026",
           "melodi", "DS_ESTIMATION_POPULATION", "Licence Ouverte 2.0",
           years="1975-2026", granularity="département × sexe × âge quinquennal",
           notes="Constaté le 02/10/2026 : EP_MEASURE = POP_JAN_1ST, AGE = Y15T19 … Y45T49, SEX = F."),
    Source("fr_insee_mar_pacs_series", "FR", "resultat",
           "INSEE (API Melodi) — Mariages (enregistrés, domiciliés), PACS, taux de nuptialité par département, séries longues",
           "melodi", "DS_MAR_PACS_DIV_SERIES", "Licence Ouverte 2.0",
           years="mariages dép. 1975-2024 ; PACS dép. 2007-2016 ; PACS France 1999-2024",
           granularity="département",
           notes="Constaté le 02/10/2026 : PACS par département seulement 2007-2016 dans cette série (tribunaux) ; "
                 "après 2017 pas de série départementale INSEE → canal PACS limité à 2007-2016 (dit dans le papier)."),
    Source("fr_insee_naissances_fecondite_series", "FR", "resultat",
           "INSEE (API Melodi) — Naissances, taux de fécondité, ICF, âge moyen à la maternité par département, séries longues",
           "melodi", "DS_NAISSANCES_FECONDITE_SERIES", "Licence Ouverte 2.0", granularity="département"),
    Source("fr_insee_populations_historiques", "FR", "resultat",
           "INSEE (API Melodi) — Populations municipales 1968-2023 (dénominateur communal total, géographie courante)",
           "melodi", "DS_POPULATIONS_HISTORIQUES", "Licence Ouverte 2.0", years="1968-2023", granularity="commune"),
    Source("fr_insee_rp_cfm", "FR", "resultat",
           "INSEE RP — Bases Couples-Familles-Ménages par commune : 2011 (var. 2006, 2011), 2016 (2011, 2016), 2021 (2010, 2015, 2021), 2022",
           "insee_page",
           "https://www.insee.fr/fr/statistiques/2044612|https://www.insee.fr/fr/statistiques/4171359|"
           "https://www.insee.fr/fr/statistiques/8205182|https://www.insee.fr/fr/statistiques/8582452",
           "Licence Ouverte 2.0", years="RP2006-RP2022 (millésimes glissants)", granularity="commune × sexe × âge × vie en couple",
           notes="Constaté le 02/10/2026 : base-cc-coupl-fam-men-2011.xls, base-cc-coupl-fam-men-2016-csv.zip, "
                 "base-cc-coupl-fam-men-2021_csv.zip (page 8205182), base-cc-coupl-fam-men-2022_csv.zip. Attention : le suffixe "
                 "« -COM » des fichiers INSEE désigne les collectivités d'outre-mer (5 lignes), pas les communes.",
           include=(r"(?i)(coupl-fam-men-2011\.xls|coupl-fam-men-2016-csv\.zip|coupl-fam-men-2021_csv\.zip|coupl-fam-men-2022_csv\.zip)$",)),
    Source("fr_insee_rp_pop_struct", "FR", "resultat",
           "INSEE RP — Bases Évolution et structure de la population par commune (sexe × âge) : 2011, 2016, 2021, 2022",
           "insee_page",
           "https://www.insee.fr/fr/statistiques/2044745|https://www.insee.fr/fr/statistiques/4171334|"
           "https://www.insee.fr/fr/statistiques/8201904|https://www.insee.fr/fr/statistiques/8581696",
           "Licence Ouverte 2.0", years="RP2006-RP2022", granularity="commune × sexe × âge",
           include=(r"(?i)evol-struct-pop-(2011\.zip|2016-csv\.zip|2021_csv\.zip|2022_csv\.zip)$",)),
    # ================================================================== France : exposition, contrôles, géo
    Source("fr_barometre_numerique", "FR", "exposition",
           "ARCEP / CGE / ANCT / Arcom (CREDOC) — Baromètre du numérique, microdonnées 2007-2025 et dictionnaire",
           "datagouv", "barometre-du-numerique", "ODbL",
           years="2007-2025", granularity="individu (âge, région, taille d'agglomération)",
           notes="Constaté le 02/10/2026 : barometre-du-numerique-2007-2025.csv (268 Mo) + dictionnaire-2007-2025.xlsx.",
           include=(r"2007-2025\.(csv|xlsx)$",)),
    Source("fr_insee_filosofi_2012", "FR", "controle",
           "INSEE — Filosofi 2012 : revenu disponible médian par commune (base-cc-filosofi-12.xls)",
           "insee_page", "https://www.insee.fr/fr/statistiques/1895078", "Licence Ouverte 2.0",
           years="2012", granularity="commune", include=(r"revenu-pauvrete-menage-2012\.zip$",)),
    Source("fr_insee_rp_activite", "FR", "controle",
           "INSEE RP — Activité des résidents 2011 (chômage par sexe × âge, diplômes) et Emploi-Population active 2016/2021",
           "insee_page",
           "https://www.insee.fr/fr/statistiques/2028668|https://www.insee.fr/fr/statistiques/4171446|"
           "https://www.insee.fr/fr/statistiques/8202916",
           "Licence Ouverte 2.0", years="RP2011, RP2016, RP2021", granularity="commune",
           notes="2011 : base infracommunale (IRIS) nationale, agrégée à la commune ; 2016 et 2021 : bases communales nationales.",
           include=(r"(?i)(infra-activite-resident-2011\.zip|emploi-pop-act-2016-csv\.zip|emploi-pop-active-2021_csv\.zip)$",)),
    Source("fr_insee_grille_densite", "FR", "controle",
           "INSEE — Grille communale de densité à 7 niveaux, 2015-2024",
           "insee_page", "https://www.insee.fr/fr/information/6439600", "Licence Ouverte 2.0", granularity="commune",
           include=(r"grille_densite_7_niveaux_(2015-2020\.zip|2024\.xlsx)$",)),
    Source("fr_insee_cog", "FR", "geo",
           "INSEE — Code officiel géographique au 1er janvier 2026 (communes, mouvements depuis 1943)",
           "insee_page", "https://www.insee.fr/fr/information/8740222", "Licence Ouverte 2.0", years="2026",
           notes="Constaté le 02/10/2026 : cog_ensemble_2026_csv.zip. Géographie cible du panel communal = COG 2026 "
                 "(celle des fichiers Melodi et ANFR) ; le COG 2024 (page 7766585) a été lu mais n'est pas la géographie cible "
                 "(déviation consignée dans preregistration_addenda.md).",
           include=(r"cog_ensemble_2026_csv\.zip$",)),
    Source("fr_dvf_statistiques", "FR", "controle",
           "Cerema / Etalab — Statistiques DVF agrégées par commune (prix, volumes)", "datagouv",
           "statistiques-dvf", "Licence Ouverte 2.0", years="2014-2024", granularity="commune",
           notes="Slug à vérifier ; non requis pour l'Étape 2."),
    # ================================================================== Europe
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
    # ================================================================== Panel international (descriptif)
    Source("wb_tfr", "WORLD", "panel", "Banque mondiale — ISF (SP.DYN.TFRT.IN)", "worldbank", "SP.DYN.TFRT.IN", "CC BY 4.0",
           notes="api.worldbank.org bloqué par la politique réseau au 02/10/2026."),
    Source("wb_mobile", "WORLD", "panel", "Banque mondiale — Abonnements mobiles pour 100 hab. (IT.CEL.SETS.P2)", "worldbank", "IT.CEL.SETS.P2", "CC BY 4.0"),
    Source("wb_internet", "WORLD", "panel", "Banque mondiale — Usagers d'Internet, % (IT.NET.USER.ZS)", "worldbank", "IT.NET.USER.ZS", "CC BY 4.0"),
    Source("wb_gdp", "WORLD", "panel", "Banque mondiale — PIB/hab. PPA constant (NY.GDP.PCAP.PP.KD)", "worldbank", "NY.GDP.PCAP.PP.KD", "CC BY 4.0"),
    Source("owid_mobile_broadband", "WORLD", "panel", "ITU via OWID — Abonnements haut débit mobile pour 100 hab.", "owid",
           "mobile-broadband-subscriptions-per-100-people", "CC BY 4.0", notes="ourworldindata.org bloqué au 02/10/2026."),
    Source("un_wpp_asfr", "WORLD", "panel", "UN WPP 2024 — Taux de fécondité par groupe d'âge quinquennal, tous pays", "direct",
           "https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/WPP2024_Fertility_by_Age5.csv.gz",
           "CC BY 3.0 IGO", years="1950-2023", granularity="pays × âge",
           notes="Nom de fichier non confirmé ; repli : API dataportalapi, indicateur ASFR5."),
    Source("itu_coverage", "WORLD", "panel", "ITU DataHub — Population couverte par au moins un réseau 3G / LTE (indicateur 100095)", "manual",
           "https://datahub.itu.int/data/?i=100095", "ITU (conditions à vérifier)", years="≈2010-2023", granularity="pays",
           notes="datahub.itu.int bloqué au 02/10/2026."),
    # ================================================================== Pays de niveau 1 (addendum requis avant estimation)
    Source("es_cobertura_2013_2021", "ES", "traitement",
           "MINECO/SETID — Base de datos histórica 2013-2021 de cobertura de banda ancha fija y móvil (LTE par entidad singular)",
           "manual", "https://datos.gob.es/en/catalogo/e05068901-base-de-datos-historica-desde-2013-a2020-de-cobertura-banda-ancha-fija-y-movil",
           "datos.gob.es (licence du jeu à vérifier)", years="2013-2021", granularity="entidad singular de población",
           notes="datos.gob.es bloqué au 02/10/2026."),
    Source("es_ine_nacimientos", "ES", "resultat", "INE — Estadística de nacimientos, microdonnées", "manual",
           "https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736177007&menu=resultados&secc=1254736195443&idp=1254735573002",
           "INE (réutilisation libre avec mention)", granularity="naissance, commune de résidence (seuil de taille)"),
    Source("se_pts_tackning", "SE", "traitement", "PTS — Mobiltäcknings- och bredbandskartläggning, par kommun, 2013+", "manual",
           "https://statistik.pts.se/mobiltacknings-och-bredbandskartlaggning", "PTS", years="2013 →", granularity="kommun"),
    Source("se_scb_fodda", "SE", "resultat", "SCB — Födda efter region, moderns ålder och barnets kön (FoddaK), API PxWeb", "manual",
           "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/BE/BE0101/BE0101H/FoddaK", "SCB (CC0)", years="1968-2024", granularity="kommun × âge",
           notes="Requête POST PxWeb à écrire."),
    Source("br_anatel_acessos", "BR", "traitement", "Anatel — Acessos SMP por município e tecnologia (mensuel)", "manual",
           "https://www.anatel.gov.br/dadosabertos/PDA/Acessos/", "Dados abertos (licence à vérifier)", years="2007 →", granularity="município"),
    Source("br_anatel_cobertura", "BR", "traitement", "Anatel — Cobertura da telefonia móvel por setor censitário", "manual",
           "https://www.anatel.gov.br/dadosabertos/PDA/Cobertura_Movel/", "Dados abertos", granularity="secteur censitaire → município"),
    Source("br_sinasc", "BR", "resultat", "DATASUS — SINASC microdonnées (DN{UF}{AAAA}.dbc)", "manual",
           "ftp://ftp.datasus.gov.br/dissemin/publicos/SINASC/NOV/DNRES/", "DATASUS (ouvert)", years="1996 →", granularity="naissance, município",
           notes="FTP : ne passe pas par le proxy HTTPS (constaté 02/10/2026) ; repli PCDaS/Fiocruz."),
    Source("br_sidra_casamentos", "BR", "resultat", "IBGE SIDRA — Tabela 4412, casamentos por idade dos cônjuges, município", "manual",
           "https://apisidra.ibge.gov.br/values/t/4412/n6/all", "IBGE", granularity="município × âge",
           notes="apisidra.ibge.gov.br bloqué au 02/10/2026."),
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
