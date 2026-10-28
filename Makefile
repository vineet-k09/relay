.PHONY: db run reset test pytest lint format check

db:
	sqlite3 .relay.db
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
	uv run ruff check --fix
	uv run ruff format
check:
	uv run ruff check
	uv run ruff format --check
	uv run mypy