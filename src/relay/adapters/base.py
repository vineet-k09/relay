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


class BaseAdapters:
    def verify_auth(self) -> bool:
        raise NotImplementedError

    def list_manifest(self) -> dict[str, FileMetaData]:
        raise NotImplementedError
