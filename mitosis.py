import bpy
import bpy_types
from math import radians
import mathutils

import time  # only imported for testing purposes


class Replicant():
    """"""
    def __init__(self, location_start,
                 location_end, obj=False, behavior="DIVIDE", parent=False,
                 scale_start=0, scale_end=mathutils.Vector((1,1,1))):
        self.parent = parent
        self.assignMotionPath(location_start, location_end)
        self.sides_empty = {'x': True, '-x': True, 'y': True, '-y': True,
                            'z': True, '-z': True}
        self.surrounded = False

        self.scale_start = scale_start
        self.scale_end = scale_end

    def isSurrounded(self):
        for side in self.sides_empty.items():
            if side[1] is True:
                return False
        self.surrounded = True
        return True

    def addStart(self):
        pass

    def setAttributesStart(self, frame_current):
        """Sets start attributes, before replicant moves to final position"""
        self.setScaleStart()

        self.setVisibilityStart()
        bpy.data.objects[self.obj.name].select_set(True)
        self.setKeyframesStart(frame_current)

    def setScaleStart(self):
        """Sets size of replicant before it moves to its final position"""
        self.obj.scale[0] = self.scale_start
        self.obj.scale[1] = self.scale_start
        self.obj.scale[2] = self.scale_start

    def setVisibilityStart(self):
        pass

    def assignMotionPath(self, location_start, location_end):
        self.location_start = location_start
        self.location_end = location_end

    def setKeyframesStart(self, current_frame):
        self.obj.keyframe_insert(
            data_path="scale", frame=current_frame)
        self.obj.keyframe_insert(
            data_path="location", frame=current_frame)
        self.obj.keyframe_insert(
            data_path="hide_render", frame=current_frame)

    def setKeyframesEnd(self, current_frame):
        self.obj.keyframe_insert(
            data_path="scale", frame=current_frame)
        self.obj.keyframe_insert(
            data_path="location", frame=current_frame)
        self.obj.keyframe_insert(
            data_path="hide_render", frame=current_frame)

    def setViewportVisAnimation(
            self, frame_visible, frame_hidden=False):
        """Add viewport visibility keyframes.
        Only run this after all other replicant properties are set
        Object is hidden when fcurve y-value is greater than or equal to 1.
        Arguments
        obj -- The blender object to animate
        frame_visible -- Set frame at which the object will become visible
        frame_hidden -- Optional argument, frame to hide object again
                        not currently implemented"""
        pass


