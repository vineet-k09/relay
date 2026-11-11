# Windows Deployment & Enterprise Execution Guide 🪟

This guide explains how to deploy and run **Relay** on Windows environments, with a particular focus on **locked-down corporate laptops** where internet `pip install` is blocked, unsigned `.exe` files risk triggering EDR alarms, and standard Linux-built artifacts cannot run.

---

## 1. Understanding the Constraints

When attempting to run Relay on a managed corporate Windows device, three distinct boundaries exist:

| Barrier | Corporate Reality | Why Past Attempts Failed |
| :--- | :--- | :--- |
| **Network Security (Proxy / Firewall)** | External access to PyPI (`pypi.org`) is blocked or SSL-inspected with custom root certificates. | `pip install <package>` fails with connection timeouts or SSL cert verification errors. |
| **Endpoint Detection & Response (EDR)** | Agents like CrowdStrike Falcon, Microsoft Defender ATP, or Carbon Black monitor new executables. | Unsigned `.exe` binaries compiled from PyInstaller dropped into `Downloads` may trigger security alerts. |
| **Binary Loader Architecture** | Native extensions (`cryptography`, `blake3`, `google-crc32c`) require platform-native machine code (`.pyd` / `.dll`). | A `zipapp` (`relay.pyz`) built on Linux contains ELF `.so` binaries. Moreover, Python's built-in `zipimport` engine **cannot** load native extensions from inside a zip file. |

> [!CAUTION]
> **Do not run `python relay.pyz status`!**  
> Running `python relay.pyz status` will fail with:  
> `ImportError: cannot import name 'exceptions' from 'cryptography.hazmat.bindings._rust'`  
> Python cannot load compiled C/Rust extensions from within a `.pyz` archive without unpacking them to disk.

---

## 2. Summary of Final Execution Commands

Depending on which deployment path you use, here are the exact commands to run Relay:

| Deployment Method | Recommended For | Final Execution Command |
| :--- | :--- | :--- |
| **Option 1: Offline Wheels** *(Recommended)* | Corporate Windows machines | `relay status <path>`<br>*(or `python -m relay.cli status <path>`)* |
| **Option 2: Zero-Pip Unpacked** | Corporate machines where `pip.exe` is banned | `$env:PYTHONPATH=".\deps;.\src"`<br>`python -m relay.cli status <path>` |
| **Option 3: GitHub Actions `.exe`** | Personal or unrestricted machines | `.\relay.exe status <path>` |

---

## 3. Option 1: Corporate-Safe Offline Wheelhouse (Recommended)

This method uses the **official, IT-approved Python interpreter** already present on your corporate machine. No suspicious `.exe` is executed, and no external network calls are made.

### Step 1: Download Windows binary wheels on Linux / Cloud Shell
On any Linux machine or Google Cloud Shell with unrestricted internet access:

```bash
# 1. Create a wheelhouse directory
mkdir -p windows_wheels

# 2. Download all required pre-compiled Windows x64 wheels from PyPI
uv run pip download \
  --platform win_amd64 \
  --only-binary=:all: \
  --python-version 3.12 \
  --dest ./windows_wheels \
  blake3 google-cloud-storage

# 3. Build Relay's pure-Python wheel
uv build
cp dist/*.whl ./windows_wheels/

# 4. Create a portable zip archive
zip -r windows_wheels.zip windows_wheels/
```

### Step 2: Transfer and Install on Corporate Windows
Transfer `windows_wheels.zip` to your Windows laptop (via USB, OneDrive, or approved transfer mechanism), extract the zip, and open PowerShell:

```powershell
# Install completely offline to user space (no admin rights, no network traffic)
python -m pip install --user --no-index --find-links .\windows_wheels relay
```

### Step 3: Run Relay
Once installed, execute Relay as a native CLI tool:

```powershell
# Check status of a local directory
relay status C:\path\to\folder

# Sync local files to a Google Cloud Storage bucket
relay sync C:\local\data gs://my-bucket/path

# Preview changes without transferring (dry-run)
relay sync C:\local\data gs://my-bucket/path --dry-run
```

*(If `relay` is not in your current system `PATH`, run via Python module invocation:)*
```powershell
python -m relay.cli status C:\path\to\folder
```

---

## 4. Option 2: Zero-Pip Unpacked Fallback (If `pip` is Completely Disabled)

If your enterprise security policy prevents executing `pip` altogether, you can unpack the wheels manually because wheel files (`.whl`) are standard `.zip` archives.

```powershell
# 1. Extract all wheels into a local dependency folder named 'deps'
Get-ChildItem .\windows_wheels\*.whl | ForEach-Object { 
    Expand-Archive $_.FullName -DestinationPath .\deps -Force 
}

# 2. Point Python's search path to deps and Relay source
$env:PYTHONPATH = ".\deps;.\src"

# 3. Run Relay using the corporate-approved python.exe
python -m relay.cli status C:\path\to\folder
python -m relay.cli sync C:\local\folder gs://my-bucket/folder
```

