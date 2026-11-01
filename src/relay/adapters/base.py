from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class FileMetaData:
    path: str
    size: int
    mtime: int | None = None
    dev: int | None = None
    inode: int | None = None
    blake3_hash: str | None = None
    crc32c: str | None = None

class BaseAdapters(ABC):
    """
    Abstract base class for environment adapters (Local, GCS, SSH/Workbench).
    Provides methods for inspection, authentication, and file transfers.
    """

    def verify_auth(self) -> bool:
        """Verify authentication/connectivity for the endpoint."""
        return True

    def list_manifest(self) -> dict[str, FileMetaData]:
        """Fetch all files and their metadata from the endpoint."""
        raise NotImplementedError

    @abstractmethod
    def rename(self, old_path: str, new_path: str) -> None:
        """Rename/move a file on the destination endpoint."""
        raise NotImplementedError

    @abstractmethod
    def copy_local(self, origin_path: str, new_path: str) -> None:
        """Clone an existing file on the destination without network transfer."""
        raise NotImplementedError

    @abstractmethod
    def transfer(self, path: str) -> FileMetaData:
        """Transfer a new or modified file from source to destination."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, path: str) -> None:
        """Delete an orphaned file from the destination endpoint."""
        raise NotImplementedError
