# ### Mitosis Integration Tests ###
#
# These integration tests are to be exectuted within a blender project.
# blender_projects/mitosis_integration_tests.blend is provided as a default, 
# pre-loaded pointing to this script.
#
# Currently, these tests simply execute test animations within Blender so basic
# proper functioning can be confirmed.
#
# These tests do not yet evaluate the results of code on a deeper quantitative
# level.

import bpy
from random import choice
import mathutils
from mitosis import CustomObj_Replicator, register
import time


def setup_blender_proj():
    """
    Adds and names objects to blender project to test upon.
    """
    pass


def test_basic_spawn_behaviors(behaviors=["DIVIDE", "INFLATE", "APPEAR"],
        spawn_offset=10, frames_to_spawn=7, scale_start=[0.7, 0.7, 0.7],
        num_generations=6, loc_offset=150):
    """
    Test listed basic spawn behaviors
    :param behaviors: list of str, names of behaviors to test.
    :param spawn_offset: int, separation between spawned objects.
    :param frames_to_spawn: int, duration of spawn animation.
    :param scale_start: list 3 in len, size of spawned objects
    :param num_generations: int, number of times to spawn
    :param loc_offset: distance between tested replicators
    :return: None
    """
    current_location = mathutils.Vector((0, 0, 0))
    for b in behaviors:
        add_random_obj_type(current_location)
        replicator1 = CustomObj_Replicator(
            behavior=b, offset=spawn_offset, frames_to_spawn=frames_to_spawn,
            scale_start=scale_start, use_x=True, use_y=True, use_z=True
        )
        replicator1.generate(num_generations)
        distance_int = get_distance_between_replicators(
            spawn_offset=spawn_offset, num_generations=num_generations)
        add_text_title(location=current_location + mathutils.Vector((0, -distance_int, 0)),
                       display_text=b)

        current_location = current_location + mathutils.Vector((loc_offset, 0 ,0))
    return current_location


def add_random_obj_type(location=(0, 0, 0)):
    """
    Add a random type of primitive object at given location
    :param location: mathutils.Vector, Location to add object at.
    """
    obj_add_funcs = [
        bpy.ops.mesh.primitive_cube_add, bpy.ops.mesh.primitive_uv_sphere_add,
        bpy.ops.mesh.primitive_ico_sphere_add, bpy.ops.mesh.primitive_cylinder_add,
        bpy.ops.mesh.primitive_cone_add, bpy.ops.mesh.primitive_torus_add,
        bpy.ops.mesh.primitive_monkey_add
    ]
    rand_func = choice(obj_add_funcs)
    rand_func(location=location)


def get_distance_between_replicators(spawn_offset, num_generations):
    """
    Get an estimate distance in 1 axis between a replicator of a given size
    Not exact, used for placing tests and display texts
    :param spawn_offset: int, offset between replicator's spawned objects
    :param num_generations: int, number of generations of replication animation
    :return: int, estimate distance between
    """
    distance = spawn_offset * num_generations
    return distance


def add_text_title(location=(0, 0, 0), display_text="Test"):
    bpy.ops.object.text_add(location=location)
    text_obj = bpy.context.active_object
    text_obj.data.body = display_text
    #text_obj.data.extrude = 0.1
    text_obj.data.size = 10.0
    text_obj.name = display_text

def test_behavior_mods(
        behaviors="DIVIDE", spawn_offset=12, frames_to_spawn=5, 
        scale_start=[0.2, 0.2, 0.2], num_generations=6,
        location=mathutils.Vector((0, 200, 0))
    ):
    """
    Create Basic blender object, then add behavior mods to it and generate.
    :return: None
    """
    add_random_obj_type(location)

    replicator1 = CustomObj_Replicator(
        behavior=behaviors, offset=spawn_offset, frames_to_spawn=frames_to_spawn,
        scale_start=scale_start, use_x=True, use_z=False
        )
    replicator1.addBehaviorMods(
        [{'data_path': 'rotation_euler', 'value': 100, 'duration': 50,
         'delay': False, 'index': 0},
         {'data_path': 'delta_location', 'value': 50, 'duration': 50,
         'delay': False, 'index': 2}])

    replicator1.generate(num_generations)

    distance_int = get_distance_between_replicators(
        spawn_offset=spawn_offset, num_generations=num_generations)

    display_text = "Behaviors Modified: "
    for mod in replicator1.behavior_mods:
        display_text = display_text + mod['data_path'] + ", "

    add_text_title(location=location + mathutils.Vector((0, -distance_int, 0)),
                    display_text=display_text)

if __name__ == "__main__":
    time_start = time.time()
    current_location = 0
    ### Basic Replication Behavior Tests ###
    current_location = test_basic_spawn_behaviors(
        behaviors=["DIVIDE", "INFLATE", "APPEAR"]
    )

    ### Behavior Mod Tests ###
    test_behavior_mods()

    print("Script duration: %.4f sec" % (time.time() - time_start))
