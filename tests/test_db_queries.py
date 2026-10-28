import sqlite3
import unittest

from relay.core.diff import Action, compute_diff
from relay.shared.print_diff import print_diff


def create_mock_dbs():
    """Builds two in-memory sqlite dbs covering all 5 core sync
    scenarios."""
    src = sqlite3.connect(":memory:")
    dst = sqlite3.connect(":memory:")

    schema = """
    CREATE TABLE files (
        path TEXT PRIMARY KEY,
        hash TEXT,
        size INTEGER,
        mtime INTEGER
    );
    """
    src.execute(schema)
    dst.execute(schema)

    # 1. UNCHANGED
    src.execute("INSERT INTO files VALUES ('docs/readme.md', 'hash_111', 100, 1000)")
    dst.execute("INSERT INTO files VALUES ('docs/readme.md', 'hash_111', 100, 1000)")

    # 2. MODIFIED (same path, different hash)
    src.execute("INSERT INTO files VALUES ('src/main.py', 'hash_222_new', 250, 2000)")
    dst.execute("INSERT INTO files VALUES ('src/main.py', 'hash_222_old', 210, 1000)")

    # 3. MOVED / RENAMED (different path, same content hash)
    src.execute("INSERT INTO files VALUES ('src/core/utils.py', 'hash_333', 500, 1500)")
    dst.execute("INSERT INTO files VALUES ('src/old_utils.py', 'hash_333', 500, 900)")

    # 4. ADDED (only in source)
    src.execute("INSERT INTO files VALUES ('assets/logo.png', 'hash_444', 12000, 3000)")

    # 5. DELETED (only in dest)
    dst.execute("INSERT INTO files VALUES ('temp/cache.tmp', 'hash_555', 40, 500)")

    return src, dst


class TestDbQueries(unittest.TestCase):
    def test_mock_scenarios(self):
        src, dst = create_mock_dbs()
        source_rows = src.execute("SELECT path, hash FROM files").fetchall()
        dest_rows = dst.execute("SELECT path, hash FROM files").fetchall()

        plan = compute_diff(source_rows, dest_rows)
        print_diff(plan)

        # Typed DiffPlan property checks (No optional guards needed)
        self.assertEqual(len(plan.unchanged), 1)
        self.assertEqual(plan.unchanged[0].path, "docs/readme.md")

        self.assertEqual(len(plan.moves), 1)
        self.assertEqual(plan.moves[0].path, "src/core/utils.py")
        self.assertEqual(plan.moves[0].origin_path, "src/old_utils.py")

        self.assertEqual(len(plan.transfers), 2)
        transfers_by_path = {t.path: t for t in plan.transfers}
        self.assertFalse(transfers_by_path["src/main.py"].is_new)  # MODIFIED
        self.assertTrue(transfers_by_path["assets/logo.png"].is_new)  # ADDED

        self.assertEqual(len(plan.deletions), 1)
        self.assertEqual(plan.deletions[0].path, "temp/cache.tmp")

        # Backward compatible iterable checks
        res_by_path = {r.path: r for r in plan}
        self.assertEqual(res_by_path["docs/readme.md"].action, Action.UNCHANGED)
        self.assertEqual(res_by_path["src/main.py"].action, Action.MODIFIED)
        self.assertEqual(res_by_path["src/core/utils.py"].action, Action.MOVED)
        self.assertEqual(res_by_path["assets/logo.png"].action, Action.ADDED)
        self.assertEqual(res_by_path["temp/cache.tmp"].action, Action.DELETED)

    def test_db_helpers(self):
        from relay.utils.db import copy_path_db, init_db, insert_db, update_path_db

        db = sqlite3.connect(":memory:")
        init_db(db)
        insert_db(db, "orig.txt", 1, 2, 100, 1000, "hash_abc", "crc_123")

        # Test update_path_db preserves metadata
        update_path_db(db, "orig.txt", "renamed.txt")
        row = db.execute(
            "SELECT path, size, hash, crc32c FROM files WHERE path = 'renamed.txt'"
        ).fetchone()
        self.assertEqual(row, ("renamed.txt", 100, "hash_abc", "crc_123"))
        self.assertIsNone(
            db.execute("SELECT path FROM files WHERE path = 'orig.txt'").fetchone()
        )

        # Test copy_path_db clones metadata
        copy_path_db(db, "renamed.txt", "copied.txt")
        row_copy = db.execute(
            "SELECT path, size, hash, crc32c FROM files WHERE path = 'copied.txt'"
        ).fetchone()
        self.assertEqual(row_copy, ("copied.txt", 100, "hash_abc", "crc_123"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
