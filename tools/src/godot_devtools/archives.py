"""Archive integrity and safe extraction helpers."""

import hashlib
import re
import shutil
import zipfile
from pathlib import Path


def is_within(path: Path, directory: Path) -> bool:
    """Return whether *path* is contained by *directory*."""
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def verify_sha256(*, name: str, expected: str, url: str, archive: Path) -> None:
    """Require an archive to match its manifest hash."""
    with archive.open("rb") as source:
        actual = hashlib.file_digest(source, "sha256").hexdigest()
    if actual.lower() != expected.lower():
        raise RuntimeError(
            f"Dependency integrity check failed: {name}\n\n"
            f"Expected SHA-256: {expected}\nActual SHA-256:   {actual}\nSource: {url}\n\n"
            "Nothing was installed."
        )


def extract_github_zip(archive: Path, destination: Path, *, strip_root: bool, target: str) -> Path:
    """Safely extract a GitHub ZIP into a temporary destination."""
    try:
        with zipfile.ZipFile(archive) as zip_file:
            members = zip_file.infolist()
            if not members:
                raise ValueError("archive is empty")
            parsed_members: list[tuple[zipfile.ZipInfo, list[str]]] = []
            roots: set[str] = set()
            for member in members:
                name = member.filename.replace("\\", "/")
                if name.startswith("/") or re.match(r"^[A-Za-z]:/", name):
                    raise ValueError(f"unsafe absolute archive member: {member.filename}")
                parts = [part for part in name.split("/") if part]
                if not parts or any(part in {".", ".."} for part in parts):
                    raise ValueError(f"unsafe archive member: {member.filename}")
                roots.add(parts[0])
                parsed_members.append((member, parts))
            if strip_root and len(roots) != 1:
                raise ValueError("archive must contain exactly one top-level directory")
            content_members = 0
            destination = destination.resolve()
            for member, parts in parsed_members:
                relative_parts = parts[1:] if strip_root else parts
                if not relative_parts:
                    continue
                output_path = (destination / Path(*relative_parts)).resolve()
                if not is_within(output_path, destination):
                    raise ValueError(f"unsafe archive member: {member.filename}")
                if member.is_dir():
                    output_path.mkdir(parents=True, exist_ok=True)
                else:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with zip_file.open(member) as source, output_path.open("wb") as output:
                        shutil.copyfileobj(source, output)
                    content_members += 1
            if not content_members:
                raise ValueError("archive root contains no files")
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise RuntimeError(f"Dependency archive extraction failed: {error}") from error
    embedded_target = destination / Path(target)
    return embedded_target if embedded_target.is_dir() else destination
