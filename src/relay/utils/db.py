from sqlite3 import Connection


def init_db(db: Connection) -> None:
    """Initialize the files table, apply schema migrations, and create indexes."""

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


def insert_db(
    db: Connection,
    path: str,
    dev: int,
    inode: int,
    size: int,
    mtime: int,
    hash: str,
    crc32c: str,
) -> None:
    """
    Insert a file's metadata into the database.

    Args:
        db (Connection): The SQLite database connection.
        path (str): The file's path.
        dev (int): The device ID containing the file.
        inode (int): The file's inode number.
        size (int): The file size in bytes.
        mtime (int): The file's modification timestamp.
        hash (str): The file's content hash.
        crc32c (str): The file's CRC32C checksum.
    """
    db.execute(
        """
        INSERT INTO files (path, dev, inode, size, mtime, hash, crc32c)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (path, dev, inode, size, mtime, hash, crc32c),
    )


def delete_path_db(db: Connection, path: str) -> None:
    """Delete a file's database entry by its path."""
    db.execute("DELETE FROM files WHERE path=?", (path,))


def update_path_db(db: Connection, old_path: str, new_path: str) -> None:
    """Rename a file's path in the database, preserving all metadata and hashes."""
    db.execute("UPDATE files SET path = ? WHERE path = ?", (new_path, old_path))


def copy_path_db(db: Connection, src_path: str, dst_path: str) -> None:
    """Clone an existing file's metadata to a new path directly in the database."""
    db.execute(
        """
        INSERT INTO files (path, dev, inode, size, mtime, hash, crc32c)
        SELECT ?, dev, inode, size, mtime, hash, crc32c
        FROM files WHERE path = ?
    """,
        (dst_path, src_path),
    )


def fetch_all_db(db: Connection) -> list[tuple[str, str]]:
    """Fetch all (path, hash) entries from the database."""
    return db.execute("SELECT path, hash FROM files").fetchall()
