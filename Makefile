.PHONY: lint lint-check lint-fix type-check

lint-fix:
	black .
	isort .
	autoflake --in-place --remove-all-unused-imports --remove-unused-variables --recursive .

lint-check:
	black --check .
	isort --check-only .
	flake8 .

type-check:
	mypy backend/core --ignore-missing-imports

lint: lint-fix lint-check type-check
