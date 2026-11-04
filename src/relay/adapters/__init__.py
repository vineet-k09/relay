"""
Transport Adapter Registry & Factory.

This module resolves the correct transport adapter (Local, Windows, GCS)
based on the source and destination endpoints provided by the user.
"""

import os
import re

from relay.adapters.base import BaseAdapters, FileMetaData
from relay.adapters.gcs import GCSTransportAdapter
from relay.adapters.local import LocalTransportAdapter
from relay.adapters.windows import GCSWindowsTransportAdapter, WindowsTransportAdapter
from relay.core.endpoint import Endpoint, EndPointType


def _is_windows_context(src: Endpoint, dst: Endpoint) -> bool:
    """
    Determines if either endpoint or the host operating system is Windows.

    WHY THIS DETECTION EXISTS:
      1. Host Detection ('os.name == "nt"'):
         If running on native Windows, Local-to-Local and GCS-to-Local
         transfers should automatically use the Windows-hardened adapters
         to handle Windows file locking, read-only flags, and NTFS File IDs.
      2. Path Pattern Detection (Drive letters 'C:\\' or UNC paths '\\\\'):
         Allows explicit Windows path testing and remote/mounted drive
         recognition even in mixed test or bridge environments.
    """
    if os.name == "nt":
        return True

    for ep in (src, dst):
        raw = ep.raw or ep.path
        # Check for Windows drive letter ('C:\', 'D:/') or UNC path ('\\server')
        if bool(re.match(r"^[a-zA-Z]:[\\/]", raw)) or raw.startswith(r"\\"):
            return True
    return False


def get_adapter(src: Endpoint, dst: Endpoint) -> BaseAdapters:
    """
    Factory function to instantiate the proper transport adapter for the given
    endpoint pair.

    ROUTING MATRIX:
      • Local <-> Local on Windows: WindowsTransportAdapter
      • Local <-> Local on Linux/Mac: LocalTransportAdapter
      • Local <-> GCS on Windows: GCSWindowsTransportAdapter
      • Local <-> GCS on Linux/Mac: GCSTransportAdapter

    WHY A CENTRAL FACTORY FUNCTION?
      - The caller (CLI, DiffEngine, SyncExecutor) does not need to know any
        OS-specific or cloud-specific details. It simply calls 'get_adapter'
        and receives an object adhering to the 'BaseAdapters' interface.
    """
    is_windows = _is_windows_context(src, dst)

    # 1. Local-to-Local (or Windows-to-Windows)
    if src.type == EndPointType.LOCAL and dst.type == EndPointType.LOCAL:
        if is_windows:
            return WindowsTransportAdapter(src.path, dst.path)
        return LocalTransportAdapter(src.path, dst.path)

    # 2. Local-to-GCS or GCS-to-Local (or Windows-to-Bucket / Bucket-to-Windows)
    if (src.type == EndPointType.LOCAL and dst.type == EndPointType.GCS) or (
        src.type == EndPointType.GCS and dst.type == EndPointType.LOCAL
    ):
        if is_windows:
            return GCSWindowsTransportAdapter(src, dst)
        return GCSTransportAdapter(src, dst)

    raise NotImplementedError(
        f"Transport between {src.type.name} and {dst.type.name} "
        "is not implemented yet. Currently supported: LOCAL <-> LOCAL, LOCAL <-> GCS."
    )


__all__ = [
    "BaseAdapters",
    "FileMetaData",
    "GCSTransportAdapter",
    "GCSWindowsTransportAdapter",
    "LocalTransportAdapter",
    "WindowsTransportAdapter",
    "get_adapter",
]
