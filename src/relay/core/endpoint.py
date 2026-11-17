"""
Endpoint Parser and Model.

Parses CLI argument strings into structured Endpoint representations
(Local directories, GCS buckets, and SSH/GCP Workbench remotes).
"""

import contextlib
import os
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path


class EndPointType(Enum):
    LOCAL = auto()
    GCS = auto()
    SSH = auto()


@dataclass
class Endpoint:
    raw: str
    type: EndPointType
    path: str
    bucket: str | None = None
    zone: str | None = None
    instance: str | None = None
    host: str | None = None
    port: int | None = None
    user: str | None = None
    key_file: str | None = None
    flags: list[str] = field(default_factory=list)


def parse_endpoint(target: str) -> Endpoint:
    """
    Parses a user-supplied target string into a typed Endpoint.

    Supported formats:
      • GCS: 'gs://my-bucket/prefix', 'gcs://my-bucket/prefix', 'gcloud storage gs://...'
      • SSH/Workbench: 'ssh zone/instance/remote_path [--flags]'
      • Local: Windows paths ('C:\\Users\\data', 'D:/backup'), relative paths ('./src'),
        or POSIX absolute paths ('/var/data').

    WHY WE STRIP QUOTES AND SPACES:
      Windows PowerShell and CMD frequently enclose paths with spaces in quotes
      (e.g., '"C:\\Program Files\\app"'). We strip surrounding quotes first so
      pathlib and regex don't fail.
    """
    target = target.strip().strip("'\"")

    # 1. Google Cloud Storage ('gcs://', 'gs://', 'gcloud storage...')
    clean_target = re.sub(r"^(gcloud\s+storage\s+)?", "", target).strip()
    gcs_match = re.match(r"^(?:gcs|gs)://([^/]+)(?:/(.*))?$", clean_target)

    if gcs_match:
        bucket = gcs_match.group(1)
        raw_path = gcs_match.group(2) or ""
        # Normalizes any Windows backslashes in GCS paths to canonical forward slashes
        clean_path = raw_path.replace("\\", "/").strip("/")
        return Endpoint(
            raw=target, type=EndPointType.GCS, path=clean_path, bucket=bucket
        )

    # 2. GCP Workbench or SSH (ssh <zone>/<instance>/<remote_path> [--flags]
    #    or ssh [user@]host:port/remote_path [--flags])
    if target.startswith("ssh "):
        parts = target[4:].strip().split()
        uri_part = parts[0]
        extra_flags = parts[1:]

        port: int | None = None
        user: str | None = None
        key_file: str | None = None
        host: str | None = None

        i = 0
        while i < len(extra_flags):
            flag = extra_flags[i]
            if flag in ("-p", "--port") and i + 1 < len(extra_flags):
                with contextlib.suppress(ValueError):
                    port = int(extra_flags[i + 1])
                i += 2
            elif flag in ("-u", "--user") and i + 1 < len(extra_flags):
                user = extra_flags[i + 1]
                i += 2
            elif flag in ("-i", "--key", "--key-file") and i + 1 < len(extra_flags):
                key_file = extra_flags[i + 1]
                i += 2
            elif flag in ("-h", "--host") and i + 1 < len(extra_flags):
                host = extra_flags[i + 1]
                i += 2
            else:
                i += 1

        # Check for host:port/path (e.g. localhost:2222/home/jupyter/project)
        host_port_match = re.match(r"^(?:([^@]+)@)?([^/:]+):(\d+)/(.*)$", uri_part)
        if host_port_match:
            u, h, p, remote_path = host_port_match.groups()
            return Endpoint(
                raw=target,
                type=EndPointType.SSH,
                path=remote_path,
                host=host or h,
                port=port or int(p),
                user=user or u,
                key_file=key_file,
                flags=extra_flags,
            )

        # Format: zone/instance/path/to/dir
        pattern = r"^([^/]+)/([^/]+)/(.+)$"
        ssh_match = re.match(pattern, uri_part)
        if ssh_match:
            zone, instance, remote_path = ssh_match.groups()
            return Endpoint(
                raw=target,
                type=EndPointType.SSH,
                path=remote_path,
                zone=zone,
                instance=instance,
                host=host,
                port=port,
                user=user,
                key_file=key_file,
                flags=extra_flags,
            )

        return Endpoint(
            raw=target,
            type=EndPointType.SSH,
            path=uri_part,
            host=host,
            port=port,
            user=user,
            key_file=key_file,
            flags=extra_flags,
        )

    # 3. Local Filesystem (Windows, Linux, or macOS)
    # If running on non-Windows but parsing an explicit Windows drive path
    # (e.g. 'C:\data' in cross-platform unit tests)
    if os.name != "nt" and re.match(r"^[a-zA-Z]:[\\/]", target):
        return Endpoint(
            raw=target,
            type=EndPointType.LOCAL,
            path=target,
        )

    # Standard local path resolution: expands '~' home dir and turns into
    # a canonical absolute path
    return Endpoint(
        raw=target,
        type=EndPointType.LOCAL,
        path=str(Path(target).expanduser().resolve()),
    )
