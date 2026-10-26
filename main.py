import os
import sqlite3

from fnmatch import fnmatch

from shared.styles import *
from shared.hash import calculate_hash
from shared.ignored import IGNORED

db = sqlite3.connect(".metasync.db")

db.execute("""
CREATE TABLE IF NOT EXISTS files(
    path TEXT PRIMARY KEY,
    size INTEGER NOT NULL,
    mtime INTEGER NOT NULL,
    hash TEXT
)
""")

for root, dirs, files in os.walk("."):
    for name in files:
        path = os.path.join(root, name)

        if any(fnmatch(path, pattern) for pattern in IGNORED):
            continue

        stat = os.stat(path)
        file_size = stat.st_size
        file_mtime = stat.st_mtime_ns

        row = db.execute(
            "SELECT size, mtime, hash FROM files WHERE path=?",
            (path,)
        ).fetchone()

        if row is None:
            file_hash = calculate_hash(path)
            
            print(f"{GREEN}new{RESET} {path}, hash: {file_hash}, st_size: {file_size}, st_mtime_ns: {file_mtime}")

            db.execute(
                "INSERT INTO files VALUES(?,?,?,?)",
                (path, file_size, file_mtime, file_hash)
            )

        else:
            db_size, db_mtime, db_hash = row

            if (
                db_size != file_size
                or db_mtime != file_mtime
            ):
                
                file_hash = calculate_hash(path)
                if db_hash == file_hash:
                    print(f"{RESET} File hash match: {file_hash}")
                else:
                    print(f"{RED}changed{RESET} {path}, st_size: {file_size}, st_mtime_ns: {file_mtime}")

                db.execute(
                    "UPDATE files SET size=?, mtime=?, hash=? WHERE path=?",
                    (file_size, file_mtime, file_hash, path)
                )

db.commit()
db.close()