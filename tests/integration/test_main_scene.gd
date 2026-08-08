extends GutTest

const MAIN_SCENE: PackedScene = preload("res://scenes/main.tscn")
const MAIN_SCRIPT: Script = preload("res://src/bootstrap/bootstrap_main.gd")


func test_main_scene_instantiates_with_project_script() -> void:
	var scene_instance: Node = MAIN_SCENE.instantiate()
	add_child_autofree(scene_instance)

	assert_eq(scene_instance.get_script(), MAIN_SCRIPT)
	assert_eq(scene_instance.call("bootstrap_value"), 42)
