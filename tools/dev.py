#!/usr/bin/env python3
"""Cross-platform developer commands for the Godot engineering starter."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements-dev.txt"
EXPECTED_GODOT_VERSION = "4.7.1.stable"


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
    }
    actions[command]()


if __name__ == "__main__":
    main()
