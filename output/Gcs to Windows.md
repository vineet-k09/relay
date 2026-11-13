```ps1
PS C:\Users\KushwahaV2\Downloads\relay\relay> gcloud config get-value proxy/address; gcloud config get-value proxy/port
voispac.voisindiaproxy.internal.vodafone.com
8080
```

```ps1
PS C:\Users\KushwahaV2\Downloads\relay\relay> $env:HTTP_PROXY = "http://voispac.voisindiaproxy.internal.vodafone.com:8080"
PS C:\Users\KushwahaV2\Downloads\relay\relay> $env:HTTPS_PROXY = "http://voispac.voisindiaproxy.internal.vodafone.com:8080"
```

```ps1
PS C:\Users\KushwahaV2\Downloads\relay\relay> sync
[temp_print] is this working?
[relay] Resolving endpoints:
    Source:      gcloud storage gs://vineetk/relay/ [GCS]
    Destination: . [LOCAL]
[temp_print] is_gcs_involved: True, src = EndPointType.GCS, dst = EndPointType.LOCAL
[temp_print] spin up src is gcp
⠇ Listing GCS bucket (gs://vineetk/relay)...
Fetched logged user token (258 characters).

ACTION       | PATH                           | ORIGIN / DETAIL
-----------------------------------------------------------------
ADDED        | .python-version                |
ADDED        | CONTEXT.md                     |
ADDED        | Local to GCS Output.md         |
ADDED        | Makefile                       |
ADDED        | QUICK_SUMMARY.md               |
ADDED        | README.md                      |
ADDED        | Scope.md                       |
ADDED        | Workbench Reference.md         |
ADDED        | assets/flow.png                |
ADDED        | dist/relay-0.1.0-py3-none-any.whl |
ADDED        | dist/relay-0.1.0.tar.gz        |
ADDED        | docs/README.md                 |
ADDED        | docs/architecture.md           |
ADDED        | docs/diff-engine.md            |
ADDED        | docs/iap-ssh-guide.md          |
ADDED        | docs/sandbox.md                |
ADDED        | docs/security-and-reversibility.md |
ADDED        | docs/transports.md             |
ADDED        | docs/windows-deployment.md     |
ADDED        | pyproject.toml                 |
ADDED        | relay.pyz                      |
ADDED        | relay.spec                     |
ADDED        | sandbox/dest/README.md         |
ADDED        | sandbox/dest/data/train.csv    |
ADDED        | sandbox/dest/old_config.json   |
ADDED        | sandbox/dest/temp/scratch.log  |
ADDED        | sandbox/source/README.md       |
ADDED        | sandbox/source/data/eval.csv   |
ADDED        | sandbox/source/data/train.csv  |
ADDED        | sandbox/source/models/config.json |
ADDED        | scripts/reset_sandbox.py       |
ADDED        | src/relay/.relayignore         |
ADDED        | src/relay/__init__.py          |
ADDED        | src/relay/__main__.py          |
ADDED        | src/relay/adapters/__init__.py |
ADDED        | src/relay/adapters/base.py     |
ADDED        | src/relay/adapters/gcs.py      |
ADDED        | src/relay/adapters/local.py    |
ADDED        | src/relay/adapters/windows.py  |
ADDED        | src/relay/cli.py               |
ADDED        | src/relay/core/diff.py         |
ADDED        | src/relay/core/endpoint.py     |
ADDED        | src/relay/core/scanner.py      |
ADDED        | src/relay/core/sync.py         |
ADDED        | src/relay/shared/__init__.py   |
ADDED        | src/relay/shared/hash.py       |
ADDED        | src/relay/shared/ignored.py    |
ADDED        | src/relay/shared/print_diff.py |
ADDED        | src/relay/shared/progress.py   |
ADDED        | src/relay/shared/styles.py     |
ADDED        | src/relay/utils/db.py          |
ADDED        | tests/test_db_queries.py       |
ADDED        | tests/test_gcs_adapter.py      |
ADDED        | tests/test_progress.py         |
ADDED        | tests/test_windows_adapter.py  |
ADDED        | uv.lock                        |
ADDED        | win_amd64_whl.zip              |

Fetched logged user token (258 characters).

Planned changes:
  • 57 to add
Syncing files [█████████████████████████] 100% (57/57) win_amd64_whl.zip

Sync completed successfully:
  • 57 transferred
```