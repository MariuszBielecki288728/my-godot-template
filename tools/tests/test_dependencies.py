import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from godot_devtools.dependencies import (
    MANAGED_DEPENDENCY_MARKER,
    dependency_is_installed,
    install_dependency,
    load_dependency_manifest,
)


def manifest_entry(**overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "name": "demo",
        "type": "github_zip",
        "version": "1.0",
        "url": "https://github.com/example/demo/archive.zip",
        "sha256": "a" * 64,
        "target": "addons/demo",
        "strip_root": True,
    }
    entry.update(overrides)
    return entry


def write_manifest(tmp_path: Path, dependencies: list[dict[str, object]]) -> Path:
    path = tmp_path / "dependencies.json"
    path.write_text(json.dumps({"schema_version": 1, "dependencies": dependencies}))
    return path


def test_load_manifest_accepts_valid_schema(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path, [manifest_entry()])
    result = load_dependency_manifest(manifest, tmp_path)
    assert result[0]["resolved_target"] == (tmp_path / "addons/demo").resolve()


@pytest.mark.parametrize(
    "entry, message",
    [
        ({"name": "demo"}, "exactly"),
        (manifest_entry(extra=True), "exactly"),
        (manifest_entry(name="demo", target="addons/other"), "Duplicate"),
    ],
)
def test_load_manifest_rejects_invalid_fields(
    tmp_path: Path, entry: dict[str, object], message: str
) -> None:
    dependencies = [entry]
    if entry.get("name") == "demo" and entry.get("target") == "addons/other":
        dependencies = [manifest_entry(), entry]
    with pytest.raises(ValueError, match=message):
        load_dependency_manifest(write_manifest(tmp_path, dependencies), tmp_path)


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("type", "local", "Unsupported dependency type"),
        ("sha256", "bad", "sha256"),
        ("url", "http://github.com/example/demo.zip", "HTTPS github.com"),
        ("url", "https://example.com/demo.zip", "HTTPS github.com"),
        ("target", "../outside", "inside the repository"),
        ("target", "/absolute", "inside the repository"),
    ],
)
def test_load_manifest_rejects_unsafe_values(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        load_dependency_manifest(
            write_manifest(tmp_path, [manifest_entry(**{field: value})]), tmp_path
        )


def test_load_manifest_rejects_colliding_targets(tmp_path: Path) -> None:
    entries = [manifest_entry(), manifest_entry(name="nested", target="addons/demo/child")]
    with pytest.raises(ValueError, match="collides"):
        load_dependency_manifest(write_manifest(tmp_path, entries), tmp_path)


def dependency(tmp_path: Path) -> dict[str, object]:
    return {**manifest_entry(), "resolved_target": tmp_path / "addons/demo"}


def test_managed_marker_is_recognized_and_corruption_requires_reinstall(tmp_path: Path) -> None:
    item = dependency(tmp_path)
    marker = item["resolved_target"] / MANAGED_DEPENDENCY_MARKER
    marker.parent.mkdir(parents=True)
    marker.write_text(json.dumps({key: item[key] for key in ("name", "version", "url", "sha256")}))
    assert dependency_is_installed(item)
    marker.write_text("not json")
    assert not dependency_is_installed(item)


def test_install_replaces_previous_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    archive = tmp_path / "download.zip"
    with zipfile.ZipFile(archive, "w") as zip_file:
        zip_file.writestr("demo-1.0/new.txt", "new")
    item = dependency(tmp_path)
    item["sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
    target = item["resolved_target"]
    target.mkdir(parents=True)
    (target / "old.txt").write_text("old")
    monkeypatch.setattr(
        "godot_devtools.dependencies.download_file",
        lambda _url, destination: destination.write_bytes(archive.read_bytes()),
    )
    install_dependency(item)
    assert (target / "new.txt").read_text() == "new"
    assert not (target / "old.txt").exists()
    assert dependency_is_installed(item)


def test_failed_replacement_restores_previous_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = tmp_path / "download.zip"
    with zipfile.ZipFile(archive, "w") as zip_file:
        zip_file.writestr("demo-1.0/new.txt", "new")
    item = dependency(tmp_path)
    item["sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
    target = item["resolved_target"]
    target.mkdir(parents=True)
    (target / "old.txt").write_text("old")
    monkeypatch.setattr(
        "godot_devtools.dependencies.download_file",
        lambda _url, destination: destination.write_bytes(archive.read_bytes()),
    )
    original_move = __import__("shutil").move

    def fail_staging_move(source: str, destination: str) -> str:
        if ".demo-install-" in source:
            raise OSError("simulated replacement failure")
        return original_move(source, destination)

    monkeypatch.setattr("godot_devtools.dependencies.shutil.move", fail_staging_move)
    with pytest.raises(RuntimeError, match="Unable to install"):
        install_dependency(item)
    assert (target / "old.txt").read_text() == "old"
