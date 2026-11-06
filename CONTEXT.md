# Relay — Project State & Context

> **Last Updated:** 2026-11-04  
> **Status:** Local-to-Local, Local-to-GCS, Windows-to-Windows, and Bucket-to-Windows adapters implemented and verified; CI active; all tests, ruff, and mypy passing.

---

## 1. Architecture Overview

Relay is a differential synchronization CLI tool combining the speed of `rsync` with the content-addressable model of `git` across environments (**Local**, **GCS**, and **SSH / GCP Workbench**).

```
CLI Presentation Layer (cli.py)
       │
       ├──> Endpoint Parsing (core/endpoint.py)
       │
       ├──> Manifest Resolution:
       │      • Local: Scanner / SQLite Ledger (core/scanner.py & utils/db.py -> .relay.db)
       │      • GCS:   Instant bucket listing (adapters/gcs.py -> list_gcs_manifest)
       │
       ├──> Diff Engine (core/diff.py -> DiffPlan) [Pure in-memory comparison]
       │
       ├──> Diff Table Preview (shared/print_diff.py)
       │
       └──> Execution Layer (core/sync.py -> SyncExecutor)
              └──> Transport Adapters:
                     • LocalTransportAdapter (adapters/local.py) [Linux / Mac]
                     • WindowsTransportAdapter (adapters/windows.py) [Windows / Cross-drive]
                     • GCSTransportAdapter (adapters/gcs.py) [Linux <-> GCS]
                     • GCSWindowsTransportAdapter (adapters/windows.py) [Windows <-> GCS]
```

---

## 2. Completed Milestones

1. **GitHub Actions CI & Auto-Formatting (`.github/workflows/ci.yml`)**:
   - Automated quality pipeline: `ruff format`, `ruff check`, `mypy`, and `pytest` (Python 3.12 & 3.13 matrix).
   - Auto-commits formatting fixes back to `main` using `stefanzweifel/git-auto-commit-action@v5` with `[skip ci]`.

2. **Local-to-Local Sync Verified**:
   - Automated sandbox (`make sandbox`) verified live across all 5 states (`UNCHANGED`, `MODIFIED`, `MOVED`, `ADDED`, `DELETED`).
   - Inode & hash move detection, dry-run, interactive `--delete`, and idempotency confirmed.

3. **GCS Transport Adapter (`src/relay/adapters/gcs.py`)**:
   - Supports bidirectional sync (`Local -> GCS` upload and `GCS -> Local` download).
   - `list_gcs_manifest()`: Instant metadata extraction using GCS `list_blobs()`.
   - Zero-egress server-side operations: `bucket.rename_blob()` and `bucket.copy_blob()`.
   - Concurrent transfers: `transfer_batch()` parallelizes file streams across 8 worker threads.
   - CRC32C alignment: `hash.py` and `db.py` compute real base64 `google_crc32c` matching GCS headers.
   - Mocked unit tests added in `tests/test_gcs_adapter.py`.

4. **Windows & Cross-Filesystem Adapters (`src/relay/adapters/windows.py`)**:
   - `WindowsTransportAdapter`: Specialized for Windows-to-Windows and cross-drive transfers (`C:` to `D:`).
     - Cross-device fallback (`EXDEV` & `WinError 17`) to `shutil.move()` when moving across drives or partitions (e.g. Btrfs vs ext4).
     - Retry loop with backoff for Windows sharing violations / file locks (`WinError 32`).
     - Safe deletion of Windows read-only files (`WinError 5`) via `stat.S_IWRITE` permission reset.
     - Pure Python native `shutil.copy2` with exact `mtime` preservation (preventing differential false-positives).
   - `GCSWindowsTransportAdapter`: Specialized for Bucket-to-Windows (Download) and Windows-to-Bucket (Upload).
     - Strict path normalization: automatically converts Windows backslashes `\` to canonical cloud forward slashes `/`.
     - Windows-hardened local downloads with metadata preservation and hash verification.
   - Dynamic routing in `adapters.get_adapter()`: automatically detects Windows OS (`os.name == 'nt'`) or Windows drive letters (`C:\`) and UNC shares (`\\`).
   - Educational, beginner-friendly "why this is here" comments throughout.
   - Unit tests added in `tests/test_windows_adapter.py` (12 total tests passing).

5. **Documentation Restructure**:
   - Modularized documentation cleanly under `docs/` (`architecture.md`, `diff-engine.md`, `sandbox.md`, `transports.md`).

---

## 3. Quick Verification Commands

```bash
# Run test suite, linting, and type checking
make check
make pytest

