import blake3
import zlib

def calculate_hashes(path):
    hasher = blake3.blake3()
    crc = 0

    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)
            crc = zlib.crc32(chunk, crc)

    return hasher.hexdigest(), f"{crc & 0xffffffff:08x}"

def calculate_hash(path):
    return calculate_hashes(path)[0]
