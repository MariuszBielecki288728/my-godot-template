"""Command-line entry point for the Godot development tooling."""

import argparse
import shutil
from collections.abc import Callable
from pathlib import Path

from .dependencies import ensure_dependencies
from .godot import export_windows, godot_check, launch, run, smoke
from .root import discover_repository_root
from .testing import test_godot


def run_python_tool(repo_root: Path, *arguments: str) -> None:
    run(["uv", "run", "--project", "tools", "--locked", *arguments], cwd=repo_root)


def gdtool(repo_root: Path, command: str) -> None:
    targets = ["src", "tests"]
    if command == "format":
        run_python_tool(repo_root, "gdformat", *targets)
    elif command == "format-check":
        run_python_tool(repo_root, "gdformat", "--check", *targets)
    elif command == "lint":
        run_python_tool(repo_root, "gdlint", *targets)
    else:
        raise ValueError(f"Unknown gdtoolkit command: {command}")


def format_project(repo_root: Path) -> None:
    run_python_tool(repo_root, "ruff", "format", "tools/src", "tools/tests")
    gdtool(repo_root, "format")


def format_check(repo_root: Path) -> None:
    run_python_tool(repo_root, "ruff", "format", "--check", "tools/src", "tools/tests")
    gdtool(repo_root, "format-check")


def lint(repo_root: Path) -> None:
    run_python_tool(repo_root, "ruff", "check", "tools/src", "tools/tests")
    gdtool(repo_root, "lint")


def test_python(repo_root: Path) -> None:
    reports = repo_root / "reports"
    reports.mkdir(exist_ok=True)
    run_python_tool(repo_root, "pytest", "tools/tests", "--junitxml=reports/pytest.xml")


def precommit(repo_root: Path) -> None:
    format_check(repo_root)
    lint(repo_root)
    test_python(repo_root)


def check(repo_root: Path) -> None:
    format_check(repo_root)
    lint(repo_root)
    test_python(repo_root)
    godot_check(repo_root)
    test_godot(repo_root)
    smoke(repo_root)


def clean(repo_root: Path) -> None:
    for path in (repo_root / ".godot", repo_root / "build", repo_root / "reports"):
        if path.exists():
            shutil.rmtree(path)
            print(f"Removed {path.relative_to(repo_root)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "deps",
            "format",
            "format-check",
            "lint",
            "test",
            "test-python",
            "test-godot",
            "godot-check",
            "smoke",
            "check",
            "run",
            "export-windows",
            "clean",
            "precommit",
        ],
    )
    return parser.parse_args()


def main() -> None:
    repo_root = discover_repository_root()
    command = parse_args().command
    actions: dict[str, Callable[[Path], None]] = {
        "deps": ensure_dependencies,
        "format": format_project,
        "format-check": format_check,
        "lint": lint,
        "test": lambda root: (test_python(root), test_godot(root)),
        "test-python": test_python,
        "test-godot": test_godot,
        "godot-check": godot_check,
        "smoke": smoke,
        "check": check,
        "run": launch,
        "export-windows": export_windows,
        "clean": clean,
        "precommit": precommit,
    }
    try:
        actions[command](repo_root)
    except RuntimeError as error:
        raise SystemExit(str(error)) from error
