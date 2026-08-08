# Architecture

This starter deliberately imposes no gameplay architecture. Its only boundaries are:

- `src/` and `scenes/`: first-party project code and executable scenes;
- `addons/`: vendored third-party code, currently GUT, excluded from first-party linting and formatting;
- `tests/`: deterministic unit tests and scene/integration tests;
- `tools/dev.py`: the single local command implementation used by `just` and CI;
- `.github/workflows/ci.yml`: CI orchestration that delegates to that tooling.

`src/bootstrap/` exists solely to prove project-owned code loads and executes. It is not a
framework and should be removed or replaced when real game code starts.
