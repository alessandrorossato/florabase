import pytest
from sqlalchemy import Connection, text

from .test_supplier_api import ORIGIN, mutate, request
from .test_supplier_api import authenticated_browser as authenticated_browser

pytestmark = pytest.mark.integration
PATH = "/api/v1/application-settings"


def test_settings_persist_across_requests_and_remain_global(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    cookie, _ = authenticated_browser
    status, _, initial = request("GET", PATH, headers={"cookie": cookie})
    assert status == 200
    assert initial == {"public_qr_base_url": None, "default_label_preset": "medium"}
    payload = {"public_qr_base_url": "https://FLORA.example/", "default_label_preset": "small"}
    status, _, saved = mutate(authenticated_browser, "PUT", PATH, payload)
    assert status == 200
    assert saved == {"public_qr_base_url": "https://flora.example", "default_label_preset": "small"}
    assert request("GET", PATH, headers={"cookie": cookie})[2] == saved
    assert database_connection.execute(
        text("SELECT public_qr_base_url, default_label_preset FROM application_settings WHERE id=1")
    ).one() == ("https://flora.example", "small")
    # Changing the default doesn't clear the explicitly retained destination.
    saved["default_label_preset"] = "large"
    assert mutate(authenticated_browser, "PUT", PATH, saved)[2] == saved
    assert database_connection.scalar(text("SELECT count(*) FROM application_settings")) == 1
    saved["public_qr_base_url"] = None
    assert mutate(authenticated_browser, "PUT", PATH, saved)[2]["public_qr_base_url"] is None


def test_settings_authentication_csrf_validation_and_no_partial_write(
    authenticated_browser: tuple[str, str],
) -> None:
    cookie, _ = authenticated_browser
    valid = {"public_qr_base_url": "https://flora.example", "default_label_preset": "medium"}
    assert request("GET", PATH)[0] == 401
    assert request("PUT", PATH, body=valid, headers={"cookie": cookie, "origin": ORIGIN})[0] == 403
    for invalid in (
        {**valid, "public_qr_base_url": "https://flora.example/?x=1"},
        {**valid, "public_qr_base_url": "https://flora.example/.."},
        {**valid, "default_label_preset": "unknown"},
        {**valid, "theme": "dark"},
    ):
        assert mutate(authenticated_browser, "PUT", PATH, invalid)[0] == 422
    assert request("GET", PATH, headers={"cookie": cookie})[2] == {
        "public_qr_base_url": None,
        "default_label_preset": "medium",
    }
