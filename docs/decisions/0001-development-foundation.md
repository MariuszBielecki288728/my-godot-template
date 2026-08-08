# ADR 0001: Development foundation

## Status

Accepted.

## Decision

Use Godot **4.7.1 stable** with typed GDScript, vendored **GUT 9.7.1**, and pinned
**gdtoolkit 4.5.0**. Use a lightweight Python CLI as the canonical implementation of
development commands, with `just` as a thin human-facing wrapper. Use GitHub Actions on
Ubuntu for headless validation and a Windows debug export smoke test.

## Rationale and tradeoffs

GDScript keeps this first layer close to Godot and avoids Mono setup. Static typing and
gdtoolkit give fast feedback without adding a framework. GUT provides headless unit and
scene tests; vendoring its official tagged release makes the test dependency reproducible
and preserves its MIT license. `just` offers discoverable commands while Python centralizes
cross-platform executable lookup and exit handling.

The selected type-related GDScript warnings are errors. This was verified against the
first-party scripts and the pinned GUT command-line execution; no GUT source or warning
suppression was modified.

Headless CI validates deterministic logic, loading, and a real executable scene quickly.
It cannot judge visual quality or game feel: future work still needs manual playtesting.
Coverage percentage is intentionally not a gate because this starter prioritizes meaningful
behavior coverage and regression protection over a vanity metric.

## Consequences

The repository stays deliberately small and does not prescribe future gameplay systems.
Contributors must keep dependency versions pinned and run `just check`; CI additionally
performs the slower Windows export smoke test.

## GUT execution

Tests run through GUT's upstream `addons/gut/gut_cmdln.gd` entry point. The project-owned
runner was removed after retesting it against the inert main scene: upstream GUT completed
its asynchronous lifecycle, returned the correct exit status, and generated JUnit XML.
The Python command deletes any prior report, requires a new report, parses it structurally,
and rejects runs with zero test cases.
