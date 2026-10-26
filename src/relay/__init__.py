import os
import sqlite3
from fnmatch import fnmatch

from .shared import *


def init_db(db: sqlite3.Connection):
    db.execute("""
    CREATE TABLE IF NOT EXISTS files(
        path TEXT PRIMARY KEY,
        dev INTEGER,
        inode INTEGER,
        size INTEGER NOT NULL,
        mtime INTEGER NOT NULL,
        hash TEXT,
        crc32c TEXT
    )
    """)

    # Schema migration helper for existing databases
    columns = [col[1] for col in db.execute("PRAGMA table_info(files)").fetchall()]
    if "dev" not in columns:
        db.execute("ALTER TABLE files ADD COLUMN dev INTEGER")
    if "inode" not in columns:
        db.execute("ALTER TABLE files ADD COLUMN inode INTEGER")
    if "crc32c" not in columns:
        db.execute("ALTER TABLE files ADD COLUMN crc32c TEXT")

    db.execute("CREATE INDEX IF NOT EXISTS idx_files_inode ON files(dev, inode)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_files_hash ON files(hash)")


def main():
    db = sqlite3.connect(".relay.db")
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
    untracked = {}  # path -> os.stat_result

    # 2. Walk current filesystem
    for root, _, files in os.walk("."):
        for name in files:
            path = os.path.join(root, name)

            if IGNORED and any(fnmatch(path, pattern) for pattern in IGNORED):
                continue

            try:
                stat = os.stat(path)
            except OSError:
                continue

            seen_paths.add(path)

            if path in db_records:
                record = db_records[path]
                if record["size"] != stat.st_size or record["mtime"] != stat.st_mtime_ns:
                    file_hash, file_crc = calculate_hashes(path)
                    if record["hash"] == file_hash:
                        print(f"{RESET}unchanged content (mtime updated): {path}")
                    else:
                        print(f"{YELLOW}changed{RESET} {path}, size: {stat.st_size}, mtime: {stat.st_mtime_ns}")

                    db.execute(
                        "UPDATE files SET dev=?, inode=?, size=?, mtime=?, hash=?, crc32c=? WHERE path=?",
                        (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, file_hash, file_crc, path),
                    )
            else:
                untracked[path] = stat

    # 3. Detect vanished files
    vanished_paths = set(db_records.keys()) - seen_paths

    # 4. Move / Rename Detection
    matched_moves = []  # list of (old_path, new_path, hash, crc, stat, reason)

    # Phase 4A: Fast Inode Matching (O(1) - instant for Linux/POSIX)
    vanished_by_inode = {}
    for vp in vanished_paths:
        dev = db_records[vp]["dev"]
        ino = db_records[vp]["inode"]
        if dev is not None and ino is not None and ino > 0:
            vanished_by_inode.setdefault((dev, ino), []).append(vp)

    for new_path, stat in list(untracked.items()):
        dev = stat.st_dev
        ino = stat.st_ino
        if (dev, ino) in vanished_by_inode and vanished_by_inode[(dev, ino)]:
            old_path = vanished_by_inode[(dev, ino)].pop(0)
            vanished_paths.remove(old_path)
            del untracked[new_path]

            old_hash = db_records[old_path]["hash"]
            old_crc = db_records[old_path]["crc32c"]
            matched_moves.append((old_path, new_path, old_hash, old_crc, stat, "inode"))

    # Phase 4B: Hash Fallback Matching (for Windows / cross-fs / when inode didn't match)
    vanished_by_size = {}
    for vp in vanished_paths:
        size = db_records[vp]["size"]
        vanished_by_size.setdefault(size, []).append(vp)

    for new_path, stat in list(untracked.items()):
        cand_paths = vanished_by_size.get(stat.st_size, [])
        if not cand_paths:
            continue

        file_hash, file_crc = calculate_hashes(new_path)
        match_old = None
        for old_p in cand_paths:
            if db_records[old_p]["hash"] == file_hash:
                match_old = old_p
                break

        if match_old:
            cand_paths.remove(match_old)
            vanished_paths.remove(match_old)
            del untracked[new_path]
            matched_moves.append((match_old, new_path, file_hash, file_crc, stat, "hash"))

    # 5. Apply Moves to DB
    for old_path, new_path, f_hash, f_crc, stat, reason in matched_moves:
        print(f"{CYAN}moved ({reason}){RESET} {old_path} -> {new_path}")
        db.execute("DELETE FROM files WHERE path=?", (old_path,))
        db.execute(
            "INSERT INTO files (path, dev, inode, size, mtime, hash, crc32c) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (new_path, stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, f_hash, f_crc),
        )

    # 6. Apply genuine Brand-New Files
    for new_path, stat in untracked.items():
        file_hash, file_crc = calculate_hashes(new_path)
        print(f"{GREEN}new{RESET} {new_path}, hash: {file_hash[:12]}..., size: {stat.st_size}")
        db.execute(
            "INSERT INTO files (path, dev, inode, size, mtime, hash, crc32c) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (new_path, stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, file_hash, file_crc),
        )

    # 7. Apply genuine Deletions
    for old_path in vanished_paths:
        print(f"{RED}deleted{RESET} {old_path}")
        db.execute("DELETE FROM files WHERE path=?", (old_path,))

    db.commit()
    db.close()
