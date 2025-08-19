.PHONY: lint lint-check lint-fix lint-fast type-check test-unit test-integration

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

# Faster local lint (no mypy)
lint-fast:
	black .
	isort .
	autoflake --in-place --remove-all-unused-imports --remove-unused-variables --recursive .
	black --check .
	isort --check-only .
	flake8 .

# Test targets for faster dev cycles
test-unit:
	pytest -m "not integration and not slow" -q

test-integration:
	pytest -m "integration" -q
