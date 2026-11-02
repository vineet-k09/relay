"""
Filesystem scanner and state tracker.
Walks a target directory, compares file stat/hashes against the SQLite ledger,
detects modifications, moves, additions, and deletions, and updates the database.
"""

import os
import sqlite3
from collections.abc import Sequence
from fnmatch import fnmatch
from pathlib import Path

from relay.shared.hash import calculate_hashes
from relay.shared.ignored import IGNORED
from relay.shared.styles import CYAN, GREEN, RED, RESET, YELLOW
from relay.utils.db import delete_path_db, init_db, insert_db

DEFAULT_IGNORED = [
    ".relay.db*",
    ".relay_dest.db*",
    ".git*",
    "__pycache__*",
    "*.pyc",
    ".pytest_cache*",
    ".mypy_cache*",
    ".venv*",
]


def _is_ignored(rel_path: str, name: str, custom_ignored: Sequence[str] | None) -> bool:
    patterns = DEFAULT_IGNORED + list(custom_ignored or [])
    for pattern in patterns:
        if fnmatch(rel_path, pattern) or fnmatch(name, pattern):
            return True
    return False


def scan_local_dir(
    target_dir: str | Path = ".",
    db: sqlite3.Connection | None = None,
    db_path: str | Path | None = None,
    verbose: bool = True,
) -> sqlite3.Connection:
    """
    Scans a local directory and updates its SQLite metadata ledger (.relay.db).

    Args:
        target_dir: The directory to scan (defaults to current working directory).
        db: An existing SQLite connection. If None, connects to target_dir/.relay.db.
        db_path: Custom database file path (optional, used if db is None).
        verbose: If True, prints discovered changes (new, changed, moved, deleted).

    Returns:
        The active sqlite3.Connection with all changes committed.
    """
    target_path = Path(target_dir).resolve()
    target_path.mkdir(parents=True, exist_ok=True)

    if db is None:
        actual_db_file = Path(db_path) if db_path else (target_path / ".relay.db")
        db = sqlite3.connect(str(actual_db_file))

    init_db(db)

    # 1. Fetch previous state from DB
    cursor = db.execute("SELECT path, dev, inode, size, mtime, hash, crc32c FROM files")
    db_records = {
        row[0]: {
            "dev": row[1],
            "inode": row[2],
            "size": row[3],
            "mtime": row[4],
            "hash": row[5],
            "crc32c": row[6],
        }
        for row in cursor.fetchall()
    }

    seen_paths = set()
    untracked = {}  # rel_path -> (full_path, stat_result)

    # 2. Walk target directory
    for root, dirs, files in os.walk(target_path):
        # Prune ignored directories in-place for faster traversal
        dirs[:] = [
            d
            for d in dirs
            if not _is_ignored(
                (Path(root) / d).relative_to(target_path).as_posix(), d, IGNORED
            )
        ]

        for name in files:
            full_file = Path(root) / name
            rel_file = full_file.relative_to(target_path).as_posix()

            if _is_ignored(rel_file, name, IGNORED):
                continue

            try:
                stat = full_file.stat()
            except OSError:
                continue

            seen_paths.add(rel_file)

            if rel_file in db_records:
                record = db_records[rel_file]
                if (
                    record["size"] != stat.st_size
                    or record["mtime"] != stat.st_mtime_ns
                ):
                    file_hash, file_crc = calculate_hashes(str(full_file))
                    if record["hash"] == file_hash:
                        if verbose:
                            print(
                                f"{RESET}unchanged content (mtime updated): {rel_file}"
                            )
                    else:
                        if verbose:
                            print(
                                f"{YELLOW}changed{RESET} {rel_file}, "
                                f"size: {stat.st_size}, mtime: {stat.st_mtime_ns}"
                            )

                    insert_db(
                        db,
                        rel_file,
                        stat.st_dev,
                        stat.st_ino,
                        stat.st_size,
                        stat.st_mtime_ns,
                        file_hash,
                        file_crc,
                    )
            else:
                untracked[rel_file] = (full_file, stat)

    # 3. Detect vanished files
    vanished_paths = set(db_records.keys()) - seen_paths

    # 4. Move / Rename Detection
    matched_moves = []

    # Phase 4A: Fast Inode Matching (O(1) - instant for Linux/POSIX)
    vanished_by_inode: dict[tuple[int, int], list[str]] = {}
    for vp in vanished_paths:
        dev = db_records[vp]["dev"]
        ino = db_records[vp]["inode"]
        if dev is not None and ino is not None and ino > 0:
            vanished_by_inode.setdefault((dev, ino), []).append(vp)

    for new_path, (_full_file, stat) in list(untracked.items()):
        dev = stat.st_dev
        ino = stat.st_ino
        if vanished_by_inode.get((dev, ino)):
            old_path = vanished_by_inode[(dev, ino)].pop(0)
            vanished_paths.remove(old_path)
            del untracked[new_path]

            old_hash = db_records[old_path]["hash"]
            old_crc = db_records[old_path]["crc32c"]
            matched_moves.append((old_path, new_path, old_hash, old_crc, stat, "inode"))

    # Phase 4B: Hash Fallback Matching (when inode differs or cross-fs)
    vanished_by_size: dict[int, list[str]] = {}
    for vp in vanished_paths:
        size = db_records[vp]["size"]
        vanished_by_size.setdefault(size, []).append(vp)

    for new_path, (_full_file, stat) in list(untracked.items()):
        cand_paths = vanished_by_size.get(stat.st_size, [])
        if not cand_paths:
            continue

        file_hash, file_crc = calculate_hashes(str(_full_file))
        match_old = None
        for old_p in cand_paths:
            if db_records[old_p]["hash"] == file_hash:
                match_old = old_p
                break

        if match_old:
            cand_paths.remove(match_old)
            vanished_paths.remove(match_old)
            del untracked[new_path]
            matched_moves.append(
                (match_old, new_path, file_hash, file_crc, stat, "hash")
            )

    # 5. Apply Moves to DB
    for old_path, new_path, f_hash, f_crc, stat, reason in matched_moves:
        if verbose:
            print(f"{CYAN}moved ({reason}){RESET} {old_path} -> {new_path}")
        delete_path_db(db, old_path)
        insert_db(
            db,
            new_path,
            stat.st_dev,
            stat.st_ino,
            stat.st_size,
            stat.st_mtime_ns,
            f_hash,
            f_crc,
        )

    # 6. Apply genuine Brand-New Files
    for new_path, (full_file, stat) in untracked.items():
        file_hash, file_crc = calculate_hashes(str(full_file))
        if verbose:
            print(
                f"{GREEN}new{RESET} {new_path}, "
                f"hash: {file_hash[:12]}..., size: {stat.st_size}"
            )
        insert_db(
            db,
            new_path,
            stat.st_dev,
            stat.st_ino,
            stat.st_size,
            stat.st_mtime_ns,
            file_hash,
            file_crc,
        )

    # 7. Apply genuine Deletions
    for old_path in vanished_paths:
        if verbose:
            print(f"{RED}deleted{RESET} {old_path}")
        delete_path_db(db, old_path)

    db.commit()
    return db
