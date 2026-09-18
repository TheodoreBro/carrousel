# Étape 0 — Plan, sources, faisabilité du design, incertitudes

Working paper : *Smartphones, réseaux sociaux, applications de rencontre et fécondité — y a-t-il un effet causal au-delà des adolescentes ?*

Statut : **en attente de validation avant tout téléchargement** (règle du déroulé, Étape 0).
Date : 18 septembre 2026. Aucune donnée n'a été téléchargée. Aucun fichier n'a été créé dans `data/`.

Ce document a été produit sans accès aux sites des producteurs de données (voir §1) : l'existence, la
couverture temporelle et la structure des sources ont été vérifiées uniquement par recherche web
(titres, identifiants de tables, documentation indexée). Tout ce qui est marqué « à confirmer » sera
re-vérifié au téléchargement et consigné dans `docs/data_log.md`.

---

## 0. Résumé exécutif

1. **Bloqueur : la politique réseau de l'environnement refuse toutes les connexions vers les sources
   primaires** (data.gouv.fr, INSEE, ANFR, ARCEP, Eurostat, Banque mondiale, KOSIS, FCC, CDC, OWID, Pew,
   éditeurs scientifiques, doi.org, CRAN). Seuls PyPI, les dépôts Ubuntu et l'API GitHub répondent.
   Sans changement de la politique réseau (mode « unrestricted » ou liste d'autorisation, §1.3), les
   Étapes 2 à 4 ne peuvent pas être exécutées conformément à la règle 1 (données réelles téléchargées
   depuis les sources primaires). Je m'arrête donc ici et je le dis, comme demandé.
2. **France : le design causal est faisable, à deux niveaux.** (i) Commune × année (≈ 34 900 communes,
   naissances domiciliées 2004-2024, bascule 4G datée par les émetteurs ANFR 2012-2020) pour l'effet
   sur la fécondité totale ; (ii) département × groupe d'âge × année (naissances 1998-2025 et mariages
   1998-2024 avec l'âge, fichiers détail INSEE) pour le test central par âge et la décomposition du
   canal. Le niveau commune ne permet **pas** l'âge de la mère (les fichiers détail n'ont que le
   département de domicile) : c'est la principale contrainte du design.
3. **Corée du Sud : pas de variation infranationale exploitable.** LTE lancé en juillet 2011, réseau
   national achevé en avril 2012 (LG U+), donc moins d'un an de décalage entre territoires, non
   observé au niveau sigungu. De plus l'API KOSIS exige une clé (compte). → Cas descriptif seulement.
4. **États-Unis : traitement disponible, résultat non reproductible.** La couverture LTE par bloc
   existe (NTIA 2010-2014, FCC 477 2014-2021), mais l'API de CDC WONDER interdit tout regroupement
   géographique ; les comptés × âge de la mère ne sont accessibles que par l'interface web (≥ 100 000
   habitants) ou par fichiers NCHS restreints. → Cas descriptif national par âge seulement, sauf si
   vous disposez d'un accès NCHS restreint.
5. **Europe (NUTS 2) : panel descriptif.** Fécondité par âge NUTS 2 (Eurostat 1990-2024) disponible,
   mais aucune mesure régionale d'Internet *mobile* ni de couverture 4G en données ouvertes tabulaires ;
   seule la part d'internautes réguliers (isoc_r_iuse_i) existe, NUTS 2 optionnel. → Faits stylisés,
   jamais utilisé pour conclure.
