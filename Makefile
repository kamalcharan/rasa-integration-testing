.PHONY: init install-dev clean lint format test

# include source code in any python subprocess
export PYTHONPATH = .

VENV_LOCATION=.venv
ACTIVATE_VENV=test -d ${VENV_LOCATION} \
  && echo "Using .venv" \
  && . ${VENV_LOCATION}/bin/activate;

SOURCE_FOLDER=rasa_integration_testing

help:
	@echo "    init"
	@echo "        Initialize virtual environment"
	@echo "    install"
	@echo "        Install dependencies"
	@echo "    install-dev"
	@echo "        Install dev dependencies"
	@echo "    clean"
	@echo "        Remove Python artifacts"
	@echo "    lint"
	@echo "        Check style with black, pylama, isort and mypy"
	@echo "    format"
	@echo "        Format code with black"
	@echo "    test"
	@echo "        Run py.test"

init:
	python3 -m venv ${VENV_LOCATION}
	${ACTIVATE_VENV} pip install --upgrade pip

install:
	${ACTIVATE_VENV} pip install -r requirements.txt

install-dev:
	${ACTIVATE_VENV} pip install -r requirements-dev.txt

clean:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f  {} +

lint:
	${ACTIVATE_VENV} pylama
	${ACTIVATE_VENV} mypy .
	${ACTIVATE_VENV} black --check .
	${ACTIVATE_VENV} isort --check

format:
	${ACTIVATE_VENV} black .
	${ACTIVATE_VENV} isort

test: clean
	${ACTIVATE_VENV} py.test tests \
		--cov-report term-missing:skip-covered \
		--cov-report html \
		--cov-fail-under=85 \
		--cov "${SOURCE_FOLDER}"
