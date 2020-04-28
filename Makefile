.PHONY: init install install-dev lint format test

# include source code in any python subprocess
export PYTHONPATH = .
SOURCE_FOLDER=rasa_integration_testing

help:
	@echo "    init"
	@echo "        Initialize virtual environment"
	@echo "    install"
	@echo "        Install dependencies"
	@echo "    lint"
	@echo "        Check style with pylama, mypy and black"
	@echo "    format"
	@echo "        Format code with black"
	@echo "    test"
	@echo "        Run py.test (use TEST_FILE variable to test a single file)"

init:
	curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python

install:
	poetry install

lint:
	poetry run pylama
	poetry run mypy .
	poetry run black --check .
	poetry run isort --check

format:
	poetry run black .
	poetry run isort

test:
	poetry run py.test \
		--cov-report term-missing:skip-covered \
		--cov-report html \
		--cov-fail-under=85 \
		--cov "${SOURCE_FOLDER}"
