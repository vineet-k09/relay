"""
Lightweight terminal progress indicator.
Thread-safe, and ANSI compatible for Linux, macOS, and Windows.
"""

import sys
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import ClassVar

from relay.shared.styles import CYAN, GREEN, RESET


class Spinner:
    """
    Rotating background spinner for indeterminate tasks (hashing,
    scanning, GCS API).

    Runs on a daemon thread so it never blocks script termination on exception.
    """

    # Braille dots with ASCII fallback
    FRAMES: ClassVar[tuple[str, ...]] = (
        "⠋",
        "⠙",
        "⠹",
        "⠸",
        "⠼",
        "⠴",
        "⠦",
        "⠧",
        "⠇",
        "⠏",
    )

    def __init__(self, message: str = "Processing..."):
        self.message = message
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def _spin(self) -> None:
        idx = 0
        while not self._stop_event.is_set():
            char = self.FRAMES[idx % len(self.FRAMES)]
            # \r moves cursor to start; \033[K clears any old trailing text
            sys.stdout.write(f"\r{CYAN}{char}{RESET} {self.message}\033[K")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.08)

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self, success_message: str | None = None) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        if success_message:
            sys.stdout.write(f"\r{GREEN}✔{RESET} {success_message}\033[K\n")
        else:
            sys.stdout.write("\r\033[K")
        sys.stdout.flush()


@contextmanager
def spin(message: str, done_message: str | None = None) -> Generator[None]:
    """Context manager for clean `with spin('Hashing...'):` usage."""
    spinner = Spinner(message)
    spinner.start()
    try:
        yield
    finally:
        spinner.stop(done_message)


class ProgressBar:
    """
    Determinate progress bar for transfers with known totals (e.g. 5/20 files).
    Purely event-driven (no background thread required).
    """

    def __init__(self, total: int, prefix: str = "Transferring", width: int = 25):
        self.total = max(total, 1)
        self.current = 0
        self.prefix = prefix
        self.width = width

    def update(self, step: int = 1, item_name: str = "") -> None:
        self.current = min(self.current + step, self.total)
        ratio = self.current / self.total
        filled = int(self.width * ratio)
        bar = "█" * filled + "░" * (self.width - filled)
        pct = int(ratio * 100)

        # Truncate long item names so the bar doesn't wrap the terminal line
        truncated = (item_name[:30] + "...") if len(item_name) > 33 else item_name

        sys.stdout.write(
            f"\r{self.prefix} [{CYAN}{bar}{RESET}] {pct:>3}% "
            f"({self.current}/{self.total}) {truncated}\033[K"
        )
        sys.stdout.flush()

        if self.current >= self.total:
            sys.stdout.write("\n")
            sys.stdout.flush()
