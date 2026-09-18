# Préregistration — Smartphones, réseaux sociaux, applications de rencontre et fécondité

Version 1.0, 18 septembre 2026. Rédigée **avant tout téléchargement et toute analyse**.
Règle de gel : ce document n'est plus modifié après le commit qui le contient. Toute déviation
ultérieure est consignée dans `docs/preregistration_addenda.md`, datée, avec sa raison, et rapportée
dans le papier (section 5 et annexe). Le hash du commit de gel est cité dans le papier.

Sont autorisées après lecture des données, et seulement elles (liste fermée, §10) : les décisions
de mesure qui dépendent de la structure exacte des fichiers (noms de variables, années disponibles,
harmonisation géographique). Les hypothèses, les résultats primaires, les règles de décision, les
estimateurs et les seuils ci-dessous ne le sont pas.

---

## 1. Questions

- **Q1.** La diffusion des smartphones, identifiée par l'arrivée de la couverture 3G/4G dans une
  unité géographique, a-t-elle un effet causal sur la fécondité des femmes de **25 ans et plus**, et
  pas seulement sur celle des adolescentes et des 20-24 ans ?
- **Q2.** Si oui, cet effet passe-t-il par la **mise en couple** (moins de couples, ou plus tard) ou
  par la **fécondité au sein des couples** ?

Le panel international et les cas de niveau 3 (`etape0_pays.md`) ne répondent à aucune de ces
questions ; ils décrivent.

## 2. Cadre conceptuel et prédictions par canal

Le smartphone agit comme une technologie d'usage (réseaux sociaux, applications de rencontre,
information, divertissement) accessible dès que la couverture mobile haut débit existe. Cinq canaux
sont distingués. Pour chacun, on écrit ce qu'il implique sur les variables observées, afin que les
résultats puissent départager ce qui est testé de ce qui reste conjecture.

| Canal | Mécanisme | Prédiction observable | Testé ici ? |
|---|---|---|---|
| (a) marché de l'appariement | l'élargissement du choix et le report de l'engagement retardent la mise en couple | baisse des taux de mariage / PACS / vie en couple aux âges 20-34 ; fécondité **au sein des couples** inchangée ; effet sur les naissances retardé de 1 à 3 ans par rapport à l'effet sur les unions | oui (H3) |
| (b) déplacement du temps | le temps d'écran remplace le temps en couple et l'activité sexuelle | baisse de la fécondité **au sein des couples**, sans effet marqué sur la mise en couple | oui (H3) |
| (c) normes et aspirations | exposition à des modèles de vie sans enfant ou à enfant unique | baisse aux âges 25-39 et pour les couples installés ; hausse de la part des rangs 1 dans les naissances ; effets plus forts chez les diplômées | partiellement (hétérogénéité par rang et par diplôme) |
| (d) coût d'opportunité | emploi, télétravail, revenu | effet ambigu ; concurrent de l'exclusion de l'instrument | partiellement (emploi des femmes 25-39 comme résultat concurrent) |
| (e) santé mentale | anxiété, dépression | baisse aux âges jeunes surtout | non |

## 3. Hypothèses

Toutes les hypothèses sont testées en bilatéral au seuil de 5 %. Le signe attendu est indiqué mais
n'entre pas dans la règle de décision.

