# Transport Adapters 🚀

Relay isolates all environment-specific filesystem and network operations behind the `TransportAdapter` interface (`src/relay/adapters/base.py`). This allows the diff engine and CLI to remain completely agnostic of whether a destination is a local directory, a cloud storage bucket, or a remote compute instance.

---

## 1. Transport Adapter Contract

Every adapter must implement the core transport methods:

```python
class TransportAdapter(ABC):
    @abstractmethod
    def rename(self, old_path: str, new_path: str) -> None:
        """Rename or move a file within the destination environment (0 egress bytes)."""

    @abstractmethod
    def copy_local(self, old_path: str, new_path: str) -> None:
        """Duplicate an existing file within the destination environment (0 egress bytes)."""

    @abstractmethod
    def transfer(self, path: str) -> None:
        """Transfer a file from source to destination."""

    @abstractmethod
    def delete(self, path: str) -> None:
        """Delete a file from the destination environment."""

    @abstractmethod
    def list_manifest(self) -> dict[str, tuple[str, int, float]]:
        """Return destination manifest mapping: path -> (hash, size, mtime)."""
```

---

## 2. Low-Level Operations Comparison

The table below contrasts how each underlying operation is executed across supported environments:

| Operation | Local Filesystem (`LocalTransportAdapter`) | Google Cloud Storage (`GCSTransportAdapter`) | GCP Workbench / SSH (`SSHTransportAdapter`) |
| :--- | :--- | :--- | :--- |
| **`rename(old, new)`** | `os.replace(src, dst)`<br>*(Instant inode update)* | `bucket.rename_blob(blob, new_name)`<br>*(Server-side rename, 0 network bytes)* | `ssh ... "mv '{old}' '{new}'"`<br>*(Remote instant move)* |
| **`copy_local(old, new)`** | `shutil.copy2(src, dst)`<br>*(Local file duplication)* | `bucket.copy_blob(blob, bucket, new_name)`<br>*(Server-side duplicate, 0 network bytes)* | `ssh ... "cp -p '{old}' '{new}'"`<br>*(Remote duplicate)* |
| **`transfer(path)`** | Read from `src_root/path`, copy to `dst_root/path` | `bucket.blob(path).upload_from_filename(local_path)` | `scp -P <port>` *(or 1-shot `-z` batch zip via `python3 -m zipfile`)* |
| **`delete(path)`** | `os.remove(path)` | `bucket.blob(path).delete()` | `ssh ... "rm -rf '{path}'"` |

---

## 3. Zero-Egress Network Optimizations

For data science and ML workflows dealing with multi-gigabyte models or datasets, cross-region and cloud egress bandwidth is expensive and slow.

Relay leverages native remote primitives whenever possible:
- **GCS Server-Side Operations**: Instead of downloading an object to the local machine and re-uploading it to a new key, `GcsAdapter` uses `bucket.rename_blob()` and `bucket.copy_blob()`. These operations execute entirely within Google Cloud's infrastructure at zero egress cost.
- **SSH / Workbench Remote Moves**: When moving files within a remote JupyterLab or Compute Engine instance, `SshAdapter` invokes `mv` directly on the remote host over the SSH connection rather than piping file content back and forth.

---

## 4. Endpoint Routing & Factory

Endpoints are parsed by `src/relay/core/endpoint.py` and routed via `src/relay/adapters/__init__.py`:

```python
def get_adapter(src: Endpoint, dst: Endpoint) -> BaseAdapters:
    is_windows = _is_windows_context(src, dst)
    if src.type == EndPointType.LOCAL and dst.type == EndPointType.LOCAL:
        return WindowsTransportAdapter(src.path, dst.path) if is_windows else LocalTransportAdapter(src.path, dst.path)
    if (src.type == EndPointType.LOCAL and dst.type == EndPointType.GCS) or (
        src.type == EndPointType.GCS and dst.type == EndPointType.LOCAL
    ):
        return GCSWindowsTransportAdapter(src, dst) if is_windows else GCSTransportAdapter(src, dst)
    if (src.type == EndPointType.LOCAL and dst.type == EndPointType.SSH) or (
        src.type == EndPointType.SSH and dst.type == EndPointType.LOCAL
    ):
        return SSHTransportAdapter(src, dst)
    raise NotImplementedError(...)
```

### Supported Endpoint Schemes

| Scheme | Example | Adapter | Status |
| :--- | :--- | :--- | :--- |
| **Local Paths** | `./data`, `/home/user/models`, `C:\project` | `LocalTransportAdapter` / `WindowsTransportAdapter` | ✅ Implemented |
| **Google Cloud Storage** | `gcs://bucket-name/path`, `gs://bucket-name/path` | `GCSTransportAdapter` / `GCSWindowsTransportAdapter` | ✅ Implemented |
| **GCP Workbench / SSH** | `ssh [user@]127.0.0.1:2222/path` or `ssh europe-west3/instance/path` | `SSHTransportAdapter` | ✅ Implemented |
