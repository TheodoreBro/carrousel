# Passation — état du projet au 2 octobre 2026

Ce fichier permet à une nouvelle session (ou à un nouvel agent) de reprendre le travail sans la
conversation d'origine. Il est mis à jour à chaque étape.

## 1. Où en est-on

- Étape 0 livrée : `docs/etape0_plan.md` (plan, sources, faisabilité France/Corée/États-Unis/Europe,
  incertitudes, décisions à valider) et `docs/etape0_pays.md` (extension à 47 pays, classement N1/N2/N3,
  ordre de vérification).
- **Étape 1 livrée : `docs/preregistration.md` (version 1.0, gelée). Ne plus la modifier ; toute
  déviation va dans `docs/preregistration_addenda.md`, et chaque pays reçoit un addendum de mesure
  avant sa première estimation (§4.2 de la préregistration).**
- **Squelette du pipeline écrit et testé (02/10)** : `scripts/common/sources.py` (registre des sources
  avec méthode de résolution des URL ; tout ce qui vient de l'Étape 0 est « à vérifier »),
  `scripts/common/download.py` (téléchargement avec reprises, SHA-256, manifeste, `docs/data_log.md`,
  arrêt net sur refus), `scripts/01_download.py` (`--list`, `--check`, `--country`, `--ids`),
  `scripts/common/did.py` (Callaway & Sant'Anna via `differences`, Sun & Abraham implémenté
  directement, did2s, TWFE, Poisson à effets fixes, MDE par permutation, méta-analyse à effets
  aléatoires), `tests/test_did.py` (8 tests sur panel synthétique, tous verts), `Makefile`,
  `paper/paper.tex` (squelette), `paper/references.bib` (vide, volontairement).
- **Aucune donnée téléchargée.** `02_treatment.py` à `06_tables.py` restent à écrire : ils dépendent
  de la structure réelle des fichiers.
- Environnement : pile Python vérifiée (`requirements.txt`) ; R sans `fixest`/`did` (CRAN bloqué) ;
  TeX Live installable via apt.
- **Bloqueur** : au 02/10, dans un conteneur neuf, la politique réseau de l'environnement « Default »
  refuse toujours toutes les sources de données (403). Le réglage à changer : menu de l'environnement
  cloud dans la barre de titre de la session → Edit → Network access (accès complet, ou domaines
  autorisés listés dans `etape0_plan.md` §1.3). Première chose à faire dans une nouvelle session :
  `python scripts/01_download.py --check`.

## 2. Décisions de l'auteur

Prises (messages du 18/09) :
- « Beaucoup plus de pays » : oui. Voir `etape0_pays.md` pour le classement et l'ordre.
- **Points 1 à 11 ci-dessous : tous validés par l'auteur le 18/09/2026.**

Points validés (voir `etape0_plan.md` §7) :
1. accès réseau (option A recommandée : unrestricted) ;
2. emplacement : sous-dossier `smartphone-fecondite/` (défaut) ;
3. cas secondaires Corée / États-Unis / Europe NUTS 2 en descriptif seulement ;
4. traitement principal France : premier émetteur 4G (ANFR), couverture ARCEP en second, 3G en robustesse ;
5. fenêtres : commune 2004-2024, département × âge 1998-2025 ;
6. estimateurs : Callaway & Sant'Anna, Sun & Abraham, did2s, TWFE comparatif ; dCDH si CRAN accessible ;
7. clé API KOSIS / accès NCHS : non par défaut ;
8. PDF : TeX Live via apt.

Décisions ouvertes par l'extension multi-pays (validées le 18/09) :
9. périmètre causal : France + niveau 1 (Espagne, Suède, Brésil, Colombie) + niveau 2 vérifiés dans
   l'ordre du §4 de `etape0_pays.md`, avec critères d'inclusion préenregistrés ;
10. synthèse entre pays par méta-analyse à effets aléatoires des estimations propres ;
11. extension descriptive à ~200 pays (ITU indicateur 100095 × UN WPP 2024).

## 3. Prochaines étapes, dans l'ordre

1. Vérifier le réseau. Si bloqué : s'arrêter et le dire (règle 1).
2. Faire valider les points 1-11 ci-dessus si ce n'est pas déjà fait.
3. Étape 1 : faite (commit contenant `preregistration.md` v1.0 ; citer son hash dans le papier).
4. Étape 2 : `make check` puis `python scripts/01_download.py --country FR` ; corriger les URL du
   registre au fur et à mesure (chaque correction est une URL réelle constatée, consignée dans
   `data_log.md`) ; écrire `02_treatment.py` (D1, D2, D3, ZDP) et `03_outcomes.py` à partir de la
   structure réelle des fichiers ; tableau d'échantillon et MDE (`did.mde_permutation`) ; first stage.
   Puis pays de niveau 1 (addendum par pays avant estimation), puis niveau 2 selon la check-list.
5. Étape 3 : estimations, figures, tableaux.
6. Étape 4 : rédaction, vérification chiffre par chiffre, références vérifiées une par une
   (les DOI listés dans `etape0_plan.md` §8 ne sont pas encore vérifiés sur la page éditeur).

## 4. Règles non négociables (rappel)

Données réelles uniquement, téléchargées depuis les sources primaires ; toute référence vérifiée
avant d'entrer dans `references.bib` ; aucun résultat externe dans les sections Résultats, Discussion,
Conclusion ; hypothèses écrites avant l'analyse et non modifiées ; corrélation et causalité
distinguées ; chaque figure et tableau produit par un script nommé.

## 5. Message de démarrage suggéré pour une nouvelle session

```
Continue le working paper smartphones/fécondité sur la branche claude/confident-pasteur-og6cgd.
Lis smartphone-fecondite/docs/handover.md, etape0_plan.md et etape0_pays.md. Vérifie l'accès
réseau aux sources (etape0_plan.md §1.1). Puis reprends à l'étape indiquée dans handover.md §3.
```
