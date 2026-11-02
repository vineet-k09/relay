# Sandbox & Testing Guide 🧪

Relay includes an automated, self-contained sandbox generator (`scripts/reset_sandbox.py`) that sets up local test directories representing all primary synchronization scenarios. This provides an instant test harness for manual verification and automated integration testing.

---

## 1. Sandbox Scenarios

Running `make sandbox` creates `sandbox/source/` and `sandbox/dest/` with the following predefined state:

```
sandbox/
├── source/
│   ├── README.md               (UNCHANGED: identical content and hash)
│   ├── data/train.csv          (MODIFIED: different content from dest)
│   ├── data/eval.csv           (ADDED: exists only in source)
│   └── models/config.json      (MOVED: content matches old_config.json in dest)
└── dest/
    ├── README.md               (UNCHANGED)
    ├── data/train.csv          (MODIFIED)
    ├── old_config.json         (MOVED candidate)
    └── temp/scratch.log        (DELETED / ORPHAN: destination-only scratch file)
```

---

## 2. Step-by-Step Verification Walkthrough

### Step 1: Reset the Sandbox
Rebuild the test environment to its initial state at any time:
```bash
make sandbox
```

### Step 2: Test a Dry-Run
Preview planned actions in the diff table without modifying the filesystem:
```bash
uv run relay sync sandbox/source sandbox/dest --dry-run
```
Expected output:
- Identifies all 5 actions in the diff table.
- Recognizes `old_config.json` $\rightarrow$ `models/config.json` as a zero-network-transfer move.
- Marks `temp/scratch.log` as an untracked destination file, safe from deletion.

### Step 3: Perform Live Synchronization
Execute the planned changes:
```bash
uv run relay sync sandbox/source sandbox/dest
```
Relay transfers the new and modified files and renames `old_config.json` to `models/config.json` instantly.

### Step 4: Verify Idempotency
Run the synchronization command a second time immediately:
```bash
uv run relay sync sandbox/source sandbox/dest
```
Relay instantly reports:
```
✨ Everything is up to date. Zero changes needed.
```

### Step 5: Prune Orphan Destination Files
To remove files that only exist in the destination (`temp/scratch.log`), supply `--delete`:
```bash
uv run relay sync sandbox/source sandbox/dest --delete
```
Relay prompts for interactive confirmation before deleting:
```
Proceed with deletion and sync? [y/N]: y
```

### Step 6: Inspect Ledger Status
View indexed files and metadata in the local ledger:
```bash
uv run relay status sandbox/source
uv run relay status sandbox/dest
```

---

## 3. Running Relay as a Standalone Binary

You can execute Relay directly in your shell without prefixing commands with `uv run`:

### Option A: Activate Virtual Environment
```bash
source .venv/bin/activate
relay sync sandbox/source sandbox/dest --dry-run
```

### Option B: Install into uv Tool Path
```bash
uv tool install --editable .
relay --help
```

---

## 4. Quality Assurance Suite

Relay maintains automated tests, code formatting, and strict type checking:

```bash
# Run test suite
uv run pytest

# Lint and verify code style
uv run ruff check

# Format code automatically
uv run ruff format

# Type check with mypy
uv run mypy

# Run all checks via Makefile
make check
```
