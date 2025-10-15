.PHONY: format lint typecheck check setup manage-% run-%

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

run-%:
	@python -m services.$*.main
