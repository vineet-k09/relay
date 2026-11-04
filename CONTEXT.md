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
