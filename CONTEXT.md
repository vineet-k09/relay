# Relay — Project State & Context
```ps1
requests.exceptions.ProxyError: HTTPSConnectionPool(host='storage.googleapis.com', port=443): Max retries exceeded with url: / (Caused by ProxyError('Unable to connect to proxy', SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1081)'))))
```
> **Last Updated:** 2026-11-08  
> **Status:** All 7 CI jobs passing (Ubuntu + Windows across Python 3.12 & 3.13; PyInstaller Windows `.exe` and Linux binary artifacts generated). CRLF newline issue in Windows test suite resolved.

---

## ⚠️ CRITICAL PAIR PROGRAMMING DIRECTIVE FOR AI ASSISTANTS

> [!IMPORTANT]
> **DO NOT write, edit, or commit codebase files directly unless the user explicitly asks you to.**
>
> The user understands and learns concepts significantly better by writing code word-by-word themselves from chat instructions and explanations rather than having the assistant edit files directly.
>
> **Default Assistant Behavior:**
> - Provide clear, detailed code snippets, diffs, explanations, and file/line references directly in the chat response.
> - Walk through the logic step-by-step so the user can implement the changes themselves.
> - Only call file-editing, file-writing, or git commit tools if the user explicitly instructs you to write the code, make the edit, or commit on their behalf.

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

6. **Windows CRLF Test Stabilization & CI Artifact Generation**:
   - Stabilized `tests/test_windows_adapter.py::test_windows_adapter_transfer` by writing binary payload (`write_bytes`) to avoid Windows CRLF newline expansion (`\r\n`), matching byte-for-byte size assertions across OS platforms.
   - All 7 CI matrix jobs passing (`Lint & Format`, `Ubuntu 3.12/3.13`, `Windows 3.12/3.13`, `Build Linux Binary`, `Build Windows Executable`).
   - GitHub Actions workflow (`.github/workflows/ci.yml`) automatically builds and archives standalone executables for both Linux (`relay-linux-x64`) and Windows (`relay-windows-x64`).

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


## 5. Windows Packaging, Portability & Enterprise Restrictions

### 5.1 The Corporate Problem Statement
On enterprise Windows laptops (e.g. corporate proxy/firewalls, SSL inspection, Zscaler, or non-admin privileges):
1. **Network install blocked**: `pip install` cannot reach external PyPI repositories.
2. **EDR / Antivirus risk**: Running an unsigned, newly built standalone `.exe` (from PyInstaller) on a corporate-managed laptop can trigger **Endpoint Detection & Response (EDR)** alerts (e.g. CrowdStrike Falcon, Microsoft Defender ATP, Carbon Black) as an untrusted binary or suspicious dropper.

---

### 5.2 Post-Mortem of Failed Attempts

#### Attempt 1: Copying Linux `.venv` to Windows
* **Symptom**: Executables and scripts in the `.venv` failed to execute on Windows.
* **Root Cause**: Virtual environments are tightly coupled to the host OS. Linux venvs contain Linux ELF binary wrappers, POSIX symlinks, and `.so` shared libraries that Windows (PE/COFF) cannot execute.

#### Attempt 2: Zipapp (`relay.pyz`) via Cloud Shell / Linux
* **Build Steps Attempted**:
  ```bash
  uv build
  unzip -q dist/*.whl -d staging/
  python3 -m zipapp staging -m "relay.cli:main" -o relay.pyz
  ```
* **Failure on Windows**:
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
* **Root Causes**:
  1. **Binary Format Mismatch (ELF vs. PE)**:
     Packages like `cryptography` (Rust), `blake3` (C/Rust), and `google-crc32c` (C) compile to platform-specific machine code. Building on Linux packaged Linux ELF `.so` libraries (`_rust.abi3.so`, `blake3.so`). Windows requires `.pyd` / `.dll` (PE32+).
  2. **Python `zipimport` Limitation**:
     Python's built-in `zipimport` engine can only import pure `.py` and `.pyc` files from inside a zip/pyz. It **cannot** dynamically load native C/Rust extensions (`.pyd` or `.so`) directly out of memory or a zip archive without physically extracting them to disk first.

---

### 5.3 Corporate-Safe Personal Solution: Offline Wheelhouse (EDR-Safe)

To run Relay safely on a corporate Windows machine without triggering EDR alarms or needing internet pip:

1. **Leverage the approved local Python**: Runs directly through the IT-approved `python.exe` already installed on the machine. No unrecognized `.exe` is executed.
2. **Download Windows-compiled wheels offline on Linux / Cloud Shell**:
   ```bash
   # 1. Download all pre-compiled Windows x64 binary wheels from PyPI
   mkdir -p windows_wheels
   uv run pip download \
     --platform win_amd64 \
     --only-binary=:all: \
     --python-version 3.12 \
     --dest ./windows_wheels \
     blake3 google-cloud-storage

   # 2. Build the pure-Python Relay wheel
   uv build
   cp dist/*.whl ./windows_wheels/

   # 3. Bundle into a single zip archive to transfer
   zip -r windows_wheels.zip windows_wheels/
   ```

