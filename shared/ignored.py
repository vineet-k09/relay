from pathlib import Path

IGNORE_FILE = Path(__file__).parent.parent / ".relayignore"

def load_ignored():
    with open(IGNORE_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]

IGNORED = load_ignored()