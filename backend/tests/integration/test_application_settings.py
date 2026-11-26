import pytest
from sqlalchemy import Connection, text

from .test_supplier_api import ORIGIN, mutate, request
from .test_supplier_api import authenticated_browser as authenticated_browser

pytestmark = pytest.mark.integration
PATH = "/api/v1/application-settings"
MEDIA_DEFAULTS = {
    "media_save_local_copy_default": True,
    "media_default_attribution": None,
    "media_default_licence_label": None,
    "media_default_licence_url": None,
}


def test_settings_persist_across_requests_and_remain_global(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    cookie, _ = authenticated_browser
    status, _, initial = request("GET", PATH, headers={"cookie": cookie})
    assert status == 200
    assert initial == {
        "public_qr_base_url": None,
        "default_label_preset": "medium",
        **MEDIA_DEFAULTS,
    }
    payload = {
        "public_qr_base_url": "https://FLORA.example/",
        "default_label_preset": "small",
        **MEDIA_DEFAULTS,
    }
    status, _, saved = mutate(authenticated_browser, "PUT", PATH, payload)
    assert status == 200
    assert saved == {
        "public_qr_base_url": "https://flora.example",
        "default_label_preset": "small",
        **MEDIA_DEFAULTS,
    }
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
    valid = {
        "public_qr_base_url": "https://flora.example",
        "default_label_preset": "medium",
        **MEDIA_DEFAULTS,
    }
    assert request("GET", PATH)[0] == 401
    assert request("PUT", PATH, body=valid, headers={"cookie": cookie, "origin": ORIGIN})[0] == 403
    for invalid in (
        {**valid, "public_qr_base_url": "https://flora.example/?x=1"},
        {**valid, "public_qr_base_url": "https://flora.example/.."},
        {**valid, "default_label_preset": "unknown"},
        {**valid, "theme": "dark"},
        {**valid, "media_default_licence_url": "http://licence.example/"},
        {key: value for key, value in valid.items() if key != "media_save_local_copy_default"},
    ):
        assert mutate(authenticated_browser, "PUT", PATH, invalid)[0] == 422
    assert request("GET", PATH, headers={"cookie": cookie})[2] == {
        "public_qr_base_url": None,
        "default_label_preset": "medium",
        **MEDIA_DEFAULTS,
    }


def test_media_defaults_persist_and_preserve_other_preferences(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    cookie, _ = authenticated_browser
    payload = {
        "public_qr_base_url": "https://flora.example",
        "default_label_preset": "large",
        "media_save_local_copy_default": False,
        "media_default_attribution": " Photo: Owner ",
        "media_default_licence_label": "CC BY 4.0",
        "media_default_licence_url": "https://creativecommons.org/licenses/by/4.0/",
    }
    status, _, saved = mutate(authenticated_browser, "PUT", PATH, payload)
    assert status == 200
    assert saved == {**payload, "media_default_attribution": "Photo: Owner"}
    assert request("GET", PATH, headers={"cookie": cookie})[2] == saved
    assert database_connection.execute(
        text(
            "SELECT media_save_local_copy_default, media_default_attribution, "
            "media_default_licence_label, media_default_licence_url "
            "FROM application_settings WHERE id=1"
        )
    ).one() == (False, "Photo: Owner", "CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/")
    cleared = {**saved, **MEDIA_DEFAULTS}
    assert mutate(authenticated_browser, "PUT", PATH, cleared)[2] == cleared
    assert request("GET", PATH, headers={"cookie": cookie})[2]["public_qr_base_url"] == (
        "https://flora.example"
    )