class Replicator():
    """"""
    # Describes the object's replication animation ###
    behaviors = ["DIVIDE", "SEPARATE", "APPEAR", "INFLATE", "DIVIDE_AND_MERGE"]

    def __init__(self, offset=4.0, start_x=0, start_y=0, start_z=0,
                 frame_start=0, frames_to_spawn=15, scale_start=0,
                 scale_end=[1, 1, 1], behavior="DIVIDE"):
        self.offset = offset
        if behavior.upper() in Replicator.behaviors:
            self.spawn_behavior = behavior
        else:
            raise ValueError("behavior keyword must be string describing "
                             " spawn behavior from the following list: " + str(
                             Replicator.behaviors))

        self.replicants = []
        self._replicants_new = []  # stores newly replicated objects

        self.frame_start = frame_start
        self.frames_to_spawn = frames_to_spawn
        self.frame_current = frame_start

        self.scale_start = scale_start
        # scale_end type check #
        if ((isinstance(scale_end, list) or (
                isinstance(scale_end, mathutils.Vector))
             ) and len(scale_end) == 3):
            for scale in scale_end:
                try:
                    1 + scale
                except TypeError:
                    raise TypeError("All items in keyword argument scale_end"
                                    "list must be numbers.")
            self.scale_end = mathutils.Vector(
                (scale_end[0], scale_end[1], scale_end[2]))
        else:
            raise TypeError("End scale keyword argument scale_end must be a "
                            "list with 3 numbers")

        location_start = mathutils.Vector((start_x, start_y, start_z))
        self._addReplicant(
            location_start=location_start, location_end=location_start)

    def nextGeneration(self):
        """Replicates any objects with nearby empty space"""
        #bpy.context.scene.tool_settings.use_keyframe_insert_auto = True
        #bpy.context.scene.frame_current = self.frame_current

        num_replicants = len(self.replicants)
        i = 0
        # while loop used instead of for loop, since spawn() adds a member to
        # self.replicants which would cause a for loop to repeat forever
        while i < num_replicants:
            replicant = self.replicants[i]
            print(replicant.obj.name)

            spawn_location = self.spawn(replicant)
            i += 1

        self.frame_current += self.frames_to_spawn

        for replicant in self._replicants_new:
            #replicant.obj.hide_set(False)
            replicant.obj.hide_render = False
            replicant.obj.scale = self.scale_end

            replicant.obj.location = replicant.location_end

            #bpy.data.objects[replicant.obj.name].select_set(True)

            replicant.setKeyframesEnd(self.frame_current)
            replicant.setViewportVisAnimation(self.frame_current)
        self._replicants_new.clear()

        #bpy.context.scene.tool_settings.use_keyframe_insert_auto = False

    def generate(self, generations=5):
        """Runs Replicator for given number of generations"""
        i = 0
        while i < generations:
            self.nextGeneration()
            i += 1

    def _addReplicant(self, location_start, location_end=False):
        """Adds a new object"""
        replicant = self.obj_type(location_start=location_start,
                                  location_end=location_end,
                                  behavior=self.spawn_behavior, parent=self,
                                  scale_start=self.scale_start)
        replicant.setAttributesStart(self.frame_current)

        #bpy.ops.anim.keyframe_insert_menu(type='Scaling')

        self.replicants.append(replicant)
        self._replicants_new.append(replicant)

        return replicant

    def spawn(self, replicant, direction=0,
              use_x=True, use_y=True, use_z=True):
        """Multiplies given replicant in the first available empty space
        Arguments:
        direction -- Integer representing a direction around given replicant
        use_x, use_y, & use_z -- Set true to allow spawn in that dimension"""
        direction += 1
        # \/ Change order of these to alter replication behavior
        if (direction is 1) and (use_x is True):
            spawn_location = replicant.obj.location + mathutils.Vector((
                self.offset, 0.0, 0.0))
        elif (direction is 2) and (use_x is True):
            spawn_location = replicant.obj.location + mathutils.Vector((
                -self.offset, 0.0, 0.0))
        elif (direction is 3) and (use_y is True):
            spawn_location = replicant.obj.location + mathutils.Vector((
                0.0, self.offset, 0.0))
        elif (direction is 4) and (use_y is True):
            spawn_location = replicant.obj.location + mathutils.Vector((
                0.0, -self.offset, 0.0))
        elif (direction is 5) and (use_z is True):
            spawn_location = replicant.obj.location + mathutils.Vector((
                0.0, 0.0, self.offset))
        elif (direction is 6) and (use_z is True):
            spawn_location = replicant.obj.location + mathutils.Vector((
                0.0, 0.0, -self.offset))
        elif direction < 6:
            spawn_location = False
        elif direction >= 6:
            return False

        if spawn_location and self.locationIsEmpty(spawn_location):
            self._addReplicant(replicant.obj.location, spawn_location)
            return spawn_location
        else:
            self.spawn(replicant, direction, use_x, use_y, use_z)

    def locationIsEmpty(self, location_vector):
        for replicant in self.replicants:
            if (replicant.obj.location == location_vector) or (
                    replicant.location_end == location_vector):
                return False
        return True

    def useActiveObject(self):
        obj_to_replicate = bpy.context.active_object


class MitosisPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Mitosis"
    bl_idname = "OBJECT_PT_mitosis"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        layout = self.layout

        obj = context.object

        row = layout.row()
        row.label(text="Active object is: " + obj.name)
        row = layout.row()
        row.prop(obj, "name")

        row = layout.row()
        row.operator("")


def register():
    bpy.utils.register_class(MitosisPanel)


def unregister():
    bpy.utils.unregister_class(MitosisPanel)


class DivideMixin():
    """Replicant Functions for divide behavior
    """
    def setAttributesStart(self, frame_current):
        Replicant.setAttributesStart(self, frame_current)


