from pathlib import Path

import pytest

from godot_devtools.testing import validate_junit_report


def test_junit_report_requires_testcase(tmp_path: Path) -> None:
    report = tmp_path / "report.xml"
    report.write_text("<testsuite><testcase name='works'/></testsuite>")
    validate_junit_report(report)


@pytest.mark.parametrize(
    "contents, message",
    [("<testsuite/>", "zero tests"), ("not xml", "malformed")],
)
def test_junit_report_rejects_invalid_content(tmp_path: Path, contents: str, message: str) -> None:
    report = tmp_path / "report.xml"
    report.write_text(contents)
    with pytest.raises(RuntimeError, match=message):
        validate_junit_report(report)


def test_junit_report_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="did not create"):
        validate_junit_report(tmp_path / "missing.xml")
