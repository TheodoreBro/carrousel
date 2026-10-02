# Tout régénérer : make all   (voir README.md)
PY ?= python
SCRIPTS := scripts

.PHONY: all check download build estimate figures tables paper test clean

all: download build estimate figures tables paper

check:              ## joignabilité des sources, sans télécharger
	$(PY) $(SCRIPTS)/01_download.py --check

download:           ## données brutes → data/raw + docs/data_log.md
	$(PY) $(SCRIPTS)/01_download.py --country FR
	$(PY) $(SCRIPTS)/01_download.py --country EU
	$(PY) $(SCRIPTS)/01_download.py --country WORLD

build:              ## traitement et résultats → data/processed
	$(PY) $(SCRIPTS)/02_treatment.py
	$(PY) $(SCRIPTS)/03_outcomes.py

estimate:           ## estimations → tables/*.csv
	$(PY) $(SCRIPTS)/04_estimate.py

figures:
	$(PY) $(SCRIPTS)/05_figures.py

tables:
	$(PY) $(SCRIPTS)/06_tables.py

paper:              ## paper/paper.pdf (latexmk) et paper/paper.md (pandoc)
	cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error paper.tex
	cd paper && pandoc paper.tex -o paper.md --wrap=none

test:
	$(PY) -m pytest -q tests

clean:
	rm -rf data/processed/* figures/*.pdf tables/*.csv tables/*.tex paper/*.aux paper/*.log paper/*.bbl paper/*.blg
