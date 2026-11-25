"""
SSH / GCP Workbench Transport Adapter.

Handles bidirectional synchronization between:
  1. Local -> SSH / Workbench (Upload)
  2. SSH / Workbench -> Local (Download)

Uses native OpenSSH ('ssh' and 'scp') via standard subprocess without requiring
external dependencies (e.g. Paramiko/Cryptography), keeping Relay 100% portable
and offline-safe for corporate Windows environments.

Connects seamlessly to GCP Workbench instances via:
  - Identity-Aware Proxy (IAP) loopback tunnel (e.g. localhost:2222)
  - GCP OS Login username discovery (e.g. first_last_company_com)
  - Standard GCP compute keys (~/.ssh/google_compute_engine)
"""

import getpass
import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import NoReturn

from relay.adapters.base import BaseAdapters, FileMetaData
from relay.core.endpoint import Endpoint, EndPointType
from relay.shared.hash import calculate_hashes


def _raise_ssh_error(action: str, exc: subprocess.CalledProcessError) -> NoReturn:
    """Raises a clear RuntimeError including stderr/stdout from failed ssh/scp."""
    detail = (exc.stderr or exc.stdout or "").strip()
    raise RuntimeError(
        f"{action} failed (exit {exc.returncode}): {detail or exc}"
    ) from exc


def get_default_ssh_key() -> Path:
    """Finds the default GCP Compute Engine OpenSSH private key."""
    gcp_key = Path.home() / ".ssh" / "google_compute_engine"
    if gcp_key.exists():
        return gcp_key

    # Fallback to standard OpenSSH keys
    for name in ("id_ed25519", "id_rsa"):
        k = Path.home() / ".ssh" / name
        if k.exists():
            return k
    return gcp_key  # returns default even if missing, OpenSSH will report error


