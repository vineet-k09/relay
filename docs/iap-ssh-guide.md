# GCP IAP Port Forwarding & Native OpenSSH Guide 🛡️

This guide explains how to establish a direct, automated, and secure connection from a local Windows environment to a GCP Compute Engine / Vertex AI Workbench instance over **Google Cloud Identity-Aware Proxy (IAP)**, bypassing GUI-based PuTTY sessions and enabling native OpenSSH and scriptable file sync via `scp` or Relay.

---

## 1. Why PuTTY Fails Automation (and Why Ports Win)

### The Legacy Default
On Windows, Google Cloud SDK defaults to Simon Tatham's PuTTY (`putty.exe`, `plink.exe`, `pscp.exe`). While functional for manual terminal clicks:
1. **Interactive GUI Isolation**: `gcloud compute ssh` launches an independent GUI window with its own isolated pseudo-terminal, breaking programmatic access from local scripts, IDEs, and CLI tools.
2. **`pscp` Stream Failures**: When copying files via `gcloud compute scp` through IAP, `pscp.exe` frequently crashes with:
   ```text
   FATAL ERROR: Remote side unexpectedly closed network connection
   ERROR: (gcloud.compute.scp) [pscp.exe] exited with return code [1].
   ```
   This is caused by PuTTY's pipe-buffering quirks over TLS tunnels and headless registry host-key prompt rejections.

### The Loopback Port Solution (`localhost:2222`)
Instead of having `gcloud` launch an SSH process, we instruct Google Cloud SDK to act purely as a **TCP forwarding bridge**:

```
┌────────────────────────────────────────────────────────┐
│                   LOCAL WINDOWS LAPTOP                 │
│                                                        │
│  Native OpenSSH / scp / Relay                          │
│         │ (Standard SSH protocol on 127.0.0.1:2222)    │
│         ▼                                              │
│  [gcloud start-iap-tunnel (Listening on 2222)]         │
└───────────────────────┬────────────────────────────────┘
                        │ Outbound TLS (HTTPS / 443) via Cloud IAP
                        ▼
┌────────────────────────────────────────────────────────┐
│                  GOOGLE CLOUD PLATFORM                 │
│                                                        │
│  Identity-Aware Proxy (IAM Authorization Check)        │
│         │ Internal GCP VPC forwarding                  │
│         ▼                                              │
│  Workbench / Compute Engine VM (Port 22 - sshd)       │
└────────────────────────────────────────────────────────┘
```

When you point native OpenSSH or Relay to `localhost:2222`, traffic flows directly through the secure IAP tunnel into the VM's SSH daemon. No PuTTY, no popups, zero network-level air gaps.

---

## 2. Command-by-Command Breakdown

### Command A: Starting the IAP Tunnel
```powershell
gcloud compute start-iap-tunnel <INSTANCE_NAME> 22 `
    --project <PROJECT_ID> `
    --zone <ZONE> `
    --local-host-port=localhost:2222
```

| Flag | Purpose |
| :--- | :--- |
| `start-iap-tunnel` | Starts a local proxy server that forwards TCP traffic over an authenticated WebSocket/TLS stream to GCP. |
| `<INSTANCE_NAME>` | The name of your Compute Engine or Workbench VM. |
| `22` | The destination port on the VM (SSH daemon default). |
| `--project` | The GCP Project containing the VM. |
| `--zone` | The geographical compute zone (e.g., `europe-west1-b`). |
| `--local-host-port=localhost:2222` | Binds the local end of the tunnel exclusively to `127.0.0.1` on port `2222`. |

---

### Command B: Registering the SSH Key with GCP OS Login
```powershell
gcloud compute os-login ssh-keys add --key-file="$HOME\.ssh\google_compute_engine.pub"
```

| Component | Purpose |
| :--- | :--- |
| `os-login ssh-keys add` | Uploads your public key (`.pub`) to your Google Cloud Identity profile across the entire organization. |
| `--key-file=...` | Path to the public key file to associate with your corporate IAM identity. |

---

### Command C: The Windows Equivalent of `chmod 600`
On Linux, securing an SSH private key requires a simple command:
```bash
chmod 600 ~/.ssh/id_rsa
```
Windows uses NTFS **Access Control Lists (ACLs)** instead of POSIX permissions. If a private key inherits read access from parent directories (e.g., `Users` or `Authenticated Users`), native Windows OpenSSH aborts immediately with:
```text
WARNING: UNPROTECTED PRIVATE KEY FILE!
Permissions for '.../google_compute_engine' are too open.
This private key will be ignored.
Load key: bad permissions
Permission denied (publickey).
```

To replicate `chmod 600` on Windows, we execute:

```powershell
# 1. Take ownership of the key file
takeown /F "$HOME\.ssh\google_compute_engine"

# 2. Disable inheritance and remove all inherited access rules
icacls "$HOME\.ssh\google_compute_engine" /inheritance:r

