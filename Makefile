.DEFAULT_GOAL := help

.PHONY: help sandbox db reset test lint format check check-tab-space sync-local-to-gs build-bin setup-win-whl project app-login login dev-to-nl

help: ## show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

sandbox: ## create a temporary folder to test the commands
	python3 scripts/reset_sandbox.py

# Db
db: ## starts .relay.db session
	@if command -v sqlite3 >/dev/null 2>&1; then \
		sqlite3 .relay.db; \
	else \
		uv run python -m sqlite3 .relay.db; \
	fi

reset: ## reset database
	rm -rf .relay.db

# Lint & Test
test: ## run test suite
	uv run pytest -s

lint: ## lint check
	uv run ruff check

format: ## format check and fix
	uv run ruff format
	uv run ruff check --fix

check: ## lint check, format check and fix
	uv run ruff check
	uv run ruff format --check
	uv run mypy

check-tab-space: ## verify Makefile format
	cat -A Makefile

# Sync
PROJECT ?= relay
DRY_RUN ?= true
sync-local-to-gs: ## sync relay or vois-shield with gs bucket
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

# Build
build-bin: ## compile to bin build files
	uv run pyinstaller relay.spec

setup-win-whl: ## setup win_amd64_whl for windows installation
	@read -p "Python version (default 3.14): " PYVER; \
	PYVER=$${PYVER:-3.14}; \
	rm -rf dist win_amd64_whl win_amd64_whl.zip && \
	mkdir -p win_amd64_whl && \
	uv run pip download --platform win_amd64 --only-binary=:all: --python-version $$PYVER --dest ./win_amd64_whl/ blake3 google-cloud-storage && \
	uv build && \
	cp dist/*.whl ./win_amd64_whl/ && \
	zip -r win_amd64_whl.zip win_amd64_whl/ && \
	rm -rf win_amd64_whl && \
	cloudshell download win_amd64_whl.zip 

# Setup
project: ## set default gcloud project
	gcloud config set project vf-grp-gbissdbx-dev-1
app-login: ## user application login
	gcloud auth application-default login
login: ## user login
	gcloud auth login

# Custom
dev-to-nl: # sync folders vf-grp-mirep-dev/ to vf-grp-mirep-nonlive/
	uv run relay sync ~/vf-grp-mi-pyramid/Dockerfiles/zeta/vf-grp-mirep-dev/mirep/vf-commentary-assistance-be/ ~/vf-grp-mi-pyramid/Dockerfiles/zeta/vf-grp-mirep-nonlive/mirep/vf-commentary-assistance-be/