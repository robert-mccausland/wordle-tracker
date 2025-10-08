.PHONY: format lint typecheck check ci setup manage-% run-%

format:
	black .

lint:
	flake8

typecheck:
	mypy .

check: lint typecheck

ci:
	pip install -r requirements.txt

setup:
	pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install

run-%:
	@python -m services.$*.main