# 3. Grant Full control ONLY to your specific logged-in user
icacls "$HOME\.ssh\google_compute_engine" /grant:r "$($env:USERNAME):(F)"
```

#### What each parameter does:
- **`takeown /F <file>`**: Explicitly asserts ownership of the target file to the currently active administrative or user account.
- **`icacls <file> /inheritance:r`**: The `/inheritance:r` switch strips all inherited permissions from parent directories (such as `C:\Users`), leaving the file with zero access entries.
- **`icacls <file> /grant:r "<User>:(F)"`**:
  - `/grant:r`: Replaces any existing explicit permissions rather than appending to them.
  - `$($env:USERNAME)`: Dynamically resolves your local Windows username (e.g., `YourWindowsUser`).
  - `:(F)`: Grants **Full Control** (Read, Write, Execute). Since no other user or group exists on the ACL, OpenSSH is satisfied that the file is strictly private.

---

## 3. GCP OS Login & Username Resolution

### Why You Cannot Use Your Local Windows Username
In standard Linux VMs, local user accounts are created manually in `/etc/passwd`. However, enterprise GCP environments enforce **GCP OS Login**, linking Linux POSIX accounts directly to your Google Cloud IAM identity.

When OS Login is enabled:
1. Google Cloud normalizes your IAM corporate email address into a valid Linux POSIX username:
   - Special characters (`.` and `@`) are converted to underscores (`_`).
   - Example: `firstname.lastname@company.com` $\rightarrow$ `firstname_lastname_company_com`.
2. The VM's PAM stack queries Google's directory service at login time to verify permissions and public keys.
3. Attempting to log in as your local Windows username or raw email fails because the VM does not have matching POSIX records.

### How to Check Your Exact GCP OS Login Username Anytime

If you ever forget or need to verify your assigned POSIX username, run:

```powershell
# Inspect your complete OS Login profile
gcloud compute os-login describe-profile
```

Look for the `username:` field in the output:
```yaml
posixAccounts:
- homeDirectory: /home/jane_doe_company_com
  primary: true
  uid: '1205294880'
  username: jane_doe_company_com
```

Alternatively, list all registered SSH keys associated with your profile:
```powershell
gcloud compute os-login ssh-keys list
```

---

## 4. `scp` (Secure Copy Protocol) Primer

`scp` uses SSH data streams to transfer files securely between hosts. It follows standard SSH authentication and encryption.

### The Port Flag Caveat: `-P` vs `-p`
A common stumbling block:
- In `ssh`, port is specified with **lowercase `-p`**:
  ```powershell
  ssh -p 2222 user@localhost
  ```
- In `scp`, port is specified with **uppercase `-P`**:
  ```powershell
  scp -P 2222 ...
  ```
> **Why?** In `scp`, lowercase `-p` was historically reserved for **preserving** file modification times, access times, and modes from the source file. Therefore, uppercase `-P` was assigned to specify the network port.

### Core Flags Reference

| Flag | Meaning | Description |
| :--- | :--- | :--- |
| `-P <port>` | Port | Destination network port (e.g., `-P 2222`). |
| `-i <file>` | Identity | Path to the private key file. |
| `-r` | Recursive | Copies entire directories recursively. |
| `-C` | Compression | Enables on-the-fly gzip compression (speeds up slow connections for text/code). |
| `-p` | Preserve | Preserves original file modification and access timestamps. |
| `-v` | Verbose | Prints detailed debugging logs (useful when diagnosing connection issues). |

### Common Usage Examples (Over Port 2222)

```powershell
# 1. Upload a single file from Windows to Workbench home directory
scp -P 2222 -i ~/.ssh/google_compute_engine C:\path\to\script.py <GCP_USERNAME>@localhost:~/script.py

# 2. Upload an entire directory recursively
scp -P 2222 -r -i ~/.ssh/google_compute_engine C:\path\to\project <GCP_USERNAME>@localhost:~/project

# 3. Download a file from Workbench to local Windows directory
scp -P 2222 -i ~/.ssh/google_compute_engine <GCP_USERNAME>@localhost:~/results.csv C:\path\to\downloads\results.csv
```

---

## 5. Daily Workflow Cheat Sheet

1. **Terminal 1 — Keep Tunnel Active**:
   ```powershell
   gcloud compute start-iap-tunnel <INSTANCE_NAME> 22 `
       --project <PROJECT_ID> `
       --zone <ZONE> `
       --local-host-port=localhost:2222
   ```

2. **Terminal 2 — Work Freely via OpenSSH / scp / Relay**:
   ```powershell
   # Interactive shell
   ssh -p 2222 -i ~/.ssh/google_compute_engine <GCP_USERNAME>@localhost

   # File copy
   scp -P 2222 -i ~/.ssh/google_compute_engine test.txt <GCP_USERNAME>@localhost:~/
   ```
