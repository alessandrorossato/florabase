import hashlib
import os
import re
import tempfile
import unicodedata
import warnings
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO
from uuid import uuid7

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from florabase.attachments.model import ATTACHMENT_MAX_BYTES, SUPPORTED_MEDIA_TYPES
from florabase.core.config import Settings

CHUNK_SIZE = 1024 * 1024
STORAGE_KEY_PATTERN = re.compile(r"objects/[0-9a-f]{2}/[0-9a-f]{32}\Z")
FORMAT_MEDIA_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


@dataclass
class AttachmentStorageError(Exception):
    code: str
    message: str


@dataclass(frozen=True)
class StoredUpload:
    storage_key: str
    original_filename: str
    media_type: str
    byte_size: int
    sha256: str
    path: Path


def normalize_filename(value: str | None) -> str:
    if value is None:
        raise AttachmentStorageError("invalid_filename", "An original filename is required")
    normalized = unicodedata.normalize("NFKC", value)
    if any(unicodedata.category(character) == "Cc" for character in normalized):
        raise AttachmentStorageError(
            "invalid_filename", "The filename contains unsupported control characters"
        )
    normalized = " ".join(normalized.split()).strip().replace("/", "_").replace("\\", "_")
    if normalized in {"", ".", ".."}:
        raise AttachmentStorageError("invalid_filename", "The filename is not usable")
    if len(normalized) > 255:
        raise AttachmentStorageError(
            "invalid_filename", "The filename must contain at most 255 characters"
        )
    return normalized


