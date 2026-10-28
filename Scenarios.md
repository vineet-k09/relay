When comparing Source (S) and Destination (D), every entry falls into
one of these buckets:

| Scenario       │ Path Match?     │ Hash Match?     │ Action Required|
─────────────────┼─────────────────┼─────────────────┼─────────────────
UNCHANGED        │ S.path ==       │ S.hash ==       │ No transfer
                 │ D.path          │ D.hash          │ needed. Skip.
MODIFIED         │ S.path ==       │ S.hash !=       │ Overwrite
                │ D.path          │ D.hash          │ destination
                │                 │                 │ file with
                │                 │                 │ source file.
MOVED /        │ S.path !=       │ S.hash ==       │ Remote/local
RENAMED        │ D.path          │ D.hash (1-to-1) │ rename (mv or
                │                 │                 │ GCS copy_blob),
                │                 │                 │ 0 bytes
                │                 │                 │ transferred
                │                 │                 │ over wire.
COPIED / DUPED │ S.path is new   │ S.hash ==       │ Copy existing
                │                 │ D.hash (D.path  │ file on
                │                 │ still in S)     │ destination
                │                 │                 │ side directly.
ADDED (NEW)    │ S.path only     │ S.hash not      │ Upload / copy
                │                 │ anywhere in D   │ new file from
                │                 │                 │ source.
DELETED        │ D.path only     │ D.hash not      │ Delete from
(ORPHAN)       │                 │ claimed by move │ destination (if
                │                 │                 │ --delete is
                │                 │                 │ active).
GCS DIGEST     │ Matches on      │ hash (BLAKE3)   │ Fall back to
MATCH          │ crc32c          │ not present on  │ crc32c matching
                │                 │ GCS             │ when syncing
                │                 │                 │ with GCS.



Forward Operation (DiffPlan)                │ Inverse Operation (Rollback)               │ Data Loss Risk?
─────────────────────────────────────────────┼────────────────────────────────────────────┼────────────────────────────────────────────
MOVED(new_path, old_path)                   │ mv new_path -> old_path                    │ None (zero egress, instant rename)
COPIED(new_path, origin_path)               │ rm new_path                                │ None (safe deletion)
ADDED(path)                                 │ rm path                                    │ None (remove newly introduced file)
MODIFIED(path)                              │ Restore pre-sync file content              │ Needs Backup (file was overwritten)
DELETED(path)                               │ Restore deleted file content               │ Needs Trash (file was removed)