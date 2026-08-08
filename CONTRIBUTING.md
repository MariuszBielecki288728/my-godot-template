# Contributing

## Initial setup

Install Godot **4.7.1 stable**, Python 3.12+ and `just`. If Godot is not on PATH, set
`GODOT_BIN` to its executable. Then run `just bootstrap` followed by `just check`.

`bootstrap` creates `.venv` and installs the pinned development tooling. It is safe to
rerun. Open `project.godot` in Godot for editor work.

## Daily commands

`just format` formats first-party GDScript. `just format-check` verifies formatting without
changing files. `just lint` runs gdtoolkit linting. `just test` runs unit and integration
tests through GUT's upstream CLI and writes `reports/gut.xml`. `just smoke` starts the real
main scene headlessly for a finite number of frames. `just run` leaves the application open
until it is manually closed. `just export-windows` creates an ignored debug Windows export
under `build/windows/`.

Run `just check` before opening a pull request; it runs format checking, linting, Godot
project validation, GUT tests, and the smoke test. Export is kept separate locally for
faster feedback but is required in CI.

## Testing and PR discipline

TDD is strongly preferred for deterministic logic and bug fixes, not mechanically required
for every visual or editor-only change. Automated tests do not replace manual playtesting.
Keep pull requests focused, include relevant tests, and describe any validation that could
not run.

## Dependency policy

Use official sources and exact pins. Do not silently upgrade Godot, GUT, or gdtoolkit;
document the compatibility reason and update documentation with any approved change.
