# Étape 0 bis — Extension à d'autres pays : faisabilité du design causal

Date : 18 septembre 2026. Complément à `etape0_plan.md` à la demande de l'auteur (« beaucoup plus de pays »).

## 0. Méthode et limites de ce balayage

Trois agents de recherche ont balayé 47 pays et les proxys mondiaux, **uniquement par recherche web**
(les sites des producteurs restent inaccessibles depuis cet environnement, voir `etape0_plan.md` §1).
Le quota de recherche de la session a été épuisé avant la fin : pour la plupart des pays, les tables
de mariages par âge et les dénominateurs de population n'ont pas pu être cherchés, et de nombreux
points sont marqués **non confirmé**. Rien n'a été téléchargé. Tout ce qui suit doit être re-vérifié
fichier en main à l'Étape 2, dans l'ordre fixé en §4.

Critère d'entrée dans la partie causale (identique pour tous les pays, à préenregistrer) :
1. calendrier de déploiement 3G/4G **infranational** (commune, district, comté), daté, couvrant
   les années de déploiement avec **au moins 3 années avant traitement** pour une part substantielle
   des unités ;
2. naissances **par âge de la mère** au même niveau ou à un niveau plus grossier, annuelles, sur les
   mêmes années ;
3. données ouvertes et **téléchargeables par script** (pas d'extraction manuelle, pas d'accès sur
   approbation) ;
4. dénominateurs de population par sexe et âge au niveau du résultat.
Mariages par âge : souhaitable, pas obligatoire (le canal est alors testé par les naissances hors
mariage / hors union quand la variable existe).

Niveaux : **N1** = prêt pour le design causal (critères 1-4 confirmés ou très probables) ;
**N2** = possible sous conditions à vérifier (nommées) ; **N3** = descriptif seulement.

## 1. Classement

### Niveau 1 — réplications causales (5 pays, France comprise)

