import io
import os
import subprocess
import sys
import tarfile
from pathlib import Path

from florabase.attachments.storage import AttachmentStorage


def environment(root: Path) -> dict[str, str]:
    result = os.environ.copy()
    result["FLORABASE_ATTACHMENT_STORAGE_ROOT"] = str(root)
    result["FLORABASE_ATTACHMENT_MAX_BYTES"] = str(25 * 1024 * 1024)
    return result


def run_artifacts(
    command: str, root: Path, *, input_bytes: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "scripts/attachment_artifacts.py", command],
        cwd=Path(__file__).parents[1],
        env=environment(root),
        input=input_bytes,
        capture_output=True,
        check=False,
    )


def test_archive_validation_and_restore_round_trip(tmp_path: Path) -> None:
    storage = AttachmentStorage(tmp_path)
    key = "objects/aa/" + "a" * 32
    source = storage.root / key
    source.parent.mkdir()
    source.write_bytes(b"stored attachment")

    archived = run_artifacts("archive", tmp_path)
    assert archived.returncode == 0
    assert archived.stdout
    validated = run_artifacts("validate-archive", tmp_path, input_bytes=archived.stdout)
    assert validated.returncode == 0
    assert b"1 file(s)" in validated.stdout

    source.unlink()
    restored = run_artifacts("restore", tmp_path, input_bytes=archived.stdout)
    assert restored.returncode == 0
    assert source.read_bytes() == b"stored attachment"
    assert source.stat().st_mode & 0o777 == 0o600
    assert not list(storage.temporary.iterdir())


def test_archive_validation_rejects_traversal_and_links(tmp_path: Path) -> None:
    for name, kind in (
        ("../escape", "file"),
        ("objects/aa/" + "a" * 32, "link"),
        ("objects/bb/" + "b" * 32, "empty"),
    ):
        payload = io.BytesIO()
        with tarfile.open(fileobj=payload, mode="w") as archive:
            member = tarfile.TarInfo(name)
            if kind == "link":
                member.type = tarfile.SYMTYPE
                member.linkname = "/etc/passwd"
                archive.addfile(member)
            elif kind == "empty":
                archive.addfile(member)
            else:
                content = b"escape"
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
        result = run_artifacts("validate-archive", tmp_path, input_bytes=payload.getvalue())
        assert result.returncode != 0
        assert (
            b"unsupported archive member" in result.stderr
            or b"unsafe archive member" in result.stderr
            or b"invalid attachment size" in result.stderr
        )
    assert not (tmp_path.parent / "escape").exists()
