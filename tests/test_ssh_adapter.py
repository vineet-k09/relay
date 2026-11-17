import json
from unittest.mock import MagicMock, patch

from relay.adapters import get_adapter
from relay.adapters.ssh import SSHTransportAdapter, list_ssh_manifest
from relay.core.endpoint import EndPointType, parse_endpoint


def test_ssh_endpoint_parsing():
    # 1. GCP zone/instance format
    ep1 = parse_endpoint("ssh europe-west1-b/my-workbench/home/jupyter/code")
    assert ep1.type == EndPointType.SSH
    assert ep1.zone == "europe-west1-b"
    assert ep1.instance == "my-workbench"
    assert ep1.path == "home/jupyter/code"

    # 2. Loopback IAP tunnel host:port format
    ep2 = parse_endpoint("ssh localhost:2222/home/jupyter/project")
    assert ep2.type == EndPointType.SSH
    assert ep2.host == "localhost"
    assert ep2.port == 2222
    assert ep2.path == "home/jupyter/project"

    # 3. Explicit user, host, port, and key flags
    ep3 = parse_endpoint(
        "ssh user_domain@127.0.0.1:2222/data/models --key ~/.ssh/custom_key"
    )
    assert ep3.type == EndPointType.SSH
    assert ep3.user == "user_domain"
    assert ep3.host == "127.0.0.1"
    assert ep3.port == 2222
    assert ep3.key_file == "~/.ssh/custom_key"
    assert ep3.path == "data/models"


def test_ssh_adapter_routing(tmp_path):
    src = parse_endpoint(str(tmp_path))
    dst = parse_endpoint("ssh europe-west1-b/instance/home/jupyter/repo")

    adapter_upload = get_adapter(src, dst)
    assert isinstance(adapter_upload, SSHTransportAdapter)
    assert adapter_upload.is_upload is True
    assert adapter_upload.is_download is False

    adapter_download = get_adapter(dst, src)
    assert isinstance(adapter_download, SSHTransportAdapter)
    assert adapter_download.is_upload is False
    assert adapter_download.is_download is True


@patch("subprocess.run")
def test_ssh_adapter_rename(mock_run, tmp_path):
    src = parse_endpoint(str(tmp_path))
    dst = parse_endpoint("ssh localhost:2222/home/jupyter/repo")
    adapter = get_adapter(src, dst)

    adapter.rename("old.txt", "new.txt")

    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    cmd = args[0]
    assert cmd[0] == "ssh"
    assert "-p" in cmd
    assert "2222" in cmd
    # Verify remote command executes mv
    assert "mv" in cmd[-1]
    assert "old.txt" in cmd[-1]
    assert "new.txt" in cmd[-1]


@patch("subprocess.run")
def test_ssh_adapter_copy_local(mock_run, tmp_path):
    src = parse_endpoint(str(tmp_path))
    dst = parse_endpoint("ssh localhost:2222/home/jupyter/repo")
    adapter = get_adapter(src, dst)

    adapter.copy_local("origin.txt", "clone.txt")

    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    cmd = args[0]
    assert cmd[0] == "ssh"
    assert "cp -p" in cmd[-1]
    assert "origin.txt" in cmd[-1]
    assert "clone.txt" in cmd[-1]


@patch("subprocess.run")
def test_ssh_adapter_delete(mock_run, tmp_path):
    src = parse_endpoint(str(tmp_path))
    dst = parse_endpoint("ssh localhost:2222/home/jupyter/repo")
    adapter = get_adapter(src, dst)

    adapter.delete("orphan.txt")

    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    cmd = args[0]
    assert cmd[0] == "ssh"
    assert "rm -rf" in cmd[-1]
    assert "orphan.txt" in cmd[-1]


@patch("subprocess.run")
def test_ssh_adapter_transfer_upload(mock_run, tmp_path):
    local_file = tmp_path / "train.py"
    local_file.write_text("print('hello')")

    src = parse_endpoint(str(tmp_path))
    dst = parse_endpoint("ssh localhost:2222/home/jupyter/repo")
    adapter = get_adapter(src, dst)

    meta = adapter.transfer("train.py")

    assert meta.path == "train.py"
    assert meta.size == len("print('hello')")
    assert meta.blake3_hash is not None

    # Verify ssh mkdir and scp were invoked
    assert mock_run.call_count == 2
    mkdir_call = mock_run.call_args_list[0][0][0]
    assert mkdir_call[0] == "ssh"
    assert "mkdir -p" in mkdir_call[-1]

    scp_call = mock_run.call_args_list[1][0][0]
    assert scp_call[0] == "scp"
    assert "-P" in scp_call
    assert "-p" in scp_call


@patch("subprocess.run")
def test_list_ssh_manifest(mock_run):
    # Mock remote python script returning json
    mock_proc = MagicMock()
    mock_proc.stdout = json.dumps([
        ["model.pt", "crc_model_123"],
        ["utils/helper.py", "crc_helper_456"],
    ])
    mock_run.return_value = mock_proc

    ep = parse_endpoint("ssh localhost:2222/home/jupyter/project")
    manifest = list_ssh_manifest(ep)

    assert manifest == [
        ("model.pt", "crc_model_123"),
        ("utils/helper.py", "crc_helper_456"),
    ]