class AppearMixin():
    """Replicant Functions for Appear behavior
    """
    def setScaleStart(self):
        pass

    def assignMotionPath(self, location_start, location_end):
        self.location_start = location_end
        self.location_end = location_end

    def setVisibilityStart(self):
        self.obj.hide_render = True
        #self.obj.hide_viewport = True

    def setViewportVisAnimation(
            self, frame_visible, frame_hidden=False):
        """Add viewport visibility keyframes.
        Only run this after all other replicant properties are set
        Object is hidden when fcurve y-value is greater than or equal to 1.
        Arguments
        obj -- The blender object to animate
        frame_visible -- Set frame at which the object will become visible
        frame_hidden -- Optional argument, frame to hide object again
                        not currently implemented"""
        #self.obj.animation_data_create()
        #act = bpy.data.actions.new('Viewport Visibility')
        act = self.obj.animation_data.action

        coordinate_list = [0, 1, frame_visible, 1, frame_visible + 1, 0]
        num_keyframes = len(coordinate_list) / 2
        assert ((len(coordinate_list) % 2) is 0), "coordinate_list must contain even number of items."

        fc = act.fcurves.new(data_path='hide_viewport')
        fc.keyframe_points.add(num_keyframes)
        fc.keyframe_points.foreach_set('co', coordinate_list)

        fc.update()  # Without this, left keyframe tangents/"Bézier handles"
                     # will extend to zero,  warping the shape of the curves 
                     # enough to lead to seemingly unpredictable changes in visibility

class DivideAndMergeMixin():
    """locationIsEmpty only detects what was empty in previous generation
    Therefore, two objects can go to the same location in a given generation
    """
    def locationIsEmpty(self, location_vector):
        for replicant in self.replicants:
            if replicant.obj.location == location_vector:
                return False
        return True


class MBall_Divide(DivideMixin, Replicant):
    """MetaBalls that divide like cells
    """
    def __init__(self, location_start, location_end, obj="metaball",
                 parent=False, scale_start=0, scale_end=[1, 1, 1], behavior="DIVIDE"):
        Replicant.__init__(self, location_start=location_start,
                           location_end=location_end, obj=obj,
                           behavior=behavior, parent=parent,
                           scale_start=scale_start, scale_end=scale_end)
        replicant = bpy.ops.object.metaball_add(type='ELLIPSOID', radius=2.0,
                                                enter_editmode=False,
                                                align='WORLD',
                                                location=(
                                                    location_start[0],
                                                    location_start[1],
                                                    location_start[2]),
                                                rotation=(0.0, 0.0, 0.0),)
        self.obj = bpy.context.active_object


class MeshCircle(Replicant):
    """Mesh Circle
    """
    def __init__(self, location_start, location_end, parent=False,
                 scale_start=0, scale_end=[1, 1, 1], behavior="DIVIDE"):
        Replicant.__init__(self, location_start=location_start,
                           location_end=location_end, behavior=behavior,
                           parent=parent, scale_start=scale_start,
                           scale_end=scale_end)
        bpy.ops.mesh.primitive_circle_add(radius=1.0, enter_editmode=False,
                                          align='WORLD',
                                          location=(
                                              location_start[0],
                                              location_start[1],
                                              location_start[2]),
                                          rotation=(0.0, 0.0, 0.0),)
        self.obj = bpy.context.active_object


class MeshSphere(Replicant):
    """Mesh Circle
    """
    def __init__(self, location_start, location_end, parent=False,
                 scale_start=0, scale_end=[1, 1, 1], behavior="DIVIDE"):
        Replicant.__init__(self, location_start=location_start,
                           location_end=location_end, behavior=behavior,
                           parent=parent, scale_start=scale_start,
                           scale_end=scale_end)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, enter_editmode=False,
                                             align='WORLD',
                                             location=(
                                                 location_start[0],
                                                 location_start[1],
                                                 location_start[2]),
                                             rotation=(0.0, 0.0, 0.0),)
        self.obj = bpy.context.active_object


class MeshCube(Replicant):
    """Mesh Cube Object to Replicate
    """
    def __init__(self, location_start, location_end, parent=False,
                 scale_start=0, scale_end=[1, 1, 1], behavior="DIVIDE"):
        Replicant.__init__(self, location_start=location_start,
                           location_end=location_end, behavior=behavior,
                           parent=parent, scale_start=scale_start,
                           scale_end=scale_end)
        bpy.ops.mesh.primitive_cube_add(enter_editmode=False,
                                        align='WORLD',
                                        location=(
                                            location_start[0],
                                            location_start[1],
                                            location_start[2]),
                                        rotation=(0.0, 0.0, 0.0),)
        self.obj = bpy.context.active_object


class MeshCube_Appear(AppearMixin, Replicant):
    def __init__(self, **kwargs):
        MeshCube.__init__(self, **kwargs)


class MBall_DivideAndMerge(DivideAndMergeMixin, Replicant):
    """locationIsEmpty only detects what was empty in previous generation
    Therefore, two objects can go to the same location in a given generation
    """
    def __init__(self):
        pass


