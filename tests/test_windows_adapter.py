"""
Unit tests for Windows and Cross-Filesystem Transport Adapters.

Tests cover:
  1. WindowsTransportAdapter (atomic rename, cross-drive fallback, copy2
     metadata, read-only delete).
  2. GCSWindowsTransportAdapter (path normalization, upload, download,
     server-side rename).
  3. get_adapter factory routing for Windows vs Linux environments.
"""

import errno
import stat
from unittest.mock import MagicMock, patch

from relay.adapters import (
    GCSTransportAdapter,
    GCSWindowsTransportAdapter,
    LocalTransportAdapter,
    WindowsTransportAdapter,
    get_adapter,
)
from relay.core.endpoint import parse_endpoint


def test_windows_adapter_rename_and_copy(tmp_path):
    """
    Verifies that WindowsTransportAdapter performs renames and local copies
    while preserving file metadata.
    """
    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    dst_dir.mkdir()

    adapter = WindowsTransportAdapter(src_dir, dst_dir)

    # 1. Test copy_local
    initial_file = dst_dir / "original.txt"
    initial_file.write_text("Windows test content")
    adapter.copy_local("original.txt", "copied.txt")

    copied_file = dst_dir / "copied.txt"
    assert copied_file.exists()
    assert copied_file.read_text() == "Windows test content"
    # Verify mtime was preserved (shutil.copy2 behavior)
    assert copied_file.stat().st_mtime_ns == initial_file.stat().st_mtime_ns

    # 2. Test rename
    adapter.rename("copied.txt", "sub/renamed.txt")
    assert not copied_file.exists()
    renamed_file = dst_dir / "sub" / "renamed.txt"
    assert renamed_file.exists()
    assert renamed_file.read_text() == "Windows test content"


def test_windows_adapter_cross_device_rename_fallback(tmp_path):
    """
    Verifies that if os.replace fails with cross-device link (EXDEV or
    WinError 17), the adapter catches the error and falls back to shutil.move.
    This simulates moving across Windows drive letters (C: -> D:) or Linux
    filesystems (ext4 -> Btrfs).
    """
    dst_dir = tmp_path / "dst"
    dst_dir.mkdir()
    adapter = WindowsTransportAdapter(tmp_path / "src", dst_dir)

    file_to_move = dst_dir / "move_me.txt"
    file_to_move.write_text("cross-device content")

    # Mock os.replace to raise OSError with errno.EXDEV (error 18)
    with patch("os.replace") as mock_replace:
        err = OSError("Invalid cross-device link")
        err.errno = errno.EXDEV
        mock_replace.side_effect = err

        adapter.rename("move_me.txt", "moved.txt")

    moved_file = dst_dir / "moved.txt"
    assert moved_file.exists()
    assert moved_file.read_text() == "cross-device content"
    assert not file_to_move.exists()


def test_windows_adapter_delete_readonly_file(tmp_path):
    """
    Verifies that WindowsTransportAdapter strips read-only attributes
    and successfully deletes read-only files.
    """
    dst_dir = tmp_path / "dst"
    dst_dir.mkdir()
    adapter = WindowsTransportAdapter(tmp_path / "src", dst_dir)

    readonly_file = dst_dir / "locked.txt"
    readonly_file.write_text("read-only file content")

    # Set file to read-only (remove write permissions)
    readonly_file.chmod(stat.S_IREAD)

    # adapter.delete should clear the read-only flag and unlink
    adapter.delete("locked.txt")
    assert not readonly_file.exists()


def test_windows_adapter_transfer(tmp_path):
    """
    Verifies that transfer() copies file and extracts FileMetaData with hashes.
    """
    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    dst_dir.mkdir()

    test_file = src_dir / "data.csv"
    test_file.write_bytes(b"col1,col2\n1,2\n")

    adapter = WindowsTransportAdapter(src_dir, dst_dir)
    meta = adapter.transfer("data.csv")

    assert (dst_dir / "data.csv").exists()
    assert meta.path == "data.csv"
    assert meta.size == len(b"col1,col2\n1,2\n")
    assert meta.blake3_hash is not None
    assert meta.crc32c is not None


