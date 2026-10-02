# Smartphones, réseaux sociaux, applications de rencontre et fécondité

Working paper reproductible. Question : y a-t-il un effet causal identifiable de la diffusion des
smartphones (via le déploiement 3G/4G) sur la fécondité des femmes de 25 ans et plus, et passe-t-il
par la mise en couple ou par la fécondité au sein des couples ? Design : différences-de-différences
échelonnées sur le calendrier infranational de la 4G, France d'abord, répliqué dans les pays où les
données ouvertes le permettent (`docs/etape0_pays.md`), synthèse par méta-analyse.

## État

Voir `docs/handover.md` (état, décisions, prochaines étapes). Préregistration gelée :
`docs/preregistration.md`. Aucune donnée n'est téléchargée tant que l'accès réseau aux sources
primaires n'est pas ouvert ; le pipeline s'arrête et le dit.

## Tout régénérer

    python3 -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt
    make check        # joignabilité des sources (rien n'est téléchargé)
    make all          # download → build → estimate → figures → tables → paper

`make test` exécute les tests du module d'estimation sur un panel synthétique (jamais utilisé dans
le papier). Le PDF demande TeX Live (`apt-get install texlive-latex-extra texlive-lang-french
latexmk`) ; à défaut, `paper/paper.md` est produit par pandoc.

## Organisation

    data/raw          bruts, jamais modifiés ; non versionnés ; empreintes SHA-256 dans docs/data_log.md et data/raw/manifest.json
    data/processed    panels construits
    scripts/          01_download.py 02_treatment.py 03_outcomes.py 04_sample_mde.py 05_estimate.py 06_figures.py 07_tables.py
    scripts/common/   sources.py (registre), download.py (téléchargement journalisé), did.py (estimateurs)
    tests/            tests sur données synthétiques
    figures/ tables/  sorties des scripts, référencées dans le texte
    paper/            paper.tex, references.bib → paper.pdf, paper.md
    docs/             etape0_plan.md, etape0_pays.md, preregistration.md, data_log.md, handover.md
