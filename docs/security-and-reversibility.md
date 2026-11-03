# Security & Reversibility Assessment 🔒

This document provides a concise security analysis of the IAP tunnel and OpenSSH key configuration, detailing the exact system changes, impact on laptop and network security, compatibility with existing tools, and full rollback procedures.

---

## 1. Executive Summary

- **Security Posture**: **Zero-Trust Compliant**. No inbound firewall ports were opened on your machine or corporate network. All traffic routes through Google Cloud's official Identity-Aware Proxy (IAP) over outbound HTTPS/TLS (Port 443).
- **Existing Setup**: **100% Preserved**. Existing PuTTY installations, `.ppk` keys, and PowerShell helper functions remain completely untouched and fully functional.
- **Data Protection**: File permissions on the SSH private key were **tightened**, preventing unauthorized local processes or other users on the operating system from reading the key.

---

## 2. Inventory of Changes Made

| Component | What Was Changed | Scope |
| :--- | :--- | :--- |
| **Local Port `2222`** | `start-iap-tunnel` listens on `127.0.0.1:2222`. | In-memory only. Exists only while the terminal command is running. |
| **Private Key Permissions** | Stripped inherited ACL permissions on `google_compute_engine` using `icacls`. | Restricted file access exclusively to the current Windows user account. |
| **Cloud Identity Profile** | Added public key (`.pub`) to GCP OS Login directory. | Associated with your authenticated cloud identity in IAM. |

---

## 3. Security Impact Analysis

### A. Laptop Security
- **No Insecure Services**: The tunnel binds strictly to loopback (`127.0.0.1` / `localhost`). It is **not** exposed to your local Wi-Fi, Ethernet, or local area network (LAN).
- **Hardened Key Storage**: Prior to the permission fix, Windows allowed inherited read permissions on the private key file. Applying `icacls /inheritance:r` ensures only your authenticated Windows user profile can read the private key.

### B. Network & Corporate Firewall Impact
- **No Inbound Openings**: Corporate firewalls block unsolicited inbound connections. The IAP tunnel establishes a standard **outbound** TLS connection (HTTPS over port 443) to Google Cloud IAP endpoints (`tunnel.cloudproxy.app`).
- **IAM Authorization**: Every connection through the tunnel requires valid GCP credentials and active IAM roles (`roles/iap.tunnelResourceAccessor`). If your GCP session expires, the tunnel immediately terminates.
- **Enterprise Audit Logs**: All connection events are logged natively in Google Cloud Audit Logs under IAP connection records.

---

## 4. Compatibility with Existing PuTTY Setup

> **Confirmation**: You can continue using your original PuTTY-based SSH commands, functions, and port forwardings without any conflict.

- **Separate Key Formats**: PuTTY uses `.ppk` files stored in PuTTY-specific configurations or Pageant. The OpenSSH key (`google_compute_engine`) is stored in standard OpenSSH PEM/OpenSSH format and is used only by native `ssh.exe` and `scp.exe`.
- **Separate Ports**: PuTTY functions connect directly through `gcloud compute ssh`. The local tunnel on port `2222` is an independent TCP forwarder that does not interfere with standard SSH ports or other PuTTY sessions.

---

## 5. How to Revert (Full Rollback Procedures)

If you ever need to completely remove or reset these configurations:

### 1. Close the IAP Tunnel
Press `Ctrl + C` in the PowerShell window running `start-iap-tunnel`, or simply close the window. The local port `2222` is immediately released and ceases to exist.

### 2. Remove the SSH Key from GCP OS Login
To remove the registered public key from your cloud identity:
```powershell
# 1. Identify the key fingerprint
gcloud compute os-login ssh-keys list

# 2. Delete the key from your OS Login profile
gcloud compute os-login ssh-keys remove --key=<FINGERPRINT>
```

### 3. Reset Windows File Permissions on the Key
To restore the default inherited NTFS permissions on the private key file:
```powershell
icacls "$HOME\.ssh\google_compute_engine" /reset
```

### 4. (Optional) Remove the OpenSSH Key Files
```powershell
Remove-Item "$HOME\.ssh\google_compute_engine" -ErrorAction SilentlyContinue
Remove-Item "$HOME\.ssh\google_compute_engine.pub" -ErrorAction SilentlyContinue
```

---

## 6. Verification Commands for Peace of Mind

Run these commands in PowerShell anytime to verify security boundaries:

```powershell
# 1. Verify that port 2222 is bound strictly to Localhost (127.0.0.1) and NOT 0.0.0.0 (all interfaces)
Get-NetTCPConnection -LocalPort 2222 | Select-Object LocalAddress, LocalPort, State

# 2. Verify file permissions on the private key (Should only list your username)
icacls "$HOME\.ssh\google_compute_engine"
```