---

## 5. Option 3: GitHub Actions Standalone Executable (`relay.exe`)

For personal machines or environments where running standalone binaries is permitted, GitHub Actions automatically compiles `relay.exe` on clean Microsoft Windows virtual machines.

### How It Works
The workflow `.github/workflows/ci.yml` contains:
* **Matrix Testing**: Validates tests on both `ubuntu-latest` and `windows-latest`.
* **Automated Packaging (`build-windows` job)**:
  1. Spins up a `windows-latest` cloud runner.
  2. Runs `uv sync --all-groups` to install dependencies.
  3. Executes `uv run pyinstaller relay.spec` to bundle the Python runtime, Windows `.pyd` binaries, and Relay into a single file.
  4. Publishes `dist/relay.exe` as a GitHub Actions artifact named `relay-windows-x64`.

### How to Download & Run
1. Go to your repository on GitHub: `https://github.com/vineet-k09/relay/actions`.
2. Click on the latest workflow run.
3. Under **Artifacts** at the bottom of the page, download **`relay-windows-x64`**.
4. Extract `relay.exe` and execute directly in PowerShell:
   ```powershell
   .\relay.exe --help
   .\relay.exe status C:\path\to\folder
   .\relay.exe sync C:\path\to\source gs://my-bucket/target
   ```