class Custom(Replicant):
    """Mesh Circle
    """
    def __init__(self, location_start, location_end, parent=False,
                 scale_start=0, scale_end=False, behavior="DIVIDE"):
        try:
            self.obj = parent.obj_to_copy.copy()
        except AttributeError as e:
            raise AttributeError("Parent Replicator must have obj_to_copy "
                                 "attribute for Custom Replicants. Original "
                                 "error:\n" + str(e))
        C = bpy.context

        self.obj.data = parent.obj_to_copy.data.copy()
        self.obj.animation_data_clear()
        self.obj.scale[0] = parent.obj_to_copy.scale[0]
        self.obj.scale[1] = parent.obj_to_copy.scale[1]
        self.obj.scale[2] = parent.obj_to_copy.scale[2]

        C.collection.objects.link(self.obj)
        self.obj.location = location_start

        if scale_end is False:
            print("SCALE WAS FALSE")
            scale_end = parent.obj_to_copy.scale
            print(scale_end)

        Replicant.__init__(self, location_start=location_start,
                           location_end=location_end, behavior=behavior,
                           parent=parent, scale_start=scale_start,
                           scale_end=scale_end)


class MBall_Replicator(Replicator):
    def __init__(self, offset=4.0, start_x=0, start_y=0, start_z=0,
                 frame_start=0, frames_to_spawn=15, scale_start=0,
                 scale_end=[1, 1, 1], behavior="DIVIDE"):
        self.obj_type = MBall_Divide
        Replicator.__init__(self, offset=offset, start_x=start_x,
                            start_y=start_y, start_z=start_z,
                            frame_start=frame_start,
                            frames_to_spawn=frames_to_spawn,
                            scale_start=scale_start, scale_end=scale_end,
                            behavior=behavior)


class MeshCircle_Replicator(Replicator):
    def __init__(self, offset=4.0, start_x=0, start_y=0, start_z=0,
                 frame_start=0, frames_to_spawn=15, scale_start=.2,
                 scale_end=[1, 1, 1], behavior="DIVIDE"):
        self.obj_type = MeshCircle
        Replicator.__init__(self, offset=offset, start_x=start_x,
                            start_y=start_y, start_z=start_z,
                            frame_start=frame_start, scale_end=scale_end,
                            frames_to_spawn=frames_to_spawn, behavior=behavior)


class MeshSphere_Replicator(Replicator):
    def __init__(self, offset=4.0, start_x=0, start_y=0, start_z=0,
                 frame_start=0, frames_to_spawn=15, scale_start=.2,
                 scale_end=[1, 1, 1], behavior="DIVIDE"):
        self.obj_type = MeshSphere
        Replicator.__init__(self, offset=offset, start_x=start_x,
                            start_y=start_y, start_z=start_z,
                            frame_start=frame_start, scale_end=scale_end,
                            frames_to_spawn=frames_to_spawn, behavior=behavior)


class MeshCube_Replicator(Replicator):
    def __init__(self, offset=4.0, start_x=0, start_y=0, start_z=0,
                 frame_start=0, frames_to_spawn=15, scale_start=.2,
                 scale_end=[1, 1, 1], behavior="DIVIDE"):
        # Assign Behavior #
        if behavior == "APPEAR":
            self.obj_type = MeshCube_Appear
        else:
            self.obj_type = MeshCube
        Replicator.__init__(self, offset=offset, start_x=start_x,
                            start_y=start_y, start_z=start_z,
                            frame_start=frame_start, scale_end=scale_end,
                            frames_to_spawn=frames_to_spawn, behavior=behavior)


class CustomObj_Replicator(Replicator):
    def __init__(self, offset=4.0, start_x=0, start_y=0, start_z=0,
                 frame_start=0, frames_to_spawn=15, scale_start=.2,
                 scale_end=[1, 1, 1], behavior="DIVIDE"):
        self.obj_type = Custom
        self.obj_to_copy = bpy.context.active_object
        scale_end = self.obj_to_copy.scale
        Replicator.__init__(self, offset=offset, start_x=start_x,
                            start_y=start_y, start_z=start_z,
                            frame_start=frame_start, scale_end=scale_end,
                            frames_to_spawn=frames_to_spawn, behavior=behavior)


# TO do - way to select a frame then add a generation that ends at that frame
# To Do - Copy any object's properties and make it a replicant
if __name__ == "__main__":
    time_start = time.time()

    #register()
    replicator1 = MeshCube_Replicator(offset=4, frames_to_spawn=10, scale_start=0, behavior="APPEAR")
    replicator1.generate(6)

    print("Script duration: %.4f sec" % (time.time() - time_start))
