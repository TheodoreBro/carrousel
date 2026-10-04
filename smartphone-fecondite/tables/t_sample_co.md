# Colombie — échantillons et MDE (généré par scripts/11_co_estimate.py --part sample)

Municipios censurés à gauche (4G ≥ 50 % dès 2015-T4) exclus : 189. Règle « ≥ 3 ans de pré-période » appliquée.

| spécification                       |   unités | années    |   unités-années |   unités traitées |   jamais traitées | cohortes   |
|:------------------------------------|---------:|:----------|----------------:|------------------:|------------------:|:-----------|
| H1 municipio 15-49                  |      932 | 1998-2024 |           25087 |               865 |                67 | 2016-2023  |
| H2b municipio 25-39                 |      932 | 1998-2024 |           25087 |               865 |                67 | 2016-2023  |
| H2 municipio 15-19                  |      932 | 1998-2024 |           25087 |               865 |                67 | 2016-2023  |
| H2 municipio 20-24                  |      932 | 1998-2024 |           25087 |               865 |                67 | 2016-2023  |
| H2 municipio 25-29                  |      932 | 1998-2024 |           25087 |               865 |                67 | 2016-2023  |
| H2 municipio 30-34                  |      932 | 1998-2024 |           25087 |               865 |                67 | 2016-2023  |
| H2 municipio 35-39                  |      932 | 1998-2024 |           25087 |               865 |                67 | 2016-2023  |
| H2 municipio 40-49                  |      932 | 1998-2024 |           25087 |               865 |                67 | 2016-2023  |
| H1 municipio 15-49 avec covariables |      932 | 1998-2024 |           25087 |               865 |                67 | 2016-2023  |

MDE par permutation des cohortes (80 %, 5 %), TWFE statique sur log(naissances + 0,5 / 1 000 femmes) :

| hypothèse           |   sd placebo |   MDE (80 %, 5 %) en log ≈ % |   permutations |   moyenne placebo |
|:--------------------|-------------:|-----------------------------:|---------------:|------------------:|
| H1 municipio 15-49  |       0.0187 |                       0.0524 |            200 |           -0.0027 |
| H2b municipio 25-39 |       0.0178 |                       0.0498 |            200 |           -0.0028 |
| H2 municipio 15-19  |       0.0202 |                       0.0566 |            200 |           -0.0020 |
| H2 municipio 20-24  |       0.0207 |                       0.0580 |            200 |           -0.0028 |
| H2 municipio 25-29  |       0.0188 |                       0.0526 |            200 |           -0.0032 |
| H2 municipio 30-34  |       0.0176 |                       0.0494 |            200 |           -0.0019 |
| H2 municipio 35-39  |       0.0220 |                       0.0617 |            200 |           -0.0016 |
| H2 municipio 40-49  |       0.0246 |                       0.0689 |            200 |           -0.0019 |
