import argparse
import sys
from pathlib import Path

from relay.shared.styles import *
from relay.core.endpoint import parse_endpoint

def parse_args():
    parser = argparse.ArgumentParser(
        prog="relay",
        description="Seamless cross-env sync for Local, GCS, and Workbench"
    )
    subparsers=parser.add_subparsers(dest="command", required=True)

    # relay sync <src> <dest>
    sync_parser = subparsers.add_parser("sync", help="Sync files between paths")
    sync_parser.add_argument("source", help="Source path, GCS uri, or SSH workbench target")
    sync_parser.add_argument("destination", help="Destination path, GCS uri, or SSH workbench target")
    sync_parser.add_argument("--dry-run", "-n", action="store_true", help="Show changes without transferring")
    sync_parser.add_argument("--delete", "-d", action="store_true", help="Delete destination files not in source")

    # relay status <target>
    status_parser = subparsers.add_parser("status", help="Inspect and hash files for an environment target")
    status_parser.add_argument("target", help="Local directory, GCS uri, or SSH workbench")

    return parser.parse_args()

def handle_sync(args):
    source_raw = args.source
    dest_raw = args.destination

    print(f"{BLUE}[relay]{RESET} Resolving endpoints:")
    print(f"    Source: {YELLOW}{source_raw}{RESET}")
    print(f"    Destination:{YELLOW}{dest_raw}{RESET}")


    # 1. parse enpoints (import fro core.enpoints)
    src = parse_endpoint(source_raw)
    dst = parse_endpoint(dest_raw)

    # 2. verify auth
    # maybe let the environment handle this one

    # 3. compute diffs

    if args.dry_run:
        print("dry run")
        return

    # 4. execute

def handle_status(args):
    print(f"{BLUE}[relay]{RESET} Status check for\
        {args.target}")
        
    # Inspect ledger and manifest

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
        print(f"{RED}[error]{RESET} {e}",
        file=sys.stderr)
        sys.exit(1)
