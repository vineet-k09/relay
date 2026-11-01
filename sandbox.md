  #### How to run it:
    # 1. Reset / recreate the sandbox anytime
    make sandbox

    # 2. Test a dry-run (preview changes without touching anything)
    uv run relay sync sandbox/source sandbox/dest --dry-run

    # 3. Perform live synchronization
    uv run relay sync sandbox/source sandbox/dest

    # 4. Run it again — notice it instantly says: "Everything is up to date"
    uv run relay sync sandbox/source sandbox/dest

    # 5. Prune orphan destination files using --delete
    uv run relay sync sandbox/source sandbox/dest --delete


  #### How to run relay directly as a shell binary (without uv run):

  You can install Relay in editable mode into your environment:

    # Option A: Activate the project venv
    source .venv/bin/activate
    relay sync sandbox/source sandbox/dest --dry-run

    # Option B: Install into uv's tool bin path
    uv tool install --editable .
    relay --help




 ### 3. Database Resolution & Cloud Filesystems (SOLID without Class Overkill)
  │ "how am i resolving if the db exists or not ... for other filesystems will i have to expand init_db or have a higher function ...
  │ kinda like SOLID principles - although i hate classes"

  #### Does init_db need to change?
  No, absolutely not.
  init_db(conn) obeys the Single Responsibility Principle: its only job is creating the SQLite tables and indexes on an open SQLite
  connection. It should not know anything about GCS, SSH, or network endpoints.
  #### How does local resolve if .relay.db exists?

  In SQLite, executing sqlite3.connect("/path/to/.relay.db") automatically creates the file on disk if it doesn't exist, and init_db()
  runs CREATE TABLE IF NOT EXISTS files (...). So local resolution is self-healing and zero-setup.

  #### How do remote filesystems (GCS, SSH) work?
  You do not need to create or store a .relay.db file inside a Google Cloud Storage bucket.

  Why? GCS is already a database of metadata.
  Every object stored in GCS natively has:
  • name (the relative path)
  • size (bytes)
  • updated (mtime timestamp)
  • crc32c (cryptographic checksum calculated automatically by Google)
  • etag / md5
  #### The Clean Architecture (Function-Based, No Class Bloat)

  You do not need heavy OOP or dozens of classes to follow SOLID. You just need pure functions with clean data boundaries:

    # High-level pipeline in handle_sync():

    # 1. Manifest Resolution (Pure I/O: Endpoint -> list of (path, hash))
    src_manifest = get_manifest(src_endpoint)
    dst_manifest = get_manifest(dst_endpoint)

    # 2. Diff Engine (Pure Domain Logic: No disk, No network, No I/O)
    diff_plan = compute_diff(src_manifest, dst_manifest)

    # 3. Execution (Pure I/O)
    executor.execute(dst_db, adapter)

  Where get_manifest is a simple dispatch function:

  • If endpoint.type == LOCAL: runs scan_local_dir(endpoint.path) and reads rows from .relay.db.
  • If endpoint.type == GCS: queries the GCS API bucket list and extracts [(blob.name, blob.crc32c), ...].
  • If endpoint.type == SSH: runs a lightweight command over SSH or uses an SFTP crawler.

  This gives you:

  1. Single Responsibility: init_db manages SQLite. compute_diff computes diffs. Adapters handle network/disk operations.
  2. Open / Closed: When you add GCS or SSH support, you write a new adapter file (src/relay/adapters/gcs.py). You do not touch diff.py,
  sync.py, or init_db.
  3. Simplicity: No class hierarchies, no convoluted abstractions—just pure functions transforming manifests into diff plans and
  delegating execution.