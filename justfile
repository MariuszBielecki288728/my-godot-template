[windows]
set shell := ["powershell.exe", "-NoProfile", "-Command"]

bootstrap:
    python tools/dev.py bootstrap

deps:
    python tools/dev.py deps

format:
    python tools/dev.py format

format-check:
    python tools/dev.py format-check

lint:
    python tools/dev.py lint

godot-check:
    python tools/dev.py godot-check

test:
    python tools/dev.py test

smoke:
    python tools/dev.py smoke

check:
    python tools/dev.py check

run:
    python tools/dev.py run

export-windows:
    python tools/dev.py export-windows

clean:
    python tools/dev.py clean
