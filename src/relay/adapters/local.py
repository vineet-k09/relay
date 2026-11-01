import os
import shutil
from pathlib import Path

from relay.adapters.base import BaseAdapters, FileMetaData
from relay.shared.hash import calculate_hashes

class LocalTransportAdapter(BaseAdapters):
    """
    Handles local-to-local filesystem transfers, copies, renames, and deletions.
    """

    def __init__(self, src_root: str | Path, dst_root: str | Path):
        self.src_root = Path(src_root).resolve()
        self.dst_root = Path(dst_root).resolve()

    def rename(self, old_path: str, new_path: str) -> None:
        src = self.dst_root / old_path
        dst = self.dst_root / new_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.replace(src, dst)

    def copy_local(self, origin_path: str, new_path: str) -> None:
        src = self.dst_root / origin_path
        dst = self.dst_root / new_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    def transfer(self, path: str) -> FileMetaData:
        src = self.src_root / path
        dst = self.dst_root / path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

        stat = dst.stat()
        file_hash, file_crc = calculate_hashes(str(dst))
        return FileMetaData(
            path=path,
            size=stat.st_size,
            mtime=stat.st_mtime_ns,
            dev=stat.st_dev,
            inode=stat.st_ino,
            blake3_hash=file_hash,
            crc32c=file_crc,
        )

    def delete(self, path: str) -> None:
        target = self.dst_root / path
        if target.is_file() or target.is_symlink():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