class AttachmentStorage:
    def __init__(self, root: Path, max_bytes: int = ATTACHMENT_MAX_BYTES) -> None:
        try:
            resolved_root = root.resolve(strict=True)
        except OSError as error:
            raise AttachmentStorageError(
                "attachment_storage_unavailable", "Attachment storage is not configured correctly"
            ) from error
        if (
            not root.is_absolute()
            or not resolved_root.is_dir()
            or resolved_root == Path(resolved_root.anchor)
            or not os.access(resolved_root, os.R_OK | os.W_OK | os.X_OK)
        ):
            raise AttachmentStorageError(
                "attachment_storage_unavailable", "Attachment storage is not configured correctly"
            )
        self.root = resolved_root
        self.max_bytes = max_bytes
        self.objects = self._owned_directory("objects")
        self.temporary = self._owned_directory(".tmp")

    @classmethod
    def from_settings(cls, settings: Settings) -> AttachmentStorage:
        return cls(settings.attachment_storage_root, settings.attachment_max_bytes)

    def _owned_directory(self, name: str) -> Path:
        path = self.root / name
        if path.is_symlink():
            raise AttachmentStorageError(
                "attachment_storage_unavailable", "Attachment storage contains an unsafe symlink"
            )
        try:
            path.mkdir(mode=0o700, exist_ok=True)
            resolved = path.resolve(strict=True)
            resolved.relative_to(self.root)
        except (OSError, ValueError) as error:
            raise AttachmentStorageError(
                "attachment_storage_unavailable", "Attachment storage is not configured correctly"
            ) from error
        if not resolved.is_dir():
            raise AttachmentStorageError(
                "attachment_storage_unavailable", "Attachment storage is not configured correctly"
            )
        return resolved

    def new_storage_key(self) -> str:
        identifier = uuid7().hex
        return f"objects/{identifier[:2]}/{identifier}"

    def _candidate(self, storage_key: str) -> Path:
        if not STORAGE_KEY_PATTERN.fullmatch(storage_key):
            raise AttachmentStorageError(
                "unsafe_storage_key", "Stored attachment location is invalid"
            )
        relative = PurePosixPath(storage_key)
        candidate = self.root.joinpath(*relative.parts)
        if candidate.is_symlink():
            raise AttachmentStorageError(
                "unsafe_storage_path", "Stored attachment location is unsafe"
            )
        try:
            candidate.resolve(strict=False).relative_to(self.root)
        except (OSError, ValueError) as error:
            raise AttachmentStorageError(
                "unsafe_storage_path", "Stored attachment location is unsafe"
            ) from error
        return candidate

    def _prepare_destination(self, storage_key: str) -> Path:
        destination = self._candidate(storage_key)
        parent = destination.parent
        if parent.is_symlink():
            raise AttachmentStorageError(
                "unsafe_storage_path", "Stored attachment location is unsafe"
            )
        try:
            parent.mkdir(mode=0o700, exist_ok=True)
            parent.resolve(strict=True).relative_to(self.root)
        except (OSError, ValueError) as error:
            raise AttachmentStorageError(
                "attachment_storage_write_failed", "Could not prepare attachment storage"
            ) from error
        if destination.exists() or destination.is_symlink():
            raise AttachmentStorageError(
                "attachment_storage_collision", "Generated attachment storage key already exists"
            )
        return destination

    @contextmanager
    def temporary_file(self) -> Iterator[tuple[BinaryIO, Path]]:
        descriptor = -1
        path: Path | None = None
        try:
            descriptor, raw_path = tempfile.mkstemp(prefix="upload-", dir=self.temporary)
            path = Path(raw_path)
            with os.fdopen(descriptor, "w+b") as stream:
                descriptor = -1
                yield stream, path
        except OSError as error:
            raise AttachmentStorageError(
                "attachment_storage_write_failed", "Could not write attachment content"
            ) from error
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if path is not None:
                with suppress(OSError):
                    path.unlink(missing_ok=True)

    async def store_upload(self, upload: UploadFile) -> StoredUpload:
        filename = normalize_filename(upload.filename)
        claimed_media_type = upload.content_type
        if claimed_media_type not in SUPPORTED_MEDIA_TYPES:
            raise AttachmentStorageError(
                "unsupported_media_type", "Only JPEG, PNG, and WebP images are supported"
            )

        try:
            with self.temporary_file() as (stream, temporary_path):
                byte_size, digest = await self._stream(upload, stream)
                media_type = self._validate_image(stream, claimed_media_type)
                storage_key = self.new_storage_key()
                destination = self._prepare_destination(storage_key)
                try:
                    os.replace(temporary_path, destination)
                except OSError as error:
                    raise AttachmentStorageError(
                        "attachment_storage_write_failed", "Could not finalize attachment content"
                    ) from error
                return StoredUpload(
                    storage_key=storage_key,
                    original_filename=filename,
                    media_type=media_type,
                    byte_size=byte_size,
                    sha256=digest,
                    path=destination,
                )
        finally:
            await upload.close()

    async def _stream(self, upload: UploadFile, stream: BinaryIO) -> tuple[int, str]:
        byte_size = 0
        digest = hashlib.sha256()
        while chunk := await upload.read(CHUNK_SIZE):
            byte_size += len(chunk)
            if byte_size > self.max_bytes:
                raise AttachmentStorageError(
                    "attachment_too_large",
                    f"Attachment payload exceeds the {self.max_bytes}-byte limit",
                )
            try:
                stream.write(chunk)
            except OSError as error:
                raise AttachmentStorageError(
                    "attachment_storage_write_failed", "Could not write attachment content"
                ) from error
            digest.update(chunk)
        if byte_size == 0:
            raise AttachmentStorageError("empty_attachment", "Attachment content must not be empty")
        stream.flush()
        os.fsync(stream.fileno())
        return byte_size, digest.hexdigest()

    def _validate_image(self, stream: BinaryIO, claimed_media_type: str) -> str:
        stream.seek(0)
        signature = stream.read(12)
        signature_format = self._signature_format(signature)
        if signature_format is None:
            raise AttachmentStorageError(
                "invalid_image", "Attachment content is not a supported image"
            )
        stream.seek(0)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(stream) as image:
                    detected_format = image.format
                    if getattr(image, "n_frames", 1) != 1:
                        raise AttachmentStorageError(
                            "animated_image_not_supported", "Animated images are not supported"
                        )
                    image.load()
        except AttachmentStorageError:
            raise
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
            raise AttachmentStorageError(
                "unsafe_image_dimensions", "Image dimensions exceed the safe decoding limit"
            ) from error
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
            raise AttachmentStorageError(
                "invalid_image", "Attachment content is malformed or truncated"
            ) from error
        if detected_format != signature_format or detected_format not in FORMAT_MEDIA_TYPES:
            raise AttachmentStorageError(
                "invalid_image", "Attachment content is not a supported image"
            )
        detected_media_type = FORMAT_MEDIA_TYPES[detected_format]
        if detected_media_type != claimed_media_type:
            raise AttachmentStorageError(
                "media_type_mismatch", "Declared media type does not match the image content"
            )
        return detected_media_type

    @staticmethod
    def _signature_format(signature: bytes) -> str | None:
        if signature.startswith(b"\xff\xd8\xff"):
            return "JPEG"
        if signature.startswith(b"\x89PNG\r\n\x1a\n"):
            return "PNG"
        if len(signature) >= 12 and signature[:4] == b"RIFF" and signature[8:12] == b"WEBP":
            return "WEBP"
        return None

    def active_path(self, storage_key: str, expected_size: int) -> Path:
        candidate = self._candidate(storage_key)
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(self.root)
            stat = resolved.stat()
        except FileNotFoundError as error:
            raise AttachmentStorageError(
                "attachment_content_missing", "Attachment metadata points to missing content"
            ) from error
        except (OSError, ValueError) as error:
            raise AttachmentStorageError(
                "unsafe_storage_path", "Stored attachment location is unsafe"
            ) from error
        if not resolved.is_file() or candidate.is_symlink():
            raise AttachmentStorageError(
                "unsafe_storage_path", "Stored attachment location is unsafe"
            )
        if stat.st_size != expected_size:
            raise AttachmentStorageError(
                "attachment_content_mismatch", "Attachment content size does not match metadata"
            )
        return resolved

    def delete_file(self, storage_key: str) -> bool:
        candidate = self._candidate(storage_key)
        if candidate.is_symlink():
            raise AttachmentStorageError(
                "unsafe_storage_path", "Stored attachment location is unsafe"
            )
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(self.root)
        except FileNotFoundError:
            return False
        except (OSError, ValueError) as error:
            raise AttachmentStorageError(
                "unsafe_storage_path", "Stored attachment location is unsafe"
            ) from error
        if not resolved.is_file():
            raise AttachmentStorageError(
                "unsafe_storage_path", "Stored attachment location is unsafe"
            )
        try:
            resolved.unlink()
        except OSError as error:
            raise AttachmentStorageError(
                "attachment_delete_failed", "Could not remove attachment content"
            ) from error
        return True
