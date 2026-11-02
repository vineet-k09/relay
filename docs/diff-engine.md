# Diff Engine & Sync Scenarios ⚖️

Relay’s diff engine (`src/relay/core/diff.py`) implements a content-addressable synchronization algorithm. Instead of blindly relying on timestamps (`mtime`) which can be altered or lost during network transfers, Relay matches files by path and cryptographic digest.

---

## 1. The 7 Diff Scenarios

When comparing Source ($S$) and Destination ($D$), every file candidate is classified into one of the following scenarios:

| Scenario | Path Match | Hash Match | Action Required | Egress Cost |
| :--- | :--- | :--- | :--- | :--- |
| **`UNCHANGED`** | $S.path == D.path$ | $S.hash == D.hash$ | **Skip** — already in sync. | 0 bytes |
| **`MODIFIED`** | $S.path == D.path$ | $S.hash \neq D.hash$ | **Overwrite** — transfer new source content over destination file. | Full file size |
| **`MOVED` / `RENAMED`** | $S.path \neq D.path$ | $S.hash == D.hash$ (1-to-1) | **Rename** — execute local/remote move (`os.replace`, GCS `rename_blob`, SSH `mv`). | **0 bytes** (zero transfer) |
| **`COPIED` / `DUPED`** | $S.path$ is new | $S.hash == D.hash$ ($D.path$ still in $S$) | **Local Duplicate** — copy file already existing on destination side directly. | **0 bytes** (zero transfer) |
| **`ADDED` (NEW)** | $S.path$ only | $S.hash$ not anywhere in $D$ | **Transfer** — upload or copy new file from source. | Full file size |
| **`DELETED` (ORPHAN)** | $D.path$ only | $D.hash$ not claimed by a move | **Delete** — remove orphan destination file (only executed when `--delete` flag is active). | 0 bytes |
| **`GCS DIGEST MATCH`** | Matches on `crc32c` | Local `hash` (BLAKE3) not on GCS | Fall back to `crc32c` matching when syncing with Google Cloud Storage. | 0 bytes |

---

## 2. Move & Rename Detection

Traditional sync utilities like `rsync` or `cp` often treat a renamed file as two separate operations:
1. Deleting the old file at destination.
2. Re-uploading the entire file to the new destination path across the network.

For large files (such as machine learning model weights, datasets, or video artifacts), this wastes significant network bandwidth and time.

Relay optimizes this using a two-tier approach:
1. **Inode Tracking (Local POSIX)**: If files share an inode on the same filesystem, Relay detects the move instantly before hashing.
2. **Hash-Addressable Matching (Cross-Device & Remote)**: Relay matches the content hash (BLAKE3 or CRC32c) of orphan destination files with newly added source files. When a match is found, Relay issues a zero-network-transfer `rename` operation on the destination environment.

---

## 3. Rollback & Safety Matrix

Relay categorizes each operation by its risk of data loss and defines its theoretical inverse operation:

| Forward Operation (`DiffPlan`) | Inverse Operation (Rollback) | Data Loss Risk? | Safety Mitigation |
| :--- | :--- | :--- | :--- |
| **`MOVED(new_path, old_path)`** | `mv new_path -> old_path` | **None** | Reversible; metadata operation only. |
| **`COPIED(new_path, origin_path)`**| `rm new_path` | **None** | Reversible; removes duplicated file. |
| **`ADDED(path)`** | `rm path` | **None** | Reversible; removes newly added file. |
| **`MODIFIED(path)`** | Restore pre-sync file content | ⚠️ **Needs Backup** | Destination file is overwritten with new content. |
| **`DELETED(path)`** | Restore deleted file content | ⚠️ **Needs Trash** | Destination file is permanently unlinked. |

---

## 4. Execution Safety Safeguards

### Dry-Run Mode (`--dry-run`)
Allows users to inspect the diff table without writing any files or mutating any metadata:
```bash
relay sync <source> <destination> --dry-run
```

### Protected Orphan Deletions (`--delete`)
By default, Relay never deletes destination files that are absent from the source. To remove orphaned files, the user must explicitly supply the `--delete` flag:
```bash
relay sync <source> <destination> --delete
```
When `--delete` is active, Relay displays an interactive confirmation prompt:
```
Proceed with deletion and sync? [y/N]:
```
Ensuring no files are deleted unintentionally.
