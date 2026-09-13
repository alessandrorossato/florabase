#!/usr/bin/env python3
import argparse
import hashlib
import os
import re
import shutil
import sys
import tarfile
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path, PurePosixPath
from typing import NoReturn
from uuid import uuid7

from sqlalchemy import select
from sqlalchemy.orm import Session

from florabase.attachments.model import ATTACHMENT_MAX_BYTES, Attachment, AttachmentState
from florabase.attachments.storage import AttachmentStorage, AttachmentStorageError
from florabase.core.config import get_settings
from florabase.db.session import get_engine

KEY_PATTERN = re.compile(r"objects/[0-9a-f]{2}/[0-9a-f]{32}\Z")
DIRECTORY_PATTERN = re.compile(r"objects(?:/[0-9a-f]{2})?\Z")


def fail(message: str) -> NoReturn:
    raise SystemExit(f"attachment artifacts: {message}")


def storage() -> AttachmentStorage:
    try:
        return AttachmentStorage.from_settings(get_settings())
    except AttachmentStorageError as error:
        fail(error.message)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def verify() -> None:
    attachment_storage = storage()
    verified = 0
    with Session(get_engine()) as database:
        attachments = list(database.scalars(select(Attachment).order_by(Attachment.id)))
    for attachment in attachments:
        try:
            path = attachment_storage.active_path(attachment.storage_key, attachment.byte_size)
        except AttachmentStorageError as error:
            if (
                attachment.state == AttachmentState.PENDING_DELETE
                and error.code == "attachment_content_missing"
            ):
                continue
            fail(f"{attachment.id}: {error.message}")
        try:
            actual_digest = digest(path)
        except OSError as error:
            fail(f"{attachment.id}: could not read stored content: {error}")
        if actual_digest != attachment.sha256:
            fail(f"{attachment.id}: SHA-256 does not match metadata")
        verified += 1
    sys.stdout.write(f"Verified {verified} stored attachment file(s) against database metadata\n")


def iter_archive_paths(attachment_storage: AttachmentStorage) -> Iterator[Path]:
    yield attachment_storage.objects
    for path in sorted(attachment_storage.objects.rglob("*")):
        if path.is_symlink():
            fail(
                f"unsafe symlink in attachment storage: {path.relative_to(attachment_storage.root)}"
            )
        relative = path.relative_to(attachment_storage.root).as_posix()
        if path.is_dir() and not DIRECTORY_PATTERN.fullmatch(relative):
            fail(f"unexpected directory in attachment storage: {relative}")
        if path.is_file() and not KEY_PATTERN.fullmatch(relative):
            fail(f"unexpected file in attachment storage: {relative}")
        if not path.is_dir() and not path.is_file():
            fail(f"unsupported filesystem entry in attachment storage: {relative}")
        yield path


def archive() -> None:
    attachment_storage = storage()
    with tarfile.open(fileobj=sys.stdout.buffer, mode="w|") as output:
        for path in iter_archive_paths(attachment_storage):
            output.add(
                path,
                arcname=path.relative_to(attachment_storage.root).as_posix(),
                recursive=False,
            )


def normalized_member_name(member: tarfile.TarInfo) -> str:
    name = PurePosixPath(member.name).as_posix()
    if name.startswith("/") or ".." in PurePosixPath(name).parts:
        fail(f"unsafe archive member: {member.name}")
    if member.isdir() and DIRECTORY_PATTERN.fullmatch(name):
        return name
    if member.isfile() and KEY_PATTERN.fullmatch(name):
        if not 1 <= member.size <= ATTACHMENT_MAX_BYTES:
            fail(f"invalid attachment size in archive: {name}")
        return name
    fail(f"unsupported archive member: {member.name}")


def validate_archive(path: Path | None = None) -> int:
    source = path.open("rb") if path is not None else sys.stdin.buffer
    count = 0
    try:
        with tarfile.open(fileobj=source, mode="r|*") as incoming:
            seen: set[str] = set()
            for member in incoming:
                name = normalized_member_name(member)
                if name in seen:
                    fail(f"duplicate archive member: {name}")
                seen.add(name)
                if member.isfile():
                    count += 1
    except (OSError, tarfile.TarError) as error:
        fail(f"invalid attachment archive: {error}")
    finally:
        if path is not None:
            source.close()
    return count


@contextmanager
def staged_restore(attachment_storage: AttachmentStorage) -> Iterator[tuple[Path, Path]]:
    identifier = uuid7().hex
    archive_path = attachment_storage.temporary / f"restore-{identifier}.tar"
    stage = attachment_storage.root / f".restore-{identifier}"
    stage.mkdir(mode=0o700)
    try:
        with archive_path.open("xb") as destination:
            shutil.copyfileobj(sys.stdin.buffer, destination, 1024 * 1024)
            destination.flush()
            os.fsync(destination.fileno())
        yield archive_path, stage
    finally:
        with suppress(OSError):
            archive_path.unlink(missing_ok=True)
        shutil.rmtree(stage, ignore_errors=True)


def extract_archive(archive_path: Path, stage: Path) -> int:
    count = 0
    seen: set[str] = set()
    with tarfile.open(archive_path, mode="r:*") as incoming:
        for member in incoming:
            name = normalized_member_name(member)
            if name in seen:
                fail(f"duplicate archive member: {name}")
            seen.add(name)
            destination = stage.joinpath(*PurePosixPath(name).parts)
            destination.resolve(strict=False).relative_to(stage)
            if member.isdir():
                destination.mkdir(mode=0o700, parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            source = incoming.extractfile(member)
            if source is None:
                fail(f"could not read archive member: {name}")
            with source, destination.open("xb") as output:
                shutil.copyfileobj(source, output, 1024 * 1024)
            destination.chmod(0o600)
            count += 1
    (stage / "objects").mkdir(mode=0o700, exist_ok=True)
    return count


def restore() -> None:
    attachment_storage = storage()
    with staged_restore(attachment_storage) as (archive_path, stage):
        validate_archive(archive_path)
        count = extract_archive(archive_path, stage)
        previous = attachment_storage.root / f".previous-{uuid7().hex}"
        attachment_storage.objects.rename(previous)
        try:
            (stage / "objects").rename(attachment_storage.objects)
        except OSError:
            previous.rename(attachment_storage.objects)
            raise
        shutil.rmtree(previous)
    sys.stdout.write(f"Restored {count} attachment file(s)\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and move Florabase attachment artifacts")
    parser.add_argument("command", choices=("verify", "archive", "validate-archive", "restore"))
    args = parser.parse_args()
    if args.command == "verify":
        verify()
    elif args.command == "archive":
        archive()
    elif args.command == "validate-archive":
        sys.stdout.write(f"Validated attachment archive with {validate_archive()} file(s)\n")
    else:
        restore()


if __name__ == "__main__":
    main()
