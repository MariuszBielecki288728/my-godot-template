import hashlib
import zipfile
from pathlib import Path

import pytest

from godot_devtools.archives import extract_github_zip, verify_sha256


def write_zip(path: Path, members: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def test_verify_sha256_accepts_matching_archive(tmp_path: Path) -> None:
    archive = tmp_path / "archive.zip"
    archive.write_bytes(b"known content")
    verify_sha256(
        name="fixture",
        expected=hashlib.sha256(archive.read_bytes()).hexdigest(),
        url="https://github.com/example/fixture.zip",
        archive=archive,
    )


def test_verify_sha256_rejects_wrong_hash(tmp_path: Path) -> None:
    archive = tmp_path / "archive.zip"
    archive.write_bytes(b"known content")
    with pytest.raises(RuntimeError, match="integrity check failed"):
        verify_sha256(
            name="fixture",
            expected="0" * 64,
            url="https://github.com/example/fixture.zip",
            archive=archive,
        )


def test_extract_zip_strips_single_root(tmp_path: Path) -> None:
    archive = tmp_path / "archive.zip"
    write_zip(archive, {"project-1.0/addon/file.txt": "contents"})
    extracted = extract_github_zip(
        archive, tmp_path / "output", strip_root=True, target="addons/demo"
    )
    assert extracted == (tmp_path / "output").resolve()
    assert (extracted / "addon/file.txt").read_text() == "contents"


@pytest.mark.parametrize("member", ["../escape.txt", "/escape.txt", "C:/escape.txt"])
def test_extract_zip_rejects_unsafe_member(tmp_path: Path, member: str) -> None:
    archive = tmp_path / "archive.zip"
    write_zip(archive, {member: "bad"})
    with pytest.raises(RuntimeError, match="unsafe"):
        extract_github_zip(archive, tmp_path / "output", strip_root=False, target="addons/demo")


def test_extract_zip_rejects_empty_archive(tmp_path: Path) -> None:
    archive = tmp_path / "archive.zip"
    write_zip(archive, {})
    with pytest.raises(RuntimeError, match="empty"):
        extract_github_zip(archive, tmp_path / "output", strip_root=True, target="addons/demo")


def test_extract_zip_requires_one_root_when_stripping(tmp_path: Path) -> None:
    archive = tmp_path / "archive.zip"
    write_zip(archive, {"first/file.txt": "a", "second/file.txt": "b"})
    with pytest.raises(RuntimeError, match="one top-level"):
        extract_github_zip(archive, tmp_path / "output", strip_root=True, target="addons/demo")
