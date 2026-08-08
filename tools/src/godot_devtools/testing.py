"""Godot/GUT test execution and JUnit report validation."""

import xml.etree.ElementTree as ElementTree
from pathlib import Path

from .dependencies import require_dependency
from .godot import find_godot, run


def validate_junit_report(report: Path) -> None:
    """Require a parseable JUnit report that contains at least one testcase."""
    if not report.is_file():
        raise RuntimeError(f"GUT did not create {report}; test discovery is not trustworthy.")
    try:
        root = ElementTree.parse(report).getroot()
    except ElementTree.ParseError as error:
        raise RuntimeError(f"GUT produced malformed JUnit XML: {error}") from error
    if not list(root.iter("testcase")):
        raise RuntimeError("GUT discovered zero tests; refusing to treat that as success.")


def test_godot(repo_root: Path) -> None:
    require_dependency(repo_root, "gut")
    reports = repo_root / "reports"
    reports.mkdir(exist_ok=True)
    report = reports / "gut.xml"
    report.unlink(missing_ok=True)
    run(
        [
            find_godot(),
            "--headless",
            "--path",
            str(repo_root),
            "--script",
            "res://addons/gut/gut_cmdln.gd",
            "-gconfig=res://.gutconfig.json",
        ],
        cwd=repo_root,
    )
    validate_junit_report(report)
