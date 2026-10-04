# Espagne — échantillons et MDE (généré par scripts/15_estimate_country.py --country ES --part sample)

Unité = municipio (> 10 000 habitants) ; cohorte = `cohort_lte_50` (cohorte 2013 = premier instantané (déc. 2013), gardée en primaire (A6)) ; censurés exclus : 0. Règle « ≥ 3 ans de pré-période » appliquée.

| spécification       |   unités | années    |   unités-années |   unités traitées |   jamais traitées | cohortes   |
|:--------------------|---------:|:----------|----------------:|------------------:|------------------:|:-----------|
| H1 municipio 15-49  |      722 | 2007-2022 |           11552 |               722 |                 0 | 2013-2016  |
| H2b municipio 25-39 |      722 | 2007-2022 |           11552 |               722 |                 0 | 2013-2016  |
| H2 municipio 15-19  |      722 | 2007-2022 |           11552 |               722 |                 0 | 2013-2016  |
| H2 municipio 20-24  |      722 | 2007-2022 |           11552 |               722 |                 0 | 2013-2016  |
| H2 municipio 25-29  |      722 | 2007-2022 |           11552 |               722 |                 0 | 2013-2016  |
| H2 municipio 30-34  |      722 | 2007-2022 |           11552 |               722 |                 0 | 2013-2016  |
| H2 municipio 35-39  |      722 | 2007-2022 |           11552 |               722 |                 0 | 2013-2016  |
| H2 municipio 40-49  |      722 | 2007-2022 |           11552 |               722 |                 0 | 2013-2016  |
| H1 avec covariables |      722 | 2007-2022 |           11552 |               722 |                 0 | 2013-2016  |

MDE par permutation des cohortes (80 %, 5 %), TWFE statique sur log(naissances + 0,5 / 1 000 femmes) :

| hypothèse   |   sd placebo |   MDE (80 %, 5 %) en log ≈ % |   permutations |   moyenne placebo |
|:------------|-------------:|-----------------------------:|---------------:|------------------:|
| H1 15-49    |       0.0086 |                       0.0240 |            200 |           -0.0010 |
| H2b 25-39   |       0.0084 |                       0.0237 |            200 |           -0.0007 |
| H2 15-19    |       0.0347 |                       0.0973 |            200 |           -0.0021 |
| H2 20-24    |       0.0225 |                       0.0630 |            200 |           -0.0023 |
| H2 25-29    |       0.0127 |                       0.0357 |            200 |           -0.0011 |
| H2 30-34    |       0.0092 |                       0.0259 |            200 |           -0.0002 |
| H2 35-39    |       0.0115 |                       0.0321 |            200 |           -0.0011 |
| H2 40-49    |       0.0217 |                       0.0609 |            200 |            0.0015 |