| Pays | Traitement (source, granularité, années) | Naissances par âge (source, granularité, années) | Mariages | Risque principal |
|---|---|---|---|---|
| **France** | ANFR émetteurs LTE par commune, cohortes 2012-2020 ; ARCEP couverture par commune 2017-T4+ ; ZDP 2011 | INSEE fichiers détail : département × âge 1998-2025 ; naissances par commune 2004-2024 (sans âge) | INSEE fichiers détail, département × âge 1998-2024 ; PACS département | pas d'âge au niveau commune |
| **Espagne** | MINECO/SETID « Base de datos histórica 2013-2021 de cobertura banda ancha fija y móvil » (datos.gob.es, un XLSX, LTE par *entidad singular de población*, agrégeable à la commune) ; 4G lancée mi-2013, couverture 48 % (2014) → 76 % (2015) | INE « Estadística de nacimientos », microdonnées annuelles en accès direct (âge de la mère, commune de résidence pour les communes au-dessus d'un seuil de population) | INE « Estadística de matrimonios », microdonnées (non confirmé) | seuil de taille des communes dans les microdonnées ; passage entidad → commune |
| **Suède** | PTS « Mobiltäcknings- och bredbandskartläggning », par kommun, annuel depuis 2013, Excel ; couverture par classe de débit (le « 4G » comme technologie n'est pas confirmé avant 2017 → seuil ≥ 10 Mbit/s comme proxy) | SCB table FoddaK « Födda efter region, moderns ålder och barnets kön » 1968-2024, kommun, API PxWeb | SCB PxWeb (identifiant non confirmé) | 4G lancée dès 2009-2010 : la variation exploitable est l'extension rurale 2013-2017 ; définitions de la mesure changeantes |
| **Brésil** | Anatel « Acessos SMP » par município × technologie, mensuel, 2007+ (abonnements, pas couverture) ; Anatel « Cobertura móvel » (% résidents couverts par secteur censitaire × opérateur × technologie ; profondeur historique non confirmée) | DATASUS SINASC, microdonnées 1996+ (município de résidence, âge, état civil de la mère y compris union consensuelle) | IBGE SIDRA table 4412 (âge des conjoints × município, API) | mesure d'adoption plutôt que de couverture ; ≤ 2 années pré-3G pour les grandes villes → design 4G (2013+) |
| **Colombie** (conditionnel) | MinTIC datos.gov.co `9mey-c8s8` « Cobertura móvil por tecnología, departamento y municipio por proveedor », trimestriel, 2G/3G/4G, API Socrata ; CRC Postdata (cabeceras et centros poblados) ; **année de début non confirmée** (≈ 2013 ?) | DANE EEVV nacimientos, microdonnées 1998-2024 (commune de résidence, âge, état civil de la mère) | aucune série trouvée | si la série débute après le lancement 4G (déc. 2013), pré-période insuffisante |

### Niveau 2 — possibles sous conditions (à vérifier dans cet ordre)

| Pays | Ce qui existe | Condition à vérifier | Niveau atteignable |
|---|---|---|---|
| **Royaume-Uni** | Ofcom Connected Nations, CSV par local authority 2015, 2016, 2017… (4G % locaux et % surface par opérateur) ; ONS/Nomis `lebirthsla` naissances par LA × groupe d'âge | fichiers 2013-2014 par LA (Infrastructure Report) ; sinon censure à gauche des LA traitées tôt | N1 sur les LA tardives |
| **Japon** | e-Stat table 出生5-2 « 出生数，市区町村・性・母の年齢(5歳階級)別 » (id 0003412062), API v3 avec clé gratuite ; mariages préfecture × âge | historique LTE par municipalité 2010-2015 (MIC ne publie que la 5G par municipalité ; PDF antérieurs) | N2 → N1 seulement avec un proxy (OpenCelliD, archives opérateurs) |
| **Allemagne** | Regionalstatistik 12612 « Lebendgeborene nach Altersgruppen der Mutter », Kreis, API GENESIS ; Breitbandatlas par Gemeinde (XLSX actuel) | série LTE par Gemeinde 2013-2019 : seulement dans les rapports PDF (atene KOM) | N2 (extraction PDF) |
| **Finlande** | StatFin 12dq naissances par municipalité × âge 5 ans 1990-2025, API ; Traficom couverture par municipalité (annuel, API partielle) | année de début de la série Traficom (4G finlandaise 2011-2016) | N1 si série ≥ 2012 |
| **Norvège** | Nkom Dekningsundersøkelsen (annuel, kommune × 4G) ; SSB naissances par région × âge de la mère 1972-2025 | téléchargements kommune 2013-2018 (vs PDF) ; niveau kommune de la table par âge | N1 possible, variation temporelle comprimée (97 % en 2018) |
| **Suisse** | BFS px-x-0102020204_102 naissances par Gemeinde × classe d'âge de la mère, API ; opendata.swiss 4G LTE disponibilité (grille 100 m) ; sites d'antennes LTE | millésimes historiques 2012-2016 ; dates de mise en service des antennes | N2 |
| **Tchéquie** | ČTÚ couverture LTE % population par obec, mensuel depuis 2015 ; ČSÚ base démographique par obec 1971+ | archive mensuelle 2015+ téléchargeable ; naissances par âge seulement au niveau okres | N2 |
| **Pologne** | UKE archive des permis radio GSM/UMTS/LTE, mensuel déc. 2014 – janv. 2021 (sites) ; GUS BDL API | naissances par âge au niveau powiat ; sites ≠ couverture ; manque 2013-2014 | N2 |
| **Italie** | ISTAT P.4 (âge en années simples, conçu pour la commune) ; AGCOM broadband map par commune | série communale 4G avant 2019 (déploiement 2012-2016) | N2, probablement N3 |
| **Danemark** | tjekditnet.dk extractions historiques depuis 2016 par kommune ; DST FODIE | déploiement 4G 2011-2015 largement antérieur à la série | N2 (design rural tardif) |
| **Belgique** | BIPT atlas, 589 communes × opérateur × technologie, depuis 2015 ; Statbel | millésimes 2015-2019 téléchargeables ; naissances commune × âge en open data | N2 |
| **Autriche** | Breitbandatlas données brutes data.gv.at (grille 100 m) ; Statistik Austria (STATcube) | historique ; conditions d'accès STATcube | N2/N3 |
| **Mexique** | INEGI naissances 1985-2024 (municipio, âge, état conjugal), mariages 1993-2024 (municipio, âges) ; CONAPO projections municipales par âge | aucun fichier scriptable de couverture par localité/municipio (cartes et PDF IFT ; BIT = abonnements par municipio, appli web) | N2 : résultats de niveau 1, traitement manquant |
| **Chili** | DEIS naissances 1992-2021 par comuna × âge ; INE projections comunales | aucune série historique de couverture par comuna | N2/N3 |
| **Pérou** | OSIPTEL couverture par centro poblado × technologie (trimestriel, instantanés jusqu'en 2019 puis 2023+) ; MINSA CNV naissances 2015-2025 (district, âge) | naissances seulement depuis 2015 (4G 2014) ; dénominateurs district × âge | N2 (districts ruraux tardifs) |
| **Équateur** | INEC naissances 1990-2024 (canton, âge) et mariages (canton, âges) | traitement à reconstruire à partir des bulletins ARCOTEL (radiobases par canton × technologie) | N2 |
| **Taïwan** | MOI/data.gov.tw naissances et mariages par âge ; NCC comptes de stations par canton/township (instantanés) | série historique par township ; croisement âge × township | N2 |
| **Afrique du Sud** | Stats SA Recorded Live Births, microdonnées 1998-2023 (district, âge) via DataFirst (inscription) ; ICASA couverture 3G/4G par province 2018+ | couverture infra-provinciale avant 2018 | N2 |
| **Turquie** | TÜİK naissances et mariages par province × âge 2001+ (interface dynamique) ; BTK bulletins provinciaux (abonnements, PDF) | 4.5G lancée nationalement en 2016 : faible échelonnement ; API non confirmée | N2/N3 |
| **Australie** | ABS naissances par SA2/LGA (taux par âge lissés sur 3 ans) ; ACMA registre des licences radio (archive mensuelle depuis 1996, sites) | pas de couverture historique ; lissage | N2/N3 |
| **Portugal** | INE/Pordata naissances par município × groupe d'âge 1996+ | aucune couverture 2012-2019 (GEO.ANACOM depuis 2022) | N3 sauf découverte |

### Niveau 3 — descriptif seulement

Corée du Sud, États-Unis (voir `etape0_plan.md` §4.2-4.3), Pays-Bas (déploiement national en 12-18
mois, pas de série), Irlande, Hongrie, Roumanie, Grèce, Argentine (naissances par province seulement),
Uruguay, Costa Rica, Nouvelle-Zélande, Israël, Inde, Indonésie, Thaïlande, Philippines, Vietnam,
Malaisie, Russie, Ukraine, Kazakhstan, Iran, Égypte, Maroc.

## 2. Extension descriptive à ~200 pays

| Source | Contenu | Usage |
|---|---|---|
| ITU DataHub, indicateur 100095 « Population coverage, by mobile network technology » (≥ 2G / 3G / LTE) | par pays × année, LTE ≈ 2015-2023 (début 3G non confirmé) ; téléchargement libre non confirmé | calendrier de couverture national |
| UN WPP 2024, fichier `WPP2024_SA5_FERT_F02` et API `population.un.org/dataportalapi` (ASFR5) | taux de fécondité par groupe d'âge quinquennal, tous pays, annuel 1950-2023 | fécondité par âge |
| Banque mondiale `IT.CEL.SETS.P2`, `IT.NET.USER.ZS`, `NY.GDP.PCAP.PP.KD`, `SP.DYN.TFRT.IN` ; ITU via OWID (haut débit mobile) | adoption, revenu | faits stylisés |
| Eurostat `isoc_ci_im_i`, `isoc_ci_ac_i`, `demo_r_frate2` | Europe par âge, régions | faits stylisés |

Cette extension permet, pour tous les pays, une superposition des courbes (couverture 3G/4G → fécondité
par âge) et une datation des ruptures. Conformément aux règles du cahier des charges, elle reste
descriptive : les corrélations trans-pays ne servent jamais de preuve.

## 3. Proxys mondiaux infranationaux : écartés ou conditionnels

- **OpenCelliD** (clé API gratuite ; champs `radio`, `created`, `lat/lon`) : date de première
  observation d'une cellule LTE par des contributeurs, pas la date de lancement ; densité de
  contributeurs très inégale ; téléchargement complet limité (conditions non confirmées). Utilisable
  seulement comme proxy de robustesse (Japon, Suisse), jamais comme traitement principal.
- **GSMA Mobile Coverage Explorer / Collins Bartholomew** : payant, non redistribuable (utilisé par
  Manacorda & Tesei 2020 ; Guriev, Melnikov & Zhuravskaya 2021). Écarté (règle des données ouvertes).
- **DHS** (historiques de naissances géolocalisés, ~60 pays) : inscription, description de projet,
  approbation, pas de redistribution. Reproductible seulement si chaque réplicateur obtient son
  propre accès. Écarté du pipeline principal ; mentionné en discussion.

## 4. Ordre de vérification à l'Étape 2 (à préenregistrer pour éviter la sélection a posteriori)

1. France (inchangé).
2. Espagne, Suède, Brésil, Colombie : vérifier les quatre critères fichier en main ; une check-list
   par pays dans `data_log.md` ; inclusion décidée **avant** toute estimation.
3. Royaume-Uni, Finlande, Norvège, Suisse, Tchéquie, Belgique : même check-list.
4. Japon, Allemagne, Mexique, Chili, Pérou, Équateur, Taïwan, Afrique du Sud, Pologne, Italie,
   Danemark, Autriche, Turquie, Australie, Portugal : seulement si le temps le permet, et dans cet
   ordre.
5. Tous les autres : descriptif via ITU × WPP.

Règle de sortie : un pays vérifié qui échoue à un critère est listé dans le papier (annexe « pays
examinés et exclus, avec la raison »), pour que l'ensemble des pays retenus ne dépende pas des
résultats.

## 5. Ce que cela change dans le papier

- Un **même design** répliqué pays par pays (mêmes définitions d'âge, mêmes estimateurs, mêmes
  fenêtres relatives au lancement 4G), une préregistration commune avec un addendum par pays
  (définition exacte du traitement, niveau, années).
- Une **synthèse entre pays** des effets par groupe d'âge (15-19, 20-24, 25-29, 30-34, 35-39) :
  méta-analyse à effets aléatoires des estimations propres du papier, avec test d'hétérogénéité.
  La conclusion sur les 25 ans et plus repose sur cette synthèse, pas sur un pays isolé.
- Décomposition du canal là où les données le permettent : mariages par âge (France, Espagne,
  Brésil, Suède à confirmer) ; état civil de la mère à la naissance (Brésil, Colombie, Mexique).
- Section descriptive élargie à ~200 pays (ITU × WPP), explicitement non causale.
- Coût : chaque pays de niveau 1 ou 2 est un pipeline complet (téléchargement, harmonisation
  géographique, traitement, estimation). Ordre de grandeur : France ≈ la moitié de l'effort ; chaque
  pays supplémentaire ≈ 10-15 % de l'effort France une fois le squelette commun écrit.
