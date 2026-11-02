# Architecture & Design 🏗️

Relay is built on a modular, differential synchronization pipeline. It decouples high-level CLI interactions, manifest resolution, diff computation, and transport execution into distinct, testable layers.

---

## 1. System Layers

```
CLI Presentation Layer (src/relay/cli.py)
       │
       ├──> Endpoint Parsing (src/relay/core/endpoint.py)
       │
       ├──> Local Scanner / Ledger (src/relay/core/scanner.py & src/relay/utils/db.py -> .relay.db)
       │
       ├──> Diff Engine (src/relay/core/diff.py -> DiffPlan)
       │
       ├──> Diff Table Preview (src/relay/shared/print_diff.py)
       │
       └──> Execution Layer (src/relay/core/sync.py -> SyncExecutor)
              └──> Transport Adapters (src/relay/adapters/base.py, src/relay/adapters/local.py)
```

### Layer Responsibilities

1. **Presentation Layer (`src/relay/cli.py`)**:
   - Parses command-line arguments using `argparse`.
   - Coordinates the workflow between endpoint resolution, diff planning, user confirmation, and execution.
   - Formats user-facing console output using ANSI styling (`src/relay/shared/styles.py`, `src/relay/shared/print_diff.py`).

2. **Endpoint Resolution (`src/relay/core/endpoint.py`)**:
   - Analyzes source and destination strings to detect environment types: `LOCAL`, `GCS` (`gs://` or `gcs://`), or `SSH` (`ssh ...`).
   - Normalizes paths and prepares endpoint metadata for adapter assignment.

3. **Scanner & State Ledger (`src/relay/core/scanner.py`, `src/relay/utils/db.py`)**:
   - Recursively traverses directories while skipping ignored patterns (`src/relay/shared/ignored.py`).
   - Computes fast cryptographic hashes (BLAKE3) and retrieves file metadata (`size`, `mtime`, `inode`).
   - Persists state in an embedded SQLite database (`.relay.db`).

4. **Diff Engine (`src/relay/core/diff.py`)**:
   - A pure domain logic component with no disk or network I/O.
   - Compares the source manifest with the destination manifest.
   - Identifies actions: `UNCHANGED`, `MODIFIED`, `MOVED`, `COPIED`, `ADDED`, `DELETED`.

5. **Execution Layer (`src/relay/core/sync.py`)**:
   - Evaluates user flags (`--dry-run`, `--delete`, interactive confirmations).
   - Translates `DiffPlan` items into operations performed via the transport adapter.
   - Synchronizes destination state ledgers after operations complete.

6. **Transport Adapters (`src/relay/adapters/`)**:
   - Concrete implementations adhering to the abstract interface `TransportAdapter`.
   - Handles the actual file moves, copies, network transfers, and deletions.

---

## 2. The Core Pipeline: Function-Based Clean Architecture

Relay favors pure functions and clear data boundaries over complex object-oriented inheritance hierarchies:

```python
# 1. Manifest Resolution (Pure I/O: Endpoint -> list of (path, hash))
src_manifest = get_manifest(src_endpoint)
dst_manifest = get_manifest(dst_endpoint)

# 2. Diff Engine (Pure Domain Logic: No disk, no network, in-memory)
diff_plan = compute_diff(src_manifest, dst_manifest)

# 3. Execution (Pure I/O: DiffPlan -> Adapter execution)
executor.execute(diff_plan, dst_db, adapter)
```

### Architectural Principles:
- **Single Responsibility**: `init_db()` manages SQLite tables. `compute_diff()` computes diffs. Transport adapters execute low-level filesystem and network calls.
- **Open / Closed Principle**: Adding a new remote adapter (such as GCS or SSH) requires adding a new adapter class in `src/relay/adapters/`. The diff engine, CLI parser, and SQLite logic remain completely untouched.
- **Testability**: Because `compute_diff()` accepts simple manifest dictionaries and produces a `DiffPlan`, the diffing logic can be tested in milliseconds without touching disk or cloud networks.

---

## 3. State & Metadata Ledger (`.relay.db`)

Relay stores file metadata in a local SQLite database named `.relay.db` located at the root of a synchronized directory.

### SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    size INTEGER NOT NULL,
    mtime REAL NOT NULL,
    hash TEXT,
    crc32c TEXT,
    inode INTEGER
);

CREATE INDEX IF NOT EXISTS idx_hash ON files(hash);
CREATE INDEX IF NOT EXISTS idx_inode ON files(inode);
```

### Self-Healing Resolution
- **Auto-Initialization**: Opening a connection to `.relay.db` creates the file on disk if missing. `init_db()` runs `CREATE TABLE IF NOT EXISTS`, making local resolution self-healing and zero-setup.
- **Safe Upserts**: Relay uses `INSERT OR REPLACE INTO files` so that existing records are updated seamlessly on file modification without primary key collisions.
- **Relative POSIX Paths**: All stored paths are normalized relative POSIX paths (e.g. `data/train.csv`), ensuring ledgers can be directly compared across different machines and operating systems.

---

## 4. Cloud Filesystems vs. Local Database

A common architectural question is whether remote filesystems (such as Google Cloud Storage) need a remote `.relay.db`.

### Why GCS Does Not Need `.relay.db`
Google Cloud Storage natively acts as a metadata database. Every object stored in GCS automatically provides:
- `blob.name` (relative path)
- `blob.size` (file size in bytes)
- `blob.updated` (timestamp `mtime`)
- `blob.crc32c` (cryptographic checksum calculated automatically by Google)
- `blob.etag` / `blob.md5_hash`

When Relay targets GCS, the `GcsAdapter` fetches the bucket's object manifest directly via the GCS API. The diff engine then compares the remote manifest against the source manifest using cloud-native checksums (`crc32c`), eliminating the need to store or synchronize an external `.relay.db` file in the bucket.
