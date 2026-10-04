# Tout régénérer : make all   (voir README.md)
PY ?= python
SCRIPTS := scripts

.PHONY: all check download log build estimate co br es figures tables paper test clean

all: download build estimate figures tables paper

check:              ## joignabilité des sources, sans télécharger
	$(PY) $(SCRIPTS)/01_download.py --check

download:           ## données brutes → data/raw + docs/data_log.md
	$(PY) $(SCRIPTS)/01_download.py --country FR
	$(PY) $(SCRIPTS)/01_download.py --country EU
	$(PY) $(SCRIPTS)/01_download.py --country WORLD

build:              ## traitement et résultats → data/processed, puis échantillons et MDE (avant toute estimation)
	$(PY) $(SCRIPTS)/02_treatment.py
	$(PY) $(SCRIPTS)/03_outcomes.py
	$(PY) $(SCRIPTS)/04_sample_mde.py
	$(PY) $(SCRIPTS)/04b_firststage.py

log:                ## régénère docs/data_log.md depuis data/raw/manifest.json
	$(PY) $(SCRIPTS)/01_download.py --log

estimate:           ## estimations → tables/*.csv
	$(PY) $(SCRIPTS)/05_estimate.py

co:                 ## Colombie : traitement, résultats, échantillon/MDE, estimations, figures et tableaux (01_download.py --country CO d'abord)
	$(PY) $(SCRIPTS)/09_co_treatment.py
	$(PY) $(SCRIPTS)/10_co_outcomes.py
	$(PY) $(SCRIPTS)/11_co_estimate.py --part sample
	$(PY) $(SCRIPTS)/11_co_estimate.py
	$(PY) $(SCRIPTS)/12_co_figures_tables.py --country CO

br:                 ## Brésil : traitement, résultats, échantillon/MDE, estimations, figures et tableaux (01_download.py --country BR d'abord)
	$(PY) $(SCRIPTS)/13_br_treatment.py
	$(PY) $(SCRIPTS)/14_br_outcomes.py
	$(PY) $(SCRIPTS)/15_estimate_country.py --country BR --part sample
	$(PY) $(SCRIPTS)/15_estimate_country.py --country BR
	$(PY) $(SCRIPTS)/12_co_figures_tables.py --country BR

es:                 ## Espagne : idem (01_download.py --country ES d'abord)
	$(PY) $(SCRIPTS)/16_es_treatment.py
	$(PY) $(SCRIPTS)/17_es_outcomes.py
	$(PY) $(SCRIPTS)/15_estimate_country.py --country ES --part sample
	$(PY) $(SCRIPTS)/15_estimate_country.py --country ES
	$(PY) $(SCRIPTS)/12_co_figures_tables.py --country ES

figures:
	$(PY) $(SCRIPTS)/06_figures.py

tables:
	$(PY) $(SCRIPTS)/07_tables.py

paper:              ## paper/paper.pdf (latexmk) et paper/paper.md (pandoc)
	cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error paper.tex
	cd paper && pandoc paper.tex -o paper.md --wrap=none

test:
	$(PY) -m pytest -q tests

clean:
	rm -rf data/processed/* figures/*.pdf tables/*.csv tables/*.tex paper/*.aux paper/*.log paper/*.bbl paper/*.blg
