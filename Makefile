# Makefile for Fly-In Drone Routing Project

PYTHON := python3
MAP ?= maps/easy/01_linear_path.txt

.PHONY: all install run debug clean lint lint-strict visualize

all: run

install:
	$(PYTHON) -m pip install --break-system-packages pygame flake8 mypy

run:
	$(PYTHON) main.py $(MAP)

debug:
	$(PYTHON) -m pdb main.py $(MAP)

clean:
	rm -rf __pycache__ .mypy_cache .pytest_cache *.pyc

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict

visualize:
	$(PYTHON) main.py $(MAP) --vis
