"""Disposable, bounded raster files in the existing durable media volume (not media objects)."""

import fcntl
import json
import os
import re
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from uuid import UUID

from PIL import Image, UnidentifiedImageError

from florabase.external_botany.provider import (
    GBIF_COL_XR_CHECKLIST_KEY,
    MAX_OCCURRENCE_TILE_BYTES,
    OccurrenceTile,
)

CONTRACT = (
    f"gbif-{GBIF_COL_XR_CHECKLIST_KEY}-present-coordinate-no-geospatial-issue-"
    "3857-hex51-geobounds-purpleYellow-noborder-Hx-v1"
)
FILE_PATTERN = re.compile(r"[a-f0-9]{64}\.[a-f0-9]{32}\.\d+\.\d+\.\d+\.tile\Z")


def contract_key(external_id: str) -> str:
    return sha256(f"{CONTRACT}\0{external_id}".encode()).hexdigest()


def cacheable(policy: str | None) -> bool:
    directives = {part.strip().split("=", 1)[0].lower() for part in (policy or "").split(",")}
    return not directives.intersection({"no-store", "no-cache", "must-revalidate"})


def validate_png(content: bytes) -> None:
    if not 0 < len(content) <= MAX_OCCURRENCE_TILE_BYTES:
        raise ValueError("Invalid tile size")
    try:
        with Image.open(BytesIO(content)) as image:
            if image.format != "PNG" or not (0 < image.width <= 1024 and 0 < image.height <= 1024):
                raise ValueError("Invalid tile format or dimensions")
            image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as error:
        raise ValueError("Invalid PNG") from error


class TileCache:
    def __init__(
        self,
        root: Path,
        *,
        total_bytes: int = 512 * 1024 * 1024,
        taxon_bytes: int = 64 * 1024 * 1024,
        max_files: int = 4096,
    ) -> None:
        self.root = root / "occurrence-cache-v1"
        self.total_bytes = total_bytes
        self.taxon_bytes = taxon_bytes
        self.max_files = max_files

    @contextmanager
    def locked(self) -> Iterator[None]:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.is_symlink():
            raise ValueError("Unsafe cache directory")
        descriptor = os.open(self.root / ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def path(self, key: str, generation: UUID, z: int, x: int, y: int) -> Path:
        if (
            not re.fullmatch(r"[a-f0-9]{64}", key)
            or not 0 <= z <= 16
            or not (0 <= x < 1 << z and 0 <= y < 1 << z)
        ):
            raise ValueError("Invalid tile key")
        return self.root / f"{key}.{generation.hex}.{z}.{x}.{y}.tile"

    def read(
        self, key: str, generation: UUID, z: int, x: int, y: int
    ) -> tuple[OccurrenceTile | None, str] | None:
        path = self.path(key, generation, z, x, y)
        with self.locked():
            try:
                descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
                with os.fdopen(descriptor, "rb") as stream:
                    metadata = json.loads(stream.readline(4096))
                    content = stream.read(MAX_OCCURRENCE_TILE_BYTES + 1)
                obtained = str(metadata["obtained_at"])
                policy = metadata.get("cache_control")
                if policy is not None and not isinstance(policy, str):
                    return None
                if not cacheable(metadata.get("cache_control")):
                    return None
                if content:
                    validate_png(content)
                elif not metadata.get("empty"):
                    return None
                os.utime(path, None)
                return (OccurrenceTile(content, "image/png") if content else None, obtained)
            except (OSError, ValueError, KeyError, TypeError) as _error:
                return None

    def write(
        self,
        key: str,
        generation: UUID,
        z: int,
        x: int,
        y: int,
        tile: OccurrenceTile | None,
        *,
        policy: str | None = None,
    ) -> bool:
        if not cacheable(policy):
            return False
        content = b"" if tile is None else tile.content
        if tile is not None:
            validate_png(content)
        data = (
            json.dumps(
                {
                    "empty": tile is None,
                    "obtained_at": datetime.now(UTC).isoformat(),
                    "cache_control": policy,
                }
            ).encode()
            + b"\n"
            + content
        )
        if len(data) > min(self.total_bytes, self.taxon_bytes):
            return False
        path = self.path(key, generation, z, x, y)
        with self.locked():
            # All cache files are flat, server-derived and globally bounded. Never follow symlinks.
            files: list[tuple[Path, int, float]] = []
            for item in self.root.iterdir():
                if item.name.startswith(".writing-") and not item.is_symlink() and item.is_file():
                    item.unlink(missing_ok=True)
                    continue
                if not FILE_PATTERN.fullmatch(item.name) or item.is_symlink():
                    continue
                stat = item.stat()
                if time.time() - stat.st_mtime > 90 * 86400:
                    item.unlink()
                elif item != path:
                    files.append((item, stat.st_size, stat.st_mtime))
            files.sort(key=lambda item: item[2])
            while files and (
                sum(size for _, size, _ in files) + len(data) > self.total_bytes
                or sum(size for name, size, _ in files if name.name.startswith(key)) + len(data)
                > self.taxon_bytes
                or len(files) >= self.max_files
            ):
                # Per-taxon pressure must evict that taxon's entries, not unrelated evidence.
                per_taxon = (
                    sum(size for name, size, _ in files if name.name.startswith(key)) + len(data)
                    > self.taxon_bytes
                )
                index = next(
                    (
                        i
                        for i, (name, _, _) in enumerate(files)
                        if not per_taxon or name.name.startswith(key)
                    ),
                    0,
                )
                victim, _, _ = files.pop(index)
                victim.unlink(missing_ok=True)
            descriptor, temporary = tempfile.mkstemp(prefix=".writing-", dir=self.root)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, path)
            finally:
                Path(temporary).unlink(missing_ok=True)
        return True

    def clear(self, key: str) -> None:
        if not re.fullmatch(r"[a-f0-9]{64}", key):
            raise ValueError("Invalid tile key")
        with self.locked():
            for item in self.root.iterdir():
                if (
                    item.name.startswith(key + ".")
                    and FILE_PATTERN.fullmatch(item.name)
                    and not item.is_symlink()
                ):
                    item.unlink(missing_ok=True)
