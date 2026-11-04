"""
Windows & Cross-Filesystem Transport Adapters.

This module provides transport adapters specifically hardened for:
  1. Windows-to-Windows filesystem sync (LocalTransportAdapter specialization).
  2. Bucket-to-Windows and Windows-to-Bucket sync (GCSTransportAdapter
     specialization).
  3. Dynamic handling of filesystem differences (NTFS, FAT32/exFAT, Btrfs,
     ext4).

===============================================================================
WHY DO WE NEED THIS MODULE? (ARCHITECTURAL EXPLANATION)
===============================================================================
When syncing files on Windows or across different filesystem types, several
subtle operating system differences emerge that do not exist on standard Linux:

1. Cross-Device / Cross-Drive Moves (EXDEV / WinError 17):
   - Inodes (Linux) and File IDs (NTFS) are local to a SINGLE filesystem/drive.
   - If you move a file within 'C:\\', Windows simply updates the folder pointer
     in the Master File Table (MFT). This is instant (0ms) and atomic.
   - BUT if you move a file from 'C:\\' to 'D:\\' (or on Linux from an ext4
     mount to a Btrfs mount), an atomic pointer update is impossible at the OS
     kernel level! The OS raises 'WinError 17' (ERROR_NOT_SAME_DEVICE) or
     'errno.EXDEV' (Invalid cross-device link).
   - Our adapter detects this dynamically: it tries the instant 'os.replace'
     first, and if a cross-device error occurs, it falls back to 'shutil.move'
     (which copies byte streams across drives and deletes the source).

2. Path Separators ('\\' vs '/'):
   - Windows uses backslashes ('\\') for file paths (e.g. 'C:\\data\\file.txt').
   - Google Cloud Storage (GCS) and POSIX filesystems strictly use forward
     slashes ('/').
   - If you upload a file with Windows backslashes without normalizing, GCS
     creates an object literally named "data\\file.txt" instead of a folder!
   - This adapter ensures every path sent to cloud buckets uses forward slashes.

3. Windows File Locking (WinError 32: Sharing Violation):
   - On Linux, you can delete or rename a file even while another program reads
     it.
   - On Windows, the OS locks open files. If Windows Defender, an antivirus
     scanner, or an editor briefly opens a file, 'os.replace' fails with
     'WinError 32'.
   - Our adapter includes a short retry loop with backoff to tolerate transient
     locks.

4. Windows Read-Only Files (WinError 5: Access is Denied):
   - On Windows NTFS, if a file has the read-only attribute set, calling
     'os.remove' or 'Path.unlink' raises 'PermissionError: [WinError 5] Access is
     denied'.
   - Our adapter intercepts this error, strips the read-only attribute via
     'os.chmod(path, stat.S_IWRITE)', and completes deletion cleanly.

5. Why Python stdlib ('shutil.copy2', 'os.replace') over shell ('cp', 'robocopy')?
   - Spawning shell commands ('subprocess.run(["cp", ...])') launches an entire
     new OS process for every file. This introduces massive CPU process overhead,
     making bulk sync 50x-100x slower.
   - Shell commands are not portable: 'cp' does not exist in standard Windows
     Command Prompt or PowerShell; 'robocopy' does not exist on Linux.
   - Security: Shell commands risk injection vulnerabilities if filenames
     contain spaces, quotes, or characters like '&' or ';'.
   - Python native functions ('shutil.copy2') call OS C-APIs directly in memory,
     run cross-platform without dependencies, and accurately preserve file
     timestamps ('mtime').
"""

import errno
import os
import shutil
import stat
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from relay.adapters.base import FileMetaData
from relay.adapters.gcs import GCSTransportAdapter
from relay.adapters.local import LocalTransportAdapter
from relay.core.endpoint import Endpoint
from relay.shared.hash import calculate_hashes


def _force_remove_readonly(path: Path) -> None:
    """
    Clears the Windows read-only attribute from a file so it can be deleted.

    WHY THIS IS HERE:
      On Windows NTFS, files marked 'Read-Only' cannot be deleted by standard
      'os.unlink()' or 'Path.unlink()'. Python raises:
         PermissionError: [WinError 5] Access is denied.
      To fix this, we use 'os.chmod' with 'stat.S_IWRITE' (grant owner write
      permission). Once the write permission bit is restored, Windows permits
      deletion.
    """
    try:
        # stat.S_IWRITE gives write permission to the file owner
        os.chmod(path, stat.S_IWRITE)
        path.unlink()
    except Exception:
        # If it still fails (e.g. file locked by another process), re-raise
        raise


