# Team01-FlightDelay-Project - one entry point per stage.
#
# A Makefile is just a list of commands with dependencies; using one here means
# the README, the report and the viva can all quote the same short command
# instead of a paragraph of shell. Windows users without make can run
# `python run_all.py --help` for the same stages.
#
#   make sample      build the synthetic fixture (seconds, no download)
#   make smoke       full pipeline on the fixture (no download)
#   make data        download and prepare the real panel (hours, ~4 GB)
#   make pipeline    run every analysis stage on the real panel
#   make dashboard   launch the interactive dashboard
#   make test        run the test suite

PY ?= python
export TEAM01_MODE ?= full

.PHONY: help setup sample data validate attribution tail clusters models figures smoke pipeline dashboard test clean

help:
	@grep -E "^#   make" Makefile | sed "s/^#   //"

setup:
	$(PY) -m pip install -r requirements.txt

sample:
	TEAM01_MODE=sample $(PY) src/scripts/00_make_sample.py

data:
	$(PY) src/scripts/01_acquire.py --years 2015-2024

validate:
	$(PY) src/scripts/02_validate.py

attribution:
	$(PY) src/scripts/03_attribution.py

tail:
	$(PY) src/scripts/04_tail.py

clusters:
	$(PY) src/scripts/05_clusters.py

models:
	$(PY) src/scripts/06_models.py

figures:
	$(PY) src/scripts/07_figures.py

pipeline:
	$(PY) run_all.py --stage pipeline

smoke:
	TEAM01_MODE=sample $(PY) src/scripts/00_make_sample.py
	TEAM01_MODE=sample $(PY) src/scripts/02_validate.py
	TEAM01_MODE=sample $(PY) src/scripts/03_attribution.py
	TEAM01_MODE=sample $(PY) src/scripts/04_tail.py
	TEAM01_MODE=sample $(PY) src/scripts/05_clusters.py
	TEAM01_MODE=sample $(PY) src/scripts/06_models.py
	TEAM01_MODE=sample $(PY) src/scripts/07_figures.py

dashboard:
	$(PY) dashboard/app.py

test:
	$(PY) -m pytest tests -q

clean:
	rm -rf outputs/tables/*.csv outputs/metrics/*.json figures/*.png
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
