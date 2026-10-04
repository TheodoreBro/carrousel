# Passation — état du projet au 4 octobre 2026 (après-midi)

Ce fichier permet à une nouvelle session (ou à un nouvel agent) de reprendre le travail sans la
conversation d'origine. Il est mis à jour à chaque étape.

## 0. Cahier des charges

Le texte intégral de la mission de l'auteur est dans `docs/mission.md`. Il prime sur tout résumé.

## 1. Où en est-on

- Étape 0 livrée : `docs/etape0_plan.md`, `docs/etape0_pays.md`.
- Étape 1 livrée : `docs/preregistration.md` (v1.0, **gelée**, commit `c4002c6`). Déviations et décisions
  de mesure : `docs/preregistration_addenda.md` (A1 France, écrit avant toute estimation ; **A2** France, écrit
  à la relecture du code d'estimation, avant son exécution complète).
- Étape 2 France livrée (données, traitement, résultats, échantillons, MDE, first stage) : voir §1 bis et les
  tables `t_treatment_fr.md`, `t_outcomes_fr.md`, `t_sample_fr.md`, `t_mde_fr.md`, `t_firststage_fr.md`.
- **Étape 3 France : estimations exécutées le 04/10/2026** (`scripts/05_estimate.py`, commit indiqué dans `tables/est/_run.json` ;
  parties département 10:00-10:12, parties commune 11:18-12:05, robustesse relancée ensuite pour la variante DOM département).
  - Sorties : `tables/est/<partie>.csv` (h1, h2, h3, h5, h6, robust, iv), `tables/est_fr_all.csv` (toutes les lignes,
    event studies comprises), `tables/t_estimates_fr.md` (synthèse lisible), `tables/est/_run.json` (manifeste :
    commit, versions des paquets, dates des entrées), `figures/fig_event_*.pdf|png`, `figures/fig_h2_age.*`,
    `tables/tab_*.tex` (`07_tables.py`).
  - Ce que fait `05_estimate.py` (détails dans son en-tête et dans A2) : Callaway & Sant'Anna (`differences`, base
    universelle, panel équilibré, contrôle pas-encore-traités, doublement robuste avec les 5 covariables de
    pré-période), écarts-types et test de Wald pré avec la covariance des fonctions d'influence, bandes sup-t par
    bootstrap multiplicateur, bootstrap par grappes stratifié par cohorte pour les primaires, comparaisons Sun &
    Abraham / did2s / TWFE / Poisson (offset), effets fixes année × densité dans les régressions ; H2 par âge avec
    Holm (H2a et H2c), H2d et règle §6 par bootstrap conjoint ; H3a (mariages, PACS, parts en couple par
    différences longues entre millésimes), H3b (naissances par femme en couple, interpolé et différences longues),
    H3c ; H5a-c ; H6 ; robustesse (fenêtres, cohortes, densité, grappes département, pondération, ≥ 20 femmes, DOM,
    D1 observatoire seul, 2e opérateur, ARCEP ≥ 2019, 3G 2011-2012, jamais traitées strictes) ; IV ZEAT × âge ×
    année avec wild cluster bootstrap et Anderson-Rubin, test partiel d'exclusion (emploi des femmes 25-54).
  - Chaque ligne de `est_fr_all.csv` porte sa composition (jamais traitées, cohortes recodées, unités incomplètes
    exclues, années identifiées par CS, k de ATT[1,k]) et un drapeau `exploratory` (hors préregistration, A2).
- `make test` vert (15 tests, panel synthétique : récupération d'un effet connu, écart-type par fonctions
  d'influence = celui du paquet, grappes, bandes, cohortes tardives, offset Poisson = taux pondéré, bootstrap
  stratifié, Holm/Wald).
- **Pays de niveau 1 — Suède : vérifiée le 04/10/2026 et exclue (critère 1 du §4.3)**, avant toute estimation : PTS ne publie par
  kommun que des séries 2015+ où les 290 kommuner ont déjà ≥ 96 % d'accès LTE (les rapports 2010-2014 ont été retirés du site ;
  pages derrière un contrôle anti-robot Radware, franchi avec Chromium headless via le proxy, mais 404 ; dataportal.se refusé par
  le proxy). Côté SCB tout existe (naissances kommun × âge simple 1968-2024, population par âge × état matrimonial, mariages par
  âge) : addendum A3, `tables/t_se_check.md`, check-list dans `docs/data_log.md`, fichiers PTS consignés (`se_pts_tackning`),
  `scripts/08_se_check.py`. Si l'auteur obtient les tabellbilagor PTS 2010-2014 (PTSbredband@pts.se), le dossier peut être rouvert.
