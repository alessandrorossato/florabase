import pytest
from pydantic import ValidationError

from florabase.botanical_profiles.schemas import BotanicalProfilePut


def test_profile_text_normalizes_outer_whitespace_and_preserves_prose() -> None:
    payload = BotanicalProfilePut(
        description="  First paragraph.\r\n\r\nSecond  paragraph.  ",
        cultivation="\t General guidance\nwith a useful line break. \n",
        uses="   ",
    )

    assert payload.description == "First paragraph.\n\nSecond  paragraph."
    assert payload.cultivation == "General guidance\nwith a useful line break."
    assert payload.uses is None
    assert not payload.is_empty


def test_profile_allows_partial_and_empty_replacement_payloads() -> None:
    assert BotanicalProfilePut(warnings="Handle with gloves.").model_dump() == {
        "description": None,
        "origin_distribution": None,
        "cultivation": None,
        "uses": None,
        "warnings": "Handle with gloves.",
    }
    assert BotanicalProfilePut().is_empty


@pytest.mark.parametrize(
    "payload",
    [
        {"description": "text\x00control"},
        {"warnings": "text\x1fcontrol"},
        {"description": "x" * 20_001},
        {"unknown": "value"},
        {"botanical_identity_id": "01900000-0000-7000-8000-000000000001"},
    ],
)
def test_profile_rejects_invalid_or_read_only_content(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        BotanicalProfilePut.model_validate(payload)