# Test sandbox locally
make sandbox
uv run relay sync sandbox/source sandbox/dest --dry-run
uv run relay sync sandbox/source sandbox/dest
uv run relay sync sandbox/source sandbox/dest --delete
uv run relay status sandbox/source
```

---

## 4. Next Steps & Roadmap

1. **Live GCS Integration Testing**:
   - Test `relay status gs://<bucket>/` and `relay sync` live against an authentic GCP bucket on laptop with GCP credentials.
2. **SSH / GCP Workbench Adapter (`src/relay/adapters/ssh.py`)**:
   - Remote execution of `mv`, `cp`, `rm` over SSH wrapper (`gcloud compute ssh`).
3. **User-Configurable Ignore Rules**:
   - Support `.relayignore` files alongside defaults.
4. **Safety & Rollback Trash**:
   - Backup directory for modified/deleted files before destructive execution.


### trying this today since normal pyz doenst work as windows dont have <3.14, havent tried exe, tried copy and downloading the whole thing but the venv had linux executeables and wont work locally - the windows cant have pip install - or any install
```bash
(relay) vineet_kushwaha1@cloudshell:~/relay$ # Build the wheel
uv build

# Unzip the source package into staging (unzip only the app code folder)
unzip -q dist/*.whl -d staging/
Building source distribution...
Building wheel from source distribution...
Successfully built dist/relay-0.1.0.tar.gz
Successfully built dist/relay-0.1.0-py3-none-any.whl
(relay) vineet_kushwaha1@cloudshell:~/relay$ python3 -m zipapp staging -m "relay.cli:main" -o relay.pyz
(relay) vineet_kushwaha1@cloudshell:~/relay$ 
```

with current version of relay
```ps1
PS C:\Users\KushwahaV2\Downloads> python .\relay.pyz status
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "C:\Users\KushwahaV2\Downloads\relay.pyz\__main__.py", line 2, in <module>
    import relay.cli
  File "C:\Users\KushwahaV2\Downloads\relay.pyz\relay\cli.py", line 4, in <module>
    from relay.adapters import get_adapter
  File "C:\Users\KushwahaV2\Downloads\relay.pyz\relay\adapters\__init__.py", line 12, in <module>
    from relay.adapters.gcs import GCSTransportAdapter
  File "C:\Users\KushwahaV2\Downloads\relay.pyz\relay\adapters\gcs.py", line 23, in <module>
    from google.cloud import storage  # type: ignore[import-untyped]
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\KushwahaV2\Downloads\relay.pyz\google\cloud\storage\__init__.py", line 35, in <module>
    from google.cloud.storage.batch import Batch
  File "C:\Users\KushwahaV2\Downloads\relay.pyz\google\cloud\storage\batch.py", line 43, in <module>
    from google.cloud import _helpers, exceptions
  File "C:\Users\KushwahaV2\Downloads\relay.pyz\google\cloud\_helpers\__init__.py", line 49, in <module>
    import google.auth.transport.requests
  File "C:\Users\KushwahaV2\Downloads\relay.pyz\google\auth\transport\requests.py", line 45, in <module>
    from google.oauth2 import service_account
  File "C:\Users\KushwahaV2\Downloads\relay.pyz\google\oauth2\service_account.py", line 78, in <module>
    from google.auth import (
    ...<8 lines>...
    )
  File "C:\Users\KushwahaV2\Downloads\relay.pyz\google\auth\_service_account_info.py", line 20, in <module>
    from google.auth import crypt, exceptions
  File "C:\Users\KushwahaV2\Downloads\relay.pyz\google\auth\crypt\__init__.py", line 40, in <module>
    from google.auth.crypt import base, es, es256, rsa
  File "C:\Users\KushwahaV2\Downloads\relay.pyz\google\auth\crypt\es.py", line 20, in <module>
    import cryptography.exceptions
  File "C:\Users\KushwahaV2\Downloads\relay.pyz\cryptography\exceptions.py", line 9, in <module>
    from cryptography.hazmat.bindings._rust import exceptions as rust_exceptions
ImportError: cannot import name 'exceptions' from 'cryptography.hazmat.bindings._rust' (unknown location)
PS C:\Users\KushwahaV2\Downloads>
```