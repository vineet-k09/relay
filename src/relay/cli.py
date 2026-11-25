import argparse
import sqlite3
import sys
from pathlib import Path

from relay.adapters import get_adapter
from relay.adapters.gcs import list_gcs_manifest
from relay.adapters.ssh import list_ssh_manifest
from relay.core.diff import compute_diff
from relay.core.endpoint import EndPointType, parse_endpoint
from relay.core.scanner import scan_local_dir
from relay.core.sync import SyncExecutor
from relay.shared.print_diff import print_diff
from relay.shared.progress import spin
from relay.shared.styles import BLUE, RED, RESET, YELLOW
from relay.utils.db import fetch_all_db


def parse_args():
    parser = argparse.ArgumentParser(
        prog="relay",
        description="Seamless cross-env sync for Local, GCS, and Workbench",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # relay sync <src> <dest>
    sync_parser = subparsers.add_parser("sync", help="Sync files between paths")
    sync_parser.add_argument(
        "source", help="Source path, GCS uri, or SSH workbench target"
    )
    sync_parser.add_argument(
        "destination", help="Destination path, GCS uri, or SSH workbench target"
    )
    sync_parser.add_argument(
        "--dry-run", "-n", action="store_true", help="Show changes without transferring"
    )
    sync_parser.add_argument(
        "--delete",
        "-d",
        action="store_true",
        help="Delete destination files not in source",
    )
    # --c, --clean to delete .relay.db
    sync_parser.add_argument(
        "--clean",
        "-c",
        action="store_true",
        help="Remove local .relay.db files after sync finishes",
    )

    # relay status <target>
    status_parser = subparsers.add_parser(
        "status", help="Inspect and hash files for an environment target"
    )
    status_parser.add_argument(
        "target", help="Local directory, GCS uri, or SSH workbench"
    )

    return parser.parse_args()


def handle_sync(args):
    src = parse_endpoint(args.source)
    dst = parse_endpoint(args.destination)
    if (
        src.type == EndPointType.LOCAL
        and dst.type == EndPointType.LOCAL
        and src.path == dst.path
    ):
        print(f"{YELLOW}[relay]{RESET} Source and Destination paths are identical.")
        return
    print(f"{BLUE}[relay]{RESET} Resolving endpoints:")
    print(f"    Source:      {YELLOW}{src.raw}{RESET} [{src.type.name}]")
    print(f"    Destination: {YELLOW}{dst.raw}{RESET} [{dst.type.name}]")

    is_checksum_needed = src.type in (
        EndPointType.GCS,
        EndPointType.SSH,
    ) or dst.type in (EndPointType.GCS, EndPointType.SSH)

    src_db = None
    dst_db = None
    try:
        # 1. Fetch manifests / DB records
        if src.type == EndPointType.LOCAL:
            with spin(f"Scanning source ledger ({src.path})..."):
                src_db = scan_local_dir(src.path, verbose=False)
                src_rows = fetch_all_db(src_db, use_crc=is_checksum_needed)
        elif src.type == EndPointType.GCS:
            with spin(f"Listing GCS bucket (gs://{src.bucket}/{src.path})..."):
                src_db = None
                src_rows = list_gcs_manifest(src.bucket or "", src.path)
        elif src.type == EndPointType.SSH:
            with spin(f"Listing SSH remote ({src.path})..."):
                src_db = None
                src_rows = list_ssh_manifest(src)
        else:
            raise NotImplementedError(
                f"Remote source {src.type.name} is not implemented yet."
            )

        if dst.type == EndPointType.LOCAL:
            with spin(f"Scanning destination ledger ({dst.path})..."):
                dst_db = scan_local_dir(dst.path, verbose=False)
                dst_rows = fetch_all_db(dst_db, use_crc=is_checksum_needed)
        elif dst.type == EndPointType.GCS:
            with spin(f"Listing GCS bucket (gs://{dst.bucket}/{dst.path})..."):
                dst_db = None
                dst_rows = list_gcs_manifest(dst.bucket or "", dst.path)
        elif dst.type == EndPointType.SSH:
            with spin(f"Listing SSH remote ({dst.path})..."):
                dst_db = None
                dst_rows = list_ssh_manifest(dst)
        else:
            raise NotImplementedError(
                f"Remote destination {dst.type.name} is not implemented yet."
            )

        # 2. Compute DiffPlan
        plan = compute_diff(src_rows, dst_rows)

        # 3. Print the diff table
        print_diff(plan)

        # 4. Resolve transport adapter
        adapter = get_adapter(src, dst)

        # 5. Hand off to SyncExecutor (handles dry-run, prompt, and execution)
        executor = SyncExecutor(plan, dry_run=args.dry_run, delete=args.delete)
        executor.execute(dst_db=dst_db, transport_adapter=adapter)

    finally:
        if args.clean:
            if src.type == EndPointType.LOCAL:
                cleanup_local_db(src_db, src.path)
            if dst.type == EndPointType.LOCAL:
                cleanup_local_db(dst_db, dst.path)
        else:
            if src_db is not None:
                src_db.close()
            if dst_db is not None:
                dst_db.close()


def handle_status(args):
    """
    Inspect a target endpoint, scan files, and display current state.
    """
    endpoint = parse_endpoint(args.target)
    print(
        f"{BLUE}[relay]{RESET} Status check for: "
        f"{YELLOW}{endpoint.raw}{RESET} ({endpoint.type.name})"
    )

    if endpoint.type == EndPointType.LOCAL:
        db = scan_local_dir(endpoint.path, verbose=True)
        count = db.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        print(f"\n{BLUE}[ledger]{RESET} Tracked files in {endpoint.path}: {count}")
        db.close()
    elif endpoint.type == EndPointType.GCS:
        with spin(f"Listing gs://{endpoint.bucket}/{endpoint.path or ''}..."):
            rows = list_gcs_manifest(endpoint.bucket or "", endpoint.path)
        print(
            f"\n{BLUE}[gcs]{RESET} Tracked objects in "
            f"gs://{endpoint.bucket}/{endpoint.path or ''}: {len(rows)}"
        )
        for path, file_crc in rows:
            print(f"  • {path} [crc32c: {file_crc}]")
    elif endpoint.type == EndPointType.SSH:
        with spin(f"Listing SSH remote ({endpoint.path})..."):
            rows = list_ssh_manifest(endpoint)
        print(f"\n{BLUE}[ssh]{RESET} Tracked files on {endpoint.raw}: {len(rows)}")
        for path, file_crc in rows:
            print(f"  • {path} [crc32c: {file_crc}]")
    else:
        print(
            f"Remote status inspection for {endpoint.type.name} "
            "will be handled by adapters."
        )


def cleanup_local_db(db: sqlite3.Connection | None, root_path: str) -> None:
    """Close SQLite connection and delete .relay.db (and any journal sidecars)."""
    if db is not None:
        db.close()
    db_file = Path(root_path) / ".relay.db"
    for suffix in ("", "-wal", "-shm", "-journal"):
        Path(f"{db_file}{suffix}").unlink(missing_ok=True)


def main():
    try:
        args = parse_args()
        if args.command == "sync":
            handle_sync(args)
        elif args.command == "status":
            handle_status(args)

    except KeyboardInterrupt:
        print(f"\n{YELLOW}[relay]{RESET} Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"{RED}[error]{RESET} {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
