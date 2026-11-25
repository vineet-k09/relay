import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from relay.adapters import get_adapter
from relay.cli import handle_sync, parse_args
from relay.core.endpoint import parse_endpoint
from relay.shared.archive import create_zip_from_paths, extract_zip_safe


def test_parse_zip_flags(monkeypatch):
    monkeypatch.setattr("sys.argv", ["relay", "sync", "src", "dst", "-z"])
    args = parse_args()
    assert args.zip is True
    assert args.zip_only is False
    assert args.unzip is False

    monkeypatch.setattr("sys.argv", ["relay", "sync", "src", "dst", "-Z", "-c"])
    args = parse_args()
    assert args.zip is False
    assert args.zip_only is True
    assert args.clean is True

    monkeypatch.setattr("sys.argv", ["relay", "sync", "src", "dst", "-u"])
    args = parse_args()
    assert args.unzip is True


def test_parse_zip_and_zip_only_mutually_exclusive(monkeypatch):
    monkeypatch.setattr("sys.argv", ["relay", "sync", "src", "dst", "-z", "-Z"])
    with pytest.raises(SystemExit):
        parse_args()


def test_extract_zip_safe_blocks_zip_slip(tmp_path):
    evil_zip = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil_zip, "w") as zf:
        zf.writestr("../../outside.txt", "boom")

    with pytest.raises(ValueError, match="Unsafe path"):
        extract_zip_safe(evil_zip, tmp_path / "dest")


@patch("subprocess.run")
def test_ssh_transfer_batch_upload(mock_run, tmp_path):
    (tmp_path / "a.py").write_text("print('a')")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.py").write_text("print('b')")

    src = parse_endpoint(str(tmp_path))
    dst = parse_endpoint("ssh 127.0.0.1:2222/home/jupyter/repo")
    adapter = get_adapter(src, dst)

    def verify_scp(cmd, **_kwargs):
        if cmd[0] == "scp":
            local_zip = cmd[-2]
            with zipfile.ZipFile(local_zip, "r") as zf:
                assert sorted(zf.namelist()) == ["a.py", "sub/b.py"]
        return MagicMock(stdout="", stderr="")

    mock_run.side_effect = verify_scp

    metas = adapter.transfer_batch(["a.py", "sub/b.py"])

    assert len(metas) == 2
    assert mock_run.call_count == 2
    assert mock_run.call_args_list[0][0][0][0] == "scp"
    ssh_cmd = mock_run.call_args_list[1][0][0]
    assert ssh_cmd[0] == "ssh"
    assert "python3 -m zipfile -e" in ssh_cmd[-1]
    assert "rm -f" in ssh_cmd[-1]


@patch("subprocess.run")
def test_ssh_transfer_batch_download(mock_run, tmp_path):
    src = parse_endpoint("ssh 127.0.0.1:2222/home/jupyter/repo")
    dst = parse_endpoint(str(tmp_path))
    adapter = get_adapter(src, dst)

    def fake_remote_pack_and_scp(cmd, **_kwargs):
        if cmd[0] == "scp":
            local_zip = cmd[-1]
            with zipfile.ZipFile(local_zip, "w") as zf:
                zf.writestr("a.py", "hello a")
                zf.writestr("sub/b.py", "hello b")
        return MagicMock(stdout="", stderr="")

    mock_run.side_effect = fake_remote_pack_and_scp

    metas = adapter.transfer_batch(["a.py", "sub/b.py"])

    assert len(metas) == 2
    assert (tmp_path / "a.py").read_text() == "hello a"
    assert (tmp_path / "sub" / "b.py").read_text() == "hello b"
    # 1 ssh pack + 1 scp download + 1 ssh rm cleanup
    assert mock_run.call_count == 3


def test_sync_zip_mode_local_roundtrip(tmp_path):
    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    (src_dir / "nested").mkdir(parents=True)
    (src_dir / "one.txt").write_text("first")
    (src_dir / "nested" / "two.txt").write_text("second")

    args = SimpleNamespace(
        source=str(src_dir),
        destination=str(dst_dir),
        dry_run=False,
        delete=False,
        clean=True,
        zip=True,
        zip_only=False,
        unzip=False,
    )
    handle_sync(args)

    assert (dst_dir / "one.txt").read_text() == "first"
    assert (dst_dir / "nested" / "two.txt").read_text() == "second"
    assert not (src_dir / ".relay.db").exists()
    assert not (dst_dir / ".relay.db").exists()


@patch("relay.adapters.gcs.storage.Client")
def test_sync_zip_only_gcs_upload(mock_client_cls, tmp_path):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    mock_blob = MagicMock()
    mock_blob.size = 128
    mock_blob.crc32c = "zip_crc"
    mock_bucket.blob.return_value = mock_blob

    src_dir = tmp_path / "proj"
    src_dir.mkdir()
    (src_dir / "app.py").write_text("print(1)")

    args = SimpleNamespace(
        source=str(src_dir),
        destination="gs://my-bucket/backups",
        dry_run=False,
        delete=False,
        clean=True,
        zip=False,
        zip_only=True,
        unzip=False,
    )
    handle_sync(args)

    mock_bucket.blob.assert_called_with("backups/proj.zip")
    mock_blob.upload_from_filename.assert_called_once()
    assert not (src_dir / ".relay.db").exists()


@patch("relay.adapters.gcs.storage.Client")
def test_sync_unzip_gcs_download(mock_client_cls, tmp_path):
    # Create a real zip archive to serve as the mocked GCS blob payload
    payload_src = tmp_path / "payload"
    payload_src.mkdir()
    (payload_src / "data.txt").write_text("restored")
    archive_path = tmp_path / "bundle.zip"
    create_zip_from_paths(payload_src, ["data.txt"], archive_path)
    archive_bytes = archive_path.read_bytes()

    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    listed_blob = MagicMock()
    listed_blob.name = "backups/bundle.zip"
    listed_blob.crc32c = "bundle_crc"
    mock_bucket.list_blobs.return_value = [listed_blob]

    dl_blob = MagicMock()
    dl_blob.download_to_filename.side_effect = lambda dest: Path(dest).write_bytes(
        archive_bytes
    )
    mock_bucket.blob.return_value = dl_blob

    dst_dir = tmp_path / "restore"
    args = SimpleNamespace(
        source="gs://my-bucket/backups/bundle.zip",
        destination=str(dst_dir),
        dry_run=False,
        delete=False,
        clean=False,
        zip=False,
        zip_only=False,
        unzip=True,
    )
    handle_sync(args)

    assert (dst_dir / "data.txt").read_text() == "restored"
    assert not (dst_dir / "bundle.zip").exists()
