class_name BootstrapFixture
extends RefCounted


## Temporary deterministic fixture proving that project-owned GDScript loads and runs.
## Delete it when the first real domain code replaces this bootstrap layer.
static func increment(value: int) -> int:
	return value + 1
