import asyncio
import hashlib
import io
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile
from PIL import Image
from starlette.datastructures import Headers

from florabase.attachments.model import ATTACHMENT_MAX_BYTES
from florabase.attachments.service import AttachmentOperationError, create_attachment
from florabase.attachments.storage import (
    AttachmentStorage,
    AttachmentStorageError,
    StoredUpload,
    normalize_filename,
)


def image_bytes(format_name: str) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (3, 2), (24, 96, 32)).save(output, format=format_name)
    return output.getvalue()


def upload(content: bytes, filename: str, media_type: str) -> UploadFile:
    return UploadFile(
        io.BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": media_type}),
    )


@pytest.mark.parametrize(
    ("format_name", "media_type"),
    [("JPEG", "image/jpeg"), ("PNG", "image/png"), ("WEBP", "image/webp")],
)
def test_store_valid_supported_images(tmp_path: Path, format_name: str, media_type: str) -> None:
    storage = AttachmentStorage(tmp_path)
    content = image_bytes(format_name)
    stored = asyncio.run(storage.store_upload(upload(content, "../../ leaf.jpg", media_type)))

    assert stored.original_filename == ".._.._ leaf.jpg"
    assert stored.media_type == media_type
    assert stored.byte_size == len(content)
    assert stored.sha256 == hashlib.sha256(content).hexdigest()
    assert stored.path.read_bytes() == content
    assert stored.storage_key.startswith("objects/")
    assert "leaf.jpg" not in stored.storage_key
    assert not list(storage.temporary.iterdir())


@pytest.mark.parametrize(
    ("content", "filename", "media_type", "code"),
    [
        (b"<svg xmlns='http://www.w3.org/2000/svg'/>", "active.svg", "image/png", "invalid_image"),
        (b"GIF89a", "animated.gif", "image/gif", "unsupported_media_type"),
        (b"ftypheic", "camera.heic", "image/heic", "unsupported_media_type"),
        (b"ftypavif", "camera.avif", "image/avif", "unsupported_media_type"),
        (b"\x89PNG\r\n\x1a\ntruncated", "bad.png", "image/png", "invalid_image"),
        (b"", "empty.png", "image/png", "empty_attachment"),
    ],
)
def test_rejects_unsupported_empty_and_malformed_content(
    tmp_path: Path, content: bytes, filename: str, media_type: str, code: str
) -> None:
    storage = AttachmentStorage(tmp_path)
    with pytest.raises(AttachmentStorageError) as caught:
        asyncio.run(storage.store_upload(upload(content, filename, media_type)))
    assert caught.value.code == code
    assert not list(storage.temporary.iterdir())
    assert not list(storage.objects.rglob("*"))


def test_rejects_spoofed_supported_media_type(tmp_path: Path) -> None:
    storage = AttachmentStorage(tmp_path)
    with pytest.raises(AttachmentStorageError) as caught:
        asyncio.run(storage.store_upload(upload(image_bytes("PNG"), "actually.png", "image/jpeg")))
    assert caught.value.code == "media_type_mismatch"


def test_filename_normalization_is_bounded_and_path_agnostic() -> None:
    assert normalize_filename("/etc/passwd") == "_etc_passwd"
    assert normalize_filename("C:\\photos\\leaf.png") == "C:_photos_leaf.png"
    with pytest.raises(AttachmentStorageError, match="control"):
        normalize_filename("bad\r\nname.png")
    with pytest.raises(AttachmentStorageError, match="255"):
        normalize_filename("x" * 256)
    with pytest.raises(AttachmentStorageError):
        normalize_filename("..")


class ChunkUpload:
    def __init__(self, remaining: int) -> None:
        self.remaining = remaining

    async def read(self, size: int) -> bytes:
        count = min(size, self.remaining)
        self.remaining -= count
        return b"x" * count