3. **Install completely offline on corporate Windows**:
   Transfer `windows_wheels.zip` to Windows, extract it, and install without touching the corporate network:
   ```powershell
   # Install to user space (no admin privileges needed, no internet traffic)
   python -m pip install --user --no-index --find-links .\windows_wheels relay
   ```

4. **Zero-Pip Fallback (if the `pip` executable itself is blocked by policy)**:
   Because wheels are standard `.zip` archives, extract them directly into a local folder:
   ```powershell
   # Extract all dependency wheels into a local deps folder
   Get-ChildItem .\windows_wheels\*.whl | ForEach-Object { Expand-Archive $_.FullName -DestinationPath .\deps -Force }

   # Run Relay by pointing PYTHONPATH to deps and src
   $env:PYTHONPATH=".\deps;.\src"
   python -m relay.cli status C:\path\to\dir
   ```

---

### 5.4 Summary of Final Commands on Windows (Do NOT run `python relay.pyz`)

> [!CAUTION]
> **Do not run `python relay.pyz status`!**  
> Running `python relay.pyz status` will fail because Python's built-in `zipimport` engine cannot load native C/Rust extensions (`cryptography`, `blake3`, `google-crc32c`) directly from a zip/pyz file without unpacking them to disk.

| Deployment Path | Context | Final Execution Command |
| :--- | :--- | :--- |
| **Option 1: Offline Wheels** *(Recommended)* | Corporate Windows machines | `relay status <path>`<br>*(or `python -m relay.cli status <path>`)* |
| **Option 2: Zero-Pip Unpacked** | Corporate machines where `pip.exe` is banned | `$env:PYTHONPATH=".\deps;.\src"`<br>`python -m relay.cli status <path>` |
| **Option 3: GitHub Actions `.exe`** | Personal or unrestricted machines | `.\relay.exe status <path>` |

---

### 5.5 CI Solution: GitHub Actions Hosted Windows Runner + PyInstaller Executable

For personal/non-corporate machines, or for releasing official standalone binaries, GitHub Actions provides cloud-hosted Windows runners (`runs-on: windows-latest`).

* **GitHub Actions Workflow (`.github/workflows/ci.yml`)**:
  - **Matrix Testing**: Runs tests on both `ubuntu-latest` and `windows-latest` across Python 3.12 and 3.13.
  - **Automated Windows Build (`build-windows` job)**:
    1. Spins up a clean, official Windows 2022/2025 runner with unrestricted internet.
    2. Installs dependencies and PyInstaller using `uv sync --all-groups`.
    3. Runs PyInstaller:
       ```powershell
       uv run pyinstaller relay.spec
       ```
    4. Automatically uploads `dist/relay.exe` as a workflow artifact named `relay-windows-x64`.
* **How to download the `.exe`**:
  Navigate to GitHub repository -> **Actions** -> click latest run -> scroll to **Artifacts** -> download `relay-windows-x64`.

---

### 5.6 Build System Configuration State
* **`pyproject.toml`**: Restored `build-system` to native `uv_build`:
  ```toml
  [build-system]
  requires = ["uv_build>=0.12.2,<0.13.0"]
  build-backend = "uv_build"
  ```
* **Dev Dependencies**: Added `pyinstaller>=6.22.3` to the `dev` dependency group for local/CI packaging.
* **Makefile**: Added `build-bin: uv run pyinstaller relay.spec` target.


# Current issue
vineet_kushwaha1@cloudshell:~/relay (vf-grp-gbissdbx-dev-1)$ uv run relay sync . "gcloud storage gs://vineetk/relay"
[relay] Resolving endpoints:
    Source:      . [LOCAL]
    Destination: gcloud storage gs://vineetk/relay [GCS]
[error] Unexpected response from metadata server: service account info is missing 'email' field.
vineet_kushwaha1@cloudshell:~/relay (vf-grp-gbissdbx-dev-1)$ gcloud auth list
gcloud config get-value account
gcloud storage ls gs://vineetk/
Credentialed Accounts

ACTIVE: *
ACCOUNT: vineet.kushwaha1@vodafone.com

To set the active account, run:
    $ gcloud config set account `ACCOUNT`

Your active configuration is: [cloudshell-9798]
vineet.kushwaha1@vodafone.com
gs://vineetk/jtd/
gs://vineetk/relay/
gs://vineetk/static-poc/
gs://vineetk/uiux/
gs://vineetk/vois_hub/
gs://vineetk/vois_shield/
vineet_kushwaha1@cloudshell:~/relay (vf-grp-gbissdbx-dev-1)$ make sync-local-to-gs
Project [relay]: 
Dry run? [true]: 
[relay] Resolving endpoints:
    Source:      . [LOCAL]
    Destination: gcloud storage gs://vineetk/relay [GCS]
[error] Unexpected response from metadata server: service account info is missing 'email' field.
make: *** [Makefile:34: sync-local-to-gs] Error 1
vineet_kushwaha1@cloudshell:~/relay (vf-grp-gbissdbx-dev-1)$ 