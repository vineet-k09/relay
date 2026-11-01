# Relay — Project State & Context

> **Last Updated:** 2026-11-01  
> **Status:** Local-to-Local synchronization fully functional end-to-end; tests, ruff, and mypy passing.

---

## 1. Architecture Overview

Relay is a differential synchronization CLI tool combining the speed of `rsync` with the content-addressable model of `git` across environments (**Local**, **GCS**, and **SSH / GCP Workbench**).

```
CLI Presentation Layer (cli.py)
       │
       ├──> Endpoint Parsing (core/endpoint.py)
       │
       ├──> Local Scanner / Ledger (core/scanner.py & utils/db.py -> .relay.db)
       │
       ├──> Diff Engine (core/diff.py -> DiffPlan)
       │
       ├──> Diff Table Preview (shared/print_diff.py)
       │
       └──> Execution Layer (core/sync.py -> SyncExecutor)
              └──> Transport Adapters (adapters/local.py, adapters/base.py)
```

---

## 2. Completed Milestones

1. **CLI Entry Point**:
   - `pyproject.toml` updated: `relay = "relay.cli:main"`.
   - `src/relay/__main__.py` added to enable `python -m relay`.
   - `src/relay/__init__.py` cleaned up (legacy prototype scanner removed).

2. **Scanner & State Ledger (`src/relay/core/scanner.py`)**:
   - Accepts arguments: `scan_local_dir(target_dir, db, db_path, verbose)`.
   - Safely resolves paths using `pathlib.Path.resolve()`.
   - Automatically ignores `.relay.db*`, `.git*`, `__pycache__*`, `.pytest_cache*`, `.mypy_cache*`.
   - Stores clean relative POSIX paths (`data/train.csv`, `README.md`) so source and destination ledgers are directly comparable.
   - Detects moves/renames via fast Inode matching (POSIX) and fallback content-hash matching (cross-device).
   - Commits and returns the active SQLite connection.

3. **Database Layer (`src/relay/utils/db.py`)**:
   - Uses `INSERT OR REPLACE INTO files` so updating existing modified files avoids primary key integrity crashes.

4. **Transport Adapters (`src/relay/adapters/`)**:
   - `base.py`: Defines the transport contract (`rename`, `copy_local`, `transfer`, `delete`, `list_manifest`).
   - `local.py`: Implements `LocalTransportAdapter` using standard filesystem operations (`shutil.copy2`, `os.replace`, `unlink`, `calculate_hashes`).
   - `__init__.py`: Factory `get_adapter(src, dst)` dynamically routes endpoints (currently handles `LOCAL -> LOCAL`).

5. **Execution & Dry-Run (`src/relay/core/sync.py` & `src/relay/cli.py`)**:
   - `SyncExecutor.confirm_plan()` handles dry-run exit cleanly without duplicate CLI prints.
   - Summarizes planned changes (`X to add`, `Y to modify`, `Z to move (0 network bytes)`, `W to delete`).
   - Prompts for confirmation when `--delete` is requested.

6. **Automated Sandbox Test Harness (`scripts/reset_sandbox.py`)**:
   - Generates a local sandbox covering all 5 core sync scenarios:
     - `UNCHANGED`
     - `MODIFIED`
     - `MOVED`
     - `ADDED`
     - `DELETED`
   - Added `make sandbox` to `Makefile`.

---

## 3. Quick Verification Commands

```bash
# Run test suite, linting, and type checking
uv run pytest
uv run ruff check
uv run mypy

# Reset and test sandbox
make sandbox
uv run relay sync sandbox/source sandbox/dest --dry-run
uv run relay sync sandbox/source sandbox/dest
uv run relay sync sandbox/source sandbox/dest --delete
uv run relay status sandbox/source
```

---

## 4. Next Steps & Roadmap

1. **GCS Adapter (`src/relay/adapters/gcs.py`)**:
   - Implement `verify_auth()` with GCP ADC / `gcloud auth`.
   - Implement `list_manifest()` by reading GCS object headers (`blob.name`, `blob.crc32c`, `blob.size`, `blob.updated`).
   - Implement `rename` via `bucket.rename_blob(...)` (zero network transfer).
   - Implement `copy_local` via `bucket.copy_blob(...)` (server-side copy).
   - Implement `transfer` (upload/download via `google-cloud-storage`).
   - Implement `delete` via `blob.delete()`.

2. **SSH / GCP Workbench Adapter (`src/relay/adapters/ssh.py`)**:
   - Parse zone/instance/remote_path from `ssh` endpoint format.
   - Remote execution of `mv`, `cp`, `rm` over SSH wrapper (`gcloud compute ssh`).

3. **User-Configurable Ignore Rules**:
   - Load custom `.relayignore` files from target directories and merge with `DEFAULT_IGNORED`.

4. **Rollback & Safety (from Scenarios.md)**:
   - Trash / backup directory for overwritten (`MODIFIED`) or removed (`DELETED`) files before destructive execution.