@patch("relay.adapters.gcs.storage.Client")
def test_gcs_windows_adapter_path_normalization(mock_client_cls, tmp_path):
    """
    Verifies that GCSWindowsTransportAdapter normalizes Windows backslashes '\\'
    into canonical forward slashes '/' for cloud bucket object names.
    """
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    src = parse_endpoint(str(tmp_path))
    dst = parse_endpoint("gs://my-bucket/remote_root")

    adapter = GCSWindowsTransportAdapter(src, dst)

    # Windows path with backslashes
    blob_name = adapter._to_gcs_blob_name("sub\\folder\\model.bin")
    assert blob_name == "remote_root/sub/folder/model.bin"
    assert "\\" not in blob_name


@patch("relay.adapters.gcs.storage.Client")
def test_gcs_windows_adapter_upload_and_download(mock_client_cls, tmp_path):
    """
    Tests upload and download flows for GCSWindowsTransportAdapter.
    """
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    # 1. Upload flow (Local Windows -> GCS)
    local_file = tmp_path / "payload.txt"
    local_file.write_text("cloud payload")

    src = parse_endpoint(str(tmp_path))
    dst = parse_endpoint("gs://bucket/data")

    upload_adapter = GCSWindowsTransportAdapter(src, dst)
    mock_blob = MagicMock()
    mock_blob.size = 13
    mock_blob.crc32c = "test_crc"
    upload_adapter.bucket.blob.return_value = mock_blob

    meta = upload_adapter.transfer("payload.txt")
    mock_blob.upload_from_filename.assert_called_once_with(str(local_file))
    assert meta.crc32c == "test_crc"

    # 2. Download flow (GCS -> Local Windows)
    download_dir = tmp_path / "downloads"
    src_cloud = parse_endpoint("gs://bucket/data")
    dst_local = parse_endpoint(str(download_dir))

    download_adapter = GCSWindowsTransportAdapter(src_cloud, dst_local)
    dl_blob = MagicMock()

    # When download_to_filename is called, write the test file to disk
    def fake_download(dest_path):
        with open(dest_path, "w") as f:
            f.write("downloaded content")

    dl_blob.download_to_filename.side_effect = fake_download
    download_adapter.bucket.blob.return_value = dl_blob

    meta_dl = download_adapter.transfer("downloaded.txt")
    assert (download_dir / "downloaded.txt").exists()
    assert meta_dl.path == "downloaded.txt"
    assert meta_dl.size == len("downloaded content")


def test_get_adapter_routing(tmp_path):
    """
    Verifies that get_adapter routes to WindowsTransportAdapter or
    GCSWindowsTransportAdapter when Windows paths (drive letters like 'C:\\'
    or UNC paths) are provided.
    """
    # 1. Standard Linux paths -> LocalTransportAdapter
    linux_src = parse_endpoint(str(tmp_path / "src"))
    linux_dst = parse_endpoint(str(tmp_path / "dst"))
    adapter = get_adapter(linux_src, linux_dst)
    assert isinstance(adapter, LocalTransportAdapter)

    # 2. Windows drive path -> WindowsTransportAdapter
    win_src = parse_endpoint(r"C:\Users\dev\source")
    win_dst = parse_endpoint(r"C:\Users\dev\dest")
    win_adapter = get_adapter(win_src, win_dst)
    assert isinstance(win_adapter, WindowsTransportAdapter)

    # 3. Windows-to-GCS -> GCSWindowsTransportAdapter
    with patch("relay.adapters.gcs.storage.Client"):
        gcs_win_adapter = get_adapter(win_src, parse_endpoint("gs://bucket/dir"))
        assert isinstance(gcs_win_adapter, GCSWindowsTransportAdapter)

    # 4. Standard Linux-to-GCS -> GCSTransportAdapter
    with patch("relay.adapters.gcs.storage.Client"):
        gcs_adapter = get_adapter(linux_src, parse_endpoint("gs://bucket/dir"))
        assert isinstance(gcs_adapter, GCSTransportAdapter)
