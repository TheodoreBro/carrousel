# Passation — état du projet au 2 octobre 2026 (soir)

Ce fichier permet à une nouvelle session (ou à un nouvel agent) de reprendre le travail sans la
conversation d'origine. Il est mis à jour à chaque étape.

## 0. Cahier des charges

Le texte intégral de la mission de l'auteur est dans `docs/mission.md`. Il prime sur tout résumé.

## 1. Où en est-on

- Étape 0 livrée : `docs/etape0_plan.md`, `docs/etape0_pays.md`.
- Étape 1 livrée : `docs/preregistration.md` (v1.0, **gelée**, commit `c4002c6`). Déviations et décisions
  de mesure : `docs/preregistration_addenda.md` (addendum A1 France, écrit **avant toute estimation**).
- **Étape 2 France : données téléchargées, traitement et résultats construits, échantillons et MDE calculés,
  first stage estimé.** Aucune estimation H1-H6 n'a été lancée.
  - Réseau (02/10) : les sources du cœur France sont joignables (data.gouv.fr instable, insee.fr, api.insee.fr,
    data.anfr.fr, data.arcep.fr, arcep.fr), ainsi qu'Eurostat, UN, SCB, PTS, INE, DANE, Anatel, doi.org et la
    plupart des éditeurs. **Restent refusés** : api.worldbank.org, ourworldindata.org, datahub.itu.int (panel
    descriptif mondial), datos.gob.es (Espagne), apisidra.ibge.gov.br (Brésil), legifrance.gouv.fr (contourné via
    arcep.fr), stats.justice.gouv.fr (HTTP 5xx, remplacé par l'API Melodi). Rien n'a été remplacé par des valeurs
    de substitution ; ces sources sont vides tant que l'accès n'est pas ouvert (réglage : menu de l'environnement
    → Edit → Network access).
  - 130 fichiers bruts (1,46 Go) consignés dans `data/raw/manifest.json` et `docs/data_log.md` (URL exacte, date,
    SHA-256, licence). Le journal contient aussi, à la main, toutes les corrections du registre constatées sur
    les pages des producteurs (section « Corrections du registre »), dont deux pièges : le slug data.gouv de
    l'Étape 0 pointait vers un jeu régional, et le suffixe « -COM » des bases INSEE désigne les collectivités
    d'outre-mer, pas les communes.
  - `scripts/02_treatment.py` → `data/processed/fr_treatment_commune.parquet` (34 833 unités × 2004-2026),
    `fr_treatment_dep.parquet` (D3), `tables/t_treatment_fr.md`. D1 = premier émetteur LTE en service (observatoire
    ANFR courant ∪ archives annuelles 2018-2025) ; 21 392 unités avec 4G, 13 312 jamais (surtout densité 6-7 :
    communes sans antenne propre, **couvertes par les sites voisins** — c'est la limite « site ≠ couverture »,
    D2 non construit, voir addendum A1) ; cohortes 2013-2027 ; 3G ; 2e opérateur ; recoupement sites ARCEP
    (écart ≤ 1 an dans 95 % des cas datés) ; ZDP (21 184 unités) et zones blanches extraites du PDF ARCEP
    2012-0039 ; densité ; D3 par département (bascule 50 % : 2013-2018, médiane 2015 ; 90 % : 44 départements).
  - `scripts/03_outcomes.py` → `fr_outcomes_commune.parquet` (naissances 2008-2025, décès, femmes 15-44 RP
    interpolées, parts en couple par âge deux sexes), `fr_outcomes_dep_age.parquet` (département × 6 groupes
    d'âge × 1998-2024 : naissances, naissances de parents mariés jusqu'en 2021, rang 1 jusqu'en 2012, épouses par
    âge, femmes au 1er janvier, taux pour 1 000), `fr_outcomes_dep.parquet` (mariages domiciliés 1975-2024, PACS
    2007-2016), `tables/t_outcomes_fr.md`. Contrôle : naissances des fichiers détail / série officielle = 1,000 à
    partir de 2010, 1,004-1,011 en 1998-2009 (enfants sans vie inclus, non corrigés, dit).
  - `scripts/04_sample_mde.py` → `tables/t_sample_fr.md|csv` (unités-années par spécification) et
    `tables/t_mde_fr.md|csv` (MDE par permutation, 200 tirages). Résultats : voir ces tables (résumé en §1 bis).
  - `scripts/04b_firststage.py` → `tables/t_firststage_fr.md|csv`, `tables/t_barometre_age_year.csv`. Baromètre du
    numérique × D3 par ZEAT (2011-2020) : +9,8 points de possession de smartphone (es 4,0, 9 groupes) et +14,9
    points d'usage des réseaux sociaux (es 3,0) pour 0 → 100 % de couverture ; l'interaction « moins de 40 ans »
    est **négative** (contraire à la prédiction H4 « davantage chez les moins de 40 ans »), rapportée telle quelle.
    Au niveau région 2020-2025 : imprécis (D3 ≥ 0,74 partout).
- `make test` vert (8 tests, panel synthétique). `make build` = 02 → 03 → 04 → 04b.
- Transparence : lors du débogage de `04_sample_mde.py` (02/10), un ATT TWFE statique sur le taux 25-29 ans a été
  affiché une fois à l'écran ; il n'a été ni enregistré ni utilisé, et le script ne calcule que des ATT placebo
  (cohortes permutées). Aucune autre estimation sur données réelles n'a eu lieu avant l'Étape 3.
- Pas encore fait : D2 (croisement SIG des cartes ARCEP), estimations (Étape 3), pays de niveau 1 et 2, panel
  mondial (hôtes bloqués), références (`references.bib` vide).

## 1 bis. Chiffres à connaître avant l'Étape 3

Voir `tables/t_sample_fr.md` et `tables/t_mde_fr.md` (générés). Échantillons : H1 commune × année 2008-2024 =
589 968 unités-années (34 704 unités métropolitaines, 21 392 traitées, 13 312 jamais, cohortes 2013-2027, pré-période
médiane 10 ans) ; H2 département × année 1998-2024 = 2 592 unités-années par groupe d'âge (96 départements, tous
basculés à D3 ≥ 50 % entre 2013 et 2018 : pas de « jamais traité » à ce niveau, le contrôle est « pas encore
traité »). MDE par permutation (80 %, 5 %, 200 tirages, TWFE statique sur le log du taux) : H1 commune 0,8 % ;
H2b 25-39 ans 1,3 % ; 15-19 ans 5,9 % ; 20-24 ans 2,8 % ; 25-29 ans 1,8 % ; 30-34 ans 1,7 % ; 35-39 ans 2,0 %.
Points à garder en tête :
- fenêtre communale 2008-2025 (pas 2004) : les cohortes 2013-2014 ont 4-5 ans de pré-période ; la règle « ≥ 3 ans »
  les garde ;
