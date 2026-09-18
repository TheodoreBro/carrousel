# Smartphones, réseaux sociaux, applications de rencontre et fécondité

Working paper reproductible. Question : y a-t-il un effet causal identifiable de la diffusion des
smartphones (via le déploiement 3G/4G) sur la fécondité des femmes de 25 ans et plus, et passe-t-il
par la mise en couple ou par la fécondité au sein des couples ?

## Statut

**Étape 0 — plan et faisabilité, en attente de validation.** Voir `docs/etape0_plan.md`.
Aucune donnée téléchargée. Bloqueur connu : la politique réseau de l'environnement refuse l'accès
aux sources primaires (détail et liste d'hôtes à autoriser dans `docs/etape0_plan.md`, §1).

## Organisation prévue

    data/raw        bruts, jamais modifiés (empreintes SHA-256 dans docs/data_log.md)
    data/processed  panels construits
    scripts/        01_download.py … 06_tables.py
    figures/ tables/ paper/
    docs/           etape0_plan.md, preregistration.md, data_log.md

## Environnement

    python3 -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt

Versions épinglées après installation et test le 18/09/2026.
