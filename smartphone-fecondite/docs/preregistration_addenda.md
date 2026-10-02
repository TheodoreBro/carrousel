# Addenda à la préregistration (v1.0, gelée)

Chaque entrée est datée, motivée, et limitée aux décisions autorisées après lecture des données
(préregistration §10 : correspondance des variables, années réellement disponibles, harmonisation
géographique, choix population/surface, correction d'erreurs manifestes). Les hypothèses, résultats
primaires, règles de décision, estimateurs et seuils ne sont pas modifiés. Tout est rapporté dans le papier
(section 5 et annexe).

## A1 — France : addendum de mesure (02/10/2026, avant toute estimation)

Rédigé fichiers en main, à l'issue de l'Étape 2 (téléchargement, `docs/data_log.md`). Aucune estimation
(H1-H6) n'a été lancée avant ce commit.

| Point de la préregistration | Ce que disent les fichiers | Décision (et catégorie §10) |
|---|---|---|
| §4.1 unité fine : « géographie du 1er janvier 2024 » | Les naissances communales (API Melodi) et l'observatoire ANFR sont diffusés dans la géographie courante (COG 2026, 34 875 communes) | Géographie de référence = **COG 2026** ; codes historiques rattachés par les mouvements du COG (fusions, rétablissements, changements de code) ; les composantes contenant plusieurs communes actuelles (communes rétablies) sont agrégées sur toute la période (harmonisation géographique) |
| §4.1 années : commune 2004-2024 | Aucune série communale INSEE scriptable avant 2008 (le jeu data.gouv 2004-2015 est une republication régionale, pas une source primaire) ; Melodi couvre 2008-2025 | Fenêtre communale = **2008-2025** (années réellement disponibles). Conséquence : les cohortes 4G 2013-2014 n'ont que 4-5 années de pré-période ; la règle « ≥ 3 années de pré-période » (§4.2) s'applique telle quelle |
| §4.1 années : département × âge 1998-2025 | Fichiers détail naissances et mariages disponibles 1998-**2024** (2025 non publié au 02/10/2026) | Fenêtre = **1998-2024** |
| §4.1 D1 : recoupement avec « les archives mensuelles de l'observatoire ANFR (2015+) » | Pas d'archive avant janvier 2018 (exports mensuels des installations sur data.gouv, 2018-01 → 2026-08) ; sites ARCEP ouverts commercialement par commune depuis 2018-T4 | Recoupement fait avec **un export ANFR par an 2018-2025** (plus ancienne date LTE connue dans l'union observatoire courant ∪ archives) et avec les **sites 4G ARCEP** (2018-T4 →). Cohortes 2013-2017 datées par les dates de mise en service déclarées, exposées au biais de survie des émetteurs démontés avant 2018 ; la robustesse « cohortes 2012-2014 exclues » (§5) est étendue à **2013-2017** en analyse complémentaire, sans changer le primaire |
| §4.1 D1 : date de mise en service | Variable `emr_dt` (observatoire) / `EMR_DT_SERVICE` (archives) ; 45 communes avec une date LTE antérieure à 2012 (impossible : premiers lancements commerciaux 4G fin 2012) ; quelques dates UMTS antérieures à 2004 | Dates LTE < 01/01/2012 recodées au 30/06/2012 ; dates UMTS < 01/01/2004 recodées au 01/12/2004 ; comptées dans `tables/t_treatment_fr.md` (correction d'erreurs manifestes) |
| §4.1 D2 : « part de la population communale couverte en 4G (ARCEP) » | L'open data ARCEP ne contient pas de taux par commune mais des cartes de couverture (geopackage) par opérateur et trimestre, 2018-T1 → | **D2 non construit à l'Étape 2** ; sa construction demande un croisement SIG (contours communaux × population) prévu en Étape 3 si le temps le permet ; sinon D2 absent et dit. Le second traitement de recoupement disponible immédiatement est la **date du premier site 4G ouvert commercialement (ARCEP)**, utilisé en robustesse pour les cohortes ≥ 2019 |
| §4.1 D3 : « part des femmes de 15-49 ans du département résidant dans une commune avec D1 = 1 » | Les bases RP communales donnent les femmes par tranches 15-29, 30-44, 45-59 | Poids = **femmes 15-44 du RP 2011** (pré-période, fixes) ; variante population totale 2011 |
| §4.1 ZDP : « décision 2011-0600 (Légifrance) » | Légifrance refusé ; la liste n'est pas dans le PDF de la décision 2011-0600 mais dans les annexes des autorisations 800 MHz (décision 2012-0039, p. 57-275) | Liste ZDP extraite de **2012-0039.pdf** (22 389 codes) ; liste « zones blanches » (p. 18-56) extraite en complément |
| §4.1 résultats H2 : « AGEMERE » | `agemere` = âge atteint dans l'année, **censuré à 17 et 46** dans les fichiers détail ; rang de naissance (`nbenfpre`) disponible **jusqu'en 2012 seulement** ; année de mariage des parents (`amar`) absente des fichiers **2022-2024** (format réduit à 14 variables ; 2023-2024 : `depdomm` au lieu de `depdom`) | Groupes d'âge sur `agemere` (15-19 inclut les mères codées 17 et moins ; 40-49 inclut 46 et plus) ; hétérogénéité par rang (H6) limitée à 1998-2012 ; H3b « naissances de parents mariés » limité à 1998-2021 |
| §4.1 résultats H3a : mariages par âge de l'épouse | Jusqu'en 2012 : année de naissance de l'épouse ; depuis 2013 (mariage pour tous) : conjoint 1 / conjoint 2 avec sexe | « Épouses » = conjointes de sexe féminin ; un mariage entre deux femmes compte deux femmes ; âge = année du mariage − année de naissance |
| §4.1 résultats H3a : PACS | Série INSEE départementale 2007-2016 seulement (enregistrement en mairie depuis novembre 2017 sans série départementale ouverte) | Canal PACS testé sur **2007-2016** ; dit dans le papier |
| §4.1 résultats H3a : part des femmes en couple par âge (RP) | Bases Couples-Familles-Ménages : tranches 15-24 et 25-39 ; millésimes 2006, 2010/2011, 2015/2016, 2021, 2022 | Interpolation linéaire entre millésimes, pas d'extrapolation au-delà de 2 ans (§4.2) |
| §4.1 dénominateurs : « RP interpolé » | Estimations localisées de population par département × sexe × âge quinquennal 1975-2026 (Melodi) au niveau département ; RP par commune (femmes 15-29, 30-44) | Département : estimations Melodi (pas d'interpolation nécessaire) ; commune : femmes 15-44 RP interpolées |
| §3 H5b : « décès des 60 ans et plus pour 1 000 habitants » | Décès communaux disponibles sans âge (Melodi) | Placebo communal = **décès totaux pour 1 000 habitants** ; au niveau département, décès par âge non téléchargés à l'Étape 2 (à ajouter si nécessaire) |
| §4.1 naissances 1998-2009 | D'après la documentation INSEE, les fichiers 1998-2009 incluent les enfants sans vie, sans variable pour les distinguer | Comptes rapprochés de la série officielle départementale (ratio par année dans `tables/t_outcomes_fr.md`) ; l'écart est rapporté, pas corrigé |

Aucune de ces décisions ne modifie les hypothèses H1-H6, les résultats primaires, les seuils ni les règles
de décision du §6 de la préregistration.
