"""
Archive and batch metadata helpers for zip-based transfers.

Uses Python's built-in zipfile module (zero external dependencies) to pack
and safely extract files across Local, GCS, and SSH environments.
"""

import zipfile
from collections.abc import Sequence
from pathlib import Path

from relay.adapters.base import FileMetaData
from relay.shared.hash import calculate_hashes


def create_zip_from_paths(root: Path, rel_paths: Sequence[str], zip_path: Path) -> Path:
    """Packs relative file paths from root into a deflated zip archive."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_path in rel_paths:
            clean_rel = rel_path.replace("\\", "/").lstrip("/")
            full_path = root / clean_rel
            if full_path.is_file():
                zf.write(full_path, arcname=clean_rel)
    return zip_path


def extract_zip_safe(zip_path: Path, target_dir: Path) -> list[str]:
    """
    Safely extracts a zip archive into target_dir (guarding against zip-slip).
    Returns the list of extracted relative file paths.
    """
    target_resolved = target_dir.resolve()
    target_resolved.mkdir(parents=True, exist_ok=True)
    extracted: list[str] = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            dest = (target_resolved / member.filename).resolve()
            if not dest.is_relative_to(target_resolved):
                raise ValueError(f"Unsafe path in zip archive: {member.filename}")
            zf.extract(member, target_resolved)
            if not member.is_dir():
                extracted.append(member.filename.replace("\\", "/"))

    return extracted


def collect_file_metadata(root: Path, rel_paths: Sequence[str]) -> list[FileMetaData]:
    """Stats and hashes a batch of local files under root."""
    results: list[FileMetaData] = []
    for rel_path in rel_paths:
        clean_rel = rel_path.replace("\\", "/").lstrip("/")
        local_file = root / clean_rel
        stat = local_file.stat()
        file_hash, file_crc = calculate_hashes(str(local_file))
        results.append(
            FileMetaData(
                path=rel_path,
                size=stat.st_size,
                mtime=stat.st_mtime_ns,
                dev=stat.st_dev,
                inode=stat.st_ino,
                blake3_hash=file_hash,
                crc32c=file_crc,
            )
        )
    return results
