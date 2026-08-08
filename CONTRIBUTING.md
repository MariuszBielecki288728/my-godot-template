# Contributing

## Initial setup

Install Godot **4.7.1 stable**, `uv`, and `just`. If Godot is not on PATH, set `GODOT_BIN` to its
executable. Run `just bootstrap` followed by `just check`.

Bootstrap lets uv create `tools/.venv` from the committed lockfile, then installs the
SHA-256-verified Godot/project dependencies declared in root `dependencies.json`. It is safe to
rerun. Generated directories such as `addons/gut/` must never be committed.

## Daily commands

`just format` and `just format-check` cover Ruff-formatted Python and first-party GDScript.
`just lint` runs Ruff and gdtoolkit. `just test` runs Pytest plus GUT and writes JUnit reports.
`just check` also performs Godot import and a headless smoke test; CI additionally runs Windows
export. `just hooks-install` is an explicit optional local convenience; `just hooks-run` runs the
fast hook gate over all files.

## Dependency policy

`dependencies.json` owns manifest-managed Godot/project dependencies such as GUT.
`tools/pyproject.toml` and generated `tools/uv.lock` own Python developer tooling. Updating GUT
changes the manifest; updating Ruff changes the tools project and regenerated lockfile. Do not
manually edit `uv.lock`, silently upgrade Godot/GUT/gdtoolkit, or commit generated dependencies.

## Testing and PR discipline

Run `just check` before opening a pull request. Keep changes focused and document any validation
that cannot run. TDD is strongly preferred for deterministic logic and bug fixes.
