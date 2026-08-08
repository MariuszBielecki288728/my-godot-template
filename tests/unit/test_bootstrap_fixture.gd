extends GutTest


func test_increment_is_deterministic() -> void:
	assert_eq(BootstrapFixture.increment(41), 42)
