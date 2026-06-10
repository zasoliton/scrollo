SHELL := /bin/zsh

PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin
PIP := $(BIN)/pip
PYTHON_VENV := $(BIN)/python
APP := $(BIN)/market-matrix-scroller

.PHONY: help venv install run test compile clean

help:
	@printf "Available targets:\n"
	@printf "  make venv      Create the virtual environment\n"
	@printf "  make install   Install the project into the virtual environment\n"
	@printf "  make run       Launch the scroller app\n"
	@printf "  make test      Run the unit tests\n"
	@printf "  make compile   Run a syntax compilation pass\n"
	@printf "  make clean     Remove caches and the virtual environment\n"

$(BIN)/activate:
	$(PYTHON) -m venv $(VENV)

venv: $(BIN)/activate

install: venv
	$(PIP) install -e .

run: install
	$(APP)

test: venv
	$(PYTHON_VENV) -m unittest discover -s tests

compile: venv
	$(PYTHON_VENV) -m compileall src tests

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache
	find src tests -type d -name "__pycache__" -prune -exec rm -rf {} +
