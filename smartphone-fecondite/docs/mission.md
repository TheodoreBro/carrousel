# Cahier des charges (texte de l'auteur, 18 septembre 2026, reproduit tel quel)

Compléments de l'auteur postérieurs à ce texte : (1) « beaucoup beaucoup plus de pays » → voir
`etape0_pays.md` ; (2) validation des points 1 à 11 de `handover.md` §2 le 18/09/2026.

---

# Mission
Rédige un working paper (6 000–9 000 mots hors annexes) sur l'effet de la diffusion des smartphones — et, à travers eux, des réseaux sociaux et des applications de rencontre — sur la fécondité. Le papier doit répondre à deux questions : (1) y a-t-il un effet causal identifiable, au-delà des adolescentes, sur les femmes de 25 ans et plus ? (2) si oui, passe-t-il par la mise en couple ou par la fécondité au sein des couples ?

Le livrable est reproductible : chaque chiffre, tableau et figure du papier est produit par du code présent dans le dépôt. Aucune donnée inventée, aucune référence non vérifiée, aucun résultat emprunté à une autre étude.

# Paramètres (à ajuster si besoin)
- Langue : français, abstract en anglais et en français.
- Cœur causal : France (déploiement 3G/4G par commune × naissances et mariages INSEE). Cas secondaires si les données le permettent : Corée du Sud (KOSIS), États-Unis (FCC × NCHS), régions européennes (Eurostat NUTS).
- Panel international : descriptif uniquement, jamais utilisé pour conclure.
- Sortie : ./paper/paper.pdf (LaTeX, ou Quarto si pdflatex indisponible) + ./paper/paper.md.
- Stack : Python (pandas, statsmodels, linearmodels, matplotlib). R autorisé pour les estimateurs de DiD échelonnée (did, fixest) si Python ne les couvre pas proprement.

# Règles non négociables
1. Données réelles uniquement, téléchargées depuis les sources primaires. Si un téléchargement échoue, arrête-toi et dis-le. Ne comble jamais un trou par des valeurs "plausibles".
2. Toute référence est vérifiée (DOI ou page éditeur consultée) avant d'entrer dans references.bib. Non vérifiable = non citée.
3. Les résultats du papier viennent exclusivement de ses propres analyses. La littérature sert à positionner la question et à justifier le design, pas à conclure. Aucun effet, aucune taille d'effet, aucune "les études montrent que" repris d'ailleurs dans les sections Résultats, Discussion ou Conclusion.
4. Hypothèses écrites AVANT l'analyse dans docs/preregistration.md et non modifiées ensuite. Les résultats nuls ou contraires sont rapportés tels quels.
5. Le papier distingue explicitement corrélation et causalité. Aucun titre, abstract ou conclusion qui surinterprète.
6. Chaque figure/tableau est généré par un script nommé dans scripts/ et référencé dans le texte.

# Données

## A. Traitement : déploiement des réseaux (variation infranationale dans le temps)
- France : ANFR (data.gouv.fr) — sites d'antennes avec technologie (2G/3G/4G/5G) et date de mise en service, agrégés par commune et par année ; ARCEP open data — couverture mobile par commune, observatoire du déploiement 4G. Construire pour chaque commune (ou département) l'année de bascule 3G et 4G.
- Corée : KOSIS / MSIT, déploiement LTE par région (variation probablement faible et rapide : le dire si c'est le cas).
- États-Unis : FCC Form 477 par comté.
- Europe : Eurostat, enquête TIC ménages (isoc_ci_*) — usage d'Internet mobile par pays, année et tranche d'âge.
Documenter précisément la mesure de traitement retenue et ses limites (couverture ≠ adoption).

## B. Résultats : fécondité et mise en couple, par âge
- France : INSEE état civil — fichiers détail naissances (âge de la mère, commune, année) et mariages ; PACS (ministère de la Justice) ; enquêtes Famille et recensement pour la proportion de femmes en couple par âge.
- Corée : Statistics Korea / KOSIS — naissances et mariages par âge et sigungu.
- Europe : Eurostat demo_frate (taux de fécondité par âge), demo_nind (nuptialité), demo_r_births (naissances régionales), EU-SILC / LFS pour le statut conjugal par âge.
- États-Unis : NCHS natality par comté et âge, ACS pour le statut conjugal.
Objectif : décomposer la variation de fécondité en (i) part des femmes en couple par âge et (ii) fécondité des femmes en couple, pour isoler le canal.

## C. Exposition : séries à croiser (pour lier traitement, adoption et usage)
- Pénétration smartphone : GSMA Intelligence, Newzoo, Pew Global Attitudes (possession de smartphone par pays et âge depuis 2013).
- Applications de rencontre : Pew (enquêtes US 2013, 2015, 2019, 2022–23, par âge), Sensor Tower / data.ai (téléchargements par pays), Google Trends en proxy. Aucune série pays-année homogène n'existe : le dire et documenter chaque proxy.
- Réseaux sociaux : DataReportal / Kepios, Eurostat isoc_ci_ac_i (usage des réseaux sociaux par âge).
Ces séries servent à vérifier que le traitement (couverture) se traduit bien en adoption puis en usage (first stage), et à décrire le calendrier relatif des trois courbes : smartphone → applis → mise en couple → fécondité.

## D. Contrôles
Revenu local, chômage des 15-24 et 25-34 ans, part de diplômées du supérieur, urbanisation, prix du logement (INSEE / notaires, OCDE), offre de garde d'enfants quand disponible.

## E. Panel international (descriptif seulement)
ISF (SP.DYN.TFRT.IN, UN WPP 2024), abonnements mobiles (IT.CEL.SETS.P2), Internet (IT.NET.USER.ZS), mobile haut débit (ITU via OWID), PIB/hab. (NY.GDP.PCAP.PP.KD). Sert aux faits stylisés et à situer les cas d'étude, rien de plus.

# Méthode

1. Faits stylisés (section descriptive, sans inférence causale) : ISF et adoption smartphone par groupe de revenu ; datation des points d'inflexion (rupture 2010–2015 en Finlande, Norvège, Corée, États-Unis…) ; superposition des courbes smartphone / applis / mariage / fécondité par âge dans les pays d'étude.

2. Identification causale (cœur du papier) :
   - Différences-de-différences échelonnées sur l'année de bascule 3G/4G par commune ou département, avec estimateurs robustes à l'adoption échelonnée (Callaway & Sant'Anna, Sun & Abraham, de Chaisemartin & D'Haultfœuille) — pas seulement un TWFE naïf.
   - Event study avec au moins 3 périodes pré-traitement pour tester les tendances parallèles.
   - Variables instrumentales : instrumenter l'adoption/l'usage par le calendrier de couverture, en discutant explicitement la restriction d'exclusion (la couverture peut affecter la fécondité par d'autres canaux : emploi, information, télétravail).
   - Erreurs standard clusterisées au niveau du traitement.

