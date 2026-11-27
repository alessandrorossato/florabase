import pytest
from pydantic import ValidationError

from florabase.application_settings.schemas import ApplicationSettingsValue

MEDIA = {
    "media_save_local_copy_default": True,
    "media_default_attribution": None,
    "media_default_licence_label": None,
    "media_default_licence_url": None,
}


@pytest.mark.parametrize(
    ("value", "normalized"),
    [
        (None, None),
        ("https://FLORA.example/", "https://flora.example"),
        ("http://localhost:8080/", "http://localhost:8080"),
        ("https://flora.example:443/", "https://flora.example"),
    ],
)
def test_public_qr_origin_normalization(value: str | None, normalized: str | None) -> None:
    settings = ApplicationSettingsValue(
        public_qr_base_url=value, default_label_preset="medium", **MEDIA
    )
    assert settings.public_qr_base_url == normalized


@pytest.mark.parametrize(
    "value",
    [
        "flora.example",
        "https:///",
        "ftp://flora.example",
        "//flora.example",
        "https://flora.example/path",
        "https://flora.example/..",
        "https://flora.example/./",
        "https://@flora.example",
        "https://flora.example/?x=1",
        "https://flora.example/#x",
        "https://flora.example?",
        "https://flora.example#",
        "https://user:pass@flora.example",
        "https://flora.example:bad",
        "https://fl ora.example",
        "",
        "https://flora.example/\npath",
        "https://" + "a" * 201 + ".example",
    ],
)
def test_invalid_public_qr_url(value: str) -> None:
    with pytest.raises(ValidationError):
        ApplicationSettingsValue(public_qr_base_url=value, default_label_preset="medium", **MEDIA)


def test_settings_contract_rejects_unknown_fields_and_preset() -> None:
    with pytest.raises(ValidationError):
        ApplicationSettingsValue.model_validate(
            {"public_qr_base_url": None, "default_label_preset": "huge", **MEDIA}
        )
    with pytest.raises(ValidationError):
        ApplicationSettingsValue.model_validate(
            {"public_qr_base_url": None, "default_label_preset": "small", "theme": "dark", **MEDIA}
        )


def test_media_defaults_are_normalized_and_required() -> None:
    settings = ApplicationSettingsValue.model_validate(
        {
            "public_qr_base_url": None,
            "default_label_preset": "medium",
            "media_save_local_copy_default": False,
            "media_default_attribution": "  Photo: Owner\r\n ",
            "media_default_licence_label": "   ",
            "media_default_licence_url": " https://creativecommons.org/licenses/by/4.0/ ",
        }
    )
    assert settings.media_save_local_copy_default is False
    assert settings.media_default_attribution == "Photo: Owner"
    assert settings.media_default_licence_label is None
    assert settings.media_default_licence_url == "https://creativecommons.org/licenses/by/4.0/"
    # A full-replace PUT must not silently reset media defaults that a stale client omits.
    with pytest.raises(ValidationError):
        ApplicationSettingsValue.model_validate(
            {"public_qr_base_url": None, "default_label_preset": "medium"}
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("media_default_licence_url", "http://creativecommons.org/licenses/by/4.0/"),
        ("media_default_licence_url", "https://licence.example:99999/"),
        ("media_default_licence_url", "creativecommons.org"),
        ("media_default_attribution", "x" * 2001),
        ("media_default_attribution", "bad\x00credit"),
        ("media_save_local_copy_default", "maybe"),
    ],
)
def test_invalid_media_defaults(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        ApplicationSettingsValue.model_validate(
            {"public_qr_base_url": None, "default_label_preset": "medium", **MEDIA, field: value}
        )
