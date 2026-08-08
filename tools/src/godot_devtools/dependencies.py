"""Manifest-managed Godot dependency installation."""

import json
import re
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from .archives import extract_github_zip, is_within, verify_sha256

MANAGED_DEPENDENCY_MARKER = ".managed-dependency.json"
DEPENDENCY_FIELDS = {"name", "type", "version", "url", "sha256", "target", "strip_root"}


def dependency_error(message: str) -> None:
    raise ValueError(f"Dependency configuration error: {message}")


def load_dependency_manifest(manifest_path: Path, repo_root: Path) -> list[dict[str, Any]]:
    """Load and strictly validate a schema-v1 project dependency manifest."""
    if not manifest_path.is_file():
        dependency_error(f"Missing {manifest_path.name}.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        dependency_error(f"Invalid JSON in {manifest_path.name}: {error.msg}.")
    if not isinstance(manifest, dict) or set(manifest) != {"schema_version", "dependencies"}:
        dependency_error("Manifest must contain exactly schema_version and dependencies.")
    if manifest["schema_version"] != 1:
        dependency_error(
            f"Unsupported schema_version {manifest['schema_version']!r}; only 1 is supported."
        )
    if not isinstance(manifest["dependencies"], list):
        dependency_error("dependencies must be an array.")

    validated: list[dict[str, Any]] = []
    names: set[str] = set()
    targets: list[Path] = []
    for entry in manifest["dependencies"]:
        if not isinstance(entry, dict):
            dependency_error("Each dependency must be an object.")
        if set(entry) != DEPENDENCY_FIELDS:
            dependency_error(
                "Each dependency must contain exactly: "
                + ", ".join(sorted(DEPENDENCY_FIELDS))
                + "."
            )
        name = entry["name"]
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9_-]+", name):
            dependency_error("Dependency name must use only lowercase letters, digits, _ and -.")
        if name in names:
            dependency_error(f"Duplicate dependency name: {name}.")
        names.add(name)
        if entry["type"] != "github_zip":
            dependency_error(f"Unsupported dependency type for {name}: {entry['type']!r}.")
        if not isinstance(entry["version"], str) or not entry["version"]:
            dependency_error(f"Dependency {name} version must be a non-empty string.")
        url = entry["url"]
        parsed_url = urllib.parse.urlparse(url) if isinstance(url, str) else None
        if (
            parsed_url is None
            or parsed_url.scheme != "https"
            or parsed_url.hostname != "github.com"
        ):
            dependency_error(f"Dependency {name} URL must be an HTTPS github.com URL.")
        sha256 = entry["sha256"]
        if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", sha256):
            dependency_error(f"Dependency {name} sha256 must be 64 hexadecimal characters.")
        target = entry["target"]
        if not isinstance(target, str) or not target:
            dependency_error(f"Dependency {name} target must be a non-empty relative path.")
        target_path = Path(target)
        if target_path.is_absolute() or any(part == ".." for part in target_path.parts):
            dependency_error(f"Dependency {name} target must stay inside the repository.")
        resolved_target = (repo_root / target_path).resolve()
        if resolved_target == repo_root or not is_within(resolved_target, repo_root):
            dependency_error(f"Dependency {name} target must stay inside the repository.")
        if not isinstance(entry["strip_root"], bool):
            dependency_error(f"Dependency {name} strip_root must be a boolean.")
        if any(
            resolved_target == other
            or resolved_target in other.parents
            or other in resolved_target.parents
            for other in targets
        ):
            dependency_error(f"Dependency target collides with another target: {target}.")
        targets.append(resolved_target)
        validated.append({**entry, "resolved_target": resolved_target})
    return validated


def dependency_marker(dependency: dict[str, Any]) -> dict[str, str]:
    return {key: dependency[key] for key in ("name", "version", "url", "sha256")}


def dependency_is_installed(dependency: dict[str, Any]) -> bool:
    marker = dependency["resolved_target"] / MANAGED_DEPENDENCY_MARKER
    if not marker.is_file():
        return False
    try:
        return json.loads(marker.read_text(encoding="utf-8")) == dependency_marker(dependency)
    except json.JSONDecodeError:
        return False


def download_file(url: str, destination: Path) -> None:
    print(f"Downloading {url}", flush=True)
    try:
        with urllib.request.urlopen(url) as response, destination.open("wb") as output:
            shutil.copyfileobj(response, output)
    except urllib.error.URLError as error:
        raise RuntimeError(f"Unable to download dependency archive: {error.reason}") from error


def install_dependency(dependency: dict[str, Any]) -> None:
    """Download, validate, and atomically install one project dependency."""
    target = dependency["resolved_target"]
    if dependency_is_installed(dependency):
        print(f"Dependency {dependency['name']} {dependency['version']} is already installed.")
        return
    print(f"Installing dependency {dependency['name']} {dependency['version']}...", flush=True)
    with tempfile.TemporaryDirectory(prefix=f"{dependency['name']}-") as temporary:
        temporary_path = Path(temporary)
        archive = temporary_path / "archive.zip"
        extracted = temporary_path / "extracted"
        extracted.mkdir()
        download_file(dependency["url"], archive)
        verify_sha256(
            name=dependency["name"],
            expected=dependency["sha256"],
            url=dependency["url"],
            archive=archive,
        )
        extracted = extract_github_zip(
            archive, extracted, strip_root=dependency["strip_root"], target=dependency["target"]
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{target.name}-install-", dir=target.parent))
        backup = target.parent / f".{target.name}-previous-{uuid.uuid4().hex}"
        try:
            shutil.copytree(extracted, staging, dirs_exist_ok=True)
            (staging / MANAGED_DEPENDENCY_MARKER).write_text(
                json.dumps(dependency_marker(dependency), indent=2) + "\n", encoding="utf-8"
            )
            if target.exists():
                shutil.move(str(target), str(backup))
            try:
                shutil.move(str(staging), str(target))
            except OSError:
                if backup.exists():
                    shutil.move(str(backup), str(target))
                raise
            if backup.exists():
                shutil.rmtree(backup)
        except OSError as error:
            raise RuntimeError(
                f"Unable to install dependency {dependency['name']}: {error}"
            ) from error
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    print(f"Installed {dependency['name']} {dependency['version']} to {target.as_posix()}.")


def ensure_dependencies(repo_root: Path) -> None:
    for dependency in load_dependency_manifest(repo_root / "dependencies.json", repo_root):
        install_dependency(dependency)


def require_dependency(repo_root: Path, name: str) -> None:
    dependency = next(
        (
            item
            for item in load_dependency_manifest(repo_root / "dependencies.json", repo_root)
            if item["name"] == name
        ),
        None,
    )
    if dependency is None or not dependency_is_installed(dependency):
        raise RuntimeError(
            f"Required development dependency '{name}' is not installed. Run: just bootstrap"
        )
