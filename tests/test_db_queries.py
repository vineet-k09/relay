from pathlib import Path
import sqlite3
import sys

RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

source_arg = sys.argv[1]
dest_arg = sys.argv[2]

source_db = Path(source_arg).resolve()
destnation_db = Path(dest_arg).resolve()

print(f"{GREEN}Source: {RESET}{source_db}")
print(f"{RED}Destination: {RESET}{destnation_db}")

src = sqlite3.connect(source_db)
dst = sqlite3.connect(destnation_db)

source_rows = src.execute("SELECT path, hash FROM files").fetchall()
dest_rows = dst.execute("SELECT path, hash FROM files").fetchall()

source_set = set(source_rows)
dest_set = set(dest_rows)

print(f"{GREEN}Only in source: ")
for row in sorted(source_set - dest_set):
    print(row)

print(f"\n{RED}Only in destination: ")
for row in sorted(dest_set - source_set):
    print(row)
print(f"{RESET}")

"""
import sqlite3
from pathlib import Path
import sys

source_path = Path(sys.argv[1]).resolve()
dest_path = Path(sys.argv[2]).resolve()

db = sqlite3.connect(":memory:")

db.execute("ATTACH DATABASE ? AS source", (str(source_path),))
db.execute("ATTACH DATABASE ? AS dest", (str(dest_path),))

rows = db.execute(""/"
    SELECT path, hash
    FROM source.files

    EXCEPT

    SELECT path, hash
    FROM dest.files
""/")

for row in rows:
    print("SOURCE ONLY:", row)
"""