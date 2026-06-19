.PHONY: format lint typecheck check setup test test-ci run-%

format:
	black .

lint:
	flake8

typecheck:
	mypy .

check: lint typecheck

setup:
	pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install

test:
	pytest

test-ci:
	pytest -v --junitxml=test-results.xml

run-%:
	@python -m services.$*.main
