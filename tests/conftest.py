from unittest.mock import patch

import pytest
from google.oauth2.credentials import Credentials


@pytest.fixture(autouse=True)
def mock_gcloud_auth():
    """
    Automatically mocks gcloud auth and project lookup for all tests.
    Ensures CI runners (without gcloud installed or authenticated) execute
    cleanly in memory without invoking external subprocesses.
    """
    mock_creds = Credentials(token="mock-ci-test-token")
    with (
        patch("relay.adapters.gcs.get_gcloud_credentials", return_value=mock_creds),
        patch("relay.adapters.gcs.get_gcloud_project", return_value="mock-project"),
    ):
        yield
