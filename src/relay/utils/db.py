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
    # 0|path    |TEXT   |0| |1
    # 1|size    |INTEGER|1| |0
    # 2|mtime   |INTEGER|1| |0
    # 3|hash    |TEXT   |0| |0
    # 4|dev     |INTEGER|0| |0
    # 5|inode   |INTEGER|0| |0
    # 6|crc32c  |TEXT   |0| |0

    # latest migrations
    if "dev" not in columns:
        db.execute("ALTER TABLE files ADD COLUMN dev INTEGER")
    if "inode" not in columns:
        db.execute("ALTER TABLE files ADD COLUMN inode INTEGER")
    if "crc32c" not in columns:
        db.execute("ALTER TABLE files ADD COLUMN crc32c TEXT")

    db.execute("CREATE INDEX IF NOT EXISTS idx_files_inode ON files(dev, inode)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_files_hash ON files(hash)")


def to_sqlite_int(val: int | None) -> int | None:
    """
    Normalizes large/unsigned 64-bit integers to signed 64-bit integers for SQLite.

    WHY THIS IS HERE:
      SQLite's INTEGER storage class is strictly signed 64-bit (-2^63 to 2^63 - 1).
      On Windows NTFS/ReFS, `os.stat().st_dev` (volume serial number) and
      `os.stat().st_ino` (file ID) can be unsigned 64-bit (or 128-bit) integers
      (e.g. st_dev=16449543437147204828). When passed directly to sqlite3, Python
      raises OverflowError: Python int too large to convert to SQLite INTEGER.
      We wrap the value into a signed 64-bit integer using two's complement,
      guaranteeing safe SQLite storage and 1-to-1 deterministic matching without
      requiring any schema alterations.
    """
    if val is None:
        return None
    val = val & 0xFFFFFFFFFFFFFFFF
    if val >= (1 << 63):
        val -= 1 << 64
    return val


def insert_db(
    db: Connection,
    path: str,
    dev: int | None,
    inode: int | None,
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
        INSERT OR REPLACE INTO files (path, dev, inode, size, mtime, hash, crc32c)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (path, to_sqlite_int(dev), to_sqlite_int(inode), size, mtime, hash, crc32c),
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


def fetch_all_db(db: Connection, use_crc: bool = False) -> list[tuple[str, str]]:
    """Fetch all (path, hash) or (path, crc32c) entries from the database."""
    col = "crc32c" if use_crc else "hash"
    return db.execute(f"SELECT path, COALESCE({col}, '') FROM files").fetchall()