3. Décomposition du canal : estimer séparément l'effet du traitement sur (a) le taux de mise en couple / mariage / PACS par âge, (b) la fécondité des femmes en couple, (c) la fécondité totale par âge. Conclure sur le canal dominant seulement si (a) et (b) donnent des réponses distinguables statistiquement.

4. Hétérogénéité par âge — test central : effets séparés pour les 15-19, 20-24, 25-29, 30-34, 35-39 ans. La question n'est pas "y a-t-il un effet chez les adolescentes" mais "y a-t-il un effet net sur les 25 ans et plus".

5. Robustesse : fenêtres alternatives, exclusion des grandes métropoles, placebo (bascule fictive décalée de 3 ans, ou variable de résultat sans lien attendu), sensibilité à la définition du traitement (couverture vs sites), contrôle des chocs concurrents (crise 2008, réformes familiales, prix du logement).

6. Mécanismes : discuter (a) élargissement du marché de l'appariement et report de la mise en couple, (b) déplacement du temps et baisse de l'activité sexuelle, (c) diffusion de normes et d'aspirations, (d) coût d'opportunité, (e) santé mentale — en distinguant ce qui est testé dans le papier de ce qui reste conjecture.

# Littérature (positionnement uniquement, ~600 mots max)
Citer pour situer la question et justifier le design, jamais pour appuyer un résultat. Pistes à vérifier une par une : Billari, Giuntella & Stella (2019), Population Studies ; Guldi & Herbst (2017), J. of Population Economics ; Bellou (2015), J. of Population Economics ; Rosenfeld, Thomas & Hausen (2019), PNAS ; Potarca (2020), PLoS ONE. Compléter par une recherche 2019–2026 (Scholar, RePEc, SSRN, NBER, arXiv) pour repérer les designs existants et ce qu'ils n'ont pas testé — notamment les 25+.

# Structure du papier
Abstract (EN + FR) · 1. Introduction (question, contribution, résultat principal en une phrase) · 2. Positionnement (court) · 3. Cadre conceptuel et hypothèses (reprend preregistration.md) · 4. Données (sources, construction, descriptives, limites de mesure) · 5. Stratégie empirique · 6. Résultats : effet causal par âge · 7. Résultats : décomposition du canal · 8. Robustesse · 9. Discussion et mécanismes · 10. Limites · 11. Conclusion et critères de révision · Références · Annexes (tableaux complets, dictionnaire des variables, sources exactes).

La section 11 doit énoncer explicitement : (i) le statut actuel du smartphone comme facteur explicatif de la baisse de fécondité au vu des résultats du papier (second ordre, premier ordre, indéterminé) ; (ii) le seuil de révision — si des études causales indépendantes répliquent un effet net sur les 25 ans et plus, et pas seulement sur les adolescentes, le smartphone doit être reclassé comme cause de premier ordre ; (iii) symétriquement, ce qui ferait rétrograder l'hypothèse.

# Organisation du dépôt
data/raw (bruts, jamais modifiés) · data/processed · scripts/01_download.py … 06_tables.py · figures/ · tables/ · paper/ · docs/preregistration.md · docs/data_log.md (par source : URL, date d'accès, licence, couverture, trous) · README.md (tout régénérer en une commande) · requirements.txt.

# Déroulé
Étape 0 — Plan, liste des sources, faisabilité du design DiD pays par pays (quelle variation infranationale existe réellement ?), incertitudes listées. Attends ma validation avant tout téléchargement.
Étape 1 — Préregistration (hypothèses par âge et par canal).
Étape 2 — Pipeline de données + data_log. Rapporte le nombre d'unités-années exploitables par spécification et la qualité du first stage.
Étape 3 — Analyses, figures, tableaux.
Étape 4 — Rédaction. Passe finale : chaque chiffre du texte relu contre les tableaux générés, chaque référence contre references.bib, aucun résultat externe dans les sections 6 à 11.

# Ce que je ne veux pas
- Des "estimations raisonnables" à la place de données.
- Des références fabriquées ou approximatives.
- Un papier qui recycle les résultats d'autres études au lieu de produire les siens.
- Des corrélations trans-pays présentées comme preuve.
- Une conclusion causale que la méthode ne permet pas.
- Une revue de littérature générique sur "la technologie et la société".
