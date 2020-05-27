.PHONY: init install install-dev lint format test

# include source code in any python subprocess
export PYTHONPATH = .
SOURCE_FOLDER=rasa_integration_testing
TEST_FOLDER=tests

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
	poetry run pylama $(SOURCE_FOLDER) $(TEST_FOLDER)
	poetry run mypy $(SOURCE_FOLDER) $(TEST_FOLDER)
	poetry run black --check $(SOURCE_FOLDER) $(TEST_FOLDER)
	poetry run isort --check -rc $(SOURCE_FOLDER) $(TEST_FOLDER)

format:
	poetry run black $(SOURCE_FOLDER) $(TEST_FOLDER)
	poetry run isort -rc $(SOURCE_FOLDER) $(TEST_FOLDER)

test:
	poetry run py.test
