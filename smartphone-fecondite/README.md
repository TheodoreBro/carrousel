# Smartphones, réseaux sociaux, applications de rencontre et fécondité

Working paper reproductible. Question : y a-t-il un effet causal identifiable de la diffusion des
smartphones (via le déploiement 3G/4G) sur la fécondité des femmes de 25 ans et plus, et passe-t-il
par la mise en couple ou par la fécondité au sein des couples ? Design : différences-de-différences
échelonnées sur le calendrier infranational de la 4G, France d'abord, répliqué dans les pays où les
données ouvertes le permettent (`docs/etape0_pays.md`), synthèse par méta-analyse.

## État

Voir `docs/handover.md` (état, décisions, prochaines étapes). Préregistration gelée :
`docs/preregistration.md` ; déviations et décisions de mesure : `docs/preregistration_addenda.md`.
Étapes 2 et 3 faites pour la France ; pays de niveau 1 vérifiés fichiers en main (check-lists dans `docs/data_log.md`) :
Suède exclue (A3), Colombie (A4), Brésil (A5) et Espagne (A6) inclus, estimés avec le même code (`make co`, `make br`, `make es`).
Les hôtes refusés par la politique réseau sont listés dans `docs/data_log.md` ; rien n'est remplacé par des valeurs de substitution.

## Tout régénérer

    python3 -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt
    make check        # joignabilité des sources (rien n'est téléchargé)
    make all          # download → build → estimate → figures → tables → paper

`make test` exécute les tests du module d'estimation sur un panel synthétique (jamais utilisé dans
le papier).

Étape 3 (estimations) : `python scripts/05_estimate.py --part all` (plusieurs heures ; parties `h1 h2 h3 h5 h6
robust iv summary` exécutables séparément, en parallèle si besoin, puis `--part summary`). Les sorties sont dans
`tables/est/<partie>.csv`, `tables/est_fr_all.csv`, `tables/t_estimates_fr.md` et le manifeste `tables/est/_run.json`.
Les tests de fonctionnement (`--fast`, `--sample N`) écrivent dans `tables/est_smoke/` ; `06_figures.py --smoke` et
`07_tables.py --smoke` les lisent et écrivent dans `figures/smoke/` et `tables/est_smoke/tex/` (jamais pour le papier). Le PDF demande TeX Live (`apt-get install texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended
texlive-lang-french texlive-science lmodern cm-super latexmk`) ; `make paper` compile `paper/paper.pdf` puis écrit `paper/paper.md`
(`scripts/22_paper_md.py`, pandoc fourni par `pypandoc_binary`, citations résolues, figures en .png).

## Organisation

    data/raw          bruts, jamais modifiés ; non versionnés ; empreintes SHA-256 dans docs/data_log.md et data/raw/manifest.json
    data/processed    panels construits
    scripts/          France : 01_download.py 02_treatment.py 03_outcomes.py 04_sample_mde.py 04b_firststage.py 05_estimate.py 06_figures.py 07_tables.py
                      Suède : 08_se_check.py ; Colombie : 09_co_treatment.py 10_co_outcomes.py 11_co_estimate.py ; Brésil : 13_br_treatment.py 14_br_outcomes.py ;
                      Espagne : 16_es_treatment.py 17_es_outcomes.py ; Brésil et Espagne : 15_estimate_country.py ; figures et tableaux par pays : 12_co_figures_tables.py --country
    scripts/common/   sources.py (registre), download.py (téléchargement journalisé), did.py (estimateurs), co.py / br.py / es.py (lecteurs)
    tests/            tests sur données synthétiques
    figures/ tables/  sorties des scripts, référencées dans le texte
    paper/            paper.tex, references.bib → paper.pdf, paper.md
    docs/             etape0_plan.md, etape0_pays.md, preregistration.md, data_log.md, handover.md