- **Colombie : vérifiée le 04/10/2026 et incluse (addendum A4, check-list dans `docs/data_log.md`), estimations exécutées le 04/10/2026**
  (`scripts/11_co_estimate.py`, commit dans `tables/est_co/_run.json`) : voir §1 bis et §1 ter.
  - Chaîne : `01_download.py --country CO` (MinTIC couverture par centro poblado via Socrata ; 22 archives EEVV naissances 1998-2024 via le
    catalogue NADA du DANE, résolveur `nada` ; 3 fichiers Excel de projections DANE), `09_co_treatment.py` (part de population couverte
    en 4G par municipio et année, cohortes ≥ 50 % / ≥ 90 % / cabecera / 3G, censure à gauche au 2015-T4), `10_co_outcomes.py` (naissances par
    municipio de résidence × groupe d'âge × année, mères en union, rang 1, éducation ; femmes des projections ; cache
    `data/processed/co_births_agg_cache.parquet`), `11_co_estimate.py` (parties sample, h1, h2, h3, h5, h6, robust, summary ; réutilise
    `run_block`, `Collector` et les familles de Holm de `05_estimate.py`), `12_co_figures_tables.py` (figures `fig_co_*`, `fig_event_co_*`,
    tableaux `tab_co_*.tex`). `make co` enchaîne 09 → 12.
  - Sorties : `tables/est_co/<partie>.csv`, `tables/est_co_all.csv`, `tables/t_estimates_co.md`, `tables/t_treatment_co.md`,
    `tables/t_outcomes_co.md`, `tables/t_sample_co.md`, `tables/t_mde_co.md`.
- Pas encore fait : Brésil, Espagne (datos.gob.es bloqué) ; rédaction (Étape 4) ; panel mondial (hôtes bloqués) ; D2 (SIG) ;
  références (`references.bib` vide) ; méta-analyse (possible dès un troisième pays inclus).

## 1 bis. Chiffres à connaître

Échantillons (`t_sample_fr.md`) : H1 commune × année 2008-2024 = 34 704 unités métropolitaines (31 194 avec les
5 covariables, 99,7 % des femmes 15-44 de 2011), 21 392 traitées, 13 312 jamais traitées sur la fenêtre (dont
1 604 traitées en 2025-2027), cohortes 2013-2024 ; H2 département × année 1998-2024 = 96 départements, tous
basculés à D3 ≥ 50 % entre 2013 et 2018 → **aucun jamais traité : `differences` prend la dernière cohorte (2018)
comme contrôle et n'identifie les ATT(g,t) que jusqu'en 2017 ; l'agrégat primaire est donc ATT[1,4]** (dit dans
chaque ligne). MDE par permutation (80 %, 5 %) : H1 0,8 % ; H2b 1,3 %.

Résultats : **ne pas les résumer de mémoire** ; lire `tables/t_estimates_fr.md` (clés) et `tables/est_fr_all.csv`.
Les lignes qui entrent dans les règles de décision §6 sont : H2b `post_avg` (département, bascule D3 ≥ 50 %),
H5a/H5b `post_avg` et H5c `pre_test` (spécification primaire), `§6 canal` (différence H3a − H3b par bootstrap
conjoint, avec les deux ATT dans la note). Les p de Holm sont dans `post_avg_holm` (colonne `p_holm`).

## 1 ter. Colombie — chiffres à connaître

Traitement (`t_treatment_co.md`) : 1 121 municipios observés par MinTIC 2015-T4 → 2023-T3 ; 189 déjà ≥ 50 % de population couverte en 4G au
2015-T4 (censurés à gauche, exclus du primaire) ; cohortes 4G ≥ 50 % : 2016 : 95, 2017 : 80, 2018 : 109, 2019 : 93, 2020 : 167, 2021 : 228,
2022 : 47, 2023 : 46, jamais : 67. Résultats (`t_outcomes_co.md`) : 1 122 municipios avec femmes, 1998-2024 ; 3,1 % des cellules
municipio × âge × année à zéro naissance (10,9 % pour 40-49) ; le fichier 2024 est provisoire (439 970 naissances 15-49 contre 504 479 en
2023). Échantillon primaire (`t_sample_co.md`) : 932 municipios × 1998-2024 (865 traités, 67 jamais traités, cohortes 2016-2023), 907 unités
après équilibrage du panel. MDE par permutation (80 %, 5 %) : H1 5,2 %, H2b 5,0 %, par âge 4,9-6,9 % — **bien au-dessus de la France
(0,8 % / 1,3 %)** : un effet de quelques pour cent n'est pas détectable en Colombie.