def test_stream_enforces_exact_binary_limit(tmp_path: Path) -> None:
    storage = AttachmentStorage(tmp_path)
    with storage.temporary_file() as (stream, _):
        size, digest = asyncio.run(storage._stream(ChunkUpload(ATTACHMENT_MAX_BYTES - 1), stream))  # type: ignore[arg-type]
    assert size == ATTACHMENT_MAX_BYTES - 1
    assert len(digest) == 64

    with storage.temporary_file() as (stream, _):
        size, digest = asyncio.run(storage._stream(ChunkUpload(ATTACHMENT_MAX_BYTES), stream))  # type: ignore[arg-type]
    assert size == ATTACHMENT_MAX_BYTES
    assert len(digest) == 64

    with storage.temporary_file() as (stream, _), pytest.raises(AttachmentStorageError) as caught:
        asyncio.run(storage._stream(ChunkUpload(ATTACHMENT_MAX_BYTES + 1), stream))  # type: ignore[arg-type]
    assert caught.value.code == "attachment_too_large"
    assert not list(storage.temporary.iterdir())


def test_decompression_bomb_warning_fails_closed(tmp_path: Path) -> None:
    storage = AttachmentStorage(tmp_path)

    class BombImage:
        format = "PNG"
        n_frames = 1

        def __enter__(self) -> BombImage:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def load(self) -> None:
            raise Image.DecompressionBombWarning("unsafe dimensions")

    with (
        patch("florabase.attachments.storage.Image.open", return_value=BombImage()),
        pytest.raises(AttachmentStorageError) as caught,
    ):
        storage._validate_image(io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")
    assert caught.value.code == "unsafe_image_dimensions"


def test_storage_root_and_resolved_paths_fail_closed(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(AttachmentStorageError):
        AttachmentStorage(missing)
    invalid_file = tmp_path / "file"
    invalid_file.write_text("not a directory")
    with pytest.raises(AttachmentStorageError):
        AttachmentStorage(invalid_file)

    storage_root = tmp_path / "root"
    storage_root.mkdir()
    storage = AttachmentStorage(storage_root)
    outside = tmp_path / "outside"
    outside.write_bytes(b"outside")
    key = "objects/aa/" + "a" * 32
    key_path = storage.root / key
    key_path.parent.mkdir()
    key_path.symlink_to(outside)
    with pytest.raises(AttachmentStorageError) as read_error:
        storage.active_path(key, len(b"outside"))
    assert read_error.value.code == "unsafe_storage_path"
    with pytest.raises(AttachmentStorageError) as delete_error:
        storage.delete_file(key)
    assert delete_error.value.code == "unsafe_storage_path"
    assert outside.read_bytes() == b"outside"


def test_write_and_rename_failures_leave_no_temporary_file(tmp_path: Path) -> None:
    storage = AttachmentStorage(tmp_path)
    image = upload(image_bytes("PNG"), "leaf.png", "image/png")
    with (
        patch("florabase.attachments.storage.os.replace", side_effect=OSError("disk")),
        pytest.raises(AttachmentStorageError) as caught,
    ):
        asyncio.run(storage.store_upload(image))
    assert caught.value.code == "attachment_storage_write_failed"
    assert not list(storage.temporary.iterdir())


def test_database_failure_cleans_finalized_file(tmp_path: Path) -> None:
    final_path = tmp_path / "stored"
    final_path.write_bytes(b"image")
    stored = StoredUpload(
        "objects/aa/" + "a" * 32,
        "leaf.png",
        "image/png",
        5,
        hashlib.sha256(b"image").hexdigest(),
        final_path,
    )
    storage = MagicMock()
    storage.store_upload = AsyncMock(return_value=stored)
    database = MagicMock()
    database.commit.side_effect = RuntimeError("database failed")

    with pytest.raises(AttachmentOperationError) as caught:
        asyncio.run(create_attachment(database, storage, upload(b"image", "leaf.png", "image/png")))
    assert caught.value.code == "attachment_metadata_write_failed"
    assert not final_path.exists()
    database.rollback.assert_called_once()


def test_delete_file_reports_missing_and_unlink_failure(tmp_path: Path) -> None:
    storage = AttachmentStorage(tmp_path)
    key = "objects/aa/" + "a" * 32
    assert storage.delete_file(key) is False
    path = storage.root / key
    path.parent.mkdir()
    path.write_bytes(b"image")
    with (
        patch.object(Path, "unlink", side_effect=OSError("read only")),
        pytest.raises(AttachmentStorageError) as caught,
    ):
        storage.delete_file(key)
    assert caught.value.code == "attachment_delete_failed"
    assert os.path.exists(path)
