import pytest
from pydantic import ValidationError

from florabase.application_settings.schemas import ApplicationSettingsValue


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
    settings = ApplicationSettingsValue(public_qr_base_url=value, default_label_preset="medium")
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
        ApplicationSettingsValue(public_qr_base_url=value, default_label_preset="medium")


def test_settings_contract_rejects_unknown_fields_and_preset() -> None:
    with pytest.raises(ValidationError):
        ApplicationSettingsValue.model_validate(
            {"public_qr_base_url": None, "default_label_preset": "huge"}
        )
    with pytest.raises(ValidationError):
        ApplicationSettingsValue.model_validate(
            {"public_qr_base_url": None, "default_label_preset": "small", "theme": "dark"}
        )
