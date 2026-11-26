"""Pure label-pattern normalization and expansion for batch propagation operations."""

import unicodedata

MAX_BATCH_COUNT = 200
MAX_LABEL_LENGTH = 255
COUNTER_PLACEHOLDER = "{n}"


def normalize_single_line(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    if any(unicodedata.category(character) == "Cc" for character in normalized):
        raise ValueError("Value must not contain control characters")
    return normalized


def default_counter_padding(count: int, counter_start: int = 1) -> int:
    if count < 1:
        raise ValueError("Count must be at least 1")
    if counter_start < 0:
        raise ValueError("Counter start must be non-negative")
    last_number = counter_start + count - 1
    return len(str(last_number))


def expand_label_pattern(
    pattern: str | None,
    *,
    count: int,
    counter_start: int = 1,
    counter_padding: int | None = None,
) -> list[str | None]:
    if count < 1 or count > MAX_BATCH_COUNT:
        raise ValueError(f"Count must be between 1 and {MAX_BATCH_COUNT}")
    if counter_start < 0:
        raise ValueError("Counter start must be non-negative")
    if counter_padding is not None and counter_padding < 0:
        raise ValueError("Counter padding must be non-negative")
    normalized = normalize_single_line(pattern)
    if normalized is None:
        return [None] * count
    padding = (
        default_counter_padding(count, counter_start)
        if counter_padding is None
        else counter_padding
    )
    labels: list[str | None] = []
    for offset in range(count):
        number = counter_start + offset
        formatted = str(number).zfill(padding)
        expanded = normalized.replace(COUNTER_PLACEHOLDER, formatted)
        if len(expanded) > MAX_LABEL_LENGTH:
            raise ValueError(f"Expanded label must not exceed {MAX_LABEL_LENGTH} characters")
        labels.append(expanded)
    return labels