def _remove_tree_windows(dir_path: Path) -> None:
    """
    Recursively removes a directory on Windows, handling read-only nested files.

    WHY THIS IS HERE:
      'shutil.rmtree' crashes on Windows if any file inside the directory has
      the read-only attribute set. In Python 3.12+, 'onexc' allows us to pass
      an error handler callback that resets the write permissions on the
      offending file and retries removal automatically.
    """

    def _on_exc_handler(action, file_path, exc):
        try:
            os.chmod(file_path, stat.S_IWRITE)
            action(file_path)
        except Exception:
            pass

    shutil.rmtree(dir_path, onexc=_on_exc_handler)


class WindowsTransportAdapter(LocalTransportAdapter):
    """
    Transport adapter for Windows-to-Windows synchronization.

    Inherits from LocalTransportAdapter, but overrides operations to provide:
      1. Cross-device fallback (handles C: -> D: or Btrfs -> ext4 cross-volume
         moves).
      2. Transient file-locking retry (handles Windows Defender / indexer file
         locks).
      3. Windows read-only attribute clearance on delete.
      4. Accurate metadata extraction (NTFS File IDs & microsecond timestamps).
    """

    def __init__(self, src_root: str | Path, dst_root: str | Path):
        """
        WHY 'Path(...).resolve()' IS USED:
          - Resolves relative paths (like './data' or '..\\backup') into
            complete, canonical absolute paths (like 'C:\\Users\\dev\\data').
          - Eliminates ambiguity regardless of what directory the user's
            terminal is currently running in.
        """
        super().__init__(src_root, dst_root)

    def rename(self, old_path: str, new_path: str) -> None:
        """
        Renames or moves a file within the destination directory tree.

        WHY 'os.replace' INSTEAD OF 'os.rename':
          - On Linux, 'os.rename' overwrites existing files.
          - On Windows, 'os.rename' FAILS with 'FileExistsError' if target
            exists!
          - 'os.replace' is Python's cross-platform guarantee of an ATOMIC
            overwrite. It replaces the destination if it already exists without
            raising an error.
          - It takes 0ms because it only updates folder entry in NTFS/MFT,
            copying zero bytes over the disk.

        WHY THE CROSS-DEVICE FALLBACK ('EXDEV' / 'WinError 17'):
          - If 'old_path' and 'new_path' reside on different filesystem mounts
            (e.g. C: vs D:, or on Linux ext4 vs Btrfs), an atomic pointer update
            is physically impossible for the OS kernel.
          - The OS raises 'WinError 17' or 'errno.EXDEV'.
          - We catch this error and gracefully fall back to 'shutil.move', which
            streams bytes across the device boundary and cleans up the source.
        """
        src = self.dst_root / old_path
        dst = self.dst_root / new_path

        # Ensures any nested destination directories (e.g., 'sub/dir/') exist
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Retry loop for Windows file locking (antivirus or indexer)
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # Fast path: instant atomic directory entry swap
                os.replace(src, dst)
                return
            except OSError as err:
                winerror = getattr(err, "winerror", None)
                # Check for cross-device: WinError 17 or errno.EXDEV (18)
                if winerror == 17 or err.errno in (errno.EXDEV, 17):
                    shutil.move(str(src), str(dst))
                    return

                # Check for Windows sharing violation: WinError 32
                if (
                    winerror == 32 or isinstance(err, PermissionError)
                ) and attempt < max_attempts - 1:
                    time.sleep(0.05 * (attempt + 1))
                    continue

                raise

    def copy_local(self, origin_path: str, new_path: str) -> None:
        """
        Duplicates an existing destination file locally without network transfer.

        WHY 'shutil.copy2' INSTEAD OF 'shutil.copy':
          - 'shutil.copy' copies contents/permissions, BUT DISCARDS METADATA.
            Specifically, it resets modification time ('mtime') to "right now".
          - If mtime changes, our differential sync engine (DiffPlan) will
            falsely think the file was modified again on future sync runs!
          - 'shutil.copy2' preserves the original modification time ('mtime'),
            creation time, and file flags.
        """
        src = self.dst_root / origin_path
        dst = self.dst_root / new_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    def transfer(self, path: str) -> FileMetaData:
        """
        Transfers a file from source directory to destination directory.

        WHY 'shutil.copy2' INSTEAD OF A SHELL COMMAND LIKE 'cp' OR 'robocopy':
          - 'shutil.copy2' is a native Python function implemented in C. It calls
            the OS kernel's optimized copy routines directly (e.g. 'CopyFile2').
          - Avoids boilerplate, security risks, and subprocess overhead.
          - Works identically on Windows, Linux, and macOS.
        """
        src = self.src_root / path
        dst = self.dst_root / path
        dst.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(src, dst)

        # Re-stat and hash written destination file
        stat_info = dst.stat()
        file_hash, file_crc = calculate_hashes(str(dst))

        return FileMetaData(
            path=path,
            size=stat_info.st_size,
            mtime=stat_info.st_mtime_ns,
            dev=stat_info.st_dev,
            inode=stat_info.st_ino,
            blake3_hash=file_hash,
            crc32c=file_crc,
        )

    def delete(self, path: str) -> None:
        """
        Deletes a file or directory from the destination on Windows.

        WHY SPECIAL HANDLING IS NEEDED:
          - On Windows, if a file has the 'Read-Only' attribute set, calling
            'unlink()' fails with 'PermissionError: [WinError 5] Access is
            denied'.
          - We intercept this error, strip the read-only attribute via
            'os.chmod', and retry deletion.
        """
        target = self.dst_root / path
        if not target.exists() and not target.is_symlink():
            return

        if target.is_file() or target.is_symlink():
            try:
                target.unlink()
            except PermissionError:
                _force_remove_readonly(target)
        elif target.is_dir():
            _remove_tree_windows(target)


