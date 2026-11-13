import base64
import zlib

import blake3

try:
    import google_crc32c
    _HAS_GOOGLE_CRC32C = True
except ImportError:
    _HAS_GOOGLE_CRC32C = False


def calculate_hashes(path: str) -> tuple[str, str]:
    """
    Computes both BLAKE3 content hash and CRC32C checksum for a file.
    Uses google_crc32c (matching Google Cloud Storage base64 format) if available,
    falling back to zlib standard crc32 hex.
    """
    hasher = blake3.blake3()

    if _HAS_GOOGLE_CRC32C:
        crc_hasher = google_crc32c.Checksum()
        with open(path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                hasher.update(chunk)
                crc_hasher.update(chunk)
        crc_str = base64.b64encode(crc_hasher.digest()).decode("utf-8")
    else:
        crc = 0
        with open(path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                hasher.update(chunk)
                crc = zlib.crc32(chunk, crc)
        crc_str = f"{crc & 0xFFFFFFFF:08x}"

    return hasher.hexdigest(), crc_str


def calculate_hash(path: str) -> str:
    return calculate_hashes(path)[0]
