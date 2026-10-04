# Passation — état du projet au 2 octobre 2026 (nuit)

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
- **Étape 3 France : estimations exécutées** (`scripts/05_estimate.py`, commit indiqué dans `tables/est/_run.json`).
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
- Pas encore fait : rédaction (Étape 4), pays de niveau 1 et 2, panel mondial (hôtes bloqués), D2 (SIG),
  références (`references.bib` vide).

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
l'emploi 25-54, compléments exploratoires).

## 3. Transparence (à reporter dans la section 5 du papier)

- Avant l'exécution complète, des chiffres réels ont été vus lors de tests de fonctionnement : ATT H2b et H3a sur le
  panel départemental complet avec bootstraps réduits (`--fast`), ATT H1 sur des sous-échantillons aléatoires de
  3 000 et 5 000 communes, et, à l'Étape 2, un ATT TWFE statique 25-29 affiché une fois lors du débogage. Aucune
  décision d'A2 n'a été prise à partir d'eux ; A2 a été commité avant le lancement complet (commit `c297ba9`).
- Deux relectures adversariales du code (workflows multi-agents, 40 puis N constats vérifiés contradictoirement)
  ont précédé l'exécution ; leurs corrections sont listées dans A2 et dans les messages de commit.
- Les sorties de tests de fonctionnement sont confinées à `tables/est_smoke/` et `figures/smoke/` (non versionnés).

## 4. Prochaines étapes, dans l'ordre

1. Lire `tables/t_estimates_fr.md` et les figures ; vérifier les lignes « non estimé » / « non estimable » et les
   écarts-types aberrants éventuels (sous-groupes H6 : l'estimateur doublement robuste est instable quand le groupe
   de contrôle d'une cohorte est petit ; les lignes « régression de résultat seule » servent de contrôle).
2. Pays de niveau 1 : Suède (api.scb.se, statistik.pts.se joignables), Colombie (datos.gov.co), Brésil (anatel ;
   SIDRA bloqué → mariages absents), Espagne (datos.gob.es bloqué → traitement absent : à signaler). Check-list §4.3
   et addendum par pays **avant** toute estimation ; réutiliser `did.py` et le squelette de `05_estimate.py`.
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
- `05_estimate.py` : un CS sur 31 000 communes avec covariables prend ≈ 40 s ; le bootstrap par grappes de la
  spécification primaire (50 tirages) ≈ 45 min ; les parties sont indépendantes et peuvent tourner en parallèle
  (deux flux sur cette machine à 4 cœurs), puis `--part summary`.

## 7. Message de démarrage suggéré pour une nouvelle session

```
Continue le working paper smartphones/fécondité sur la branche claude/confident-pasteur-og6cgd,
dossier smartphone-fecondite/. Lis dans l'ordre docs/mission.md, docs/handover.md,
docs/preregistration.md, docs/preregistration_addenda.md, docs/etape0_plan.md, docs/etape0_pays.md.
Crée le venv (python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt),
vérifie `python scripts/01_download.py --check`, puis `python scripts/01_download.py --country FR`
(idempotent : consigne les fichiers déjà présents) et `make build`. Reprends à l'étape indiquée dans
handover.md §4.
```