# last run
```ps1
PS C:\Users\KushwahaV2\Downloads\relay\relay> python -m relay.cli sync "gcloud storage gs://vineetk/relay/" . --dry-run
[relay] Resolving endpoints:
    Source:      gcloud storage gs://vineetk/relay/ [GCS]
    Destination: . [LOCAL]
[error] Your default credentials were not found. To set up Application Default Credentials, see https://cloud.google.com/docs/authentication/external/set-up-adc for more information.
PS C:\Users\KushwahaV2\Downloads\relay\relay> python -m relay.cli sync "gcloud storage gc://vineetk/relay/" . --dry-run
[relay] Resolving endpoints:
    Source:      gcloud storage gc://vineetk/relay/ [LOCAL]
    Destination: . [LOCAL]
[error] [WinError 123] The filename, directory name, or volume label syntax is incorrect: 'C:\\Users\\KushwahaV2\\Downloads\\relay\\relay\\gcloud storage gc:\\vineetk\\relay'
PS C:\Users\KushwahaV2\Downloads\relay\relay> python -m relay.cli sync "gcloud storage gs://vineetk/relay/" . --dry-run
[relay] Resolving endpoints:
    Source:      gcloud storage gs://vineetk/relay/ [GCS]
    Destination: . [LOCAL]
[error] Your default credentials were not found. To set up Application Default Credentials, see https://cloud.google.com/docs/authentication/external/set-up-adc for more information.
PS C:\Users\KushwahaV2\Downloads\relay\relay> gcloud auth application-default login
Your browser has been opened to visit:

    https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com&redirect_uri=http%3A%2F%2Flocalhost%3A8085%2F&scope=openid+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.email+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcloud-platform+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fsqlservice.login&state=ty2ebmc7UDbpC2mXpNvlfyJDeeq1QH&access_type=offline&code_challenge=r8EnKojzMHY_KNsBEStjSn0Ay6gcagvs6-lSKCVK5l8&code_challenge_method=S256

ERROR: There was a problem with web authentication. Try running again with --no-browser.
ERROR: (gcloud.auth.application-default.login) Could not reach the login server. A potential cause of this could be because you are behind a proxy. Please set the environment variables HTTPS_PROXY and HTTP_PROXY to the address of the proxy in the format "protocol://address:port" (without quotes) and try again.
Example: HTTPS_PROXY=http://192.168.0.1:8080
PS C:\Users\KushwahaV2\Downloads\relay\relay> gcloud auth application-default login
Your browser has been opened to visit:

    https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com&redirect_uri=http%3A%2F%2Flocalhost%3A8085%2F&scope=openid+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.email+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcloud-platform+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fsqlservice.login&state=3HniufBsSfLQp2HtlLmyQUS0b0Zm7q&access_type=offline&code_challenge=5ayIjH7vN-Z_22OLKsgu0VDd57gjN6l80jO2lyaIFkE&code_challenge_method=S256


Credentials saved to file: [C:\Users\KushwahaV2\AppData\Roaming\gcloud\application_default_credentials.json]

These credentials will be used by any library that requests Application Default Credentials (ADC).
WARNING:
Cannot find a quota project to add to ADC. You might receive a "quota exceeded" or "API not enabled" error. Run $ gcloud auth application-default set-quota-project to add a quota project.


To take a quick anonymous survey, run:
  $ gcloud survey

PS C:\Users\KushwahaV2\Downloads\relay\relay> python -m relay.cli sync "gcloud storage gs://vineetk/relay/" . --dry-run
[relay] Resolving endpoints:
    Source:      gcloud storage gs://vineetk/relay/ [GCS]
    Destination: . [LOCAL]
C:\Users\KushwahaV2\AppData\Roaming\Python\Python314\site-packages\google\auth\_default.py:113: UserWarning: Your application has authenticated using end user credentials from Google Cloud SDK without a quota project. You might receive a "quota exceeded" or "API not enabled" error. See the following page for troubleshooting: https://cloud.google.com/docs/authentication/adc-troubleshooting/user-creds.
  warnings.warn(_CLOUD_SDK_CREDENTIALS_WARNING)
[error] Project was not passed and could not be determined from the environment.
PS C:\Users\KushwahaV2\Downloads\relay\relay> gcloud config set project vf-grp-gbissdbx-dev-1
WARNING: Your active project does not match the quota project in your local Application Default Credentials file. This might result in unexpected quota issues.

To update your Application Default Credentials quota project, use the `gcloud auth application-default set-quota-project` command.
Project 'vf-grp-gbissdbx-dev-1' lacks an 'environment' tag. Please create or add a tag with key 'environment' and a value like 'Production', 'Development', 'Test', or 'Staging'. Add an 'environment' tag using `gcloud resource-manager tags bindings create`. See https://cloud.google.com/resource-manager/docs/creating-managing-projects#designate_project_environments_with_tags for details.
Updated property [core/project].
PS C:\Users\KushwahaV2\Downloads\relay\relay> python -m relay.cli sync "gcloud storage gs://vineetk/relay/" . --dry-run
[relay] Resolving endpoints:
    Source:      gcloud storage gs://vineetk/relay/ [GCS]
    Destination: . [LOCAL]
C:\Users\KushwahaV2\AppData\Roaming\Python\Python314\site-packages\google\auth\_default.py:113: UserWarning: Your application has authenticated using end user credentials from Google Cloud SDK without a quota project. You might receive a "quota exceeded" or "API not enabled" error. See the following page for troubleshooting: https://cloud.google.com/docs/authentication/adc-troubleshooting/user-creds.
  warnings.warn(_CLOUD_SDK_CREDENTIALS_WARNING)
C:\Users\KushwahaV2\AppData\Roaming\Python\Python314\site-packages\google\auth\_default.py:113: UserWarning: Your application has authenticated using end user credentials from Google Cloud SDK without a quota project. You might receive a "quota exceeded" or "API not enabled" error. See the following page for troubleshooting: https://cloud.google.com/docs/authentication/adc-troubleshooting/user-creds.
  warnings.warn(_CLOUD_SDK_CREDENTIALS_WARNING)
[error] Timeout of 120.0s exceeded, last exception: HTTPSConnectionPool(host='oauth2.googleapis.com', port=443): Max retries exceeded with url: /token (Caused by ConnectTimeoutError(<HTTPSConnection(host='oauth2.googleapis.com', port=443) at 0x1dbcf08a710>, 'Connection to oauth2.googleapis.com timed out. (connect timeout=60)'))
PS C:\Users\KushwahaV2\Downloads\relay\relay> ls


    Directory: C:\Users\KushwahaV2\Downloads\relay\relay


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----        11/11/2026  11:48 PM          20480 .relay.db


PS C:\Users\KushwahaV2\Downloads\relay\relay> python -m relay.cli sync "gcloud storage gs://vineetk/relay/" . --dry-run
[relay] Resolving endpoints:
    Source:      gcloud storage gs://vineetk/relay/ [GCS]
    Destination: . [LOCAL]
C:\Users\KushwahaV2\AppData\Roaming\Python\Python314\site-packages\google\auth\_default.py:113: UserWarning: Your application has authenticated using end user credentials from Google Cloud SDK without a quota project. You might receive a "quota exceeded" or "API not enabled" error. See the following page for troubleshooting: https://cloud.google.com/docs/authentication/adc-troubleshooting/user-creds.
  warnings.warn(_CLOUD_SDK_CREDENTIALS_WARNING)
C:\Users\KushwahaV2\AppData\Roaming\Python\Python314\site-packages\google\auth\_default.py:113: UserWarning: Your application has authenticated using end user credentials from Google Cloud SDK without a quota project. You might receive a "quota exceeded" or "API not enabled" error. See the following page for troubleshooting: https://cloud.google.com/docs/authentication/adc-troubleshooting/user-creds.
  warnings.warn(_CLOUD_SDK_CREDENTIALS_WARNING)

[relay] Operation cancelled by user.
PS C:\Users\KushwahaV2\Downloads\relay\relay> ^C
PS C:\Users\KushwahaV2\Downloads\relay\relay> gcloud storage ls gs://vineetk/
gs://vineetk/jtd/
gs://vineetk/relay/
gs://vineetk/static-poc/
gs://vineetk/uiux/
gs://vineetk/vois_hub/
gs://vineetk/vois_shield/
PS C:\Users\KushwahaV2\Downloads\relay\relay>
```