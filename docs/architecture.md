# Architecture

This starter deliberately imposes no gameplay architecture. Its boundaries are:

- `src/` and `scenes/`: first-party Godot runtime code and executable scenes;
- `tests/`: GUT tests for Godot code;
- `dependencies.json`: exact manifest-managed Godot/project dependency pins;
- `addons/gut/`: generated third-party Godot development code, excluded from first-party checks;
- `tools/`: isolated uv-managed Python development-tool project and its Pytest suite;
- `justfile`: thin repository-level developer-command facade;
- `.github/workflows/ci.yml`: CI orchestration over the same `godot-dev` commands.

`src/bootstrap/` exists solely to prove project-owned code loads and executes. It is not a
framework and should be removed or replaced when real game code starts.
