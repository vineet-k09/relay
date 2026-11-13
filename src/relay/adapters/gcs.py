"""
Google Cloud Storage (GCS) Transport Adapter.

Handles synchronization between:
  1. Local -> GCS (Upload)
  2. GCS -> Local (Download)
  3. GCS -> GCS (Bucket-to-bucket copy/sync)

Key GCS Principles:
  - GCS does NOT have physical directories. Slashes '/' in object names create
    virtual folder hierarchies in the UI.
  - GCS computes CRC32C checksums automatically on upload and stores them in base64.
  - bucket.rename_blob() and bucket.copy_blob() are instant server-side operations
    costing 0 egress network bandwidth!
"""

import errno
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from google.cloud import storage  # type: ignore[import-untyped]
from google.oauth2.credentials import Credentials

from relay.adapters.base import BaseAdapters, FileMetaData
from relay.core.endpoint import Endpoint, EndPointType
from relay.shared.hash import calculate_hashes
from relay.shared.styles import BLUE, CYAN, RED, RESET, YELLOW


def configure_windows_proxy() -> None:
    """
    Auto-detects and configures corporate proxy from gcloud if running on Windows.

    WHY THIS EXISTS:
      In corporate enterprise environments (e.g. Vodafone / Zscaler), outbound HTTPS
      traffic is restricted and must pass through a forward proxy. While 'gcloud' CLI
      has the corporate proxy configured, Python's standard requests/urllib3 does not
      automatically discover it unless HTTPS_PROXY is set.

      IMPORTANT PROXY SCHEME NOTE:
      Always use 'http://' (never 'https://') for the proxy URL scheme, even for
      HTTPS_PROXY (e.g. 'http://proxy:8080'). Forward proxies expect an unencrypted
      HTTP CONNECT tunnel; giving 'https://' forces Python to attempt a TLS handshake
      directly with the proxy port, resulting in SSLEOFError.
    """
    if os.name != "nt":
        return

    if "HTTPS_PROXY" not in os.environ and "https_proxy" not in os.environ:
        try:
            gcloud_bin = shutil.which("gcloud") or "gcloud"
            addr = subprocess.check_output(
                [gcloud_bin, "config", "get-value", "proxy/address"],
                shell=True,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            port = subprocess.check_output(
                [gcloud_bin, "config", "get-value", "proxy/port"],
                shell=True,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()

            if (
                addr
                and port
                and addr not in ("(unset)", "")
                and port not in ("(unset)", "")
            ):
                proxy_url = f"http://{addr}:{port}"
                os.environ["HTTP_PROXY"] = proxy_url
                os.environ["HTTPS_PROXY"] = proxy_url
                print(f"{BLUE}[relay]{RESET} Corporate proxy configured: {proxy_url}")
        except Exception:
            pass


def get_gcloud_credentials() -> Credentials:
    """
    Retrieves Google Cloud credentials using 'gcloud auth print-access-token'.

    Automatically configures Windows corporate proxy before fetching credentials.
    """
    configure_windows_proxy()
    gcloud_bin = shutil.which("gcloud") or "gcloud"
    try:
        token = subprocess.check_output(
            [gcloud_bin, "auth", "print-access-token"],
            shell=(os.name == "nt"),
            text=True,
            stderr=subprocess.PIPE,
        ).strip()
        print(f"{BLUE}[relay]{RESET} Using gcloud credentials (active session).")
        return Credentials(token=token)
    except Exception as exc:
        print(
            f"{RED}[error]{RESET} Failed to retrieve Google Cloud token via 'gcloud'."
        )
        print(f"{YELLOW}[hint]{RESET} Make sure Google Cloud SDK is installed and run:")
        print(f"       {CYAN}gcloud auth login{RESET}")
        print(f"       {CYAN}gcloud auth application-default login{RESET}")
        raise SystemExit(1) from exc


def get_gcloud_project() -> str | None:
    """Retrieves active Google Cloud project ID from gcloud config."""
    try:
        gcloud_bin = shutil.which("gcloud") or "gcloud"
        project = subprocess.check_output(
            [gcloud_bin, "config", "get-value", "project"],
            shell=(os.name == "nt"),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if project and project not in ("(unset)", ""):
            return project
        return None
    except Exception:
        return None


def list_gcs_manifest(
    bucket_name: str, prefix: str | None = None
) -> list[tuple[str, str]]:
    """
    Fetches the list of all files and their CRC32C checksums from a GCS bucket.

    This replaces running a local disk scanner on GCS. GCS is already a database
    of metadata, so a single list_blobs() query returns all objects, sizes, and
    pre-computed checksums in ~1 second.

    Args:
        bucket_name: Name of the GCS bucket (without gs://).
        prefix: Optional folder/prefix path inside the bucket.

    Returns:
        A list of (relative_path, crc32c_hash) tuples, ready for compute_diff().
    """
    client = storage.Client(
        project=get_gcloud_project(), credentials=get_gcloud_credentials()
    )
    bucket = client.bucket(bucket_name)

    # Clean up prefix: remove leading/trailing slashes
    clean_prefix = (prefix or "").strip("/")
    # If prefix is "data", list_blobs(prefix="data/") restricts search to that folder
    list_prefix = f"{clean_prefix}/" if clean_prefix else None

    manifest: list[tuple[str, str]] = []
    blobs = bucket.list_blobs(prefix=list_prefix)

    for blob in blobs:
        # Ignore folder placeholder markers (keys ending with '/')
        if blob.name.endswith("/"):
            continue

        # Strip the prefix to get the clean relative path
        if clean_prefix and blob.name.startswith(f"{clean_prefix}/"):
            rel_path = blob.name[len(clean_prefix) + 1 :]
        else:
            rel_path = blob.name

        # GCS returns blob.crc32c as a base64 string, e.g. "yZRlqg=="
        crc = blob.crc32c or ""
        manifest.append((rel_path, crc))

    return manifest


class GCSTransportAdapter(BaseAdapters):
    """
    Adapter executing sync operations when GCS is an endpoint.

    Automatically handles directionality:
      - Upload mode (Local -> GCS): destination is bucket.
      - Download mode (GCS -> Local): destination is local filesystem.
    """

    def __init__(self, src: Endpoint, dst: Endpoint):
        """
        Initializes the adapter and determines upload vs. download direction.

        Args:
            src: Source endpoint (Local or GCS).
            dst: Destination endpoint (Local or GCS).
        """
        self.src = src
        self.dst = dst
        self.is_upload = src.type == EndPointType.LOCAL and dst.type == EndPointType.GCS
        self.is_download = (
            src.type == EndPointType.GCS and dst.type == EndPointType.LOCAL
        )

        self.client = storage.Client(
            project=get_gcloud_project(), credentials=get_gcloud_credentials()
        )

        if self.is_upload:
            # Upload: Source is Local directory, Destination is GCS bucket
            self.src_root = Path(src.path).resolve()
            self.bucket = self.client.bucket(dst.bucket or "")
            self.prefix = (dst.path or "").strip("/")
        elif self.is_download:
            # Download: Source is GCS bucket, Destination is Local directory
            self.bucket = self.client.bucket(src.bucket or "")
            self.prefix = (src.path or "").strip("/")
            self.dst_root = Path(dst.path).resolve()
        else:
            raise NotImplementedError(
                f"GCS transport between {src.type} and {dst.type} not supported."
            )

    def _to_gcs_blob_name(self, rel_path: str) -> str:
        """
        Combines bucket prefix with relative file path.
        Example: prefix='backup', rel_path='data/train.csv' -> 'backup/data/train.csv'

        WHY WE CONVERT BACKSLASHES ('\\') TO FORWARD SLASHES ('/'):
          - On Windows, file paths use backslashes (e.g., 'data\\train.csv').
          - Cloud object stores (GCS, S3) strictly use forward slashes ('/')
            to represent virtual folders.
          - If backslashes were sent directly, GCS would interpret 'data\\train.csv'
            as a flat filename with a backslash in its name instead of a folder.
        """
        clean_rel = rel_path.replace("\\", "/").lstrip("/")
        if self.prefix:
            clean_prefix = self.prefix.replace("\\", "/").strip("/")
            return f"{clean_prefix}/{clean_rel}"
        return clean_rel

    def rename(self, old_path: str, new_path: str) -> None:
        """
        Renames or moves a file on the destination.

        - If destination is GCS: Uses bucket.rename_blob() server-side
          (0 egress bytes!).
        - If destination is Local: Uses os.replace() directly on disk with fallback
          for cross-filesystem moves (e.g., Btrfs vs ext4, or Windows C: vs D:).
        """
        if self.is_upload:
            # Destination is GCS
            old_blob_name = self._to_gcs_blob_name(old_path)
            new_blob_name = self._to_gcs_blob_name(new_path)
            blob = self.bucket.blob(old_blob_name)
            if blob.exists():
                self.bucket.rename_blob(blob, new_blob_name)
        else:
            # Destination is Local
            src_file = self.dst_root / old_path
            dst_file = self.dst_root / new_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.replace(src_file, dst_file)
            except OSError as err:
                winerror = getattr(err, "winerror", None)
                if winerror == 17 or err.errno in (errno.EXDEV, 17):
                    shutil.move(str(src_file), str(dst_file))
                else:
                    raise

    def copy_local(self, origin_path: str, new_path: str) -> None:
        """
        Duplicates an existing destination file without network transfer.

        - If destination is GCS: Uses bucket.copy_blob() server-side (0 egress bytes!).
        - If destination is Local: Uses shutil.copy2().
        """
        if self.is_upload:
            # Destination is GCS
            src_blob_name = self._to_gcs_blob_name(origin_path)
            dst_blob_name = self._to_gcs_blob_name(new_path)
            blob = self.bucket.blob(src_blob_name)
            if blob.exists():
                self.bucket.copy_blob(blob, self.bucket, dst_blob_name)
        else:
            # Destination is Local
            src_file = self.dst_root / origin_path
            dst_file = self.dst_root / new_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)

    def transfer(self, path: str) -> FileMetaData:
        """
        Transfers a single file across the network (Upload or Download).

        - Upload (Local -> GCS): blob.upload_from_filename(local_path)
        - Download (GCS -> Local): blob.download_to_filename(local_path)
        """
        if self.is_upload:
            # Upload: Local file -> GCS blob
            local_file = self.src_root / path
            blob_name = self._to_gcs_blob_name(path)
            blob = self.bucket.blob(blob_name)

            blob.upload_from_filename(str(local_file))
            blob.reload()  # Refresh metadata (size, crc32c) after upload

            return FileMetaData(
                path=path,
                size=blob.size or local_file.stat().st_size,
                crc32c=blob.crc32c,
            )
        else:
            # Download: GCS blob -> Local file
            blob_name = self._to_gcs_blob_name(path)
            blob = self.bucket.blob(blob_name)

            dst_file = self.dst_root / path
            dst_file.parent.mkdir(parents=True, exist_ok=True)

            blob.download_to_filename(str(dst_file))
            stat = dst_file.stat()
            file_hash, file_crc = calculate_hashes(str(dst_file))

            return FileMetaData(
                path=path,
                size=stat.st_size,
                mtime=stat.st_mtime_ns,
                dev=stat.st_dev,
                inode=stat.st_ino,
                blake3_hash=file_hash,
                crc32c=file_crc,
            )

    def transfer_batch(
        self, paths: list[str], max_workers: int = 8
    ) -> list[FileMetaData]:
        """
        Clubs and parallelizes multiple file transfers using a thread pool.

        Instead of waiting sequentially for one network round-trip at a time,
        this streams multiple files concurrently across worker threads.

        Args:
            paths: List of relative paths to transfer.
            max_workers: Number of simultaneous upload/download worker threads.

        Returns:
            List of FileMetaData for all transferred files.
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
        Deletes an orphaned file from the destination.

        - If destination is GCS: blob.delete()
        - If destination is Local: os.unlink() / rmtree()
        """
        if self.is_upload:
            blob_name = self._to_gcs_blob_name(path)
            blob = self.bucket.blob(blob_name)
            if blob.exists():
                blob.delete()
        else:
            target = self.dst_root / path
            if target.is_file() or target.is_symlink():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)
