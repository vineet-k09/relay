.PHONY: db run reset test pytest lint format check sandbox test-local-to-gs-vois-shield-dry-run

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

test-local-to-gs-vois-shield:
	uv run relay sync \
		~/security-awareness-platform/frontend/VShield/src/Pages/Training/ \
		"gcloud storage gs://vineetk/vois_shield/src/Pages/Training" \
		--delete

test-local-to-gs-vois-shield-dry-run:
	uv run relay sync \
		~/security-awareness-platform/frontend/VShield/src/Pages/Training/ \
		"gcloud storage gs://vineetk/vois_shield/src/Pages/Training" \
		--dry-run
		
build-bin:
	uv run pyinstaller relay.spec
