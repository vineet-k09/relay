"""
Core implementation of how files are synchronized based on the DiffPlan.
Execution Order: Moves -> Copies -> Transfers (Added/Modified) -> Deletions (--delete)
"""

import sqlite3
from contextlib import nullcontext
from dataclasses import dataclass

from relay.adapters.base import BaseAdapters
from relay.core.diff import DiffPlan
from relay.shared.progress import ProgressBar
from relay.shared.styles import BLUE, CYAN, GREEN, RED, RESET, YELLOW
from relay.utils.db import copy_path_db, delete_path_db, insert_db, update_path_db


@dataclass
class SyncStats:
    transferred: int = 0
    moved: int = 0
    copied: int = 0
    deleted: int = 0
    skipped: int = 0


class SyncExecutor:
    def __init__(self, plan: DiffPlan, dry_run: bool = False, delete: bool = False):
        self.plan = plan
        self.dry_run = dry_run
        self.delete = delete
        self.stats = SyncStats()

    def confirm_plan(self) -> bool:
        """User review step before modifying destination or state."""
        if self.plan.total_changes == 0:
            print("\nEverything is up to date. Zero changes needed.")
            return False

        added_count = sum(1 for t in self.plan.transfers if t.is_new)
        modified_count = len(self.plan.transfers) - added_count
        moved_count = len(self.plan.moves)
        copied_count = len(self.plan.copies)
        deleted_count = len(self.plan.deletions)

        print("\nPlanned changes:")
        if added_count:
            print(f"  • {GREEN}{added_count} to add{RESET}")
        if modified_count:
            print(f"  • {YELLOW}{modified_count} to modify{RESET}")
        if moved_count:
            print(f"  • {CYAN}{moved_count} to move{RESET} (zero network transfer)")
        if copied_count:
            print(
                f"  • {BLUE}{copied_count} to duplicate locally{RESET} "
                "(zero network transfer)"
            )
        if self.delete and deleted_count:
            print(f"  • {RED}{deleted_count} to delete{RESET}")
        elif deleted_count:
            print(
                f"  • {YELLOW}{deleted_count} untracked on destination{RESET} "
                "(kept, use --delete to prune)"
            )

        if self.dry_run:
            print("\n[dry-run] Dry run active. No changes applied.")
            return False

        if deleted_count > 0 and self.delete:
            ans = input("\nProceed with deletion and sync? [y/N]: ").strip().lower()
            return ans in ("y", "yes")

        return True

    def execute(
        self, dst_db: sqlite3.Connection | None, transport_adapter: BaseAdapters
    ) -> SyncStats:
        """Executes operations in safe topological order and updates DB state."""
        if not self.confirm_plan():
            return self.stats

        db_context = dst_db if dst_db is not None else nullcontext()
        with db_context:
            # 1. MOVED: Rename on destination and update path in DB (if DB present)
            for move in self.plan.moves:
                transport_adapter.rename(move.origin_path, move.path)
                if dst_db is not None:
                    update_path_db(
                        dst_db, old_path=move.origin_path, new_path=move.path
                    )
                self.stats.moved += 1

            # 2. COPIED: Clone existing destination file locally
            for copy_item in self.plan.copies:
                transport_adapter.copy_local(copy_item.origin_path, copy_item.path)
                if dst_db is not None:
                    copy_path_db(
                        dst_db, src_path=copy_item.origin_path, dst_path=copy_item.path
                    )
                self.stats.copied += 1

            # 3. TRANSFERS: Added / Modified
            if self.plan.transfers:
                bar = ProgressBar(
                    total=len(self.plan.transfers), prefix="Syncing files"
                )
                for transfer in self.plan.transfers:
                    meta = transport_adapter.transfer(transfer.path)
                    if dst_db is not None:
                        insert_db(
                            dst_db,
                            path=transfer.path,
                            dev=meta.dev or 0,
                            inode=meta.inode or 0,
                            size=meta.size,
                            mtime=meta.mtime or 0,
                            hash=meta.blake3_hash or transfer.hash,
                            crc32c=meta.crc32c or "",
                        )
                    self.stats.transferred += 1
                    bar.update(item_name=transfer.path)

            # 4. DELETED: Prune if delete flag is set
            if self.delete and self.plan.deletions:
                del_bar = ProgressBar(
                    total=len(self.plan.deletions), prefix="Pruning files"
                )
                for deletion in self.plan.deletions:
                    transport_adapter.delete(deletion.path)
                    if dst_db is not None:
                        delete_path_db(dst_db, deletion.path)
                    self.stats.deleted += 1
                    del_bar.update(item_name=deletion.path)

        self.stats.skipped = len(self.plan.unchanged)

        print("\nSync completed successfully:")
        print(f"  • {GREEN}{self.stats.transferred} transferred{RESET}")
        if self.stats.moved:
            print(f"  • {CYAN}{self.stats.moved} moved{RESET}")
        if self.stats.copied:
            print(f"  • {BLUE}{self.stats.copied} copied{RESET}")
        if self.stats.deleted:
            print(f"  • {RED}{self.stats.deleted} deleted{RESET}")
        return self.stats