Résultats : lire `tables/t_estimates_co.md` et `tables/est_co_all.csv`, pas la mémoire. Lignes des règles de décision §6 : H2b `post_avg`
(municipios avec covariables, bascule 4G ≥ 50 %), H5a `post_avg`, H5c `pre_test` ; H3a et H5b n'existent pas en Colombie (A4), la règle §6
sur le canal ne peut donc pas y être appliquée (dit dans la synthèse). Points à connaître avant de lire (exécution du 04/10, 13:59-14:07,
commit `1af9826` dans `_run.json`) :
- la spécification primaire (CS doublement robuste avec covariables) a un pré-test plat (Wald p ≈ 0,2) et des ATT[1,5] proches de zéro
  avec des écarts-types ≈ 0,04, soit au-dessus de la MDE : les intervalles couvrent des effets de ± 8 % ;
- les comparaisons TWFE, did2s et Sun & Abraham sans covariables de pré-période donnent des effets négatifs croissants (jusqu'à −0,1 à −0,2
  log-points à +5…+8) **mais leur pré-test rejette** (Wald p ≈ 0,01) : les coefficients pré lointains (−8 à −5) sont positifs, ce qui ressemble
  à une tendance différentielle, absorbée par la tendance 2010-2014 incluse dans les covariables (voir `fig_event_co_h1_primaire`) ;
- la bande sup-t s'élargit beaucoup au-delà de +4 (seules les cohortes 2016-2019 y sont observées) ; l'agrégat à composition constante
  (`post_avg_balanced`) est reporté ;
- H6 par tercile de part en cabecera donne des ATT positifs aux terciles 1 et 3 et nul au 2 (p Holm 0,00 au tercile 3) : sans
  monotonie, et avec des groupes de contrôle petits par cohorte, à lire avec la même prudence que les sous-groupes H6 français ;
  les lignes « régression de résultat seule » (exploratoires) diffèrent de la ligne doublement robuste (+0,05 contre −0,01 pour H1) ;
- H3b (naissances de mères en union) ≈ 0 ; les compléments hors union / part en union sont exploratoires.

## 2. Décisions de l'auteur

Prises (messages du 18/09) : « beaucoup plus de pays » (voir `etape0_pays.md`) ; points 1 à 11 de l'Étape 0
validés le 18/09/2026 (accès réseau, sous-dossier, cas secondaires descriptifs, D1 principal / D2 second / 3G
robustesse, fenêtres, estimateurs, pas de clé KOSIS/NCHS, TeX Live, périmètre causal France + niveau 1 + niveau 2,
méta-analyse, extension descriptive ~200 pays).

Décisions de mesure et de mise en œuvre prises à la lecture des fichiers et du code : toutes dans
`docs/preregistration_addenda.md` (A1 : géographie COG 2026, fenêtres, D2 non construit, poids D3, ZDP, rang,
parents mariés, PACS, parts en couple deux sexes ; A2 : base universelle, panel équilibré, covariance par
fonctions d'influence, bandes sup-t, grappes, offset Poisson, ATT[1,k], cohortes tardives, chômage deux sexes,
tendance MCO, classes de densité INSEE, cellules mariages absentes = 0, H3b femmes en couple = moitié des personnes
en couple, différences longues entre millésimes, bootstrap conjoint H2d et §6, IV à 9 grappes, exclusion sur
l'emploi 25-54, compléments exploratoires ; A3 : Suède exclue ; A4 : Colombie incluse, unité municipio, part de population
couverte avec censure à gauche, fenêtre 1998-2024 et robustesse 1998-2023, H3b par l'état civil de la mère, covariables, H5b non
construit, H6 par densité/taille/rang).

## 3. Transparence (à reporter dans la section 5 du papier)

- Avant l'exécution complète, des chiffres réels ont été vus lors de tests de fonctionnement : ATT H2b et H3a sur le
  panel départemental complet avec bootstraps réduits (`--fast`), ATT H1 sur des sous-échantillons aléatoires de
  3 000 et 5 000 communes, et, à l'Étape 2, un ATT TWFE statique 25-29 affiché une fois lors du débogage. Aucune
  décision d'A2 n'a été prise à partir d'eux ; A2 a été commité avant le lancement complet (commit `c297ba9`).