def get_os_login_user() -> str:
    """
    Attempts to discover GCP OS Login username (e.g. first_last_company_com).
    Falls back to current OS username if gcloud is unavailable.
    """
    gcloud_bin = shutil.which("gcloud")
    if gcloud_bin:
        try:
            account = subprocess.check_output(
                [gcloud_bin, "config", "get-value", "account"],
                shell=(os.name == "nt"),
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()

            if account and account != "(unset)":
                # GCP OS Login converts '.' and '@' into '_'
                return account.replace(".", "_").replace("@", "_")
        except Exception:
            pass

    # Fallback to local machine username
    return getpass.getuser()


def list_ssh_manifest(endpoint: Endpoint) -> list[tuple[str, str]]:
    """
    Fetches relative paths and CRC32C checksums from the remote SSH endpoint.

    Executes a fast remote Python one-liner on the Workbench instance that:
      1. Walks the remote directory (ignoring .git, __pycache__, etc.)
      2. Computes CRC32C (matching GCS and local Relay format)
      3. Outputs JSON array of [path, crc] tuples
    """
    host = endpoint.host or "127.0.0.1"
    port = endpoint.port or 2222
    user = endpoint.user or get_os_login_user()
    key_file = (
        Path(endpoint.key_file).expanduser()
        if endpoint.key_file
        else get_default_ssh_key()
    )
    remote_path = endpoint.path.replace("\\", "/").rstrip("/")

    # Embedded python script executed on the remote Workbench instance
    remote_script = (
        "import os, sys, json, base64\n"
        f"root = {json.dumps(remote_path)}\n"
        "results = []\n"
        "if os.path.exists(root):\n"
        "    for dirpath, dirnames, filenames in os.walk(root):\n"
        "        dirnames[:] = [\n"
        "            d for d in dirnames\n"
        "            if not d.startswith('.')\n"
        "            and d not in ('__pycache__', 'node_modules', '.venv')\n"
        "        ]\n"
        "        for f in filenames:\n"
        "            if f.startswith('.') or f.endswith('.pyc'):\n"
        "                continue\n"
        "            full_path = os.path.join(dirpath, f)\n"
        "            rel_path = os.path.relpath(full_path, root).replace('\\\\', '/')\n"
        "            try:\n"
        "                import google_crc32c\n"
        "                hasher = google_crc32c.Checksum()\n"
        "                with open(full_path, 'rb') as fp:\n"
        "                    while chunk := fp.read(65536):\n"
        "                        hasher.update(chunk)\n"
        "                crc = base64.b64encode(hasher.digest()).decode('utf-8')\n"
        "            except ImportError:\n"
        "                import zlib\n"
        "                c = 0\n"
        "                with open(full_path, 'rb') as fp:\n"
        "                    while chunk := fp.read(65536):\n"
        "                        c = zlib.crc32(chunk, c)\n"
        "                crc = f'{c & 0xFFFFFFFF:08x}'\n"
        "            results.append((rel_path, crc))\n"
        "print(json.dumps(results))\n"
    )

    cmd = [
        "ssh",
        "-p",
        str(port),
        "-i",
        str(key_file),
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        "BatchMode=yes",
        f"{user}@{host}",
        f"python3 -c {shlex.quote(remote_script)}",
    ]

    try:
        proc = subprocess.run(
            cmd,
            check=True,
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
        )
        items = json.loads(proc.stdout.strip())
        return [(item[0], item[1]) for item in items]
    except subprocess.CalledProcessError as exc:
        _raise_ssh_error("SSH manifest scan", exc)


class SSHTransportAdapter(BaseAdapters):
    """
    Adapter executing sync operations when SSH / Workbench is an endpoint.
    """

    def __init__(self, src: Endpoint, dst: Endpoint):
        self.src = src
        self.dst = dst
        self.is_upload = src.type == EndPointType.LOCAL and dst.type == EndPointType.SSH
        self.is_download = (
            src.type == EndPointType.SSH and dst.type == EndPointType.LOCAL
        )

        if not (self.is_upload or self.is_download):
            raise NotImplementedError(
                f"SSH transport between {src.type} and {dst.type} not supported."
            )

        self.ssh_ep = dst if self.is_upload else src
        self.local_ep = src if self.is_upload else dst

        # Paths
        self.local_root = Path(self.local_ep.path).resolve()
        # Ensure remote path uses forward slashes (Linux remote)
        self.remote_root = self.ssh_ep.path.replace("\\", "/").rstrip("/")

        # Connection settings: default to loopback IAP tunnel (localhost:2222)
        self.host = self.ssh_ep.host or "127.0.0.1"
        self.port = self.ssh_ep.port or 2222
        self.user = self.ssh_ep.user or get_os_login_user()
        self.key_file = (
            Path(self.ssh_ep.key_file).expanduser()
            if self.ssh_ep.key_file
            else get_default_ssh_key()
        )

    def _run_ssh(self, remote_command: str) -> subprocess.CompletedProcess[str]:
        """
        Executes a remote command via native OpenSSH.
        Uses BatchMode=yes to fail fast instead of hanging on password prompts.
        """
        cmd = [
            "ssh",
            "-p",
            str(self.port),
            "-i",
            str(self.key_file),
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "BatchMode=yes",
            f"{self.user}@{self.host}",
            remote_command,
        ]
        try:
            return subprocess.run(
                cmd,
                check=True,
                text=True,
                capture_output=True,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as exc:
            _raise_ssh_error("SSH command", exc)

    def _run_scp(
        self, src_path: str, dst_path: str
    ) -> subprocess.CompletedProcess[str]:
        """
        Transfers a file via native scp.
        NOTE: scp uses UPPERCASE '-P' for port (-p is reserved for preserving mtime).
        """
        cmd = [
            "scp",
            "-P",
            str(self.port),
            "-p",
            "-i",
            str(self.key_file),
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "BatchMode=yes",
            src_path,
            dst_path,
        ]
        try:
            return subprocess.run(
                cmd,
                check=True,
                text=True,
                capture_output=True,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as exc:
            _raise_ssh_error("SCP transfer", exc)

    def _to_remote_path(self, rel_path: str) -> str:
        """Normalizes Windows backslashes to Linux forward slashes."""
        clean = rel_path.replace("\\", "/").lstrip("/")
        return f"{self.remote_root}/{clean}" if self.remote_root else clean

    def rename(self, old_path: str, new_path: str) -> None:
        """
        Renames or moves a file on the destination (zero network egress).
        - If destination is SSH: runs remote 'mv' via ssh.
        - If destination is Local: uses os.replace with cross-filesystem fallback.
        """
        if self.is_upload:
            remote_old = self._to_remote_path(old_path)
            remote_new = self._to_remote_path(new_path)

            # Ensure target parent directory exists on remote VM
            remote_parent = str(Path(remote_new).parent).replace("\\", "/")
            cmd = (
                f"mkdir -p {shlex.quote(remote_parent)} && "
                f"mv {shlex.quote(remote_old)} {shlex.quote(remote_new)}"
            )
            self._run_ssh(cmd)
        else:
            # Destination is Local
            src_file = self.local_root / old_path
            dst_file = self.local_root / new_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.replace(src_file, dst_file)
            except OSError:
                shutil.move(str(src_file), str(dst_file))

    def copy_local(self, origin_path: str, new_path: str) -> None:
        """
        Duplicates an existing destination file without network transfer.
        - If destination is SSH: runs remote 'cp -p' via ssh (preserving mtime).
        - If destination is Local: uses shutil.copy2().
        """
        if self.is_upload:
            remote_orig = self._to_remote_path(origin_path)
            remote_new = self._to_remote_path(new_path)
            remote_parent = str(Path(remote_new).parent).replace("\\", "/")
            cmd = (
                f"mkdir -p {shlex.quote(remote_parent)} && "
                f"cp -p {shlex.quote(remote_orig)} {shlex.quote(remote_new)}"
            )
            self._run_ssh(cmd)
        else:
            src_file = self.local_root / origin_path
            dst_file = self.local_root / new_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)

    def delete(self, path: str) -> None:
        """Deletes an orphaned file or directory from the destination."""
        if self.is_upload:
            remote_target = self._to_remote_path(path)
            self._run_ssh(f"rm -rf {shlex.quote(remote_target)}")
        else:
            local_target = self.local_root / path
            if local_target.is_file() or local_target.is_symlink():
                local_target.unlink()
            elif local_target.is_dir():
                shutil.rmtree(local_target)

    def transfer(self, path: str) -> FileMetaData:
        """
        Transfers a single file across the network via native scp.
        - Upload (Local -> SSH): local file to remote host.
        - Download (SSH -> Local): remote file to local disk.
        """
        clean_path = path.replace("\\", "/")

        if self.is_upload:
            local_file = self.local_root / clean_path
            remote_dest = self._to_remote_path(clean_path)
            remote_parent = str(Path(remote_dest).parent).replace("\\", "/")

            # 1. Ensure remote parent directory exists before scp
            self._run_ssh(f"mkdir -p {shlex.quote(remote_parent)}")

            # 2. scp local_file user@host:remote_dest
            target = f"{self.user}@{self.host}:{remote_dest}"
            self._run_scp(str(local_file), target)

            stat = local_file.stat()
            file_hash, file_crc = calculate_hashes(str(local_file))
            return FileMetaData(
                path=path,
                size=stat.st_size,
                mtime=stat.st_mtime_ns,
                blake3_hash=file_hash,
                crc32c=file_crc,
            )
        else:
            # Download (SSH -> Local)
            local_file = self.local_root / clean_path
            local_file.parent.mkdir(parents=True, exist_ok=True)
            remote_src = self._to_remote_path(clean_path)

            # scp user@host:remote_src local_file
            source = f"{self.user}@{self.host}:{remote_src}"
            self._run_scp(source, str(local_file))

            stat = local_file.stat()
            file_hash, file_crc = calculate_hashes(str(local_file))
            return FileMetaData(
                path=path,
                size=stat.st_size,
                mtime=stat.st_mtime_ns,
                dev=stat.st_dev,
                inode=stat.st_ino,
                blake3_hash=file_hash,
                crc32c=file_crc,
            )