6. **Outillage :** pile Python complète installée et vérifiée (pandas 3.0, statsmodels 0.15,
   linearmodels 7.0, pyfixest 0.60, csdid 0.4, differences 0.3). R est installable via apt mais sans
   `fixest`/`did` (CRAN bloqué, paquets absents d'Ubuntu) → l'estimateur de Chaisemartin & D'Haultfœuille
   n'est disponible ni en Python ni en R dans cet environnement (voir §6, U7). LaTeX (TeX Live)
   installable via apt.
7. **Décisions à valider** : §7 (emplacement dans le dépôt, périmètre des cas secondaires, définition
   du traitement principal, fenêtre temporelle, accès réseau).

---

## 1. Environnement d'exécution : ce qui marche, ce qui bloque

### 1.1 Réseau (testé le 18/09/2026 depuis le conteneur et via l'outil de fetch)

| Hôte | Rôle | Statut |
|---|---|---|
| www.data.gouv.fr, static/files/object.files.data.gouv.fr | ANFR, ARCEP, INSEE (miroirs), Baromètre du numérique, DVF | **bloqué (403, politique d'organisation)** |
| www.insee.fr, api.insee.fr | fichiers détail état civil, RP, estimations de population | **bloqué** |
| data.anfr.fr, data.arcep.fr | observatoire ANFR, couvertures ARCEP | **bloqué** |
| www.justice.gouv.fr, stats.justice.gouv.fr | PACS | **bloqué** |
| ec.europa.eu (API Eurostat) | demo_r_frate2, isoc_* | **bloqué** |
| api.worldbank.org, population.un.org, ourworldindata.org | panel international | **bloqué** |
| kosis.kr, www.data.go.kr, www.msit.go.kr | Corée | **bloqué** |
| wonder.cdc.gov, data.cdc.gov, www.fcc.gov, broadbandmap.fcc.gov, www2.ntia.gov | États-Unis | **bloqué** |
| www.pewresearch.org | possession smartphone / applis par âge | **bloqué** |
| doi.org, tandfonline.com, link.springer.com, pnas.org, journals.plos.org, nber.org, ideas.repec.org | vérification des références | **bloqué** |
| cran.r-project.org, cloud.r-project.org | paquets R | **bloqué** |
| pypi.org, files.pythonhosted.org | paquets Python | ok |
| archive.ubuntu.com, security.ubuntu.com | apt (R, TeX Live) | ok |
| api.github.com | dépôt | ok |
| recherche web (outil WebSearch) | vérification d'existence uniquement | ok |

Le README du proxy indique de ne pas contourner ces refus et de les signaler. C'est ce que je fais.

### 1.2 Outils

| Outil | Statut | Remarque |
|---|---|---|
| Python 3.11 + pandas, numpy, scipy, statsmodels, linearmodels | installé (venv), versions dans `requirements.txt` | |
| pyfixest 0.60 | installé | `feols`, `fepois` (Poisson à effets fixes), `event_study` (TWFE, did2s de Gardner), `SaturatedEventStudy` (interactions cohorte × période, type Sun & Abraham), `lpdid` |
| csdid 0.4.2, drdid, differences 0.3 | installés | Callaway & Sant'Anna (ATT(g,t), agrégations dynamiques/cohortes, doubly robust) |
| de Chaisemartin & D'Haultfœuille (`did_multiplegt_dyn`) | **indisponible** | pas sur PyPI ; version R sur CRAN (bloqué) ; pas dans Ubuntu |
| R 4.x (`r-base-core`) | installable via apt | `r-cran-fixest` et `r-cran-did` **absents** des dépôts Ubuntu ; CRAN bloqué → R inutile en l'état |
| TeX Live (`texlive-latex-extra`, `texlive-lang-french`, `biber`, `latexmk`) | installable via apt (non installé) | route LaTeX → `paper.pdf` possible |
| pandoc 3.9 (via `pypandoc_binary`) + weasyprint 70 | installés | route de secours HTML → PDF si TeX Live échoue |
| Quarto | indisponible | |

Ressources : 4 cœurs, 15 Go de RAM, ~30 Go d'espace disque. Suffisant pour les fichiers ANFR
(~0,5 Go), les fichiers détail INSEE (~0,8 M lignes/an) et les bases communales du RP. Les données FCC
477 par bloc (plusieurs Go par millésime) ne seraient pas traitées dans ce conteneur de toute façon.

### 1.3 Ce qu'il faut pour lever le bloqueur

Option A (recommandée) : passer l'environnement en accès réseau « unrestricted » dans la
configuration de l'environnement Claude Code (documentation :
https://code.claude.com/docs/en/claude-code-on-the-web).
Option B : liste d'autorisation minimale pour le cœur France + panel + références :
`www.data.gouv.fr`, `static.data.gouv.fr`, `files.data.gouv.fr`, `object.files.data.gouv.fr`,
`www.insee.fr`, `api.insee.fr`, `catalogue-donnees.insee.fr`, `data.anfr.fr`, `www.anfr.fr`,
`data.arcep.fr`, `www.arcep.fr`, `www.legifrance.gouv.fr`, `www.justice.gouv.fr`,
`stats.justice.gouv.fr`, `datafoncier.cerema.fr`, `www.credoc.fr`, `ec.europa.eu`,
`api.worldbank.org`, `population.un.org`, `ourworldindata.org`, `api.ourworldindata.org`,
`www.pewresearch.org`, `doi.org`, `www.tandfonline.com`, `link.springer.com`, `www.pnas.org`,
`journals.plos.org`, `www.nber.org`, `ideas.repec.org`, `papers.ssrn.com`, `arxiv.org`,
plus `cloud.r-project.org` si vous voulez l'estimateur dCDH en R, et `kosis.kr`, `www.data.go.kr`,
`www.msit.go.kr`, `wonder.cdc.gov`, `data.cdc.gov`, `www2.ntia.gov`, `www.fcc.gov`,
`us-fcc.app.box.com` pour les cas secondaires.
Option C (dégradée, non recommandée) : vous téléchargez les fichiers et les déposez dans `data/raw/`
avec l'URL et la date ; le pipeline vérifie les empreintes SHA-256 consignées dans `data_log.md`.
Cela respecte « données réelles uniquement » mais pas « tout régénérer en une commande ».

---

## 2. Plan de travail

| Étape | Contenu | Livrables | Condition |
|---|---|---|---|
| 0 (ce document) | plan, sources, faisabilité, incertitudes | `docs/etape0_plan.md`, `requirements.txt` | validation de votre part |
| 1 | préregistration : hypothèses par âge et par canal, spécifications, règles de décision, puissance attendue | `docs/preregistration.md` (gelé ensuite, hash du commit cité dans le papier) | validation Étape 0 |
| 2 | téléchargement (`01_download.py`), journal des données, construction du traitement (`02_treatment.py`), des résultats (`03_outcomes.py`), rapport d'unités-années par spécification et first stage | `data/raw`, `data/processed`, `docs/data_log.md`, `tables/t_sample.md`, `tables/t_firststage.*` | réseau ouvert |
| 3 | estimations (`04_estimate.py`), figures (`05_figures.py`), tableaux (`06_tables.py`) | `figures/*.pdf`, `tables/*.tex` | Étape 2 |
| 4 | rédaction, relecture chiffre par chiffre, références vérifiées, compilation | `paper/paper.md`, `paper/paper.pdf`, `paper/references.bib` | Étape 3 |

Commande unique de régénération prévue : `make all` (ou `python run_all.py`) → téléchargement →
traitement → estimations → figures/tableaux → PDF.

---

## 3. Inventaire des sources

Légende « Vérif. » : **C** = existence et contenu confirmés par recherche web (titre, identifiant,
documentation indexée) ; **P** = partiellement confirmé, détails à vérifier au téléchargement ;
**N** = non confirmé.

### 3.1 Traitement (déploiement des réseaux)

| # | Source | Contenu | Granularité | Années | Accès | Vérif. |
|---|---|---|---|---|---|---|
| T1 | ANFR, *Données sur les installations radioélectriques de plus de 5 watts* (data.gouv.fr, data.anfr.fr) | tables SUP_STATION, SUP_SUPPORT, SUP_EMETTEUR (`EMR_LB_SYSTEME` = GSM/UMTS/LTE/NR par bande, `EMR_DT_SERVICE` = date de mise en service de l'émetteur), SUP_ANTENNE ; code commune INSEE | émetteur → commune | photographie courante, dates de service remontant aux années 2000 ; export mensuel | licence ouverte ; ~0,5 Go | C |
| T2 | ANFR, *Observatoire 2G, 3G, 4G, 5G* (data.gouv.fr, data.anfr.fr `observatoire_2g_3g_4g`) | par support × opérateur × génération : statut (en service / autorisé), date, `code_insee` ; ~825 000 enregistrements, 516 Mo ; archives mensuelles depuis 2015 sur anfr.fr | support → commune, mensuel | 2015-2026 (archives), dates de service antérieures | licence ouverte | C |
| T3 | ARCEP, *Mon réseau mobile* / `data.arcep.fr/mobile/couvertures_theoriques` | taux de couverture 2G/3G/4G par commune et opérateur (population, surface), « bonne couverture » / « couverture limitée » | commune, trimestriel | 2017-T4 → 2026 | licence ouverte | C |
| T4 | ARCEP, décision n° 2011-0600 (Légifrance) | liste des communes de la **zone de déploiement prioritaire** (ZDP) 800 MHz : 22 500 communes, 18 % de la population, 63 % du territoire ; obligation de couvrir 40 % de la population de la ZDP au 17/01/2017 (Orange, SFR, Bouygues) | commune (statut fixe) | fixé en 2011 | Légifrance (bloqué) | C |
| T5 | ARCEP, *Les grandes dates de la 4G* ; observatoire des zones peu denses | calendrier des lancements commerciaux (2012-2013), obligations | national | 2012-2022 | arcep.fr | P |
| T6 | Corée : MSIT, *무선통신서비스 가입 현황* (statistiques mensuelles d'abonnements sans fil, dont LTE et smartphones, par 시도) ; miroir data.go.kr | abonnés LTE / smartphone par province | province (17), mensuel | ≈ 2011-2026 | fichiers xlsx (bloqué) | P (province × mois à confirmer) |
| T7 | États-Unis : NTIA *National Broadband Map* / State Broadband Initiative | couverture sans fil mobile par bloc de recensement, technologie, vitesse annoncée | bloc → comté | déc. 2010 → juin 2014 (semestriel) | www2.ntia.gov (bloqué) ; plusieurs Go | C |
| T8 | États-Unis : FCC Form 477 *Mobile Deployment* | couverture par fournisseur × technologie (LTE, HSPA, EV-DO…) par bloc (centroïde) | bloc → comté | 2014 → déc. 2021 | fcc.gov / Box (bloqué) ; plusieurs Go par millésime | C |
| T9 | Europe : Eurostat `isoc_r_iuse_i` | individus utilisant régulièrement Internet, régions | NUTS 1 obligatoire, NUTS 2 optionnel | 2006-2025 | API Eurostat (bloqué) | C |
| T10 | Europe : DG CONNECT, *Broadband Coverage in Europe* (IHS/Point Topic/Omdia) | couverture LTE par NUTS 3 | NUTS 3 | 2011-2022 | rapports PDF ; tableaux NUTS 3 non trouvés en données ouvertes | P → probablement inutilisable |

### 3.2 Résultats (fécondité, mise en couple)

| # | Source | Contenu | Granularité | Années | Vérif. |
|---|---|---|---|---|---|
| R1 | INSEE, *Fichiers détail état civil – naissances* | une ligne par naissance : `AGEMERE`, `DEPDOM` (département de domicile), `TUDOM` (tranche d'unité urbaine), `AMAR` (année de mariage des parents → naissance dans/hors mariage), `NBENF` (rang), `SITUATMR` (situation professionnelle de la mère). **Pas de commune.** | département × âge | 1998-2013 (série « Naissances, décès et mariages de 1998 à 2013 »), puis annuel 2014-2025 | C |
| R2 | INSEE, *Naissances domiciliées annuelles par commune* (`DS_ETAT_CIVIL_NAIS_COMMUNES`, « Naissances et décès domiciliés 2014-2023 ») + data.gouv.fr *Naissances de 2004 à 2015 par commune* | comptes annuels de naissances par commune de domicile de la mère, sans âge | commune | 2004-2015 et 2014-2024 → 2004-2024 après raccord | C (raccord des deux séries à vérifier) |
| R3 | INSEE, *Fichiers détail état civil – mariages* | âge des époux, `DEPDOM` / département de mariage, année ; ~230-250 000 lignes/an | département × âge | 1998-2024 | C |
| R4 | Ministère de la Justice, cube `PACS_CON_TI` (stats.justice.gouv.fr) ; INSEE bilan démographique départemental (PACS depuis 2017, enregistrement en mairie) | PACS conclus par département ; âge moyen seulement | département | 1999-2016 (tribunaux), 2017-2024 (INSEE) | P |
| R5 | INSEE RP, base *Couples – Familles – Ménages* (millésimes annuels) | population de 15 ans ou plus par sexe, tranche d'âge (15-19, 20-24, 25-39, 40-54, 55-79, 80+) et vie en couple | commune | RP2006 → RP2022 (millésimes glissants sur 5 ans) | P (noms exacts des variables à lire dans le dictionnaire) |
| R6 | INSEE, *Estimations de population par département, sexe et âge quinquennal* (`estim-pop-dep-sexe-aq`) | dénominateurs département × âge | département | 1975-2025 | C |
| R7 | INSEE RP, base *Évolution et structure de la population* | population par sexe et âge par commune (dénominateurs communaux) | commune | RP2006 → RP2022 | C |
| R8 | Eurostat `demo_r_frate2` | taux de fécondité par âge, NUTS 2 (491 461 cellules, MAJ 03/09/2026) | NUTS 2 × âge | 1990-2024 | C |
| R9 | Eurostat `demo_frate`, `demo_nind`, `demo_find` | taux par âge, nuptialité, ISF nationaux | pays | 1960-2024 | C |
| R10 | KOSIS `DT_1B81A28` (naissances par sigungu × âge de la mère, 5 ans), `DT_1B81A17` (ISF et taux par âge par sigungu), `DT_1B83A15` (mariages par sigungu) | Corée, infranational | sigungu (≈ 250) | ≈ 1997/2000-2025 | C (identifiants) ; accès API sur clé |
| R11 | CDC WONDER *Natality 2007-2024* | naissances par âge de la mère ; comté seulement si ≥ 100 000 hab. ; **API sans regroupement géographique** | national par âge (API) | 2007-2024 | C |
| R12 | Pew Research Center (2013, 2015, 2019, 2022) | usage des sites/applis de rencontre par âge (18-29 : 53 % en 2022 ; 30-49 : 37 %) | pays × âge | 4 vagues | C |

### 3.3 Exposition (adoption, usage)

| # | Source | Contenu | Granularité | Années | Vérif. |
|---|---|---|---|---|---|
| E1 | CREDOC / ARCEP / CGE, *Baromètre du numérique* — microdonnées sur data.gouv.fr depuis 2007 | équipement smartphone, usages (réseaux sociaux), par âge, région, taille d'unité urbaine ; n ≈ 2 000-4 000/an | individu → région × âge × année | 2007-2025 | C (microdonnées annoncées en open data ; variables région à vérifier) |
| E2 | Eurostat `isoc_ci_im_i` / `isoc_cimobi_dev` | usage d'Internet mobile hors domicile par âge | pays × âge | 2012-2023 | C |
| E3 | Eurostat `isoc_ci_ac_i` | usage des réseaux sociaux par âge | pays × âge | 2011-2025 | C |
| E4 | Pew, *Mobile Fact Sheet* | possession de smartphone par âge, États-Unis | pays × âge | 2011-2025 | C |
| E5 | ITU via OWID (`mobile-broadband-subscriptions`), Banque mondiale `IT.CEL.SETS.P2`, `IT.NET.USER.ZS` | adoption nationale | pays | 2000-2024 | C |
| E6 | Applications de rencontre : Pew (US), Google Trends (proxy), Sensor Tower/data.ai (payant, non utilisé) | pas de série pays-année homogène | — | — | à documenter comme tel |
| E7 | DataReportal / Kepios | usagers des réseaux sociaux par pays | pays | 2012-2026 | P (rapports, pas de tableau homogène) |

### 3.4 Contrôles (France)

| # | Source | Contenu | Granularité | Années | Vérif. |
|---|---|---|---|---|---|
| C1 | INSEE Filosofi | revenu disponible médian | commune | 2012-2021 | C |
| C2 | INSEE RP, base *Activité des résidents* | chômage 15-24 / 25-54, part de diplômées du supérieur | commune, millésimes | 2006-2022 | C |
| C3 | INSEE, grille communale de densité, zonage en aires d'attraction des villes | urbanisation | commune | fixe | C |
| C4 | Cerema DV3F, *indicateurs de marchés immobiliers* (data.gouv.fr « Statistiques DVF ») | prix médian au m², volumes | commune, EPCI | 2010-2024 | C |
| C5 | CAF / ONAPE, capacités d'accueil petite enfance (data.caf.fr) | places EAJE, assistantes maternelles | commune / département | 2016-2024 | P |
| C6 | ARCEP, observatoire haut débit fixe (ADSL/fibre par commune) | contrôle du canal « Internet fixe » | commune | 2017-2026 | P |
| C7 | INSEE, Code officiel géographique (COG) et tables de passage | harmonisation des communes nouvelles 2015-2024 | commune | annuel | C |

### 3.5 Panel international (descriptif)

Banque mondiale `SP.DYN.TFRT.IN`, `IT.CEL.SETS.P2`, `IT.NET.USER.ZS`, `NY.GDP.PCAP.PP.KD` ;
UN WPP 2024 (ISF, taux par âge) ; ITU via OWID (haut débit mobile). Tous confirmés (identifiants
standard), tous bloqués actuellement.

---

## 4. Faisabilité du design causal, pays par pays

### 4.1 France — cœur du papier

**Variation infranationale réelle.**
- *4G* : lancements commerciaux entre mi-2012 et fin 2013 selon l'opérateur, d'abord dans les grandes
  villes ; extension aux villes moyennes 2014-2015 ; zones rurales 2015-2019 (obligation ZDP au
  17/01/2017, puis « New Deal mobile » 2018). Les dates de mise en service des émetteurs LTE (T1/T2)
  donnent, pour chaque commune, l'année du premier émetteur 4G en service : cohortes 2012 → 2020,
  avec une masse importante en 2014-2017. C'est de la vraie variation échelonnée, avec 8+ années de
  pré-période pour les cohortes tardives (naissances communales dès 2004).
- *3G* : émetteurs UMTS 2004-2012. La photographie ANFR ne contient que les supports encore existants
  → biais de survie pour les dates anciennes ; et la pré-période communale (2004) est trop courte pour
  les cohortes 3G précoces. La 3G sera traitée en robustesse (cohortes 2008-2012) et en descriptif,
  pas comme design principal.
- *Couverture effective (T3)* : à partir de 2017-T4 seulement, mais elle capte une variation
  différente : passage de « couverture limitée » à « bonne couverture », et couverture par les 4
  opérateurs. Elle sert (a) à valider la mesure par émetteurs, (b) à une seconde définition du
  traitement (année où ≥ 90 % de la population communale est couverte par ≥ 1 puis par 4 opérateurs),
  sur la fenêtre 2014-2024.
- *ZDP (T4)* : appartenance fixée en 2011 par une règle de densité. Elle a avancé la 4G dans une
  partie des communes rurales par rapport à des communes rurales comparables hors ZDP. Utilisable
  comme instrument du calendrier (ou comme triple différence) chez les communes peu denses.

**Mesures de traitement retenues (à préciser en préregistration).**
- D1 (principale) : `4G_{c,t} = 1` si au moins un émetteur LTE en service dans la commune *c* au
  1er janvier de l'année *t* (ANFR, T1 recoupé avec T2). Variante : au moins deux opérateurs.
- D2 : part de la population communale couverte en 4G (ARCEP, T3), fenêtre 2017-2024 ; bascule
  définie au franchissement de 90 %.
- D3 : exposition départementale = part de la population du département résidant dans une commune
  traitée (D1), pondérée par la population des femmes de 15-49 ans → variable continue échelonnée,
  utilisée pour le niveau département × âge.
- Limite écrite noir sur blanc : couverture ≠ adoption ≠ usage. Le first stage (§5.6) mesure le lien
  couverture → adoption avec le Baromètre du numérique (E1).

**Résultats et niveaux.**

| Niveau | Unités | Années | Résultats | Rôle |
|---|---|---|---|---|
| Commune × année | ≈ 34 900 (géographie 2024 harmonisée) | 2004-2024 (21 ans) → ≈ 730 000 unités-années | naissances domiciliées (R2) ; naissances pour 1 000 femmes 15-49 (R7) ; part des femmes 15-24 / 25-39 en couple (R5, millésimes) | effet sur la fécondité totale, event study, placebos, hétérogénéité par densité/ZDP |
| Département × groupe d'âge × année | 96 + 5 DOM ; âges 15-19, 20-24, 25-29, 30-34, 35-39, 40-49 | 1998-2025 (28 ans) → ≈ 17 000 | taux de fécondité par âge (R1/R6) ; taux de nuptialité par âge (R3) ; PACS (R4, sans âge) ; naissances dans/hors mariage (R1 `AMAR`) ; femmes en couple par âge (R5 agrégé) | **test central 25 ans et plus**, décomposition du canal |
| Région × âge × année | 13 régions (22 avant 2016) | 2011-2025 | possession de smartphone, usage des réseaux sociaux (E1) | first stage, IV |

**Contraintes et réponses.**
1. *Pas d'âge de la mère au niveau commune.* Réponse : la question centrale (effet net sur les 25+)
   est testée au niveau département avec traitement continu échelonné (D3), 28 années dont 14 avant
   la 4G. Le niveau commune fournit l'effet total avec la meilleure identification. Les deux niveaux
   doivent être cohérents (l'effet total communal doit se retrouver dans la somme des effets par âge).
2. *Déploiement ciblé sur les zones denses.* Réponse : tendances parallèles conditionnelles
   (Callaway & Sant'Anna avec covariables de pré-période : densité, revenu, diplôme, tendance
   1999-2011 des naissances), comparaison restreinte aux communes de même classe de densité, et
   instrument ZDP.
3. *Biais de survie ANFR pour les dates anciennes.* Réponse : recoupement avec les archives mensuelles
   de l'observatoire (2015-2026) pour les cohortes 2015+, et avec la couverture ARCEP 2017-T4 ; les
   cohortes 2012-2014 sont marquées comme moins fiables et exclues en robustesse.
4. *Communes nouvelles (≈ 2 500 fusions 2015-2019).* Réponse : agrégation à la géographie 2024 via
   les tables de passage du COG (C7), sur toute la période.
5. *Petits effectifs (médiane ≈ 3 naissances/an par commune).* Réponse : Poisson à effets fixes
   (`fepois`), et agrégats par cohorte ; les erreurs standard sont groupées au niveau de la commune
   (niveau du traitement), avec vérification au niveau département.
6. *Chocs concurrents* : crise 2008-2009, réforme des allocations 2014-2015 (modulation, congé
   parental), déploiement du très haut débit fixe, COVID 2020-2021. Réponse : effets fixes année ×
   classe de densité, contrôle de la couverture fixe (C6), exclusion de 2020-2021 en robustesse.
7. *RP en millésimes glissants* : la part de femmes en couple au niveau commune est une moyenne sur 5
   ans → réponse retardée et lissée, à interpréter comme borne inférieure de l'effet de calendrier ;
   l'analyse du canal repose surtout sur les mariages par âge (annuels, département).

**Puissance.** Un calcul de taille d'effet minimale détectable (simulation par permutation de dates
de bascule fictives sur les vraies données) sera fait à l'Étape 2, avant toute estimation, et rapporté
dans le papier. Ordre de grandeur attendu : quelques pour cent des naissances au niveau commune ;
au niveau département × âge, un effet inférieur à 2-3 % d'un taux par âge sera probablement
indétectable — ce sera dit.

### 4.2 Corée du Sud — pas de design causal

- LTE : SK Telecom en juillet 2011, LG U+ réseau national achevé en avril 2012, KT à partir de
  janvier 2012 ; couverture des 84 villes fin 2011 et de l'ensemble du pays en 2012-2013. La variation
  entre sigungu tient en 12 à 18 mois, et aucune source publique ne la mesure au niveau sigungu.
- MSIT publie des abonnements LTE / smartphone par province (17) et par mois : une intensité
  d'adoption, pas un calendrier de couverture ; corrélé au revenu et à l'âge de la population.
- KOSIS : tables sigungu × âge de la mère confirmées, mais l'API exige une clé liée à un compte ; le
  téléchargement web n'est pas scriptable proprement.
- Recommandation : **descriptif national et provincial** (calendrier smartphone → mariage → fécondité
  par âge), section faits stylisés, sans inférence. Si vous fournissez une clé API KOSIS, j'ajoute un
  panel province × âge en descriptif ; je ne présenterai pas d'estimation « causale » Corée.

### 4.3 États-Unis — traitement disponible, résultats non reproductibles

- Traitement : NTIA (déc. 2010-juin 2014, tout le déploiement LTE de Verizon/AT&T) puis FCC 477
  (2014-2021) au niveau bloc. Lourd (plusieurs Go/millésime) mais faisable si l'on agrège par comté.
- Résultats : CDC WONDER expose comté × âge de la mère uniquement pour les comtés ≥ 100 000 habitants
  (≈ 600 comtés, presque tous couverts tôt) **et son API interdit tout regroupement par lieu** ; les
  fichiers publics NCHS n'ont plus de géographie infra-État depuis 2005 ; les fichiers restreints
  exigent un accord d'utilisation. Un pipeline reproductible ne peut donc pas produire de panel
  comté × âge × année.
- Recommandation : **descriptif national par âge** (WONDER via API, national seulement ; Pew pour
  smartphone et applis par âge). Si vous disposez d'un accès NCHS restreint, le design comté ×
  âge devient possible et je le préregistre séparément.

### 4.4 Europe (NUTS 2) — panel descriptif

- Résultats solides (taux de fécondité par âge NUTS 2, 1990-2024) ; mais le traitement régional se
  réduit à la part d'internautes réguliers (pas mobile, NUTS 2 optionnel, séries incomplètes), et la
  couverture LTE NUTS 3 de la Commission n'est publiée qu'en rapports.
- Recommandation : faits stylisés (datation des ruptures 2010-2015 par région ; corrélation
  intra-pays entre progression de l'usage d'Internet et baisse de la fécondité par âge, avec effets
  fixes région et pays × année), présentés comme non causaux.

### 4.5 Panel international — descriptif uniquement, conformément au cahier des charges.

---

## 5. Stratégie empirique proposée (résumé ; détail en préregistration)

5.1 **Effet total, commune × année (2004-2024)** : DiD échelonné sur D1 avec (a) Callaway & Sant'Anna
(`differences`/`csdid`, contrôle = jamais traités puis pas-encore-traités, covariables de pré-période),
(b) event study saturée cohorte × période (Sun & Abraham, `pyfixest.SaturatedEventStudy`),
(c) did2s de Gardner, (d) TWFE naïf rapporté à titre de comparaison. Poisson à effets fixes pour les
comptes, log-taux pour les taux. Au moins 3 périodes pré-traitement affichées (jusqu'à 8). Erreurs
standard groupées par commune ; robustesse au niveau département. Estimateur dCDH : uniquement si CRAN
est accessible (§6, U7) ; sinon absence signalée.

5.2 **Effet par âge, département × âge × année (1998-2025)** : traitement continu échelonné D3 ;
event study sur l'année où D3 franchit 50 % (puis 90 %) avec Callaway & Sant'Anna ; spécification
continue avec effets fixes département × âge et année × âge. Test central : coefficients 25-29, 30-34,
35-39 vs 15-19, 20-24, et test d'égalité.

5.3 **Décomposition du canal** : (a) mariages pour 1 000 femmes par âge, PACS pour 1 000 femmes
(département), part des femmes en couple par âge (RP) ; (b) naissances pour 1 000 femmes en couple
par âge (numérateur R1, dénominateur R5 agrégé au département) ; (c) fécondité totale par âge.
Conclusion sur le canal dominant seulement si (a) et (b) sont statistiquement distinguables (test de
différence des coefficients, même échantillon, mêmes années).

5.4 **Hétérogénéité** : par âge (5.2), par densité (grille INSEE), ZDP / hors ZDP, par revenu
communal, par part de diplômées.

5.5 **Robustesse** : fenêtres 2008-2019 et 2004-2024 ; exclusion des unités urbaines > 200 000 hab. ;
placebo bascule décalée de −3 ans ; résultat placebo (décès des 60 ans et plus, ou naissances
2004-2011 sur cohortes futures) ; D1 vs D2 ; cohortes 2012-2014 exclues ; contrôle haut débit fixe ;
exclusion 2020-2021 ; groupage département.

5.6 **First stage et IV** : Baromètre du numérique (E1) : possession de smartphone par région × âge ×
année régressée sur l'exposition 4G régionale (D3 agrégée). 2SLS au niveau région × âge × année
uniquement, présenté comme re-normalisation de la forme réduite. Restriction d'exclusion discutée
explicitement (emploi, télétravail, information, services publics en ligne) et testée partiellement :
effet de la 4G sur l'emploi des femmes 25-39 (RP) comme canal concurrent.

5.7 **Faits stylisés** (sans inférence) : ISF et adoption par groupe de revenu (panel international) ;
datation des ruptures par pays (Finlande, Norvège, Corée, États-Unis, France) par tests de rupture
structurelle ; superposition des courbes smartphone → applis/réseaux sociaux → mariage → fécondité par
âge (France : Baromètre, Eurostat, INSEE ; États-Unis : Pew, WONDER ; Corée : MSIT, KOSIS national).

---

## 6. Incertitudes

| # | Incertitude | Impact | Plan B |
|---|---|---|---|
| U1 | Accès réseau (§1) | bloquant | options A/B/C |
| U2 | Raccord des deux séries de naissances communales (2004-2015 et 2014-2024) : définitions identiques ? | fenêtre de pré-période | si incompatibles, fenêtre 2014-2024 seulement pour les cohortes 2017+ (rurales) ; le niveau département garde 1998+ |
| U3 | Fiabilité des dates `EMR_DT_SERVICE` avant 2015 (biais de survie, dates de modification) | datation des cohortes 2012-2014 | recoupement observatoire 2015+, cohortes précoces en robustesse ; D2 en second traitement |
| U4 | Noms des variables « en couple par sexe et âge » dans la base RP communale ; disponibilité de 15-19 et 20-24 séparés | canal mise en couple au niveau commune | repli sur les mariages par âge (département) |
| U5 | Baromètre du numérique : la variable région est-elle dans les microdonnées ouvertes ? taille d'échantillon par région × âge | first stage / IV | first stage national par âge seulement ; IV abandonnée, dit explicitement |
| U6 | PACS par département après 2017 (enregistrement en mairie) : série INSEE complète ? | canal PACS | mariages seuls |
| U7 | Estimateur de Chaisemartin & D'Haultfœuille indisponible (Python : absent ; R : CRAN bloqué) | méthode | CS + Sun & Abraham + did2s ; ajout de dCDH si CRAN ouvert |
| U8 | Puissance au niveau département × âge | conclusion sur les 25+ | calcul MDE préenregistré, résultat nul rapporté comme « non détecté à la puissance X » |
| U9 | Corée : clé API KOSIS | cas secondaire | descriptif national via tables déjà publiques (à vérifier) |
| U10 | États-Unis : accès NCHS restreint | cas secondaire | descriptif national |
| U11 | Vérification des références : doi.org et éditeurs bloqués | `references.bib` | vérification à l'Étape 4 une fois le réseau ouvert ; aucune référence non vérifiée ne sera citée |
| U12 | Taille des téléchargements ANFR/RP (~2-3 Go bruts au total) et disque (~30 Go) | pipeline | ok ; FCC/NTIA exclus de toute façon |

---

## 7. Décisions à valider

1. **Réseau** : option A (unrestricted), B (liste §1.3) ou C (dépôt manuel) ? Défaut proposé : A.
2. **Emplacement dans le dépôt** : le dépôt `carrousel` est un atelier Remotion avec déjà un dossier
   `scripts/`. Je propose de placer le projet dans le sous-dossier `smartphone-fecondite/` (structure
   `data/`, `scripts/`, `figures/`, `tables/`, `paper/`, `docs/` à l'intérieur), plutôt qu'à la racine.
   Défaut : sous-dossier.
3. **Périmètre des cas secondaires** : Corée, États-Unis et Europe en descriptif uniquement (pas de
   panel « causal » secondaire), pour les raisons de §4.2-4.4. Défaut : oui.
4. **Traitement principal** : D1 (premier émetteur 4G en service, ANFR) avec D2 (couverture ARCEP)
   en second ; 3G en robustesse. Défaut : oui.
5. **Fenêtre principale** : commune 2004-2024, département × âge 1998-2025, avec exclusion 2020-2021 en
   robustesse (pas dans la spécification principale). Défaut : oui.
6. **Estimateurs** : Callaway & Sant'Anna (principal), Sun & Abraham, did2s, TWFE comparatif ; dCDH
   seulement si CRAN accessible. Défaut : oui.
7. **Clé API KOSIS / accès NCHS** : en avez-vous ? Défaut : non → descriptif.
8. **PDF** : TeX Live via apt (pdflatex). Défaut : oui ; repli pandoc + weasyprint.

Après validation : Étape 1 (préregistration), puis Étape 2 dès que le réseau est ouvert.

---

## 7 bis. Extension multi-pays

À la demande de l'auteur (18/09), 47 pays supplémentaires ont été balayés : classement, sources et
ordre de vérification dans `etape0_pays.md`. Décisions ouvertes correspondantes : `handover.md` §2,
points 9-11.

## 8. Littérature repérée (positionnement uniquement)

Références proposées dans le cahier des charges, DOI retrouvés par recherche web (page éditeur non
consultée : bloquée). Elles n'entreront dans `references.bib` qu'après consultation de la page
éditeur ou de doi.org (règle 2).

| Référence | DOI | Ce qu'elle apporte au positionnement | Ce qu'elle ne teste pas |
|---|---|---|---|
| Billari, Giuntella & Stella (2019), *Population Studies* 73(3) | 10.1080/00324728.2019.1584327 | haut débit fixe → fécondité **positive** chez les femmes diplômées 25-45 (Allemagne, SOEP) | Internet mobile, mise en couple |
| Guldi & Herbst (2017), *J. Population Economics* 30(1) | 10.1007/s00148-016-0605-0 | haut débit fixe → baisse de la fécondité adolescente (États-Unis, comtés) | 25 ans et plus |
| Bellou (2015), *J. Population Economics* 28(2) | 10.1007/s00148-014-0527-7 | haut débit fixe → hausse des mariages 21-30 ans (États-Unis) | fécondité, mobile |
| Rosenfeld, Thomas & Hausen (2019), *PNAS* 116(36) | 10.1073/pnas.1908630116 | la rencontre en ligne devient le premier mode de rencontre vers 2013 (États-Unis) | causalité |
| Potarca (2020), *PLoS ONE* 15(12) | 10.1371/journal.pone.0243733 | couples formés via applis en Suisse : intentions de cohabitation et de fécondité | causalité |

Travaux 2019-2026 repérés (à vérifier un par un à l'Étape 4 ; liste non exhaustive) :
Myers (2026), *Is the iPhone Birth Control? Causal Evidence from AT&T's 2007-2011 Carrier Monopoly*,
NBER WP 35310 (effets sur 15-19 et 20-24, États-Unis) ; Ershov, Fong & Yildirim (2026), *What Happens
When Dating Goes Online?*, NBER WP 34757 (sites vs applis, mariages et divorces par comté) ; Hudson,
*The Collapse of Teen Fertility in the Digital Era* (Royaume-Uni, couverture 4G et relief) ; études 3G
en Afrique subsaharienne (Nigeria ; Global Data Lab 2025 : mariages et grossesses adolescentes, femmes
plus âgées non affectées) ; *Dating apps and marriage rates*, Economics Letters (2026) ; *How broadband
internet access shapes fertility decisions: evidence and mechanisms* (Chine, 2025). Constat provisoire
qui motive le papier : les designs causaux existants portent presque tous sur les adolescentes ou les
moins de 25 ans, ou sur le haut débit fixe ; l'effet net sur les 25 ans et plus via le mobile reste
le trou à combler.
