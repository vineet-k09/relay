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
    flags: list[str] = field(default_factory=list)


def parse_endpoint(target: str) -> Endpoint:
    target = target.strip()

    # gcs ('gcs://', 'gs://', 'gcloud storage...')
    clean_target = re.sub(r"^(gcloud\s+storage\s+)?", "", target).strip()
    gcs_match = re.match(r"^(?:gcs|gs)://([^/]+)(?:/(.*))?$", clean_target)

    if gcs_match:
        bucket = gcs_match.group(1)
        path = gcs_match.group(2)
        return Endpoint(raw=target, type=EndPointType.GCS, path=path, bucket=bucket)
    # gcp workbench (ssh <zone>/<instance>/<remote_path> [--flags])
    if target.startswith("ssh "):
        parts = target[4:].strip().split()
        uri_part = parts[0]
        extra_flags = parts[1:]

        # format: zone/instance/path/to/dir
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
                flags=extra_flags,
            )

    # default to local path
    return Endpoint(
        raw=target,
        type=EndPointType.LOCAL,
        path=str(Path(target).expanduser().resolve()),
    )
