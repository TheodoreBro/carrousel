# Statut du smartphone comme facteur (préregistration §6, addendum A9) — généré par scripts/23_status.py

Taux = naissances des 25-39 ans pour 1 000 femmes de 25-39 ans, agrégé sur les unités du panel de chaque pays ; variation entre la première cohorte de H2b et la dernière année du panel. ATT en % du taux contrefactuel (`t_meta.md`). Part expliquée = ATT / variation observée.

| pays     |   année lancement |   dernière année |   taux 25-39 lancement |   taux 25-39 dernière |   variation observée % |   naissances 25-39 lancement |   ATT pays % |   part expliquée par l'ATT du pays % |
|:---------|------------------:|-----------------:|-----------------------:|----------------------:|-----------------------:|-----------------------------:|-------------:|-------------------------------------:|
| France   |              2013 |             2024 |                 105.94 |                 86.16 |                 -18.67 |                    635567.00 |         1.80 |                                -9.63 |
| Colombie |              2016 |             2024 |                  57.39 |                 39.74 |                 -30.77 |                    308791.00 |        -1.38 |                                 4.48 |
| Brésil   |              2014 |             2024 |                  63.29 |                 57.06 |                  -9.84 |                   1570563.00 |        -4.67 |                                47.46 |
| Espagne  |              2013 |             2022 |                  66.91 |                 62.25 |                  -6.96 |                    286945.00 |        44.11 |                              -633.84 |

Baisse observée moyenne (pondérée par les naissances à l'année de lancement) : -13.86 %.

## Effet poolé 25-39 (A7) et statut

| variante                                        | pays                              |   poolé % | IC 95 %          |    p |   baisse observée moyenne % |   part expliquée % | part expliquée, IC 95 %   | statut (§6, A9)                          |
|:------------------------------------------------|:----------------------------------|----------:|:-----------------|-----:|----------------------------:|-------------------:|:--------------------------|:-----------------------------------------|
| primaire (es analytique, tous pays)             | France, Colombie, Brésil, Espagne |      9.67 | [-12.59, +31.93] | 0.39 |                      -13.86 |             -69.77 | [-230, +91]               | indéterminé (IC couvrant une part ≥ 5 %) |
| es bootstrap                                    | France, Colombie, Brésil, Espagne |     -0.04 | [-9.01, +8.92]   | 0.99 |                      -13.86 |               0.30 | [-64, +65]                | indéterminé (IC couvrant une part ≥ 5 %) |
| sans pays au pré-test rejeté (A7, exploratoire) | Colombie, Brésil                  |     -3.92 | [-7.53, -0.31]   | 0.03 |                      -13.86 |              28.29 | [+2, +54]                 | premier ordre                            |

Règle (§6) : premier ordre si la part expliquée ≥ 25 %, second ordre 5-25 %, négligeable < 5 % ou non détecté avec puissance suffisante (A9 : effet non significatif et IC sous 5 % de la baisse), indéterminé sinon. Le statut du papier est celui de la variante « primaire ».
