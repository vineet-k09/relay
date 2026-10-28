from sqlite3 import Connection

def init_db(db: Connection):
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
    # 0|path|TEXT|0||1
    # 1|size|INTEGER|1||0
    # 2|mtime|INTEGER|1||0
    # 3|hash|TEXT|0||0
    # 4|dev|INTEGER|0||0
    # 5|inode|INTEGER|0||0
    # 6|crc32c|TEXT|0||0
    # latest migrations
    
    if "dev" not in columns:
        db.execute("ALTER TABLE files ADD COLUMN dev INTEGER")
    if "inode" not in columns:
        db.execute("ALTER TABLE files ADD COLUMN inode INTEGER")
    if "crc32c" not in columns:
        db.execute("ALTER TABLE files ADD COLUMN crc32c TEXT")

    db.execute("CREATE INDEX IF NOT EXISTS idx_files_inode ON files(dev, inode)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_files_hash ON files(hash)")


def insert_db(db: Connection, path: str, dev: int, inode: int, size: int, mtime: int, hash: str, crc32c: str):
    db.execute(
            "INSERT INTO files (path, dev, inode, size, mtime, hash, crc32c) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (path, dev, inode, size, mtime, hash, crc32c)
    )

def delete_path_db(db: Connection, path: str):
    db.execute("DELETE FROM files WHERE path=?", (path,))