# First stage France (H4) — généré par scripts/04b_firststage.py

Baromètre du numérique (ARCEP/CGE/ANCT/Arcom, CREDOC) : individus ≥ 12 ans, pondérés (POND). D3 = part des femmes de 15-44 ans (RP 2011) de la zone résidant dans une commune avec ≥ 1 émetteur LTE en service au 1er janvier (02_treatment.py), agrégée des départements à la zone. Effets fixes zone, année, classe d'âge (6 classes). Erreurs groupées par zone (9 ZEAT ou 13 régions : peu de groupes, inférence indicative).

Étendue de D3 entre ZEAT par année (min-max) : 2004: 0.00-0.00; 2005: 0.00-0.00; 2006: 0.00-0.00; 2007: 0.00-0.00; 2008: 0.00-0.00; 2009: 0.00-0.00; 2010: 0.00-0.00; 2011: 0.00-0.00; 2012: 0.00-0.00; 2013: 0.01-0.26; 2014: 0.35-0.90; 2015: 0.48-0.94; 2016: 0.57-0.95; 2017: 0.65-0.97; 2018: 0.70-0.97; 2019: 0.73-0.98; 2020: 0.74-0.98; 2021: 0.77-0.98; 2022: 0.79-0.98; 2023: 0.81-0.99; 2024: 0.82-0.99; 2025: 0.83-0.99; 2026: 0.84-0.99

| échantillon               | résultat   | terme                |   coef |    se |     p |   p_wild |   coef non pondéré |     n |   zones | années    |   moyenne y |
|:--------------------------|:-----------|:---------------------|-------:|------:|------:|---------:|-------------------:|------:|--------:|:----------|------------:|
| ZEAT × année, 2011-2020   | smartphone | D3                   |  0.098 | 0.040 | 0.039 |    0.495 |              0.084 | 24078 |       9 | 2011-2020 |       0.584 |
| ZEAT × année, 2011-2020   | smartphone | D3 (40 ans et plus)  |  0.125 | 0.056 | 0.057 |    0.531 |              0.105 | 24078 |       9 | 2011-2020 |       0.584 |
| ZEAT × année, 2011-2020   | smartphone | D3 × moins de 40 ans | -0.065 | 0.044 | 0.179 |    0.365 |             -0.053 | 24078 |       9 | 2011-2020 |       0.584 |
| ZEAT × année, 2011-2020   | social     | D3                   |  0.149 | 0.030 | 0.001 |    0.090 |              0.147 | 20884 |       9 | 2011-2020 |       0.620 |
| ZEAT × année, 2011-2020   | social     | D3 (40 ans et plus)  |  0.246 | 0.030 | 0.000 |    0.007 |              0.240 | 20884 |       9 | 2011-2020 |       0.620 |
| ZEAT × année, 2011-2020   | social     | D3 × moins de 40 ans | -0.217 | 0.034 | 0.000 |    0.002 |             -0.205 | 20884 |       9 | 2011-2020 |       0.620 |
| Région × année, 2020-2025 | smartphone | D3                   |  0.340 | 0.259 | 0.214 |    0.418 |              0.268 | 20683 |      13 | 2020-2025 |       0.882 |
| Région × année, 2020-2025 | smartphone | D3 (40 ans et plus)  |  0.459 | 0.274 | 0.120 |    0.299 |              0.388 | 20683 |      13 | 2020-2025 |       0.882 |
| Région × année, 2020-2025 | smartphone | D3 × moins de 40 ans | -0.421 | 0.057 | 0.000 |    0.001 |             -0.492 | 20683 |      13 | 2020-2025 |       0.882 |
| Région × année, 2020-2022 | social     | D3                   | -0.736 | 0.496 | 0.164 |    0.196 |             -0.544 |  7399 |      13 | 2020-2022 |       0.698 |
| Région × année, 2020-2022 | social     | D3 (40 ans et plus)  | -0.742 | 0.494 | 0.159 |    0.205 |             -0.537 |  7399 |      13 | 2020-2022 |       0.698 |
| Région × année, 2020-2022 | social     | D3 × moins de 40 ans |  0.024 | 0.096 | 0.805 |    0.681 |             -0.056 |  7399 |      13 | 2020-2022 |       0.698 |

Lecture : un coefficient de 0,10 sur D3 signifie que passer de 0 à 100 % de couverture 4G de la zone est associé à +10 points de la probabilité de posséder un smartphone (resp. d'avoir participé à des réseaux sociaux dans l'année), à année, zone et classe d'âge donnés. Corrélation conditionnelle ; la variation de D3 entre ZEAT est faible après 2016.
