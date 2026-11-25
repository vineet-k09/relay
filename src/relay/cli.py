import argparse
import sqlite3
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

from relay.adapters import get_adapter
from relay.adapters.gcs import list_gcs_manifest
from relay.adapters.ssh import list_ssh_manifest
from relay.core.diff import compute_diff
from relay.core.endpoint import Endpoint, EndPointType, parse_endpoint
from relay.core.scanner import scan_local_dir
from relay.core.sync import SyncExecutor
from relay.shared.archive import create_zip_from_paths, extract_zip_safe
from relay.shared.print_diff import print_diff
from relay.shared.progress import spin
from relay.shared.styles import BLUE, CYAN, GREEN, RED, RESET, YELLOW
from relay.utils.db import delete_path_db, fetch_all_db


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
    zip_group = sync_parser.add_mutually_exclusive_group()
    zip_group.add_argument(
        "--zip",
        "-z",
        action="store_true",
        help=(
            "Bundle transfers into a temporary zip, transfer once, "
            "and unpack on destination"
        ),
    )
    zip_group.add_argument(
        "--zip-only",
        "-Z",
        action="store_true",
        help=(
            "Archive source files into a single .zip on destination without unpacking"
        ),
    )
    sync_parser.add_argument(
        "--unzip",
        "-u",
        action="store_true",
        help=(
            "Extract downloaded .zip archive(s) on local destination and remove the zip"
        ),
    )

    # relay status <target>
    status_parser = subparsers.add_parser(
        "status", help="Inspect and hash files for an environment target"
    )
    status_parser.add_argument(
        "target", help="Local directory, GCS uri, or SSH workbench"
    )

    return parser.parse_args()


def handle_zip_only(src: Endpoint, dst: Endpoint, args) -> None:
    """Packs a LOCAL source into a single .zip and uploads it without unpacking."""
    if src.type != EndPointType.LOCAL:
        raise ValueError("--zip-only (-Z) requires a LOCAL source directory.")

    src_db = None
    try:
        with spin(f"Scanning source ledger ({src.path})..."):
            src_db = scan_local_dir(src.path, verbose=False)
            rel_paths = [p for p, _ in fetch_all_db(src_db)]

        if not rel_paths:
            print(f"{YELLOW}[relay]{RESET} No files found to archive.")
            return

        if dst.path.lower().endswith(".zip"):
            if dst.type == EndPointType.LOCAL:
                dst_p = Path(dst.path)
                archive_name = dst_p.name
                dst_dir_path = str(dst_p.parent)
            else:
                norm = dst.path.replace("\\", "/").rstrip("/")
                if dst.type == EndPointType.GCS:
                    norm = norm.lstrip("/")
                archive_name = norm.rsplit("/", 1)[-1]
                dst_dir_path = norm.rsplit("/", 1)[0] if "/" in norm else ""
            dst_dir_ep = replace(dst, path=dst_dir_path)
        else:
            archive_name = f"{Path(src.path).name or 'relay_archive'}.zip"
            dst_dir_ep = dst

        print(
            f"\nArchiving {GREEN}{len(rel_paths)}{RESET} files into "
            f"{CYAN}{archive_name}{RESET} -> {YELLOW}{dst.raw}{RESET}"
        )
        if getattr(args, "dry_run", False):
            print("\n[dry-run] Dry run active. No archive created or transferred.")
            return

        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / archive_name
            with spin(f"Packing {len(rel_paths)} files into {archive_name}..."):
                create_zip_from_paths(Path(src.path), rel_paths, zip_path)

            temp_src_ep = Endpoint(raw=tmp_dir, type=EndPointType.LOCAL, path=tmp_dir)
            adapter = get_adapter(temp_src_ep, dst_dir_ep)
            with spin(f"Uploading {archive_name}..."):
                meta = adapter.transfer(archive_name)

        print(f"\n{GREEN}Archive uploaded:{RESET} {archive_name} ({meta.size} bytes)")
    finally:
        if getattr(args, "clean", False):
            cleanup_local_db(src_db, src.path)
        elif src_db is not None:
            src_db.close()


def handle_sync(args):
    src = parse_endpoint(args.source)
    dst = parse_endpoint(args.destination)
    zip_mode = getattr(args, "zip", False)
    zip_only = getattr(args, "zip_only", False)
    unzip_mode = getattr(args, "unzip", False)

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

    if zip_only:
        handle_zip_only(src, dst, args)
        return

    if unzip_mode and dst.type != EndPointType.LOCAL:
        raise ValueError(
            "--unzip (-u) requires a LOCAL destination directory; "
            "use --zip (-z) for remote unpacking."
        )

    is_checksum_needed = src.type in (
        EndPointType.GCS,
        EndPointType.SSH,
    ) or dst.type in (EndPointType.GCS, EndPointType.SSH)

    single_zip_target: str | None = None
    if (
        unzip_mode
        and src.type in (EndPointType.GCS, EndPointType.SSH)
        and src.path.lower().endswith(".zip")
    ):
        norm = src.path.replace("\\", "/").rstrip("/")
        if src.type == EndPointType.GCS:
            norm = norm.lstrip("/")
        single_zip_target = norm.rsplit("/", 1)[-1]
        parent_dir = norm.rsplit("/", 1)[0] if "/" in norm else ""
        src = replace(src, path=parent_dir)

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

        if single_zip_target is not None:
            src_rows = [(p, h) for p, h in src_rows if p == single_zip_target]

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
        executor = SyncExecutor(
            plan, dry_run=args.dry_run, delete=args.delete, zip_mode=zip_mode
        )
        stats = executor.execute(dst_db=dst_db, transport_adapter=adapter)

        if unzip_mode and not args.dry_run and stats.transferred > 0:
            for t in plan.transfers:
                if t.path.lower().endswith(".zip"):
                    zip_file = Path(dst.path) / t.path
                    if zip_file.is_file():
                        extracted = extract_zip_safe(zip_file, zip_file.parent)
                        zip_file.unlink()
                        if dst_db is not None:
                            delete_path_db(dst_db, t.path)
                            dst_db.commit()
                        print(
                            f"  • {CYAN}Extracted {len(extracted)} files{RESET} "
                            f"from {t.path} (removed temporary zip)"
                        )

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
