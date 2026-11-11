import io
import sys
import time

from relay.shared.progress import ProgressBar, Spinner, spin


def test_progress_bar_basic():
    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured
        bar = ProgressBar(total=2, prefix="Syncing")
        bar.update(1, "test_file.txt")
        bar.update(1, "done_file.txt")
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    assert "Syncing" in output
    assert "100%" in output
    assert "(2/2)" in output
    assert output.endswith("\n")


def test_progress_bar_long_filename():
    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured
        bar = ProgressBar(total=1)
        long_name = "a" * 50 + ".txt"
        bar.update(1, long_name)
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    assert "..." in output


def test_spinner_lifecycle():
    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured
        spinner = Spinner("Testing...")
        spinner.start()
        time.sleep(0.1)
        spinner.stop("All good")
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    assert "All good" in output


def test_spin_context_manager():
    captured = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured
        with spin("Working...", "Finished"):
            time.sleep(0.05)
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    assert "Finished" in output