- femmes 15-44 communales : dernier millésime RP 2022, prolongé 2 ans (2023, 2024) ; 2025 sans dénominateur ;
- niveau département × âge : 96 départements, 1998-2024, dénominateurs Melodi ; H3b « parents mariés » 1998-2021 ;
- Baromètre : ZEAT disponible jusqu'en 2020 seulement, REGION à partir de 2020.

## 2. Décisions de l'auteur

Prises (messages du 18/09) : « beaucoup plus de pays » (voir `etape0_pays.md`) ; points 1 à 11 de l'Étape 0
validés le 18/09/2026 (accès réseau, sous-dossier, cas secondaires descriptifs, D1 principal / D2 second / 3G
robustesse, fenêtres, estimateurs, pas de clé KOSIS/NCHS, TeX Live, périmètre causal France + niveau 1 + niveau 2,
méta-analyse, extension descriptive ~200 pays).

Décisions de mesure prises à la lecture des fichiers (liste fermée §10 de la préregistration) : toutes dans
`docs/preregistration_addenda.md` (A1). Les plus importantes : géographie COG 2026 ; fenêtre communale 2008-2025 ;
D2 non construit à l'Étape 2 ; recoupement des cohortes avec les archives 2018-2025 (pas 2015) ; parts en couple
deux sexes ; PACS 2007-2016 ; rang jusqu'en 2012 ; parents mariés jusqu'en 2021.

