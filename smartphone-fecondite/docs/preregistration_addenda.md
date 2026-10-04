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