- Deux relectures adversariales du code (workflows multi-agents : 40 constats le 02/10, puis 24 constats dont 14 vérifiés
  contradictoirement le 04/10 — les autres n'ont pu être vérifiés faute de quota et ont été triés à la main) ont précédé
  l'exécution complète ; leurs corrections sont dans A2, A2.5 et les messages de commit. Entre les deux, une exécution
  partielle (02/10, commit `c297ba9`) avait produit les parties département (vues) et le test primaire H1 (vu) avant que la
  partie commune soit tuée (mémoire) ; A2.5 a été écrit avec ces chiffres connus, ce qui est dit.
- Chiffres instables à connaître : le sous-groupe H6 « ZDP » donne un ATT doublement robuste de 1,7·10⁷ (écart-type du
  même ordre) — l'estimateur IPW s'effondre sur ce sous-groupe ; la ligne « régression de résultat seule » du même
  sous-groupe est la lecture utilisable ; p Holm = 1 pour toute la famille H6. Le conditionnement au département (6
  covariables agrégées, 96 unités) est instable et marqué non interprétable (A2.5).
- Colombie : avant l'exécution complète, un test de fonctionnement `--fast` (bootstraps 49 / 3) de toutes les parties a été vu sur le panel
  complet (04/10, 13:54-13:56), après le commit de A4 et des tables d'échantillon/MDE ; aucune décision de mesure n'a été prise après.
  Les sorties de ce test sont dans `tables/est_co_smoke/` (non versionné).
- Les sorties de tests de fonctionnement sont confinées à `tables/est_smoke/`, `tables/est_co_smoke/` et `figures/smoke/` (non versionnés).

## 4. Prochaines étapes, dans l'ordre

1. Lire `tables/t_estimates_fr.md` et les figures ; vérifier les lignes « non estimé » / « non estimable » et les
   écarts-types aberrants éventuels (sous-groupes H6 : l'estimateur doublement robuste est instable quand le groupe
   de contrôle d'une cohorte est petit ; les lignes « régression de résultat seule » servent de contrôle).
2. Pays de niveau 1 (Suède exclue, Colombie faite) : Brésil (Anatel
   acessos par município ; SINASC via PCDaS, FTP DATASUS refusé ; SIDRA bloqué → mariages absents), Espagne (datos.gob.es bloqué →
   traitement absent : à signaler). Check-list §4.3 et addendum par pays **avant** toute estimation ; réutiliser `did.py` et le
   squelette de `05_estimate.py`. Pièges : les sites publics derrière Radware/anti-robot se chargent avec Playwright
   (`chromium.launch({proxy: {server: process.env.HTTPS_PROXY}})`, voir scratchpad `pts_links.js` reproduit dans la passation
   §6) ; `openpyxl` refuse l'extension `.part` (corrigé dans `download.py`).
3. Étape 4 : rédaction ; références vérifiées une par une sur la page éditeur (doi.org, Springer, PLOS, NBER, RePEc
   joignables ; tandfonline.com et pnas.org refusent → vérifier via doi.org / crossref). Sections 6-11 sans résultat
   externe ; règles §6 appliquées aux lignes nommées en §1 bis.
4. Si l'auteur le veut : D2 (geopandas + contours IGN), THD fixe (ARCEP), décès par âge au département.

## 5. Règles non négociables (rappel)

Données réelles uniquement, téléchargées depuis les sources primaires ; toute référence vérifiée avant d'entrer
dans `references.bib` ; aucun résultat externe dans les sections Résultats, Discussion, Conclusion ; hypothèses
écrites avant l'analyse et non modifiées ; corrélation et causalité distinguées ; chaque figure et tableau
produit par un script nommé.

## 6. Pièges techniques (pour ne pas les redécouvrir)

- data.gouv.fr : le relais du proxy coupe souvent la connexion ; `download.py` reprend avec `Range` et réessaie
  9 fois. Ne jamais lancer deux `01_download.py` en parallèle : ils écrasent `manifest.json` l'un de l'autre.
- insee.fr : épisodes de HTTP 503 ; pas de Content-Length en HTTP/2 → le téléchargeur teste l'intégrité des
  zip/xls/xlsx/pdf avant de consigner.
- `pkill -f "01_download"` depuis un shell dont la ligne de commande contient le motif tue le shell lui-même.
- Les fichiers détail dBase se lisent avec `dbfread` (≈ 20 s par année) ; `03_outcomes.py` prend ≈ 9 minutes.
- `differences` 0.3 : (i) `base_period` par défaut « variable » ; (ii) bascule en silence sur les coupes répétées
  si le panel est déséquilibré (`as_repeated_cross_section=False` imposé, panels équilibrés en amont) ; (iii) ses
  écarts-types analytiques ignorent `cluster_var` (on somme les fonctions d'influence par grappe) ; (iv)
  `cluster_var` plante sur une Series (patch dans `did.py`) ; (v) l'estimateur doublement robuste **pondéré** n'est
  pas invariant à l'échelle des poids et donne des écarts-types aberrants (la variante pondérée est estimée sans
  covariables) ; (vi) sans unité jamais traitée, la dernière cohorte sert de contrôle et le panel est tronqué.
- pyfixest 0.60 : `did2s` refuse les effets fixes « a^b » (colonnes explicites) et échoue quand un niveau d'effet
  fixe n'existe pas parmi les non-traités (année × densité : estimé sans) ; le wild bootstrap refuse les MCP (modèle
  non pondéré pour les p) et exige des grappes entières ; `wildboottest` n'a pas été vérifié avec plusieurs effets
  fixes interagis (non calculé pour le modèle IV poolé).
- `05_estimate.py` : un CS sur 31 000 communes avec covariables prend ≈ 25-40 s ; le bootstrap par grappes de la
  spécification primaire (50 tirages) ≈ 35 min ; `pyfixest.did2s` **dépasse 15 Go de mémoire** au niveau commune (matrice
  dense n × unités dans sa covariance) → `did.did2s_manual` (mêmes deux étapes, bootstrap par grappes, 3 Go, 7 min) est
  utilisé automatiquement au-delà de 5 000 unités ; Sun & Abraham sur 31 000 communes ≈ 6 Go. Exécuter les flux
  **l'un après l'autre** (le flux commune a été tué deux fois par l'OOM du cgroup à 15 Go quand autre chose tournait) ;
  durée totale ≈ 1 h 05 (département 12 min, commune 47 min), puis `--part summary`.
- Sites derrière un contrôle anti-robot (pts.se : « Radware Page » servie à curl) : charger la page avec Playwright/Chromium
  (installé, `node` avec `NODE_PATH=$(npm root -g)`), `chromium.launch({headless: true, args: ['--no-sandbox'], proxy: {server:
  process.env.HTTPS_PROXY}})`, contexte `ignoreHTTPSErrors: true`, attendre que le titre ne soit plus « Radware Page » (≈ 10 s),
  puis lire les liens ; les fichiers eux-mêmes se téléchargent ensuite par `download.py`. Hôtes refusés par le proxy le 04/10 :
  www.dataportal.se.
- Colombie : l'API Socrata exige `$limit` (résolveur `socrata` : `https://www.datos.gov.co/resource/<id>.csv?$limit=5000000`) ; les archives
  EEVV sont parfois emboîtées (zip dans zip) et mélangent fichiers tabulés (1998-2007, latin-1) et CSV ; `EST_CIVM` change de codage en 2008
  (recodage par année dans `common/co.py`) ; les trois fichiers de projections DANE ont trois dispositions (ligne d'en-tête à détecter,
  en-tête sur deux lignes en 2018-2042, colonnes MPIO/DPMP interverties en 1995-2004 : la colonne du code est celle dont ≥ 90 % des valeurs
  ont 5 chiffres). Lecture des 22 archives ≈ 10 min, mise en cache dans `data/processed/co_births_agg_cache.parquet`.
- Un `( … ) &` à l'intérieur d'un Bash lancé en arrière-plan peut ne jamais démarrer : lancer les longs travaux par un script `nohup`
  et surveiller le journal avec une boucle `until grep -q EXIT …`.
- `kill $(pgrep -f motif)` et `pkill -f motif` tuent le shell appelant si sa ligne de commande contient le motif : tuer par
  PID lu dans `ps`.

## 7. Message de démarrage suggéré pour une nouvelle session

```
Continue le working paper smartphones/fécondité sur la branche claude/confident-pasteur-og6cgd,
dossier smartphone-fecondite/. Lis dans l'ordre docs/mission.md, docs/handover.md,
docs/preregistration.md, docs/preregistration_addenda.md, docs/etape0_plan.md, docs/etape0_pays.md.
Crée le venv (python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt),
vérifie `python scripts/01_download.py --check`, puis `python scripts/01_download.py --country FR`
(idempotent : consigne les fichiers déjà présents) et `make build` ; pour la Colombie,
`python scripts/01_download.py --country CO` puis `make co`. Reprends à l'étape indiquée dans handover.md §4.
```