## 3. Prochaines étapes, dans l'ordre

1. Relire `tables/t_sample_fr.md`, `t_mde_fr.md`, `t_treatment_fr.md`, `t_outcomes_fr.md`, `t_firststage_fr.md` et
   l'addendum A1 ; si l'auteur veut D2 avant les estimations, construire le croisement SIG (geopandas + contours
   communaux IGN, non téléchargés) — sinon passer à l'Étape 3.
2. Étape 3 France : `scripts/05_estimate.py` (Callaway & Sant'Anna primaire via `differences`, Sun & Abraham,
   did2s, TWFE, Poisson ; H1 commune ; H2 département × âge sur D3 ≥ 50 % ; H3 ; H5 placebos ; H6), puis
   `06_figures.py`, `07_tables.py`. Les fonctions sont dans `scripts/common/did.py` (testées sur synthétique).
3. Pays de niveau 1 : Suède (api.scb.se et statistik.pts.se joignables), Colombie (datos.gov.co joignable),
   Brésil (anatel joignable ; SIDRA bloqué → mariages absents), Espagne (datos.gob.es bloqué → traitement absent :
   à signaler). Check-list des critères §4.3 et addendum par pays **avant** toute estimation.
4. Étape 4 : rédaction ; références vérifiées une par une sur la page éditeur (doi.org, Springer, PLOS, NBER,
   RePEc joignables ; tandfonline.com et pnas.org refusent → vérifier via doi.org / crossref).

## 4. Règles non négociables (rappel)

Données réelles uniquement, téléchargées depuis les sources primaires ; toute référence vérifiée avant d'entrer
dans `references.bib` ; aucun résultat externe dans les sections Résultats, Discussion, Conclusion ; hypothèses
écrites avant l'analyse et non modifiées ; corrélation et causalité distinguées ; chaque figure et tableau
produit par un script nommé.

## 5. Pièges techniques de l'environnement (pour ne pas les redécouvrir)

- data.gouv.fr : le relais du proxy coupe souvent la connexion ; `download.py` reprend avec `Range` et réessaie
  9 fois. Ne jamais lancer deux `01_download.py` en parallèle : ils écrasent `manifest.json` l'un de l'autre.
- insee.fr : épisodes de HTTP 503 ; pas de Content-Length en HTTP/2 → un transfert coupé passe inaperçu : le
  téléchargeur teste l'intégrité des zip/xls/xlsx/pdf avant de consigner.
- `pkill -f "01_download"` depuis un shell dont la ligne de commande contient le motif tue le shell lui-même.
- Les fichiers détail dBase se lisent avec `dbfread` (≈ 20 s par année) ; `03_outcomes.py` prend ≈ 9 minutes.

## 6. Message de démarrage suggéré pour une nouvelle session

```
Continue le working paper smartphones/fécondité sur la branche claude/confident-pasteur-og6cgd,
dossier smartphone-fecondite/. Lis dans l'ordre docs/mission.md, docs/handover.md,
docs/preregistration.md, docs/preregistration_addenda.md, docs/etape0_plan.md, docs/etape0_pays.md.
Crée le venv (python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt),
vérifie `python scripts/01_download.py --check`, puis `python scripts/01_download.py --country FR`
(idempotent : consigne les fichiers déjà présents) et `make build`. Reprends à l'étape indiquée dans
handover.md §3.
```
