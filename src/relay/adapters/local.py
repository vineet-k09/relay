import errno
import os
import shutil
from pathlib import Path

from relay.adapters.base import BaseAdapters, FileMetaData
from relay.shared.hash import calculate_hashes


class LocalTransportAdapter(BaseAdapters):
    """
    Handles local-to-local filesystem transfers, copies, renames, and deletions.

    Works across POSIX (Linux, macOS) and Windows local directories, dynamically
    handling filesystem differences (e.g., ext4 vs Btrfs mount points, NTFS, etc.).
    """

    def __init__(self, src_root: str | Path, dst_root: str | Path):
        # WHY Path(...).resolve():
        # Resolves any relative paths (e.g., './src', '../dest') into canonical,
        # absolute filesystem paths, ensuring safety against working-directory shifts.
        self.src_root = Path(src_root).resolve()
        self.dst_root = Path(dst_root).resolve()

    def rename(self, old_path: str, new_path: str) -> None:
        """
        Renames or moves a file within the destination environment.

        WHY os.replace INSTEAD OF os.rename:
          - On Linux, os.rename silently overwrites an existing file.
          - On Windows, os.rename crashes with FileExistsError if destination exists!
          - os.replace is Python's atomic, cross-platform overwrite guarantee.
          - It takes 0ms (instant inode/MFT pointer swap, 0 bytes moved over disk).

        WHY EXDEV / CROSS-FILESYSTEM FALLBACK (Btrfs vs ext4, or C: vs D:):
          - Moving across different filesystem partitions (e.g., ext4 mount to
            Btrfs mount) cannot be done via an atomic pointer change because each
            filesystem has its own independent inode ledger.
          - The OS kernel raises errno.EXDEV (Invalid cross-device link) or WinError 17.
          - We catch this error dynamically and fall back to shutil.move (copy bytes
            and delete source).
        """
        src = self.dst_root / old_path
        dst = self.dst_root / new_path
        dst.parent.mkdir(parents=True, exist_ok=True)

        try:
            os.replace(src, dst)
        except OSError as err:
            # Check for cross-device link (errno 18: EXDEV) or Windows cross-drive (17)
            winerror = getattr(err, "winerror", None)
            if err.errno in (errno.EXDEV, 17) or winerror == 17:
                shutil.move(str(src), str(dst))
            else:
                raise

    def copy_local(self, origin_path: str, new_path: str) -> None:
        """
        Clones an existing file on the destination without network transfer.

        WHY shutil.copy2 INSTEAD OF shutil.copy:
          - shutil.copy only copies file content, discarding mtime.
          - If mtime is updated to "now", our diff engine will falsely detect
            the file as modified!
          - shutil.copy2 preserves all file metadata (exact mtime, permissions, flags).
        """
        src = self.dst_root / origin_path
        dst = self.dst_root / new_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    def transfer(self, path: str) -> FileMetaData:
        """
        Copies a file from source to destination and extracts fresh metadata.

        WHY shutil.copy2 INSTEAD OF RUNNING 'cp' IN A SHELL:
          - 'cp' spawns an OS shell subprocess, creating severe process overhead
            for thousands of files.
          - 'cp' does not exist natively on Windows (unless inside Git Bash or WSL).
          - shutil.copy2 is a native C-speed Python standard library call that
            works universally.
        """
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
        """
        Deletes a file or directory from the destination.
        """
        target = self.dst_root / path
        if not target.exists() and not target.is_symlink():
            return

        if target.is_file() or target.is_symlink():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
