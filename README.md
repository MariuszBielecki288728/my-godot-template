# Godot Engineering Starter

An AI-friendly, reproducible Godot project foundation. It proves a small typed GDScript
change can be formatted, linted, loaded by Godot, tested, smoke-tested, exported, and
validated in CI.

It is deliberately **not** a game framework or gameplay starter. It contains no player,
inventory, combat, tiles, world generation, networking, or other domain architecture.

## Requirements

- Godot **4.7.1 stable** (standard GDScript build, not C#/Mono)
- Python 3.12+ (for development tooling only)
- `just`

Set `GODOT_BIN` when Godot is not available as `godot` or `godot4` on PATH.
The development CLI verifies that the resolved executable is Godot 4.7.1 stable before it
runs a Godot command.

## Quick start

```text
Create a repository from this template
just bootstrap
just check
just run
```

`just bootstrap` creates a local `.venv` and installs pinned `gdtoolkit==4.5.0`.

## Commands

| Command | Purpose |
| --- | --- |
| `just bootstrap` | Create/update the local development environment. |
| `just format` | Format first-party GDScript. |
| `just format-check` | Check formatting without mutation. |
| `just lint` | Lint first-party GDScript. |
| `just godot-check` | Fully import the project headlessly. |
| `just test` | Run GUT unit and integration tests with JUnit output. |
| `just smoke` | Run the real main scene headlessly for a few frames. |
| `just check` | Standard local completion gate. |
| `just run` | Start the project with Godot; close it manually when done. |
| `just export-windows` | Create a debug Windows export in ignored `build/`. |
| `just clean` | Remove generated Godot cache, build, and report output. |

`just check` intentionally excludes export for quick daily feedback. CI runs
`export-windows` after the same checks.

The configured type-related GDScript warnings are treated as errors. This applies to the
checked project and is compatible with the pinned GUT release used by the test command.

## Layout

```text
addons/gut/       Pinned GUT 9.7.1 (vendored third-party test dependency)
scenes/           Minimal executable main scene
src/bootstrap/    Temporary typed validation fixture and main-scene script
tests/            Unit and scene/integration tests
tools/dev.py      Canonical cross-platform development CLI
docs/             Architecture notes and decisions
```

Read [AGENTS.md](AGENTS.md) before assigning coding work to an agent. The small fixture in
`src/bootstrap/bootstrap_fixture.gd` is intentionally temporary: remove it once real domain
code replaces it.

This repository is intended to be marked as a GitHub Template Repository through GitHub's
repository settings. That setting is deliberately not changed by this project.
