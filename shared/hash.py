import blake3
def calculate_hash(path):
    hasher = blake3.blake3()

    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)

    return hasher.hexdigest()