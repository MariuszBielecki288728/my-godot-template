"""Godot process discovery and project commands."""

import os
import re
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

EXPECTED_GODOT_VERSION = "4.7.1.stable"


def run(command: Sequence[str], *, cwd: Path) -> None:
    """Run a subprocess transparently and preserve its exit code."""
    print("+", " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=cwd, check=False)
    if completed.returncode:
        raise RuntimeError(
            f"Command failed with exit code {completed.returncode}: {' '.join(command)}"
        )


def is_expected_godot_version(detected: str) -> bool:
    """Allow the exact pinned version plus official build metadata."""
    return bool(re.match(rf"^{re.escape(EXPECTED_GODOT_VERSION)}(?:\.|$)", detected.strip()))


def validate_godot_version(executable: str) -> str:
    completed = subprocess.run(
        [executable, "--version"], capture_output=True, text=True, check=False
    )
    detected = completed.stdout.strip() or completed.stderr.strip() or "unknown"
    if completed.returncode or not is_expected_godot_version(detected):
        raise RuntimeError(
            f"Incorrect Godot version. Expected: {EXPECTED_GODOT_VERSION} "
            "(official build metadata is allowed). "
            f"Detected: {detected}. Executable: {executable}."
        )
    return executable


def find_godot() -> str:
    configured = os.environ.get("GODOT_BIN")
    candidates = [configured] if configured else ["godot", "godot4"]
    for candidate in candidates:
        if not candidate:
            continue
        resolved = shutil.which(candidate)
        if resolved:
            return validate_godot_version(resolved)
        if configured and Path(candidate).is_file():
            return validate_godot_version(candidate)
    checked = "GODOT_BIN" if configured else "godot, godot4"
    raise RuntimeError(f"Godot executable was not found. Checked: {checked}.")


def godot_check(repo_root: Path) -> None:
    run([find_godot(), "--headless", "--path", str(repo_root), "--import"], cwd=repo_root)


def smoke(repo_root: Path) -> None:
    run([find_godot(), "--headless", "--path", str(repo_root), "--quit-after", "10"], cwd=repo_root)


def launch(repo_root: Path) -> None:
    run([find_godot(), "--path", str(repo_root)], cwd=repo_root)


def export_windows(repo_root: Path) -> None:
    output = repo_root / "build" / "windows" / "godot-engineering-starter.exe"
    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            find_godot(),
            "--headless",
            "--path",
            str(repo_root),
            "--export-debug",
            "Windows Desktop",
            str(output),
        ],
        cwd=repo_root,
    )
    if not output.is_file():
        raise RuntimeError(
            "Godot reported a successful export but no Windows executable was created."
        )
