# Traitement France — synthèse (généré par scripts/02_treatment.py)

## Journal de construction

- COG 2026 : 34,875 communes, 34,833 unités harmonisées (32 composantes regroupant plusieurs communes actuelles)
- Observatoire ANFR : 832,277 lignes, fichier observatoireOd_20261001.csv
-   statuts : En service 638,644, Techniquement opérationnel 123,450, Projet approuvé 70,183
-   en service : 638,644 lignes ; dates manquantes : 0
-   codes commune inconnus du COG 2026 : 88 (97701, 97801, 97502, 97501, 98818, 98817, 98813, 98827…)
-   recodage LTE : 62 émetteurs (45 communes) datés avant 2012-01-01 → 2012-06-30
-   recodage UMTS : 258 émetteurs (173 communes) datés avant 2004-01-01 → 2004-12-01
-   archive 20180131_DATA.zip : 705,718 émetteurs présents, datés par l'instantané (2018-01-31, borne supérieure), 15,535 communes
-   archive 20181231-export-etalab-data.zip : 889,340 émetteurs présents, datés par l'instantané (2018-12-31, borne supérieure), 15,900 communes
-   archive 20201201-export-etalab-data.zip : 1,038,399 émetteurs datés (EMR_DT_SERVICE), 16,828 communes
-   archive 20211223-export-etalab-data.zip : 1,148,371 émetteurs datés (EMR_DT_SERVICE), 18,042 communes
-   archive 20221223-export-etalab-data.zip : 1,247,772 émetteurs datés (EMR_DT_SERVICE), 19,164 communes
-   archive 20231222-export-etalab-data.zip : 1,355,934 émetteurs datés (EMR_DT_SERVICE), 19,950 communes
-   archive 20241231-export-etalab-data.zip : 1,512,974 émetteurs datés (EMR_DT_SERVICE), 20,698 communes
-   archive 20251231-export-etalab-data.zip : 1,602,648 émetteurs datés (EMR_DT_SERVICE), 21,247 communes
- Sites ARCEP : 21,803 communes avec ≥ 1 site 4G entre 2018-T4 et le dernier trimestre
- Décision ARCEP 2012-0039 : 3,226 codes « zones blanches » (p. 18-56), 22,388 codes ZDP (p. 57-275) → 21,184 unités harmonisées
- Grille de densité 2024 : 34,833 communes, niveaux [np.int64(1), np.int64(2), np.int64(3), np.int64(4), np.int64(5), np.int64(6), np.int64(7)]
- RP 2011 (poids fixes D3) : 34,816 unités, femmes 15-44 = 12,447,089

## Cohortes 4G (D1), France métropolitaine, unités harmonisées

| cohorte | observatoire ∪ archives | observatoire seul | 2e opérateur | sites ARCEP (≥ 2019 datés) |
|---|---|---|---|---|
| jamais | 13,312 | 13,364 | 15,760 | 13,026 |
| 2013 | 139 | 126 | 7 | 0 |
| 2014 | 2,291 | 2,157 | 711 | 0 |
| 2015 | 1,273 | 1,259 | 821 | 0 |
| 2016 | 2,201 | 2,102 | 1,178 | 0 |
| 2017 | 2,821 | 2,842 | 3,005 | 0 |
| 2018 | 2,634 | 2,662 | 2,958 | 0 |
| 2019 | 2,119 | 1,397 | 1,553 | 12,840 |
| 2020 | 506 | 1,077 | 810 | 1,067 |
| 2021 | 2,384 | 2,542 | 2,341 | 2,675 |
| 2022 | 1,345 | 1,396 | 1,166 | 1,410 |
| 2023 | 1,231 | 1,260 | 1,250 | 833 |
| 2024 | 844 | 879 | 1,075 | 1,318 |
| 2025 | 758 | 772 | 995 | 766 |
| 2026 | 543 | 555 | 692 | 546 |
| 2027 | 303 | 314 | 382 | 223 |

## Cohortes 3G (UMTS)

| cohorte | unités |
|---|---|
| jamais | 13,796 |
| 2005 | 1,182 |
| 2006 | 877 |
| 2007 | 617 |
| 2008 | 561 |
| 2009 | 1,184 |
| 2010 | 1,500 |
| 2011 | 2,020 |
| 2012 | 2,838 |
| 2013 | 998 |
| 2014 | 596 |
| 2015 | 458 |
| 2016 | 497 |
| 2017 | 939 |
| 2018 | 597 |
| 2019 | 888 |
| 2020 | 178 |
| 2021 | 913 |
| 2022 | 1,107 |
| 2023 | 1,097 |
| 2024 | 665 |
| 2025 | 676 |
| 2026 | 350 |
| 2027 | 170 |

## Accord entre sources de datation

- Unités avec LTE dans l'observatoire courant : 21,340 ; dans les archives 2018-2025 : 21,081 ; dans l'union : 21,392.
- Parmi les 21,029 unités présentes dans les deux : écart de cohorte nul 19,688, 1 an 750, > 1 an 591 (archives plus anciennes dans 1,334 cas).
- Unités où la cohorte retenue diffère de l'observatoire seul : 1,386.
- Sites ARCEP : 8,540 unités avec un premier site 4G commercial daté 2019-T1 ou après ; écart (ARCEP − D1) médian 0 an(s), ≤ 1 an dans 95% des cas, ARCEP postérieur de > 2 ans dans 2%.
- Unités avec D1 = 1 au 1/1/2019 mais aucun site 4G ARCEP au 2018-T4 : 852.

## ZDP, zones blanches, densité

- ZDP : 21,184 unités métropolitaines (61.0%) ; zones blanches : 3,142.
- Cohorte 4G médiane : ZDP 2020, hors ZDP 2017 ; jamais traitées : ZDP 44.9%, hors ZDP 28.1%.

| densité (1 = dense … 7 = très peu dense) | unités | cohorte 4G médiane | jamais 4G |
|---|---|---|---|
| 1 | 764 | 2014 | 1.0% |
| 2 | 525 | 2014 | 1.0% |
| 3 | 882 | 2015 | 16.6% |
| 4 | 1,939 | 2015 | 15.6% |
| 5 | 5,066 | 2017 | 16.0% |
| 6 | 18,303 | 2019 | 45.7% |
| 7 | 7,225 | 2021 | 50.8% |

## D3 (exposition départementale, poids RP 2011 femmes 15-44)

| seuil | départements basculés | année médiane | min | max |
|---|---|---|---|---|
| 50 % | 96 / 96 | 2015 | 2013 | 2018 |
| 90 % | 44 / 96 | 2019 | 2013 | 2026 |
