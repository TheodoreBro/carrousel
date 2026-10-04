# Brésil — échantillons et MDE (généré par scripts/15_estimate_country.py --country BR --part sample)

Unité = município ; cohorte = `cohort_4g_1` (cohorte 2014 = première observation utilisable (A5)) ; censurés exclus : 0. Règle « ≥ 3 ans de pré-période » appliquée.

| spécification       |   unités | années    |   unités-années |   unités traitées |   jamais traitées | cohortes   |
|:--------------------|---------:|:----------|----------------:|------------------:|------------------:|:-----------|
| H1 município 15-49  |     5558 | 2003-2024 |          122276 |              5558 |                 0 | 2014-2023  |
| H2b município 25-39 |     5558 | 2003-2024 |          122276 |              5558 |                 0 | 2014-2023  |
| H2 município 15-19  |     5558 | 2003-2024 |          127834 |              5558 |                 0 | 2014-2023  |
| H2 município 20-24  |     5558 | 2003-2024 |          127834 |              5558 |                 0 | 2014-2023  |
| H2 município 25-29  |     5558 | 2003-2024 |          127834 |              5558 |                 0 | 2014-2023  |
| H2 município 30-34  |     5558 | 2003-2024 |          127834 |              5558 |                 0 | 2014-2023  |
| H2 município 35-39  |     5558 | 2003-2024 |          127834 |              5558 |                 0 | 2014-2023  |
| H2 município 40-49  |     5558 | 2003-2024 |          127834 |              5558 |                 0 | 2014-2023  |
| H1 avec covariables |     5558 | 2003-2024 |          122276 |              5558 |                 0 | 2014-2023  |

MDE par permutation des cohortes (80 %, 5 %), TWFE statique sur log(naissances + 0,5 / 1 000 femmes) :

| hypothèse   |   sd placebo |   MDE (80 %, 5 %) en log ≈ % |   permutations |   moyenne placebo |
|:------------|-------------:|-----------------------------:|---------------:|------------------:|
| H1 15-49    |       0.0046 |                       0.0128 |            200 |           -0.0004 |
| H2b 25-39   |       0.0048 |                       0.0135 |            200 |           -0.0005 |
| H2 15-19    |       0.0064 |                       0.0178 |            200 |           -0.0003 |
| H2 20-24    |       0.0055 |                       0.0154 |            200 |           -0.0002 |
| H2 25-29    |       0.0053 |                       0.0149 |            200 |           -0.0007 |
| H2 30-34    |       0.0061 |                       0.0172 |            200 |           -0.0004 |
| H2 35-39    |       0.0076 |                       0.0214 |            200 |           -0.0003 |
| H2 40-49    |       0.0103 |                       0.0287 |            200 |            0.0001 |
