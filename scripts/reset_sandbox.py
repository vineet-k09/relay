#!/usr/bin/env python3
"""
Sets up a reproducible local sandbox to test Relay sync scenarios:
- UNCHANGED: File exists in both with identical hash.
- MODIFIED:  File exists in both with different content.
- MOVED:     File in destination has old name but matches source hash.
- ADDED:     File exists only in source.
- DELETED:   Orphan file exists only in destination.
"""

import shutil
import sys
from pathlib import Path

SANDBOX_DIR = Path("sandbox").resolve()
SRC_DIR = SANDBOX_DIR / "source"
DST_DIR = SANDBOX_DIR / "dest"


def create_sandbox():
    if SANDBOX_DIR.exists():
        print(f"Cleaning up existing {SANDBOX_DIR}...")
        shutil.rmtree(SANDBOX_DIR)

    # 1. Create directory structures
    (SRC_DIR / "data").mkdir(parents=True, exist_ok=True)
    (SRC_DIR / "models").mkdir(parents=True, exist_ok=True)
    (DST_DIR / "data").mkdir(parents=True, exist_ok=True)
    (DST_DIR / "temp").mkdir(parents=True, exist_ok=True)

    # 2. Populate Source files
    (SRC_DIR / "README.md").write_text("# Project Relay\nInitial documentation.\n")
    (SRC_DIR / "data" / "train.csv").write_text(
        "id,feature,label\n1,10.5,1\n2,20.2,0\n"
    )
    (SRC_DIR / "data" / "eval.csv").write_text("id,feature,label\n99,15.1,1\n")
    (SRC_DIR / "models" / "config.json").write_text(
        '{"learning_rate": 0.001, "epochs": 10}\n'
    )

    # 3. Populate Destination files to trigger diff scenarios
    # UNCHANGED: identical to source README.md
    (DST_DIR / "README.md").write_text("# Project Relay\nInitial documentation.\n")

    # MODIFIED: different content from source train.csv
    (DST_DIR / "data" / "train.csv").write_text("id,feature,label\n1,0.0,0\n")

    # MOVED: old location of config.json (identical content to models/config.json)
    (DST_DIR / "old_config.json").write_text('{"learning_rate": 0.001, "epochs": 10}\n')

    # DELETED / UNTRACKED: file only present in destination
    (DST_DIR / "temp" / "scratch.log").write_text("temporary run output\n")

    print("\n✅ Sandbox created successfully at ./sandbox/")
    print("\nFile structure:")
    print("  sandbox/source/")
    print("    ├── README.md               (will be: UNCHANGED)")
    print("    ├── data/train.csv          (will be: MODIFIED)")
    print("    ├── data/eval.csv           (will be: ADDED)")
    print("    └── models/config.json      (will be: MOVED from old_config.json)")
    print("  sandbox/dest/")
    print("    ├── README.md")
    print("    ├── data/train.csv")
    print("    ├── old_config.json")
    print(
        "    └── temp/scratch.log        (will be: UNTRACKED / DELETED with --delete)"
    )

    print("\nTry it with:")
    print("  uv run relay sync sandbox/source sandbox/dest --dry-run")
    print("  uv run relay sync sandbox/source sandbox/dest")
    print("  uv run relay status sandbox/source")
    print("  uv run relay status sandbox/dest")


if __name__ == "__main__":
    create_sandbox()
    sys.exit(0)
