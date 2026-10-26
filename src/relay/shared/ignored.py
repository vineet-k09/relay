from pathlib import Path

from .styles import YELLOW

IGNORE_FILE = Path(__file__).parent.parent / ".relayignore"

def load_ignored():
    try:
        with open(IGNORE_FILE, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"{YELLOW}No .relayignore file found, consider creating one to prevent node_modules, .git files from tracking")

IGNORED = load_ignored()