.PHONY: db run reset test pytest lint format check sandbox

sandbox:
	python3 scripts/reset_sandbox.py

db:
	@if command -v sqlite3 >/dev/null 2>&1; then \
		sqlite3 .relay.db; \
	else \
		uv run python -m sqlite3 .relay.db; \
	fi
run:
	uv run relay
reset:
	rm -rf .relay.db
test:
	uv run python tests/test_db_queries.py
pytest:
	uv run pytest -s

lint:
	uv run ruff check
format:
	uv run ruff format
	uv run ruff check --fix
check:
	uv run ruff check
	uv run ruff format --check
	uv run mypy