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
| §4.1 résultats H3a : part des femmes en couple par âge (RP) | Les bases communales Couples-Familles-Ménages donnent les personnes vivant en couple par groupe d'âge (15-19, 20-24, 25-39, 40-54) **sans ventilation par sexe** (`P<yy>_POP<grp>_COUPLE`) ; millésimes 2006, 2011, 2016, 2021, 2022 | Résultat H3a(iii) mesuré sur les **deux sexes** : part des 15-24 et des 25-39 ans vivant en couple ; interpolation linéaire entre millésimes, pas d'extrapolation au-delà de 2 ans (§4.2) |
| §4.1 dénominateurs : « RP interpolé » | Estimations localisées de population par département × sexe × âge quinquennal 1975-2026 (Melodi) au niveau département ; RP par commune (femmes 15-29, 30-44) | Département : estimations Melodi (pas d'interpolation nécessaire) ; commune : femmes 15-44 RP interpolées |
| §3 H5b : « décès des 60 ans et plus pour 1 000 habitants » | Décès communaux disponibles sans âge (Melodi) | Placebo communal = **décès totaux pour 1 000 habitants** ; au niveau département, décès par âge non téléchargés à l'Étape 2 (à ajouter si nécessaire) |
| §4.1 naissances 1998-2009 | D'après la documentation INSEE, les fichiers 1998-2009 incluent les enfants sans vie, sans variable pour les distinguer | Comptes rapprochés de la série officielle départementale (ratio par année dans `tables/t_outcomes_fr.md`) ; l'écart est rapporté, pas corrigé |

Aucune de ces décisions ne modifie les hypothèses H1-H6, les résultats primaires, les seuils ni les règles
de décision du §6 de la préregistration.

## A2 — France : addendum d'estimation (02/10/2026, Étape 3, écrit avant la lecture des résultats complets)

Rédigé à la relecture adversariale de `scripts/05_estimate.py` et `scripts/common/did.py` (40 constats, consignés
dans la passation), **avant** l'exécution complète des estimations. Deux séries de chiffres réels ont été vues avant ce
commit, lors de tests de fonctionnement : un ATT H2b sur le panel départemental complet avec bootstraps réduits
(`--fast`), et un ATT H1 sur un sous-échantillon aléatoire de 3 000 puis 5 000 communes. Ils n'ont servi qu'à
vérifier que le code tourne ; aucune décision ci-dessous n'a été prise à partir d'eux (section 5 du papier).

### A2.1 Corrections de mise en œuvre (sans changement des hypothèses, estimateurs ni seuils)

| Point | Constat | Décision |
|---|---|---|
| Période de base de l'event study CS | `differences` utilise par défaut une base « variable » (t contre t−1) ; la préregistration fixe la référence −1 | Base **universelle** (référence −1) pour toutes les event studies ; test H5c sur −8..−2 |
| Panel déséquilibré | `differences` bascule en silence sur l'estimateur « coupes répétées » dès qu'une observation manque | Estimateur panel imposé ; chaque bloc est **équilibré explicitement** (unités observées toutes les années de la fenêtre) et les exclusions sont comptées dans les notes de `est_fr_all.csv`. Exception : le placebo H5a, déséquilibré par construction (les unités sortent à leur vraie bascule), gardé tel quel et dit |
| Écart-type de la moyenne +1..+5 | Calculé sous indépendance des coefficients (anti-conservateur) | **Covariance complète** des coefficients reconstruite à partir des fonctions d'influence (CS) ou de la matrice de covariance groupée (Sun & Abraham, did2s, TWFE) ; bootstrap par grappes stratifié par cohorte en contrôle pour les spécifications primaires |
| Bandes simultanées | Non produites | Bandes **sup-t** par bootstrap multiplicateur de Rademacher sur les fonctions d'influence (999 tirages), tracées à côté des IC ponctuels |
| Test H5c | Somme des t² (ignore la covariance) | **Wald joint** avec la covariance des coefficients −8..−2 (pseudo-inverse) |
| Grappes ≠ unité (commune → département) | Les écarts-types « analytiques » de `differences` ignorent `cluster_var` | Fonctions d'influence **sommées par grappe** (sandwich groupé usuel) avant le calcul |
| Poisson | log(exposition) en régresseur libre | **Offset** log(exposition) ; ATT rapporté aussi en % du taux contrefactuel |
| Libellé « ATT[1,5] » | +5 n'existe pas pour les cohortes tardives ; au niveau département, sans unité jamais traitée, `differences` prend la dernière cohorte comme contrôle et n'identifie les ATT(g,t) que jusqu'à l'année précédant cette cohorte (1998-2017) | Libellé **ATT[1,k]** avec k = dernière période disponible ≤ 5 ; années identifiées, cohortes et effectifs par période relative écrits dans chaque ligne ; agrégat complémentaire « composition constante » (cohortes observées jusqu'à +5) pour H1 et H2b |
| Cohortes postérieures à la fenêtre (2025-2027 au niveau commune ; 2020-2024 pour la fenêtre 2008-2019) | Recodées « jamais traitées » par `differences` avec un simple avertissement, mais traitées comme cohortes pré-seulement par les autres estimateurs | Recodage **explicite et identique** pour tous les estimateurs, effectif écrit dans les notes ; variante « jamais traitées strictes » (cohortes 2025-2027 exclues) en robustesse |
| Covariable « taux de chômage 15-24 » | Chômage des femmes 15-24 utilisé | **Deux sexes** (P11_HCHOM1524 + P11_FCHOM1524) / P11_ACT1524, conformément au §4.1 |
| Tendance des naissances | « 2004-2011 » impossible (fenêtre 2008+) ; calculée sur deux points | **Pente MCO** de log(naissances + 0,5) sur 2008-2011 (4 points). Cette covariable est construite sur les résultats 2008-2011 du panel et contamine mécaniquement les coefficients pré de ces années : H5c est rapporté **aussi sans elle** |
| Classes de densité | Niveau 2 (centres urbains intermédiaires) classé « dense » | Grille INSEE : dense = {1}, intermédiaire = {2, 3, 4}, rural = {5, 6, 7} (tableau d'échantillon, figure de déploiement et H6 régénérés) |
| Chocs concurrents §4.1 | Effets fixes année × densité absents ; très haut débit absent | Effets fixes **année × classe de densité** dans les estimateurs de régression (Sun & Abraham, did2s, TWFE, Poisson) ; pour CS, la classe de densité entre par les covariables de l'estimateur doublement robuste. Couverture très haut débit fixe : **non téléchargée, non estimée** (ligne « non construit ») |
| Cellules département × âge absentes des fichiers mariages (15-19 surtout) | Supprimées comme manquantes (sélection sur le résultat) | **Codées 0** quand l'année est lue (`03_outcomes.py`) ; pour les groupes avec cellules nulles, asinh du taux pour CS et Poisson avec offset en comparaison (le log sans correction reste la règle au département) |
| Fenêtre communale | A1 annonce 2008-2025 ; 2025 n'a pas de dénominateur ; 2023-2024 utilisent le dénominateur 2022 (prolongement à plat) | Fenêtre estimée **2008-2024**, dite ; robustesse 2008-2022 |
| ARCEP | Cohortes ≥ 2020 au lieu de ≥ 2019 (A1) | **≥ 2019** |
| 3G | Cohortes ≥ 2013 incluses ; la préregistration limite la robustesse 3G aux cohortes 2008-2012 | **Cohortes 2011-2012** (2008-2010 exclues par la règle « ≥ 3 ans de pré-période ») |
| H6 | Sous-groupes estimés sans la spécification primaire | Spécification primaire (covariables, pas-encore-traités) sur chaque sous-groupe ; les covariables constantes dans un sous-groupe (indicatrices de densité) sont retirées et dites |
| H2a | Non corrigée | Famille de Holm {15-19, 20-24} ajoutée (H2c inchangée : {25-29, 30-34, 35-39, 40-49}) |
| H2d et règle §6 « canal » | Différences testées sous indépendance | **Bootstrap conjoint** par département, stratifié par cohorte, les deux ATT recalculés sur chaque tirage (écart-type sous indépendance gardé pour mémoire) |
| IV | 9 grappes ZEAT : CRV1, F = t² et IC de Wald non fiables ; test d'exclusion absent | p du **wild cluster bootstrap** (Webb, 9 999 tirages) pour la forme réduite et le premier étage ; intervalle d'**Anderson-Rubin** par inversion du test ; test partiel de la restriction d'exclusion : effet de D3 sur le **taux d'emploi des femmes 25-54** (RP, seul groupe disponible ; préreg. : 25-39) par département aux millésimes 2011, 2016, 2021 |

### A2.2 Résultat H3b et parts en couple (décisions de mesure, catégorie « correspondance des variables »)

- **H3b préenregistré** (naissances pour 1 000 femmes en couple par âge) : construit au département pour 25-39 et
  15-24 ; dénominateur = **moitié des personnes en couple** du groupe d'âge (RP, deux sexes, les couples de même sexe
  étant négligeables à cette échelle), **interpolée linéairement** entre millésimes (2006-2022, prolongement ≤ 2 ans,
  règle A1). Comme tout résultat interpolé, ses coefficients pré sont mécaniquement contaminés ; il est donc **aussi**
  estimé par **différences longues entre millésimes** (2011 → 2016 sur l'indicatrice « bascule ≤ 2016 », 2011 → 2021
  sur les années d'exposition), sans interpolation.
- Le résultat « naissances de parents mariés pour 1 000 femmes » n'est **pas** H3b (dénominateur = toutes les femmes,
  faute de femmes mariées par âge au département) : rapporté comme complément.
- **H3a(iii)** (part en couple, commune) : même traitement — différences longues entre millésimes comme résultat
  principal, event study interpolée marquée « exploratoire ».
- **Règle §6 « canal »** : les deux tests qui y entrent sont nommés — H3a = mariages de femmes 25-39 pour 1 000 femmes
  (CS, ATT[1,k]) et H3b = naissances pour 1 000 femmes en couple 25-39 (CS, ATT[1,k]) ; « effets standardisés » = les deux
  ATT en log-points ; la différence est testée par bootstrap conjoint. H3 est présentée sans correction de tests
  multiples (la préregistration ne prévoit Holm que pour les âges et les hétérogénéités).
- **H3c** : première période relative ≥ 0 où le coefficient CS est négatif avec IC ponctuel excluant 0, pour les
  mariages 25-39 et pour les naissances par femme en couple 25-39 (lecture descriptive).

### A2.3 Analyses complémentaires hors préregistration (drapeau « exploratoire » dans `est_fr_all.csv`)

Ajoutées à la relecture, **sans changement du primaire** :
- **référence −2** (`anticipation = 1`) pour H1 et H2b : l'année −1 est partiellement exposée (émetteur en service en
  médiane 5 mois avant le 1er janvier de la cohorte) et les naissances suivent les conceptions de 9 mois ; le primaire
  (référence −1) est une borne basse en valeur absolue si l'effet commence avec l'exposition ;
- H1 **pondéré** par les femmes 15-44 de 2011 (effet moyen par femme) et H1 sur les communes d'**au moins 20 femmes**
  (le primaire non pondéré est dominé par les très petites communes et par la correction +0,5) ;
- fenêtre 2008-2022 ; contrôle « jamais traitées strictes » ; agrégat à composition constante.

### A2.4 Ce qui n'est pas fait

- D2 (couverture ARCEP ≥ 90 % de la population) : non construit (croisement SIG non réalisé), ligne « non construit ».
- Couverture très haut débit fixe en contrôle variable : non téléchargée.
- `pyfixest.SaturatedEventStudy` : Sun & Abraham implémenté directement (régression saturée cohorte × période relative,
  agrégation par parts de cohortes avec covariance groupée) ; sans unité jamais traitée (niveau département), Sun &
  Abraham et did2s ne sont pas estimables et une ligne le dit.
- Décès des 60 ans et plus au département (H5b) : non téléchargés ; le placebo communal utilise les décès totaux (A1).

Aucune de ces décisions ne modifie les hypothèses H1-H6, les résultats primaires, les seuils ni les règles de
décision du §6 de la préregistration.

### A2.5 Deuxième relecture adversariale (04/10/2026, après une première exécution partielle)

Une première exécution complète a été lancée le 02/10 (commit `c297ba9`) ; les parties département (H2, H3, IV) ont abouti
et ont été vues ; la partie commune a été interrompue (processus tué) après le test primaire H1 et son bootstrap. Une
deuxième relecture adversariale (24 constats, 14 confirmés par vérification contradictoire, les autres non vérifiés
faute de quota) a conduit aux corrections suivantes, appliquées **avant** la ré-exécution complète et **sans changer**
les hypothèses, les résultats primaires ni les seuils :

| Point | Constat | Décision |
|---|---|---|
| Dénominateurs communaux 2008-2010 | `interpolate_years` interpolait les millésimes RP **en positions** de colonnes, pas en années : sans colonne 2007, le segment 2006 → 2011 donnait à 2008 un quart (au lieu de deux cinquièmes) de la variation (écart relatif du dénominateur 2008 de ±5 % aux centiles 5/95) | **Corrigé** (grille d'années contiguë avant interpolation ; correction d'erreur manifeste) ; `fr_outcomes_commune` régénéré, toutes les parties communales ré-estimées |
| Agrégat « composition constante » | Calculé par restriction de l'échantillon à partir de la dernière année observée (2024) et non de la dernière année identifiée (2017 au département) : identique au primaire au département, et modifiant le groupe de contrôle au niveau commune | Agrégation **restreinte, pas l'échantillon** : à partir des ATT(g,t) et de leurs fonctions d'influence, cohortes g telles que g + 5 ≤ dernière année identifiée, poids fixes = tailles de cohortes ; « non calculable » quand aucune cohorte ne satisfait la condition (département) ; effets par période écrits dans la note |
| Sun & Abraham, did2s, TWFE, Poisson sans unité jamais traitée | Déclarés « non estimables » alors qu'ils le sont avec la convention de Callaway & Sant'Anna (dernière cohorte = contrôle, fenêtre ≤ année précédente) ; TWFE et Poisson estimés sur 1998-2024 alors que CS ne porte que sur ≤ 2017 | Comparaisons estimées sur la **fenêtre identifiée** (années < dernière cohorte, dernière cohorte recodée contrôle), dit dans l'échantillon ; TWFE statique sur la fenêtre complète gardé en complément exploratoire ; les indicatrices d'event study sans support ne sont plus créées |
| Niveau département sans covariables | H2 et H3 étaient estimés sans les contrôles de pré-période (§5 : doublement robuste pour H1, H2, H3) ; déviation non consignée | Covariables **agrégées au département** (moyennes communales pondérées par les femmes 15-44 de 2011 : log revenu médian, diplômées du supérieur, chômage 15-24, parts de densité ; tendance 2008-2011 du log du taux du groupe) ajoutées pour H2b, H2 par âge, H3a et H3b 25-39, **en plus** de la version sans covariables. Au test de fonctionnement, ce conditionnement est **numériquement instable** à 96 unités (cohortes de 2 à 33 départements, 6 covariables : estimations de plusieurs log-points, écarts-types de 0,1 à 1 ; le même constat vaut pour la régression de résultat seule) : ces lignes sont rapportées, marquées exploratoires et non interprétables, et le niveau département reste présenté **sans conditionnement** (tel que codé avant les résultats), ce que le papier dit explicitement comme déviation par rapport au §5 |
| Bandes sup-t | Valeur critique calculée sur toutes les périodes relatives renvoyées par `differences` (jusqu'à −16..+11) | Max |t| restreint aux coefficients rapportés (−8..+8) |
| Agrégat « simple » | Écart-type du paquet, non groupé quand grappe ≠ unité | Fonctions d'influence sommées par grappe comme pour l'event study |
| Poisson en % | p recalculée sur l'échelle en % (≠ p du coefficient) | p du coefficient β = 0 reportée sur les deux lignes ; écart-type en % par la méthode delta |
| Covariables dans Sun & Abraham / TWFE / Poisson | Constantes dans le temps, absorbées en silence par les effets fixes unité | Retirées de ces régressions et dites « absorbées » ; les chocs concurrents entrent par les effets fixes année × densité |
| Robustesse ARCEP | Cohorte « 2019 » = site déjà présent au premier trimestre observé (2018-T4) : censure à gauche (12 840 communes), traitée comme une vraie cohorte | Cohortes datées **≥ 2020** seulement ; la cohorte 2019 est **exclue** (pas recodée « jamais traitée ») |
| Robustesse DOM | Filosofi 2012 ne couvre pas les DOM : la variante « DOM inclus » était vide (0 commune d'outre-mer) | Variante communale avec les covariables **sans le revenu médian** ; variante H2b au département avec les 4 DOM (971-974, D3 disponible) |
| Terme de Holm | « ATT[1,k] (Holm) » littéral, k non reporté | Terme réel, k et années identifiées dans la ligne ; note si k diffère dans la famille |
| IV | Adoption « 20-24 » = classe 18-24 ans du Baromètre, non dite ; « vide » pour un intervalle non calculé ; p CRV1 et p wild bootstrap mélangées | Étiquettes corrigées (« 18-24 (Baromètre) → naissances 20-24 ») ; colonne `p_type` ; « non calculé » pour le modèle poolé |
| H4 (first stage) | Inférence CRV1 à 9 grappes seulement | p du wild cluster bootstrap (Webb, 9 999 tirages, modèle non pondéré) ajoutée dans `t_firststage_fr` |
| Résultats préenregistrés absents | H3a(iii) au département ; H3c sans les naissances ; sensibilité à la transformation pour H2b ; fenêtre 2008-2019 au département ; H5c au département | Ajoutés (différences longues des parts en couple au département ; H3c pour les naissances 25-39 ; taux brut et asinh pour H2b ; fenêtre 2008-2019 ; ligne H5c département) ; les fenêtres « 1998-2019 » et « sans 2020-2021 » au département sont identiques au primaire par construction (ATT identifiés ≤ 2017), dit |
| Analyses hors préregistration | Agrégat 20-34, compléments « parents mariés » par groupe et part des naissances de parents mariés, D3 continu par groupe, « hors densité 1 », TWFE fenêtre complète | Marquées **exploratoires** |

Comme pour A2, ces décisions ont été prises à la lecture du code et des sorties partielles du 02/10 (H2, H3, IV vues ; H1
primaire vu), avant la ré-exécution complète ; elles sont rapportées dans la section 5 du papier.

## A3 — Suède : décision d'inclusion (04/10/2026, avant toute estimation) — **exclue**

Vérification des quatre critères du §4.3, fichiers en main (`docs/data_log.md`, source `se_pts_tackning` ; `tables/t_se_check.md`,
produit par `scripts/08_se_check.py`). Aucune estimation n'a été lancée sur la Suède.

| Critère | Constat | Verdict |
|---|---|---|
| (1) traitement infranational daté avec ≥ 3 années de pré-période pour ≥ 30 % des unités | La seule série par kommun en ligne chez PTS (statistik.pts.se) qui date l'accès au LTE commence en **2015** : part des ménages avec accès au haut débit fixe via LTE, 2015-2022. En 2015, **les 290 kommuner sont déjà à ≥ 96 % (centile 5 : 99,3 % ; 282 kommuner ≥ 99 %)** ; aucune n'est sous le seuil préenregistré de 50 % ni sous la variante 90 %. Les séries de couverture mobile par kommun (surface couverte par classe de débit, 2016-2024 ; « mobilmål », 2020-2024) mesurent des gains de qualité (10/30 Mbit/s par type de zone) après une couverture 4G déjà quasi totale : dès 2016, la surface couverte en 4G ≥ 10 Mbit/s est ≥ 50 % dans 288 kommuner sur 290 et ≥ 90 % dans 259 ; elles ne datent pas une bascule. Les rapports PTS 2010-2014 (période de l'extension 4G) ne sont plus en ligne : pages `pts.se/dokument/rapporter/...` supprimées (404 après passage du contrôle anti-robot), recherche du site et sitemap sans résultat antérieur à 2023, portail dataportal.se refusé par le proxy. Avec les données disponibles, **toutes les unités sont « toujours traitées » à la première année observée** : aucune cohorte datable, aucune pré-période | **non rempli** |
| (2) naissances par âge au niveau de l'unité, annuelles, couvrant la pré-période | SCB FoddaK : naissances par kommun × âge simple de la mère × sexe, 1968-2024 (API PxWeb, métadonnées vérifiées) | rempli |
| (3) téléchargement scriptable, licence | SCB : API ouverte, CC0 ; PTS : fichiers Excel publics (consignés) | rempli pour ce qui existe |
| (4) dénominateurs par sexe et âge | SCB BefolkningNy : population par kommun × état matrimonial × âge simple × sexe, 1968-2024 ; mariages par âge (CivilstandTypPar, 2000-2024) également disponibles | rempli |

Décision : **Suède exclue de la partie causale** (critère 1), listée dans l'annexe « pays examinés et exclus, avec la raison ». Ce qui
pourrait rouvrir le dossier, hors de ce papier : les tabellbilagor des rapports PTS 2010-2014 (bredbandskartläggning / mobiltäcknings-
kartläggning), si PTS les remet en ligne ou les fournit sur demande (PTSbredband@pts.se) — ils dateraient l'extension 4G de 2010-2014 et
la pré-période existerait (naissances SCB depuis 1968). Une exposition continue construite sur la couverture surfacique ≥ 10 Mbit/s
(2016-2024) n'est pas un traitement échelonné au sens du §4.2 et n'est pas utilisée.

## A4 — Colombie : addendum de mesure et décision d'inclusion (04/10/2026, avant toute estimation)

Rédigé fichiers en main (`docs/data_log.md`, sources `co_mintic_cobertura`, `co_divipola`, `co_dane_eevv_nacimientos`,
`co_dane_proyecciones`). Aucune estimation n'a été lancée sur la Colombie avant ce commit.

### Critères d'inclusion (§4.3)

| Critère | Constat | Verdict |
|---|---|---|
| (1) traitement infranational daté, ≥ 3 ans de pré-période pour ≥ 30 % des unités | MinTIC, « Cobertura móvil por tecnología, departamento y municipio por proveedor » (datos.gov.co `9mey-c8s8`, CC BY-SA 4.0) : drapeaux de couverture 2G/3G/HSPA/4G/LTE/5G par centro poblado × opérateur × trimestre, **2015-T4 → 2023-T3**, 1 102-1 121 municipios. Au 2015-T4, **361 municipios sur 1 102 (33 %) ont déjà de la 4G à la cabecera** (lancement commercial 2014 : censure à gauche) ; 537 au 2016-T4, 712 au 2017-T4, 979 au 2018-T4, 1 070 au 2019-T4, 1 101 au 2023-T3. Les naissances existent depuis 1998 : les municipios dont la 4G arrive après 2015-T4 (≈ 67 %) ont ≥ 3 ans de pré-période | rempli |
| (2) naissances par âge au niveau de l'unité, annuelles, couvrant la pré-période | DANE EEVV, microdonnées des naissances 1998-2024 (catalogue NADA, téléchargement direct) : municipio de **résidence de la mère** (`CODPTORE`, `CODMUNRE`), âge de la mère en groupes quinquennaux (`EDAD_MADRE` : 10-14 … 50-54), état civil de la mère (`EST_CIVM`), nombre d'enfants nés vivants (`N_HIJOSV`) ; mêmes variables de 1998 (fichiers texte tabulés) à 2024 (CSV) | rempli |
| (3) téléchargement scriptable, licence | API Socrata (CSV complet), URL de téléchargement NADA stables (`catalog/<id>/download/<n>`, sans identification), fichiers Excel DANE ; licences CC BY-SA 4.0 (datos.gov.co) et conditions du catalogue DANE (microdonnées anonymisées d'usage public) | rempli |
| (4) dénominateurs par sexe et âge | DANE, projections de population municipales par área (cabecera / centros poblados y rural disperso), sexe et **âge simple**, base CNPV 2018 : 1995-2004, 2005-2017, 2018-2042 | rempli |

Décision : **Colombie incluse** dans la partie causale.

### Décisions de mesure (§4.2 ; catégories §10)

| Point | Ce que disent les fichiers | Décision |
|---|---|---|
| Unité | naissances par municipio de résidence × groupe d'âge ; couverture par centro poblado | **municipio** (1 102 au 2015-T4 ; codes DIVIPOLA à 5 chiffres) × groupe d'âge ; unité d'inférence (grappes) = municipio |
| Traitement (§4.2 : « première année où la couverture 4G de la population atteint 50 % ») | Couverture binaire par centro poblado et opérateur ; pas de population par centro poblado dans le jeu ; les projections DANE donnent la population de la **cabecera** et celle de l'ensemble « centros poblados + rural disperso » | Part de population couverte en 4G (au moins un opérateur, drapeau `cobertuta_4g` ou `cobertura_lte`) = [pop. cabecera × 1(cabecera couverte) + pop. hors cabecera × (part des centros poblados couverts)] / pop. totale, au **dernier trimestre observé de l'année** ; cohorte = première année avec part ≥ 50 % (variante 90 %). Les municipios déjà ≥ 50 % au **2015-T4** sont **censurés à gauche** : exclus du primaire (« toujours traités », comme la cohorte ARCEP 2019 en France) ; en robustesse, cohorte 2015 (borne haute) |
| Années | couverture 2015-T4 → 2023-T3 ; naissances 1998-2024 (le fichier 2024 est provisoire : 439 970 naissances de mères de 15-49 ans contre 504 479 en 2023 ; constaté dans `t_outcomes_co.md`) ; projections 1995-2042 | Fenêtre d'estimation **1998-2024** (cohortes 2016-2023 ; 2024 sans couverture observée : cohortes ≥ 2024 recodées « pas encore traitées » sur la fenêtre, dit) ; robustesse **1998-2023** (sans l'année provisoire 2024) |
| Groupes d'âge | `EDAD_MADRE` quinquennal 10-14 … 50-54 ; « sans information » (99) | 15-19, 20-24, 25-29, 30-34, 35-39, 40-49 (= 40-44 + 45-49) ; mères < 15 ans et ≥ 50 ans hors périmètre (comptées dans `t_outcomes_co.md`) ; âge manquant exclu et compté |
| Résultats de canal (H3) | Pas de série de mariages par municipio × âge ; `EST_CIVM` à la naissance : en union libre ≥ 2 ans / < 2 ans, séparée-divorcée, veuve, célibataire, mariée | H3a non testable (dit) ; **H3b** = naissances de mères **en union** (mariée ou union libre ; codage de `EST_CIVM` différent avant 2008 — 1998-2007 : 2 = mariée, 4 = union libre — vérifié dans les dictionnaires DANE et recodé) pour 1 000 femmes du groupe d'âge (dénominateur : toutes les femmes, faute de femmes en union par âge au municipio — même limite qu'en France, dit) et part des naissances hors union ; H3c non testable |
| Dénominateurs | Projections par âge simple et área | Femmes par groupe d'âge au 30 juin ; pas d'interpolation nécessaire |
| Forme du résultat | 1 121 municipios, médiane ≈ 10 000 habitants : nombreuses cellules municipio × âge × année à zéro naissance | log(naissances + 0,5 pour 1 000 femmes) comme au niveau commune en France (§5), Poisson à effets fixes avec offset en comparaison ; sensibilité taux brut / asinh rapportée |
| Contrôles de pré-période (§4.1) | Pas de Filosofi ni RP communal ; projections DANE par área | part de population en cabecera en 2015 (densité), log de la population 2015, part des naissances de mères de niveau d'éducation supérieur en 2013-2015 (`NIV_EDUM`, codes 7-12 du codage 2008+), tendance 2010-2014 du log du taux ; liste écrite ici, avant estimation |
| Placebo H5b | Décès par municipio : DANE EEVV « defunciones » non téléchargées à ce stade | H5b non construit (dit) ; H5a et H5c estimés |
| Hétérogénéité H6 | densité (part cabecera, terciles), population (terciles), **rang de naissance** (`N_HIJOSV` disponible toute la période : rang 1 vs 2+) | H6 : densité, taille, rang 1 vs 2+ ; pas de revenu ni de ZDP |
| COVID | 2020-2021 | robustesse « sans 2020-2021 » comme en France |

## A5 — Brésil : addendum de mesure et décision d'inclusion (04/10/2026, avant toute estimation)

Rédigé fichiers en main (check-list dans `docs/data_log.md` ; sources `br_anatel_municipios_atendidos`, `br_ibge_nascidos_vivos`,
`br_ibge_censo_mulheres`, `br_ibge_populacao_estimada`, `br_ibge_casamentos`). Aucune estimation n'a été lancée sur le Brésil avant ce commit.

### Critères d'inclusion (§4.3)

| Critère | Constat | Verdict |
|---|---|---|
| (1) traitement infranational daté, ≥ 3 ans de pré-période pour ≥ 30 % des unités | Anatel, « Municípios atendidos por SMP » : présence de chaque technologie par opérateur et município, instantanés de décembre 2013-2016 puis mensuels 2017 → 2026-08 ; 5 570 municípios. Au 2013-12 la 4G est « NÃO » partout (y compris São Paulo, où elle est commercialisée depuis avril 2013) : première observation utilisable 2014-12. Première année de présence 4G (≥ 1 opérateur) : 2014 : 189, 2015 : 298, 2016 : 551, 2017 : 2 739, 2018 : 680, 2019 : 399, 2020 : 424, 2021 : 170, 2022 : 60, 2023 : 60. Naissances depuis 2003 → ≥ 11 ans de pré-période pour toutes les unités | rempli |
| (2) naissances par âge au niveau de l'unité, annuelles, couvrant la pré-période | IBGE, Estatísticas do Registro Civil (table 2609, API) : nés vivants enregistrés dans l'année, par município de **résidence de la mère**, année de naissance et groupe d'âge de la mère, 2003-2024. DATASUS/SINASC (microdonnées) inaccessible depuis l'environnement (FTP et TabNet réinitialisés par le proxy, PCDaS avec compte) | rempli |
| (3) téléchargement scriptable, licence | fichiers zip Anatel (dados abertos) et API IBGE sans identification | rempli |
| (4) dénominateurs par sexe et âge | IBGE, recensements 2000 (groupes quinquennaux), 2010 et 2022 (âges simples) par município, et estimations annuelles de population totale (table 6579) ; pas de projection municipale annuelle par âge accessible (DATASUS bloqué) → interpolation entre recensements (ci-dessous) | rempli |

Décision : **Brésil inclus** dans la partie causale.

### Décisions de mesure (§4.2 ; catégories §10)

| Point | Ce que disent les fichiers | Décision |
|---|---|---|
| Unité | município (code IBGE à 7 chiffres) ; 5 565 municípios en 2000, 5 570 depuis 2013 | município ; les 5 municípios créés après 2000 et leurs municípios d'origine sont exclus (géographie la plus récente non reconstituable en 2000, §10) ; grappes = município |
| Traitement (§4.2 : « première année où la couverture 4G de la population atteint 50 % ») | pas de part de population couverte avant 2021-11 ; présence binaire de la 4G par opérateur et município | **présence de la 4G par au moins un opérateur** dans le município (instantané de décembre 2014-2016, premier mois de présence 2017 →) ; cohorte = année de première présence ; le régulateur ne publiant pas la part de population couverte, c'est le seul indicateur municipal daté (§10). La cohorte 2014 (189 municípios) contient des municípios peut-être couverts dès 2013 (première observation utilisable 2014-12) : gardée en primaire, **exclue en robustesse** ; variante « ≥ 2 opérateurs » ; 3G en robustesse (présence 3G, instantanés dès 2013-12, municípios déjà couverts au 2013-12 exclus comme censurés) |
| Années | naissances 2003-2024 (2024 : enregistrements tardifs de 2025 non disponibles → provisoire) ; traitement 2014-2023 | fenêtre d'estimation **2003-2024**, robustesse 2003-2023 ; cohortes 2014-2023 ; « jamais traités » = municípios sans 4G au 2024-12 (aucun : tous couverts en 2023 → contrôle = pas encore traités, dernière cohorte 2023) |
| Naissances par année d'occurrence | la table 2609 donne les naissances **enregistrées** dans l'année t par année de naissance | naissances de l'année t = enregistrées en t et nées en t + enregistrées en t+1 et nées en t ; convention SIDRA lue le 04/10/2026 avant estimation : « - » = zéro absolu, « ... » = non disponible et « X » = secret (manquants, comptés) |
| Groupes d'âge | groupes quinquennaux 15-19 … 45-49, < 15, ≥ 50, ignoré | 15-19, 20-24, 25-29, 30-34, 35-39, 40-49 ; < 15 et ≥ 50 hors périmètre ; âge ignoré exclu et compté |
| Dénominateurs | femmes par âge aux recensements 2000, 2010, 2022 ; population totale annuelle 2001-2021, 2024 (estimations IBGE) | femmes du groupe d'âge en t = part du groupe dans la population totale du município, interpolée linéairement entre recensements (constante après 2022) × population totale de l'année (estimation IBGE ; 2007, 2022 et 2023 interpolés/recensement) ; **dit : dénominateurs lissés, le taux ne capte que les variations du numérateur entre recensements** |
| Canal (H3) | mariages homme-femme par município et groupe d'âge de l'épouse 2013-2024 (table 4412) ; pas d'état civil de la mère dans la table 2609 | **H3a** sur la fenêtre 2013-2024 (mariages de femmes pour 1 000 femmes du groupe d'âge ; pré-période courte, dite) ; H3b et H3c non testables (dit) |
| Forme du résultat | nombreuses petites unités (médiane ≈ 11 000 habitants) | log(naissances + 0,5 pour 1 000 femmes) comme en Colombie ; Poisson à effets fixes en comparaison ; taux brut / asinh en sensibilité |
| Contrôles de pré-période (§4.1) | recensement 2010, naissances 2003-2013 | log de la population 2010, part des femmes 15-49 dans la population 2010, niveau moyen 2008-2013 et tendance 2008-2013 du log du taux 15-49 ; liste écrite ici, avant estimation |
| Placebo H5b | décès par município non téléchargés | H5b non construit (dit) ; H5a et H5c estimés |
| Hétérogénéité H6 | population 2010 ; grande région (5) ; pas de rang de naissance ni de densité | H6 : terciles de population 2010 et grandes régions |
| COVID | 2020-2021 | robustesse « sans 2020-2021 » |

## A6 — Espagne : addendum de mesure et décision d'inclusion (04/10/2026, avant toute estimation)

Rédigé fichiers en main (check-list dans `docs/data_log.md` ; sources `es_cobertura_municipios_2013_2020`, `es_cobertura_municipios_2021_2025`,
`es_ine_nacimientos_microdatos`, `es_ine_matrimonios_microdatos`, `es_ine_padron_municipios_edad`). Aucune estimation n'a été lancée sur
l'Espagne avant ce commit.

### Critères d'inclusion (§4.3)

| Critère | Constat | Verdict |
|---|---|---|
| (1) traitement infranational daté, ≥ 3 ans de pré-période pour ≥ 30 % des unités | MINECO/SETELECO, couverture LTE en % de la population par municipio (8 131) : déc. 2013, déc. 2014, déc. 2015, juin 2016 → juin 2020 ; municipios ≥ 50 % : 210, 1 051, 2 795, 3 713, 5 313, 7 274, 7 735, 7 948. Parmi les 753 municipios de plus de 10 000 habitants (seuls identifiables dans les naissances, critère 2) : 179 (déc. 2013), 580 (déc. 2014), 749 (déc. 2015), 753 (juin 2016). Naissances par municipio depuis 2007 → ≥ 6 ans de pré-période pour les 574 municipios (76 %) basculés après 2013 | rempli |
| (2) naissances par âge au niveau de l'unité | INE, microdonnées des naissances : municipio de résidence de la mère codé **seulement si > 10 000 habitants** (81,7 % des naissances en 2019), âge de la mère, état civil, rang | rempli pour les municipios > 10 000 habitants (l'unité est donc ce sous-ensemble ; les tables agrégées INE par municipio ne couvrent que 155 villes) |
| (3) téléchargement scriptable, licence | xlsx sur digital.gob.es (datos.gob.es bloqué par le proxy), zip INE ; réutilisation libre avec mention | rempli |
| (4) dénominateurs par sexe et âge | INE, Padrón continuo par municipio, sexe et âge quinquennal, 1er janvier 2003-2022 (série arrêtée en 2022) | rempli |

Décision : **Espagne incluse** dans la partie causale, avec une **limite d'identification dite avant estimation** : parmi les municipios
> 10 000 habitants, la bascule ≥ 50 % est concentrée sur 2013-2015 et aucun n'est « jamais traité » ; Callaway & Sant'Anna identifie les ATT(g,t)
contre les cohortes pas encore traitées, donc pour 2014 (contrôle = cohortes 2015-2016) et 2015 (contrôle = cohorte 2016, 4 municipios) : les
effets au-delà de +1 ne sont pas identifiés sur la spécification primaire ; les comparaisons (TWFE, Sun & Abraham, did2s) sur la fenêtre
identifiée seulement.

### Décisions de mesure (§4.2 ; catégories §10)

| Point | Ce que disent les fichiers | Décision |
|---|---|---|
| Unité | municipio (code INE à 5 chiffres = province + municipio) codé si > 10 000 habitants l'année de la naissance | municipios codés **toutes les années de la fenêtre** (panel équilibré) ; grappes = municipio ; les municipios ayant changé de code (fusions) sont exclus s'ils ne sont pas identifiables sur toute la fenêtre |
| Traitement | % de population couverte en LTE, instantanés de décembre (2013-2015) puis de juin (2016-2020) | cohorte = année du premier instantané avec part ≥ 50 % (variante 90 %) ; déc. 2013 → 2013 (4G commercialisée depuis mi-2013 : cohorte 2013 gardée en primaire, **exclue en robustesse** comme première observation) ; juin t → t ; municipios < 50 % en juin 2020 = jamais traités sur la fenêtre (4 parmi les > 10 000) |
| Années | microdonnées 2007-2024 (dessins d'enregistrement 2007-2015 et 2016+) ; Padrón par âge 2003-2022 | fenêtre d'estimation **2007-2022** (les naissances 2023-2024 n'ont pas de dénominateur municipal par âge : dit) ; robustesse « sans 2020-2021 » |
| Groupes d'âge | âge de la mère en années (EDADM) | 15-19, 20-24, 25-29, 30-34, 35-39, 40-49 ; < 15 et ≥ 50 hors périmètre, comptés |
| Dénominateurs | Padrón au 1er janvier par groupe quinquennal | femmes du groupe au 1er janvier de l'année (pas d'interpolation ; moyenne 1er janvier t / t+1 non retenue pour rester comparable aux autres pays) |
| Canal (H3) | mariages (microdonnées 2008-2024, municipio de résidence du couple codé si > 10 000, sexe et âge des conjoints) ; état civil de la mère à la naissance (célibataire, mariée, veuve, divorcée/séparée ; l'union libre n'est pas distinguée) | **H3a** = mariages de femmes (couples homme-femme, âge de l'épouse) pour 1 000 femmes du groupe, fenêtre 2008-2022 ; **H3b** = naissances de mères **mariées** pour 1 000 femmes (dénominateur : toutes les femmes, dit) ; H3c non testable |
| Forme du résultat | municipios > 10 000 habitants : peu de cellules nulles par groupe d'âge | log(naissances + 0,5 pour 1 000 femmes) comme en Colombie et au Brésil ; Poisson à effets fixes en comparaison |
| Contrôles de pré-période (§4.1) | Padrón, naissances 2007-2012 | log de la population 2013, part des femmes 15-49 en 2013, part des naissances de mères nées à l'étranger 2010-2012, tendance 2008-2012 du log du taux 15-49 ; liste écrite ici |
| Placebo H5b | décès par municipio non téléchargés | H5b non construit (dit) ; H5a et H5c estimés |
| Hétérogénéité H6 | population 2013 ; rang (NUMHV) | H6 : terciles de population 2013 ; rang 1 vs 2+ |
| COVID | 2020-2021 | robustesse « sans 2020-2021 » |

## A7 — Synthèse entre pays : règles de mise en œuvre (04/10/2026, avant toute méta-analyse)

Quatre pays inclus (France, Colombie, Brésil, Espagne) ; §4.3 exige ≥ 3. Écrit après les estimations nationales (France, Colombie, Espagne
exécutées ; Brésil en cours) et **avant** le premier calcul poolé. Ce que §5 fixe : méta-analyse à effets aléatoires (REML) des ATT par
groupe d'âge en % du taux contrefactuel, intervalle de prédiction, I² ; test primaire = estimation poolée 25-39 ans.

| Point | Décision |
|---|---|
| Lignes retenues par pays | l'ATT[1,k] primaire de chaque pays (`post_avg`, Callaway & Sant'Anna, spécification primaire : France département D3 ≥ 50 % ; Colombie, Brésil, Espagne municipios avec covariables), pour H2b (25-39) et pour chaque groupe d'âge (H2a, H2c) ; k est celui identifié dans le pays (4 en France, 5 en Colombie, 1 en Espagne), **dit** dans le tableau |
| Conversion en % | 100 × (exp(ATT) − 1) ; écart-type par la méthode delta (100 × exp(ATT) × es) |
| Écart-type | primaire : écart-type par covariance des fonctions d'influence (celui de §5) ; secondaire : écart-type du bootstrap par grappes quand il existe (`post_avg_boot`) |
| Méthode | REML itéré (`statsmodels.combine_effects`), IC 95 %, intervalle de prédiction à 95 % (t à K − 2 degrés de liberté), I², τ² |
| Pays dont le pré-test (H5c) est rejeté | **primaire = tous les pays inclus, sans exclusion** (§5 ne prévoit pas de filtre) ; **sensibilité, décidée ici** : poolé sans les pays dont le test de Wald pré de la spécification primaire H2b rejette à 5 % — au moment d'écrire, c'est le cas de la France (p = 0,004) et de l'Espagne (p < 0,001) ; cette sensibilité est exploratoire et n'entre pas dans la règle §6 |
| Règle §6 | appliquée telle quelle : H2b rejetée (p < 0,05) de même signe dans ≥ 2 pays de niveau 1 et poolé significatif, et H5a-c non rejetés dans ces pays ; le script imprime chaque condition pays par pays |
| Sorties | `scripts/18_meta.py` → `tables/t_meta.md`, `tables/t_meta.csv`, `figures/fig_meta.pdf` (forêt par groupe d'âge) |
