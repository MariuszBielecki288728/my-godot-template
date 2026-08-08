[windows]
set shell := ["powershell.exe", "-NoProfile", "-Command"]

bootstrap:
    uv run --project tools --locked godot-dev deps

deps:
    uv run --project tools --locked godot-dev deps

format:
    uv run --project tools --locked godot-dev format

format-check:
    uv run --project tools --locked godot-dev format-check

lint:
    uv run --project tools --locked godot-dev lint

test:
    uv run --project tools --locked godot-dev test

godot-check:
    uv run --project tools --locked godot-dev godot-check

smoke:
    uv run --project tools --locked godot-dev smoke

check:
    uv run --project tools --locked godot-dev check

run:
    uv run --project tools --locked godot-dev run

export-windows:
    uv run --project tools --locked godot-dev export-windows

clean:
    uv run --project tools --locked godot-dev clean

hooks-install:
    uv run --project tools --locked pre-commit install

hooks-run:
    uv run --project tools --locked pre-commit run --all-files
