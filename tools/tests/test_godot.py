from pathlib import Path

import pytest

from godot_devtools.godot import is_expected_godot_version
from godot_devtools.root import discover_repository_root


@pytest.mark.parametrize("version", ["4.7.1.stable", "4.7.1.stable.official"])
def test_expected_godot_version_accepts_official_metadata(version: str) -> None:
    assert is_expected_godot_version(version)


@pytest.mark.parametrize("version", ["4.7.0", "4.7.2", "4.8", "4.7.1.dev"])
def test_expected_godot_version_rejects_other_versions(version: str) -> None:
    assert not is_expected_godot_version(version)


def test_repository_root_discovery_walks_to_godot_markers(tmp_path: Path) -> None:
    (tmp_path / "project.godot").write_text("[application]")
    (tmp_path / "dependencies.json").write_text("{}")
    nested = tmp_path / "tools/src/godot_devtools"
    nested.mkdir(parents=True)
    assert discover_repository_root(nested) == tmp_path
