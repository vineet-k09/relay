from unittest.mock import MagicMock, patch

from relay.adapters import get_adapter
from relay.adapters.gcs import GCSTransportAdapter, list_gcs_manifest
from relay.core.endpoint import EndPointType, parse_endpoint


def test_endpoint_parsing():
    ep1 = parse_endpoint("gs://my-bucket/data/folder")
    assert ep1.type == EndPointType.GCS
    assert ep1.bucket == "my-bucket"
    assert ep1.path == "data/folder"

    ep2 = parse_endpoint("gcloud storage gcs://my-bucket/raw")
    assert ep2.type == EndPointType.GCS
    assert ep2.bucket == "my-bucket"
    assert ep2.path == "raw"

    ep3 = parse_endpoint("./sandbox/source")
    assert ep3.type == EndPointType.LOCAL


@patch("relay.adapters.gcs.storage.Client")
def test_list_gcs_manifest(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    # Mock blobs returned by GCS
    blob1 = MagicMock()
    blob1.name = "prefix/data/train.csv"
    blob1.crc32c = "crc_train"
    blob1.size = 100

    blob2 = MagicMock()
    blob2.name = "prefix/README.md"
    blob2.crc32c = "crc_readme"
    blob2.size = 50

    mock_bucket.list_blobs.return_value = [blob1, blob2]

    manifest = list_gcs_manifest("test-bucket", prefix="prefix")

    assert manifest == [
        ("data/train.csv", "crc_train"),
        ("README.md", "crc_readme"),
    ]


@patch("relay.adapters.gcs.storage.Client")
def test_gcs_adapter_upload(mock_client_cls, tmp_path):
    # Setup local file
    local_file = tmp_path / "hello.txt"
    local_file.write_text("Hello World!")

    src = parse_endpoint(str(tmp_path))
    dst = parse_endpoint("gs://test-bucket/remote_dir")

    adapter = get_adapter(src, dst)
    assert isinstance(adapter, GCSTransportAdapter)
    assert adapter.is_upload is True

    # Test transfer (upload)
    mock_blob = MagicMock()
    mock_blob.size = 12
    mock_blob.crc32c = "mock_crc"
    adapter.bucket.blob.return_value = mock_blob

    meta = adapter.transfer("hello.txt")
    adapter.bucket.blob.assert_called_with("remote_dir/hello.txt")
    mock_blob.upload_from_filename.assert_called_once_with(str(local_file))
    assert meta.path == "hello.txt"

    # Test rename (server-side rename)
    mock_blob.exists.return_value = True
    adapter.rename("old.txt", "new.txt")
    adapter.bucket.rename_blob.assert_called_once()

    # Test delete
    adapter.delete("hello.txt")
    mock_blob.delete.assert_called_once()