**H1 — effet total (niveau unité fine).** L'arrivée de la 4G dans une commune (ou l'unité
équivalente) modifie le nombre de naissances pour 1 000 femmes de 15-49 ans. Signe attendu : négatif.
Résultat primaire : ATT moyen sur les années +1 à +5 après la bascule (Callaway & Sant'Anna).

**H2 — effet par âge (test central).**
- H2a : effet négatif sur les taux de fécondité des 15-19 et 20-24 ans.
- H2b : effet sur le taux de fécondité agrégé des **25-39 ans** (pondéré par les effectifs de femmes).
  C'est le **test primaire du papier** : un seul test, sans correction pour tests multiples.
- H2c : effets séparés 25-29, 30-34, 35-39 et 40-49 (secondaires, corrigés par Holm au sein de chaque
  pays).
- H2d : test d'égalité entre l'effet 15-24 et l'effet 25-39 (secondaire).

**H3 — canal.**
- H3a (mise en couple) : effet sur (i) le taux de mariage pour 1 000 femmes par âge, (ii) le taux de
  PACS ou d'union enregistrée quand il existe, (iii) la part des femmes en couple par âge
  (recensement). Signe attendu : négatif.
- H3b (fécondité des couples) : effet sur les naissances pour 1 000 femmes **en couple** par âge
  (numérateur : naissances par âge ; dénominateur : femmes en couple par âge). Là où la variable
  existe (Brésil, Colombie, Mexique, France via l'année de mariage des parents), résultat
  complémentaire : naissances de mères en couple / mariées pour 1 000 femmes en couple / mariées.
- H3c (calendrier) : sous (a), l'effet sur les unions précède l'effet sur les naissances d'au moins un
  an dans l'event study ; sous (b), les deux sont simultanés ou l'effet sur les naissances précède.

**H4 — first stage.** La couverture 4G augmente la possession de smartphone et l'usage des réseaux
sociaux (Baromètre du numérique, région × âge × année ; Eurostat par pays × âge), davantage chez les
moins de 40 ans. Si H4 n'est pas vérifiée dans un pays, la forme réduite y reste interprétable comme
effet de la couverture, mais pas comme effet du smartphone ; le papier le dit.

**H5 — placebos et falsification.**
- H5a : aucun effet des « bascules » décalées de −3 ans (pré-tendances).
- H5b : aucun effet sur un résultat sans lien attendu : décès des 60 ans et plus pour 1 000 habitants.
- H5c : coefficients pré-traitement de l'event study conjointement nuls (test de Wald sur −8 à −2, la
  période −1 servant de référence).

**H6 — hétérogénéité (secondaire, exploratoire, corrigée par Holm).** Effets par densité (grille
communale ; rural / intermédiaire / dense), par revenu médian communal (terciles de pré-période), par
part de diplômées du supérieur (terciles), par appartenance à la zone de déploiement prioritaire
(France), par rang de naissance (1 vs 2+).

**Prédictions descriptives (non testées statistiquement).** Dans les pays où les séries existent, la
courbe d'adoption du smartphone par âge précède de 1 à 3 ans la baisse de la mise en couple et de 2 à
4 ans la baisse de la fécondité des mêmes âges. Une désynchronisation (baisse de fécondité antérieure
à l'adoption) est un fait contraire, rapporté tel quel.

## 4. Unités, traitement, résultats

### 4.1 France (cœur)

| Élément | Définition |
|---|---|
| Unité fine | commune, géographie du 1er janvier 2024 (communes fusionnées agrégées sur toute la période via les tables de passage du COG) ; France métropolitaine ; DOM en robustesse |
| Unité âge | département (96 métropolitains ; DOM en robustesse) × groupe d'âge (15-19, 20-24, 25-29, 30-34, 35-39, 40-49) |
| Années | commune 2004-2024 ; département × âge 1998-2025 |
| **D1** (traitement principal) | `4G_ct = 1` si au moins un émetteur LTE (ANFR, `EMR_LB_SYSTEME` commençant par « LTE ») est en service dans la commune au 1er janvier de l'année *t* ; cohorte = première année où D1 = 1. Recoupement avec les archives mensuelles de l'observatoire ANFR (2015+) ; en cas de désaccord de plus d'un an, l'observatoire prime |
| **D2** (second traitement) | année où la part de la population communale couverte en 4G par au moins un opérateur (ARCEP) atteint 90 % ; fenêtre 2017-2024 ; et variante « 4 opérateurs » |
| **D3** (exposition département) | part des femmes de 15-49 ans du département résidant dans une commune avec D1 = 1 ; bascule département = première année où D3 ≥ 50 % (variante 90 %) |
| 3G | même construction sur les émetteurs UMTS, robustesse seulement (cohortes 2008-2012) |
| Résultat H1 | naissances domiciliées de l'année (INSEE) ; taux pour 1 000 femmes 15-49 (RP, millésime interpolé linéairement entre millésimes) |
| Résultats H2 | naissances par âge de la mère (fichiers détail, `AGEMERE`, `DEPDOM`) pour 1 000 femmes de l'âge (estimations de population départementales) |
| Résultats H3a | mariages par âge de l'épouse (fichiers détail mariages, département de domicile) pour 1 000 femmes ; PACS pour 1 000 femmes 15-49 (département) ; part des femmes en couple par groupe d'âge (base Couples-Familles-Ménages, commune et département) |
| Résultat H3b | naissances par âge / femmes en couple du même âge (département) ; naissances de parents mariés (`AMAR` renseignée) / femmes mariées |
| First stage | Baromètre du numérique : possession de smartphone, usage quotidien des réseaux sociaux, par région × âge × année, régressés sur D3 régional |
| Contrôles (pré-période, pour les tendances parallèles conditionnelles) | classe de densité, revenu médian (Filosofi 2012 ou premier millésime), part de diplômées du supérieur (RP 2011), taux de chômage 15-24 (RP 2011), tendance des naissances 2004-2011 |
| Chocs concurrents | effets fixes année × classe de densité ; couverture fixe très haut débit (ARCEP) en contrôle variable dans le temps en robustesse ; exclusion 2020-2021 en robustesse |

### 4.2 Autres pays (niveau 1 et 2)

Règle commune, à décliner dans un **addendum par pays** rédigé et committé **avant** la première
estimation de ce pays, et limité aux points de mesure ci-dessous.

| Élément | Règle par défaut (modifiable seulement dans l'addendum, avec raison) |
|---|---|
| Unité | la plus fine où naissances par âge et traitement coexistent (commune / municipio / kommun / local authority / Kreis) |
| Traitement, sources de **couverture** (Espagne, Suède, Colombie, Royaume-Uni, Finlande, Norvège, Tchéquie, Belgique…) | cohorte = première année où la couverture 4G de la population de l'unité (ou de la surface si seule disponible) atteint **50 %** par au moins un opérateur ; variante 90 % |
| Traitement, sources d'**adoption** (Brésil : accès Anatel par technologie) | cohorte = première année où les accès 4G atteignent **1 pour 100 habitants** dans le município ; variante 5 pour 100 |
| Traitement, sources de **sites** (Pologne, Suisse, Équateur, Australie) | cohorte = première année avec au moins un site LTE en service ; utilisable seulement en robustesse d'un pays de niveau 1, jamais comme traitement principal |
| Pré-période minimale | 3 années observées avant la cohorte ; les unités traitées avant la troisième année de données sont exclues (« toujours traitées ») |
| Groupes d'âge | 15-19, 20-24, 25-29, 30-34, 35-39, 40-49 ; si le pays ne fournit que des groupes différents, la correspondance est écrite dans l'addendum et le test primaire porte sur le groupe le plus proche de 25-39 |
| Dénominateurs | population féminine par âge de la source officielle nationale ; interpolation linéaire entre années manquantes ; jamais d'extrapolation au-delà de deux ans |
| Résultats de canal | mariages par âge quand ils existent ; état civil / union de la mère à la naissance quand il existe ; sinon H3 non testé pour ce pays, dit explicitement |

### 4.3 Critères d'inclusion des pays (fixés maintenant, appliqués à l'Étape 2 dans l'ordre de `etape0_pays.md` §4)

Un pays est inclus dans la partie causale si, fichiers en main : (1) traitement infranational daté
avec ≥ 3 années de pré-période pour au moins 30 % des unités ; (2) naissances par âge au niveau de
l'unité ou plus grossier, annuelles, couvrant la pré-période ; (3) téléchargement scriptable et
licence permettant la reproduction ; (4) dénominateurs par sexe et âge. Un pays qui échoue est
listé en annexe avec la raison. **La décision d'inclusion est prise et committée avant toute
estimation sur ce pays**, et n'est jamais révisée après. Nombre minimal pour la synthèse entre
pays : 3 pays inclus (France comprise). En dessous, pas de méta-analyse ; les résultats sont
présentés pays par pays.

## 5. Stratégie d'estimation

**Spécification primaire (H1, H2, H3) : Callaway & Sant'Anna (2021)** sur les cohortes de bascule,
groupe de contrôle = unités pas encore traitées (variante : jamais traitées), estimateur doublement
robuste avec les contrôles de pré-période, agrégation dynamique (event study, −8 à +8, référence −1)
et agrégation « moyenne sur +1 à +5 » pour les résultats primaires. Implémentation : paquet Python
`differences` (ATTgt), vérifié contre `csdid`.

**Spécifications de comparaison (toujours rapportées)** : event study saturée cohorte × période
(Sun & Abraham 2021, `pyfixest.SaturatedEventStudy`) ; did2s (Gardner 2022) ; TWFE naïf. Si CRAN
devient accessible : de Chaisemartin & D'Haultfœuille (`did_multiplegt_dyn`) ajouté sans changer le
primaire.

**Forme des résultats** : comptes → Poisson à effets fixes (`fepois`) avec exposition = femmes de
l'âge ; l'ATT est exprimé en % du taux contrefactuel. Pour Callaway & Sant'Anna, résultat = log du
taux (naissances + 0,5 pour les zéros au niveau commune ; sans correction au niveau département) ;
la sensibilité à la transformation est rapportée (taux brut, log, asinh).

**Traitement continu (D3 département)** : bascule à 50 % pour le primaire ; en complément, régression
à effets fixes département × âge et année × âge sur D3 continu, en signalant que l'interprétation
sous traitement continu repose sur des hypothèses plus fortes.

**Inférence** : erreurs standard groupées au niveau de l'unité de traitement (commune ; département
pour le niveau âge). Bootstrap multiplicatif de Callaway & Sant'Anna pour les bandes simultanées de
l'event study. Robustesse : groupage au département pour le niveau commune. Tests secondaires
corrigés par Holm au sein de chaque famille (âges d'un pays ; hétérogénéités d'un pays).

**Fenêtres** : primaire = toutes les années disponibles ; robustesse = 2008-2019 (hors COVID et hors
cohortes précoces mal datées), et exclusion des cohortes 2012-2014 en France (biais de survie ANFR).

**Puissance** : avant toute estimation, taille d'effet minimale détectable (80 %, 5 %) par
permutation des cohortes sur les vraies données (200 permutations), pour H1 et H2b, par pays.
Rapportée dans le tableau des échantillons. Un résultat nul est décrit comme « non détecté à la
puissance de X % pour un effet de Y % ».

**IV (secondaire)** : 2SLS au niveau région × âge × année (France), adoption instrumentée par D3.
Présentée comme re-normalisation de la forme réduite. La restriction d'exclusion est discutée et
partiellement testée : effet de D3 sur l'emploi des femmes 25-39 (RP) ; si cet effet est significatif,
l'IV n'est pas interprétée.

**Synthèse entre pays** : méta-analyse à effets aléatoires (REML) des ATT par groupe d'âge exprimés
en % du taux contrefactuel, avec intervalle de prédiction et I². Le test primaire de la synthèse est
l'estimation poolée pour 25-39 ans.

## 6. Règles de décision (écrites avant les résultats)

| Conclusion | Condition |
|---|---|
| **Effet net sur les 25 ans et plus : établi** | H2b rejetée (p < 0,05) dans au moins deux pays de niveau 1 avec le même signe, et estimation poolée significative ; H5a-c non rejetées dans ces pays |
| **Effet net sur les 25 ans et plus : non détecté** | H2b non rejetée dans les pays inclus et estimation poolée non significative, avec intervalle de confiance excluant un effet ≥ 3 % du taux 25-39 → « absence d'effet d'au moins 3 % » |
| **Indéterminé** | tout autre cas (intervalles larges, signes contraires entre pays, placebos rejetés) |
| **Canal dominant : mise en couple** | H3a rejetée avec signe négatif et H3b non rejetée, et différence des effets standardisés significative à 5 % |
| **Canal dominant : fécondité des couples** | symétrique |
| **Canal indéterminé** | différence non significative, ou les deux rejetées, ou données de canal absentes |
| **Statut du smartphone comme facteur de la baisse de fécondité (section 11)** | *premier ordre* si l'effet poolé sur 25-39 explique ≥ 25 % de la baisse observée du taux 25-39 entre l'année de lancement 4G et la dernière année observée, dans les pays inclus ; *second ordre* si entre 5 % et 25 % ; *négligeable* si < 5 % ou non détecté avec puissance suffisante ; *indéterminé* sinon. Ce calcul utilise uniquement les estimations du papier |
| **Critères de révision (section 11)** | à la hausse : réplication indépendante d'un effet net sur les 25+ dans ≥ 2 pays supplémentaires avec un design causal ; à la baisse : échec de réplication dans ≥ 2 pays de niveau 1 ou rejet des placebos dans la réplication |

## 7. Ce qui sera rapporté quoi qu'il arrive

Toutes les estimations primaires et secondaires, tous les pays vérifiés (inclus ou exclus, avec la
raison), toutes les spécifications de comparaison, les placebos, les MDE, les tableaux d'échantillon
(unités-années par spécification), les first stages, les déviations à cette préregistration.

## 8. Ce qui n'est pas testé et ne sera pas conclu

Le canal santé mentale ; l'effet propre des applications de rencontre séparément des réseaux sociaux
(aucune série infranationale d'usage) ; tout effet dans les pays de niveau 3 ; toute causalité à
partir du panel international ou du panel NUTS 2.

## 9. Ordre d'exécution

1. Téléchargement et journal (`data_log.md`) ; 2. construction du traitement et vérification de
cohérence entre sources (D1 vs D2 vs observatoire) ; 3. tableau d'échantillon et MDE ; 4. décision
d'inclusion des pays (§4.3), committée ; 5. first stage ; 6. estimations primaires ; 7. secondaires,
robustesse, hétérogénéité ; 8. synthèse. Aucune estimation d'un pays avant son addendum.

## 10. Liste fermée des décisions autorisées après lecture des données

- correspondance des noms de variables et des codes géographiques avec les définitions ci-dessus ;
- première et dernière année réellement disponibles par source ;
- harmonisation des fusions et scissions d'unités (règle : agrégation à la géographie la plus
  récente) ;
- pour un pays, choix entre « population » et « surface » couverte selon ce que publie le
  régulateur ;
- correction d'erreurs manifestes de saisie dans les sources (dates de mise en service antérieures au
  lancement commercial national → recodées à la date de lancement, comptées et rapportées).

Tout le reste est fixé.
