# Godot Engineering Starter

An AI-friendly, reproducible Godot project foundation. It proves a small typed GDScript change
can be formatted, linted, loaded by Godot, tested, smoke-tested, exported, and validated in CI.
It is deliberately not a game framework or gameplay starter.

## Requirements

- Godot **4.7.1 stable** (standard GDScript build, not C#/Mono)
- `uv`, which manages the isolated Python 3.12 tooling environment
- `just`

Set `GODOT_BIN` when Godot is not available as `godot` or `godot4` on PATH. The tooling checks
the resolved executable is Godot 4.7.1 stable before it runs Godot commands.

## Quick start

```text
just bootstrap
just check
just run
```

`just bootstrap` creates `tools/.venv` from the committed `tools/uv.lock`, installs the packaged
development tooling, then installs SHA-256-verified project dependencies from root
`dependencies.json`. No Python formatter, linter, or test runner needs global installation.

## Commands

| Command | Purpose |
| --- | --- |
| `just bootstrap` / `just deps` | Sync locked tooling and install manifest-managed Godot dependencies. |
| `just format` / `just format-check` | Format or check first-party Python and GDScript. |
| `just lint` | Run Ruff and gdtoolkit linting. |
| `just test` | Run Pytest tooling tests plus GUT tests with JUnit output. |
| `just godot-check` / `just smoke` | Import the project or run its main scene headlessly. |
| `just check` | Standard local completion gate. |
| `just run` / `just export-windows` | Launch the project or create an ignored Windows debug export. |
| `just clean` | Remove generated Godot cache, build, and reports. |
| `just hooks-install` / `just hooks-run` | Optionally install or run the fast pre-commit gate. |

`just check` excludes export for fast daily feedback; CI runs `export-windows` after the same
checks. Hooks are optional convenience only and are never installed during bootstrap.

## Layout

```text
dependencies.json       Pins for third-party Godot/project dependencies
addons/gut/             Generated GUT test dependency (ignored)
src/ and scenes/        First-party Godot runtime code
tests/                  GUT unit and integration tests
tools/                  Isolated uv-managed Python development-tool project
tools/src/              Installed godot-dev command implementation
tools/tests/            Pytest tests for development-tool contracts
docs/                   Architecture notes and decisions
```

Read [AGENTS.md](AGENTS.md) before assigning coding work to an agent. The small fixture in
`src/bootstrap/bootstrap_fixture.gd` is intentionally temporary: remove it once real domain
code replaces it.