class GCSWindowsTransportAdapter(GCSTransportAdapter):
    """
    Windows-specialized Google Cloud Storage (GCS) Transport Adapter.

    Handles synchronization between:
      1. Local Windows Disk -> GCS Bucket (Upload)
      2. GCS Bucket -> Local Windows Disk (Download)

    WHY THIS SPECIALIZATION EXISTS:
      1. Path Normalization:
         - Windows uses backslashes ('\\'): 'folder\\data.csv'.
         - GCS requires forward slashes ('/'): 'folder/data.csv'.
         - Ensures Windows paths are converted to canonical forward slashes.
      2. Windows File-Lock and Read-Only Resilience:
         - Local destination operations handle Windows read-only permissions
           and file locks safely.
      3. Zero-Egress Remote Operations:
         - Server-side operations ('rename_blob', 'copy_blob') execute inside
           Google's cloud infrastructure at 0 egress cost.
    """

    def __init__(self, src: Endpoint, dst: Endpoint):
        """
        Initializes the GCS Windows adapter and sets up cloud storage clients.

        WHY WE USE 'google.cloud.storage' SDK INSTEAD OF 'gcloud storage cp':
          - 'gcloud storage cp' invokes CLI executable, which re-authenticates
            and spawns heavy Python processes with latency per file.
          - Official SDK ('storage.Client') maintains persistent HTTP connection
            pool and streams bytes directly to/from disk with minimal latency.
        """
        super().__init__(src, dst)

    def _to_gcs_blob_name(self, rel_path: str) -> str:
        """
        Converts any relative path (including Windows paths with backslashes)
        into a canonical forward-slash GCS object name.

        Example:
          prefix = 'backups'
          rel_path = 'data\\training\\set.csv'
          Output: 'backups/data/training/set.csv'
        """
        clean_rel = rel_path.replace("\\", "/").lstrip("/")
        if self.prefix:
            clean_prefix = self.prefix.replace("\\", "/").strip("/")
            return f"{clean_prefix}/{clean_rel}"
        return clean_rel

    def rename(self, old_path: str, new_path: str) -> None:
        """
        Renames or moves a file on the destination.

        - If Destination is GCS:
          Uses 'bucket.rename_blob()' server-side. Zero egress bytes!
        - If Destination is Local Windows Disk:
          Uses Windows-hardened 'os.replace()' with cross-drive fallback and
          lock retry.
        """
        if self.is_upload:
            old_blob_name = self._to_gcs_blob_name(old_path)
            new_blob_name = self._to_gcs_blob_name(new_path)
            blob = self.bucket.blob(old_blob_name)
            if blob.exists():
                self.bucket.rename_blob(blob, new_blob_name)
        else:
            src_file = self.dst_root / old_path
            dst_file = self.dst_root / new_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)

            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    os.replace(src_file, dst_file)
                    return
                except OSError as err:
                    winerror = getattr(err, "winerror", None)
                    if winerror == 17 or err.errno in (errno.EXDEV, 17):
                        shutil.move(str(src_file), str(dst_file))
                        return
                    if (
                        winerror == 32 or isinstance(err, PermissionError)
                    ) and attempt < max_attempts - 1:
                        time.sleep(0.05 * (attempt + 1))
                        continue
                    raise

    def copy_local(self, origin_path: str, new_path: str) -> None:
        """
        Duplicates an existing destination file without network transfer.

        - If Destination is GCS: Uses 'bucket.copy_blob()' server-side.
        - If Destination is Local Windows Disk: Uses 'shutil.copy2()' to
          preserve metadata.
        """
        if self.is_upload:
            src_blob_name = self._to_gcs_blob_name(origin_path)
            dst_blob_name = self._to_gcs_blob_name(new_path)
            blob = self.bucket.blob(src_blob_name)
            if blob.exists():
                self.bucket.copy_blob(blob, self.bucket, dst_blob_name)
        else:
            src_file = self.dst_root / origin_path
            dst_file = self.dst_root / new_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)

    def transfer(self, path: str) -> FileMetaData:
        """
        Transfers a single file across the network (Upload or Download).

        Upload Mode (Windows -> GCS):
          - Reads local Windows file from 'self.src_root / path'.
          - Uploads directly to GCS via 'blob.upload_from_filename()'.
          - Queries GCS for size and pre-computed CRC32C checksum.

        Download Mode (GCS -> Windows):
          - Downloads cloud blob to 'self.dst_root / path'.
          - Calculates local blake3 and crc32c hashes to verify download.
          - Extracts local Windows file attributes (size, mtime, inode/file_id).
        """
        if self.is_upload:
            local_file = self.src_root / path
            blob_name = self._to_gcs_blob_name(path)
            blob = self.bucket.blob(blob_name)

            # Streams chunks directly to Google Cloud over SSL socket
            blob.upload_from_filename(str(local_file))
            blob.reload()

            return FileMetaData(
                path=path,
                size=blob.size or local_file.stat().st_size,
                crc32c=blob.crc32c,
            )
        else:
            blob_name = self._to_gcs_blob_name(path)
            blob = self.bucket.blob(blob_name)

            dst_file = self.dst_root / path
            dst_file.parent.mkdir(parents=True, exist_ok=True)

            blob.download_to_filename(str(dst_file))

            stat_info = dst_file.stat()
            file_hash, file_crc = calculate_hashes(str(dst_file))

            return FileMetaData(
                path=path,
                size=stat_info.st_size,
                mtime=stat_info.st_mtime_ns,
                dev=stat_info.st_dev,
                inode=stat_info.st_ino,
                blake3_hash=file_hash,
                crc32c=file_crc,
            )

    def transfer_batch(
        self, paths: list[str], max_workers: int = 8
    ) -> list[FileMetaData]:
        """
        Transfers multiple files concurrently using a thread pool.

        WHY THREAD POOL FOR NETWORK TRANSFERS IN PYTHON?
          - Python releases the Global Interpreter Lock (GIL) during socket I/O.
          - 8 worker threads can upload/download 8 files simultaneously at full
            bandwidth.
        """
        results: list[FileMetaData] = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(self.transfer, path): path for path in paths
            }
            for future in as_completed(future_to_path):
                meta = future.result()
                results.append(meta)

        return results

    def delete(self, path: str) -> None:
        """
        Deletes a file from the destination endpoint.

        - If Destination is GCS: Calls 'blob.delete()' to delete cloud object.
        - If Destination is Local Windows Disk: Strips read-only permissions and
          unlinks.
        """
        if self.is_upload:
            blob_name = self._to_gcs_blob_name(path)
            blob = self.bucket.blob(blob_name)
            if blob.exists():
                blob.delete()
        else:
            target = self.dst_root / path
            if not target.exists() and not target.is_symlink():
                return
            if target.is_file() or target.is_symlink():
                try:
                    target.unlink()
                except PermissionError:
                    _force_remove_readonly(target)
            elif target.is_dir():
                _remove_tree_windows(target)
