from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class FileMetaData:
    path: str
    size: int
    mtime: Optional[int] = None
    dev: Optional[int] = None
    inode: Optional[int] = None
    blake3_hash: Optional[str] = None
    crc32c: Optional[str] = None

class BaseAdapters:
    def verify_auth(self) -> bool:
        raise NotImplementedError

    def list_manifest(self) -> Dict[str, FileMetaData]:
        raise NotImplementedError
