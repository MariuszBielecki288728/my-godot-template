#!/usr/bin/env python3
"""Cross-platform developer commands for the Godot engineering starter."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ElementTree
import zipfile
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements-dev.txt"
DEPENDENCY_MANIFEST = ROOT / "dependencies.json"
EXPECTED_GODOT_VERSION = "4.7.1.stable"
MANAGED_DEPENDENCY_MARKER = ".managed-dependency.json"
DEPENDENCY_FIELDS = {
    "name",
    "type",
    "version",
    "url",
    "sha256",
    "target",
    "strip_root",
}


def dependency_error(message: str) -> None:
    raise SystemExit(f"Dependency configuration error: {message}")


def is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def load_dependency_manifest() -> list[dict[str, Any]]:
    """Load and strictly validate schema-v1 development dependency pins."""
    if not DEPENDENCY_MANIFEST.is_file():
        dependency_error(f"Missing {DEPENDENCY_MANIFEST.name}.")
    try:
        manifest = json.loads(DEPENDENCY_MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        dependency_error(f"Invalid JSON in {DEPENDENCY_MANIFEST.name}: {error.msg}.")
    if not isinstance(manifest, dict) or set(manifest) != {"schema_version", "dependencies"}:
        dependency_error("Manifest must contain exactly schema_version and dependencies.")
    if manifest["schema_version"] != 1:
        dependency_error(
            f"Unsupported schema_version {manifest['schema_version']!r}; only 1 is supported."
        )
    dependencies = manifest["dependencies"]
    if not isinstance(dependencies, list):
        dependency_error("dependencies must be an array.")

    validated: list[dict[str, Any]] = []
    names: set[str] = set()
    targets: list[Path] = []
    for entry in dependencies:
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
        resolved_target = (ROOT / target_path).resolve()
        if resolved_target == ROOT or not is_within(resolved_target, ROOT):
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
    return {
        "name": dependency["name"],
        "version": dependency["version"],
        "url": dependency["url"],
        "sha256": dependency["sha256"],
    }


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
        raise SystemExit(f"Unable to download dependency archive: {error.reason}") from error


def verify_sha256(dependency: dict[str, Any], archive: Path) -> None:
    with archive.open("rb") as source:
        actual = hashlib.file_digest(source, "sha256").hexdigest()
    expected = dependency["sha256"]
    if actual.lower() != expected.lower():
        raise SystemExit(
            f"Dependency integrity check failed: {dependency['name']}\n\n"
            f"Expected SHA-256: {expected}\n"
            f"Actual SHA-256:   {actual}\n"
            f"Source: {dependency['url']}\n\n"
            "Nothing was installed."
        )
    print("SHA-256 verified.", flush=True)


def extract_github_zip(
    archive: Path, destination: Path, *, strip_root: bool, target: str
) -> Path:
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
                relative_path = Path(*relative_parts)
                output_path = (destination / relative_path).resolve()
                if not is_within(output_path, destination):
                    raise ValueError(f"unsafe archive member: {member.filename}")
                if member.is_dir():
                    output_path.mkdir(parents=True, exist_ok=True)
                    continue
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with zip_file.open(member) as source, output_path.open("wb") as output:
                    shutil.copyfileobj(source, output)
                content_members += 1
            if not content_members:
                raise ValueError("archive root contains no files")
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise SystemExit(f"Dependency archive extraction failed: {error}") from error
    embedded_target = destination / Path(target)
    return embedded_target if embedded_target.is_dir() else destination


def install_dependency(dependency: dict[str, Any]) -> None:
    target = dependency["resolved_target"]
    if dependency_is_installed(dependency):
        print(
            f"Dependency {dependency['name']} {dependency['version']} is already installed.",
            flush=True,
        )
        return
    print(f"Installing dependency {dependency['name']} {dependency['version']}...", flush=True)
    with tempfile.TemporaryDirectory(prefix=f"{dependency['name']}-") as temporary:
        temporary_path = Path(temporary)
        archive = temporary_path / "archive.zip"
        extracted = temporary_path / "extracted"
        extracted.mkdir()
        download_file(dependency["url"], archive)
        verify_sha256(dependency, archive)
        extracted = extract_github_zip(
            archive,
            extracted,
            strip_root=dependency["strip_root"],
            target=dependency["target"],
        )

        target.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{target.name}-install-", dir=target.parent))
        try:
            shutil.copytree(extracted, staging, dirs_exist_ok=True)
            (staging / MANAGED_DEPENDENCY_MARKER).write_text(
                json.dumps(dependency_marker(dependency), indent=2) + "\n", encoding="utf-8"
            )
            backup = target.parent / f".{target.name}-previous-{uuid.uuid4().hex}"
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
            raise SystemExit(f"Unable to install dependency {dependency['name']}: {error}") from error
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    print(
        f"Installed {dependency['name']} {dependency['version']} to "
        f"{target.relative_to(ROOT).as_posix()}.",
        flush=True,
    )


def ensure_dependencies() -> None:
    for dependency in load_dependency_manifest():
        install_dependency(dependency)


def require_dependency(name: str) -> None:
    dependency = next(
        (item for item in load_dependency_manifest() if item["name"] == name), None
    )
    if dependency is None or not dependency_is_installed(dependency):
        raise SystemExit(
            f"Required development dependency '{name}' is not installed.\n\n"
            "Run:\n    just bootstrap"
        )


def run(command: Sequence[str], *, cwd: Path = ROOT) -> None:
    """Run a subprocess transparently and preserve its non-zero exit code."""
    print("+", " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=cwd, check=False)
    if completed.returncode:
        raise SystemExit(completed.returncode)


def find_godot() -> str:
    """Find and validate the configured Godot binary."""
    configured = os.environ.get("GODOT_BIN")
    candidates = [configured] if configured else ["godot", "godot4"]
    for candidate in candidates:
        if not candidate:
            continue
        resolved = shutil.which(candidate)
        if resolved:
            return validate_godot_version(resolved)
        explicit_path = Path(candidate)
        if configured and explicit_path.is_file():
            return validate_godot_version(str(explicit_path))
    checked = "GODOT_BIN" if configured else "godot, godot4"
    raise SystemExit(
        "Godot executable was not found.\n\n"
        f"Checked: {checked}\n"
        "Install Godot 4.7.1 or set GODOT_BIN to the executable path."
    )


def validate_godot_version(executable: str) -> str:
    """Require the Godot version pinned by this starter."""
    completed = subprocess.run(
        [executable, "--version"], capture_output=True, text=True, check=False
    )
    detected = completed.stdout.strip() or completed.stderr.strip() or "unknown"
    version_pattern = rf"^{re.escape(EXPECTED_GODOT_VERSION)}(?:\.|$)"
    if completed.returncode or not re.match(version_pattern, detected):
        raise SystemExit(
            "Incorrect Godot version.\n\n"
            f"Expected: {EXPECTED_GODOT_VERSION} (official build metadata is allowed)\n"
            f"Detected: {detected}\n"
            f"Executable: {executable}\n\n"
            "Install the required Godot version or set GODOT_BIN to its executable path."
        )
    return executable


def venv_python() -> Path:
    """Return the platform-specific Python executable inside the local venv."""
    name = "Scripts/python.exe" if os.name == "nt" else "bin/python"
    return VENV / name


def require_dev_python() -> str:
    executable = venv_python()
    if not executable.is_file():
        raise SystemExit(
            "Development environment is not installed. Run `just bootstrap` first."
        )
    return str(executable)


def bootstrap() -> None:
    if not venv_python().is_file():
        run([sys.executable, "-m", "venv", str(VENV)])
    python = str(venv_python())
    run([python, "-m", "pip", "install", "--requirement", str(REQUIREMENTS)])
    ensure_dependencies()


def gdtool(command: str) -> None:
    python = require_dev_python()
    targets = ["src", "tests", "tools"]
    if command == "format":
        run([python, "-m", "gdtoolkit.formatter", *targets])
    elif command == "format-check":
        run([python, "-m", "gdtoolkit.formatter", "--check", *targets])
    elif command == "lint":
        run([python, "-m", "gdtoolkit.linter", *targets])
    else:
        raise ValueError(f"Unknown gdtoolkit command: {command}")


def godot_check() -> None:
    run([find_godot(), "--headless", "--path", str(ROOT), "--import"])


def test() -> None:
    require_dependency("gut")
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    report = reports / "gut.xml"
    report.unlink(missing_ok=True)
    run(
        [
            find_godot(),
            "--headless",
            "--path",
            str(ROOT),
            "--script",
            "res://addons/gut/gut_cmdln.gd",
            "-gconfig=res://.gutconfig.json",
        ]
    )
    if not report.is_file():
        raise SystemExit("GUT did not create reports/gut.xml; test discovery is not trustworthy.")
    try:
        root = ElementTree.parse(report).getroot()
    except ElementTree.ParseError as error:
        raise SystemExit(f"GUT produced malformed JUnit XML: {error}") from error
    if not list(root.iter("testcase")):
        raise SystemExit("GUT discovered zero tests; refusing to treat that as success.")


def smoke() -> None:
    run([find_godot(), "--headless", "--path", str(ROOT), "--quit-after", "10"])


def check() -> None:
    gdtool("format-check")
    gdtool("lint")
    godot_check()
    test()
    smoke()


def launch() -> None:
    run([find_godot(), "--path", str(ROOT)])


def export_windows() -> None:
    output = ROOT / "build" / "windows" / "godot-engineering-starter.exe"
    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            find_godot(),
            "--headless",
            "--path",
            str(ROOT),
            "--export-debug",
            "Windows Desktop",
            str(output),
        ]
    )
    if not output.is_file():
        raise SystemExit("Godot reported a successful export but no Windows executable was created.")


def clean() -> None:
    for path in (ROOT / ".godot", ROOT / "build", ROOT / "reports"):
        if path.exists():
            shutil.rmtree(path)
            print(f"Removed {path.relative_to(ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "bootstrap",
            "format",
            "format-check",
            "lint",
            "godot-check",
            "test",
            "smoke",
            "check",
            "run",
            "export-windows",
            "clean",
            "deps",
        ],
    )
    return parser.parse_args()


def main() -> None:
    command = parse_args().command
    actions = {
        "bootstrap": bootstrap,
        "format": lambda: gdtool("format"),
        "format-check": lambda: gdtool("format-check"),
        "lint": lambda: gdtool("lint"),
        "godot-check": godot_check,
        "test": test,
        "smoke": smoke,
        "check": check,
        "run": launch,
        "export-windows": export_windows,
        "clean": clean,
        "deps": ensure_dependencies,
    }
    actions[command]()


if __name__ == "__main__":
    main()
