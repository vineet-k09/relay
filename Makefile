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

PROJECT ?= relay
DRY_RUN ?= true
sync-local-to-gs:
	@read -p "Project [relay]: " PROJECT; \
	PROJECT=$${PROJECT:-relay}; \
	read -p "Dry run? [true]: " DRY_RUN; \
	DRY_RUN=$${DRY_RUN:-true}; \
	SRC=$$( \
		if [ "$$PROJECT" = "relay" ]; then \
			echo "."; \
		elif [ "$$PROJECT" = "vois-shield" ]; then \
			echo "$$HOME/security-awareness-platform/frontend/VShield/src/Pages/Training/"; \
		else \
			echo "ERROR: Unknown project '$$PROJECT'" >&2; exit 1; \
		fi \
	); \
	DST=$$( \
		if [ "$$PROJECT" = "relay" ]; then \
			echo "gcloud storage gs://vineetk/relay"; \
		else \
			echo "gcloud storage gs://vineetk/vois_shield/src/Pages/Training"; \
		fi \
	); \
	FLAG=$$( \
		if [ "$$DRY_RUN" = "true" ]; then \
			echo "--dry-run"; \
		else \
			echo "--delete"; \
		fi \
	); \
	uv run relay sync "$$SRC" "$$DST" $$FLAG

test-local-to-gs-vois-shield:
	uv run relay sync \
		~/security-awareness-platform/frontend/VShield/src/Pages/Training/ \
		"gcloud storage gs://vineetk/vois_shield/src/Pages/Training" \
		--delete
l-to-gs-relay-sync:
	uv run relay sync . "gcloud storage gs://vineetk/relay" --delete

test-local-to-gs-vois-shield-dry-run:
	uv run relay sync \
		~/security-awareness-platform/frontend/VShield/src/Pages/Training/ \
		"gcloud storage gs://vineetk/vois_shield/src/Pages/Training" \
		--dry-run
		
build-bin:
	uv run pyinstaller relay.spec

setup-win-whl:
	@read -p "Python version (default 3.14): " PYVER; \
	PYVER=$${PYVER:-3.14}; \
	mkdir -p win_amd64_whl && \
	uv run pip download --platform win_amd64 --only-binary=:all: --python-version $$PYVER --dest ./win_amd64_whl/ blake3 google-cloud-storage && \
	zip -r relay_windows_whl.zip win_amd64_whl/ && \
	rm -rf win_amd64_whl