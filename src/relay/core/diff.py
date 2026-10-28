"""
Queries the two src and dest databases and reports the differences.
Uses in-memory dictionary comparisons to avoid complex cross joins and
provide clear, testable categorization for moves, copies, and updates.
"""

import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

from ..utils.db import fetch_all_db

RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"


class Action(Enum):
    UNCHANGED = auto()
    MODIFIED = auto()
    ADDED = auto()
    MOVED = auto()
    COPIED = auto()
    DELETED = auto()


@dataclass(frozen=True)
class MoveItem:
    path: str
    origin_path: str
    hash: str


@dataclass(frozen=True)
class CopyItem:
    path: str
    origin_path: str
    hash: str


@dataclass(frozen=True)
class TransferItem:
    path: str
    hash: str
    is_new: bool  # True if ADDED, False if MODIFIED


@dataclass(frozen=True)
class DeleteItem:
    path: str
    hash: str


@dataclass(frozen=True)
class UnchangedItem:
    path: str
    hash: str


@dataclass
class DiffResult:
    action: Action
    path: str
    origin_path: str | None = None
    hash: str | None = None


@dataclass
class DiffPlan:
    moves: list[MoveItem] = field(default_factory=list)
    copies: list[CopyItem] = field(default_factory=list)
    transfers: list[TransferItem] = field(default_factory=list)
    deletions: list[DeleteItem] = field(default_factory=list)
    unchanged: list[UnchangedItem] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return (
            len(self.moves)
            + len(self.copies)
            + len(self.transfers)
            + len(self.deletions)
        )

    def to_results(self) -> list[DiffResult]:
        res = []
        for u in self.unchanged:
            res.append(DiffResult(Action.UNCHANGED, u.path, hash=u.hash))
        for m in self.moves:
            res.append(
                DiffResult(Action.MOVED, m.path, origin_path=m.origin_path, hash=m.hash)
            )
        for c in self.copies:
            res.append(
                DiffResult(
                    Action.COPIED, c.path, origin_path=c.origin_path, hash=c.hash
                )
            )
        for t in self.transfers:
            action = Action.ADDED if t.is_new else Action.MODIFIED
            res.append(DiffResult(action, t.path, hash=t.hash))
        for d in self.deletions:
            res.append(DiffResult(Action.DELETED, d.path, hash=d.hash))
        return res

    def __iter__(self):
        return iter(self.to_results())


def compute_diff(src_rows: list[tuple], dst_rows: list[tuple]) -> DiffPlan:
    # Each row is at least (path, hash, ...)
    src_by_path = {r[0]: r[1] for r in src_rows}
    dst_by_path = {r[0]: r[1] for r in dst_rows}

    src_by_hash = defaultdict(list)
    dst_by_hash = defaultdict(list)
    for r in src_rows:
        path, h = r[0], r[1]
        if h:
            src_by_hash[h].append(path)
    for r in dst_rows:
        path, h = r[0], r[1]
        if h:
            dst_by_hash[h].append(path)

    plan = DiffPlan()
    claimed_dst_path = set()

    # Pass 1: Compare files present in Source
    for path, h in src_by_path.items():
        if path in dst_by_path:
            dst_h = dst_by_path[path]
            if h == dst_h:
                plan.unchanged.append(UnchangedItem(path=path, hash=h))
            else:
                plan.transfers.append(TransferItem(path=path, hash=h, is_new=False))
            claimed_dst_path.add(path)
        else:
            candidates = [
                dp for dp in dst_by_hash.get(h, []) if dp not in claimed_dst_path
            ]
            if candidates:
                old_path = candidates[0]
                claimed_dst_path.add(old_path)
                if old_path not in src_by_path:
                    plan.moves.append(MoveItem(path=path, origin_path=old_path, hash=h))
                else:
                    plan.copies.append(
                        CopyItem(path=path, origin_path=old_path, hash=h)
                    )
            else:
                plan.transfers.append(TransferItem(path=path, hash=h, is_new=True))

    # Pass 2: Remaining dst files are orphans/deleted
    for path, h in dst_by_path.items():
        if path not in claimed_dst_path:
            plan.deletions.append(DeleteItem(path=path, hash=h))

    return plan


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m relay.core.diff <source_db> <dest_db>")
        sys.exit(1)

    source_arg = sys.argv[1]
    dest_arg = sys.argv[2]

    source_db = Path(source_arg).resolve()
    destination_db = Path(dest_arg).resolve()

    print(f"{GREEN}Source: {RESET}{source_db}")
    print(f"{RED}Destination: {RESET}{destination_db}")

    src = sqlite3.connect(source_db)
    dst = sqlite3.connect(destination_db)

    source_rows = fetch_all_db(src)
    dst_rows = fetch_all_db(dst)

    result = compute_diff(source_rows, dst_rows)

    from relay.shared.print_diff import print_diff

    print_diff(result)
