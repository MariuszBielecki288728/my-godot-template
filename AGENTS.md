# Agent guidance

## Before editing

Inspect relevant files, nearby tests, and existing patterns first. Make focused changes;
do not duplicate abstractions or refactor unrelated code without a concrete reason.

## Architecture and typing

This is tooling infrastructure, not a game framework. Prefer simple, typed GDScript and
deterministic logic. Avoid speculative frameworks, unnecessary global state, and
gameplay-specific systems until a real game demonstrates the need.

## Tests

For deterministic behavior and bug fixes, prefer: write or adjust a test, observe it fail,
implement the change, then observe success. Do not manufacture meaningless tests for visual
or editor-only work. Add regression tests for bugs when practical.

## Dependencies and third-party code

Add a dependency only for a concrete need after checking existing tooling, and document the
reason. Never silently upgrade Godot, GUT, or core tooling. `addons/gut/` is vendored
third-party code: do not reformat or casually modify it.

## Validation

Before declaring normal implementation work complete, run `just check`. If a required check
cannot run, state what was blocked, why, and what did run. Never claim checks pass without
executing them. Fix root causes; never disable tests, weaken linting, blanket-suppress
warnings, delete assertions, or skip checks merely to obtain green CI.
