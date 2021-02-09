import bpy
import bpy_types
from math import radians
import mathutils

import time  # only imported for testing purposes


class Replicant():
    """"""
    def __init__(self, location_start,
                 location_end, obj=False, parent=False,
                 scale_start=0, scale_end=mathutils.Vector((1, 1, 1))):
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

        bpy.data.objects[self.obj.name].select_set(True)
        self.setKeyframesStart(frame_current)

    def setScaleStart(self):
        """Sets size of replicant before it moves to its final position"""
        self.obj.scale[0] = self.scale_start
        self.obj.scale[1] = self.scale_start
        self.obj.scale[2] = self.scale_start

    def assignMotionPath(self, location_start, location_end):
        self.location_start = location_start
        self.location_end = location_end

    def setKeyframesStart(self, current_frame):
        self.obj.keyframe_insert(
            data_path="scale", frame=current_frame)
        self.obj.keyframe_insert(
            data_path="location", frame=current_frame)

    def setKeyframesEnd(self, current_frame):
        self.obj.keyframe_insert(
            data_path="scale", frame=current_frame)
        self.obj.keyframe_insert(
            data_path="location", frame=current_frame)

    def setViewportVisAnimation(
            self, frame_visible, frame_hidden=False):
        """This method not used with default behavior."""
        pass

    def setPostBehaviors(self, frame_current):
        """Adds post replication animation behaviors to replicant"""
        BehaviorModifier.spin(self.obj, keyframe_start=frame_current,
                              length=10,
                              )
        pass


class Replicator():
    """"""
    # Describes the object's replication animation ###
    behaviors = ["DIVIDE", "SEPARATE", "APPEAR", "INFLATE", "DIVIDE_AND_MERGE"]

    def __init__(self, offset=4.0, frame_start=0, frames_to_spawn=15,
                 scale_start=0, scale_end=[1, 1, 1],
                 start_x=0, start_y=0, start_z=0,):
        self.offset = offset

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

        if start_x is False:  # If this is CustomObj_Replicator
            location_start = self.obj_to_copy.location
            first_replicant = Replicant(
                location_start, location_start, parent=self)
            first_replicant.obj = self.obj_to_copy
            self.replicants.append(first_replicant)
        else:
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

            spawn_location = self.spawn(replicant)
            i += 1
        self.frame_current += self.frames_to_spawn

        for replicant in self._replicants_new:
            replicant.obj.scale = self.scale_end

            replicant.obj.location = replicant.location_end

            replicant.setKeyframesEnd(self.frame_current)
            replicant.setViewportVisAnimation(self.frame_current)
            #replicant.setPostBehaviors(self.frame_current)
        self._replicants_new.clear()

    def generate(self, generations=5):
        """Runs Replicator for given number of generations"""
        i = 0
        while i < generations:
            self.nextGeneration()
            i += 1

    def _addReplicant(self, location_start, location_end=False):
        """Adds a new object"""
        replicant = self.obj_type(location_start=location_start,
                                  location_end=location_end, parent=self,
                                  scale_start=self.scale_start)
        replicant.setAttributesStart(self.frame_current)
        #replicant.obj.active_material.name = 
        #replicant.obj.setMaterials()

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

    def _getBehaviorObject(self, behavior):
        behavior = behavior.upper()
        if (behavior in Replicator.behaviors) and (
                behavior in self.behavior_objs.keys()):
            return self.behavior_objs[behavior]
        else:
            raise ValueError("behavior keyword must be string describing "
                             "spawn behavior from the following list: " + str(
                                 self.behavior_objs.keys()))


#######
# GUI #
#######

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


##########################
# Behavior Mixin Methods #
##########################

class DivideMixin():
    """Replicant Methods for divide behavior
    """
    def setAttributesStart(self, frame_current):
        Replicant.setAttributesStart(self, frame_current)


class AppearMixin():
    """Replicant Methods for Appear behavior
    """
    def setScaleStart(self):
        pass

    def assignMotionPath(self, location_start, location_end):
        self.location_start = location_end
        self.location_end = location_end

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
        assert ((len(coordinate_list) % 2) is 0
                ), "coordinate_list must contain even number of items."

        fc = act.fcurves.new(data_path='hide_viewport')
        fc.keyframe_points.add(num_keyframes)
        fc.keyframe_points.foreach_set('co', coordinate_list)

        fc.update()  # Without this, left keyframe tangents/"Bézier handles"
                     # will extend to zero,  warping the shape of the curves 
                     # enough to lead to seemingly unpredictable changes in visibility
        fc_hide_render = act.fcurves.new(data_path='hide_render')
        fc_hide_render.keyframe_points.add(num_keyframes)
        fc_hide_render.keyframe_points.foreach_set('co', coordinate_list)

        fc_hide_render.update()


class AppearMixin_MBall(AppearMixin):
    """Replicant Methods for Appear behavior of MBall
    """
    def setKeyframesEnd(self, current_frame):
        # Additional lines for MBall specifically
        self.setScaleStart()
        self.obj.keyframe_insert(
            data_path="scale", frame=(current_frame - 1))
        self.obj.scale = self.scale_end

        # original setKeyframesMethod below
        self.obj.keyframe_insert(
            data_path="scale", frame=current_frame)
        self.obj.keyframe_insert(
            data_path="location", frame=current_frame)


class InflateMixin():
    """Replicant Methods for Inflate behavior.
    """
    def setScaleStart(self):
        """Sets size of replicant before it moves to its final position"""
        self.obj.scale[0] = 0
        self.obj.scale[1] = 0
        self.obj.scale[2] = 0

    def assignMotionPath(self, location_start, location_end):
        self.location_start = location_end
        self.location_end = location_end

        self.obj.location = location_end


class DivideAndMergeMixin():
    """locationIsEmpty only detects what was empty in previous generation
    Therefore, two objects can go to the same location in a given generation
    """
    def locationIsEmpty(self, location_vector):
        for replicant in self.replicants:
            if replicant.obj.location == location_vector:
                return False
        return True


##################################
# Pre/Post Replication Behaviors #
##################################

class BehaviorModifier():
    def __init__(self, keyframe_start, keyframe_end):
        pass

    def setBehavior(obj, behavior, behavior_func, keyframe_start, length,
                    delay=False, **kwargs):
        obj.keyframe_insert(
            data_path=behavior, frame=keyframe_start)
        if delay:
            obj.keyframe_insert(
                data_path=behavior, frame=(keyframe_start + delay))
            final_frame = keyframe_start + delay + length
        else:
            final_frame = keyframe_start + length

        behavior_func(kwargs)

        obj.keyframe_insert(
            data_path=behavior, frame=final_frame)

    def spin(obj, keyframe_start, length, delay=False, value=5, axis='X'):
        obj.keyframe_insert(
            data_path="rotation_euler", frame=keyframe_start)
        if delay:
            obj.keyframe_insert(
                data_path="rotation_euler", frame=(keyframe_start + delay))
            final_frame = keyframe_start + delay + length
        else:
            final_frame = keyframe_start + length

        bpy.ops.transform.rotate(value=value, orient_axis=axis,
                                 orient_type='GLOBAL',
                                 )
        obj.keyframe_insert(
            data_path="rotation_euler", frame=final_frame)


##############
# Replicants #
##############

class MBall(DivideMixin, Replicant):
    """MetaBalls that divide like cells
    """
    def __init__(self, **kwargs):
        bpy.ops.object.metaball_add(type='ELLIPSOID', radius=2.0,
                                    enter_editmode=False,
                                    align='WORLD',
                                    location=(
                                        kwargs['location_start'][0],
                                        kwargs['location_start'][1],
                                        kwargs['location_start'][2]),
                                    rotation=(0.0, 0.0, 0.0),)
        self.obj = bpy.context.active_object
        Replicant.__init__(self, **kwargs)


class MBall_Appear(AppearMixin_MBall, Replicant):
    """Mesh Cube Object to Replicate, will appear in final location"""
    def __init__(self, **kwargs):
        MBall.__init__(self, **kwargs)


class MBall_Inflate(InflateMixin, Replicant):
    """Mesh Cube Object to Replicate, will inflate in place"""
    def __init__(self, **kwargs):
        MBall.__init__(self, **kwargs)


class MBall_DivideAndMerge(DivideAndMergeMixin, Replicant):
    """locationIsEmpty only detects what was empty in previous generation
    Therefore, two objects can go to the same location in a given generation
    """
    def __init__(self, **kwargs):
        MBall.__init__(self, **kwargs)


class MeshCircle(Replicant):
    """Mesh Circle
    """
    def __init__(self, **kwargs):
        bpy.ops.mesh.primitive_circle_add(radius=1.0, enter_editmode=False,
                                          align='WORLD',
                                          location=(
                                              kwargs['location_start'][0],
                                              kwargs['location_start'][1],
                                              kwargs['location_start'][2]),
                                          rotation=(0.0, 0.0, 0.0),)
        self.obj = bpy.context.active_object
        Replicant.__init__(self, **kwargs)


class MeshSphere(Replicant):
    """Mesh Circle
    """
    def __init__(self, **kwargs):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, enter_editmode=False,
                                             align='WORLD',
                                             location=(
                                                 kwargs['location_start'][0],
                                                 kwargs['location_start'][1],
                                                 kwargs['location_start'][2]),
                                             rotation=(0.0, 0.0, 0.0),)
        self.obj = bpy.context.active_object
        Replicant.__init__(self, **kwargs)


class MeshSphere_Appear(AppearMixin, Replicant):
    """Mesh Cube Object to Replicate, will appear in final location"""
    def __init__(self, **kwargs):
        MeshCube.__init__(self, **kwargs)


class MeshSphere_Inflate(InflateMixin, Replicant):
    """Mesh Cube Object to Replicate, will inflate in place"""
    def __init__(self, **kwargs):
        MeshCube.__init__(self, **kwargs)


class IcoSphere(Replicant):
    """Mesh Ico Sphere
    """
    def __init__(self, **kwargs):
        bpy.ops.mesh.primitive_ico_sphere_add(radius=1.0, enter_editmode=False,
                                              align='WORLD',
                                              location=(
                                                  kwargs['location_start'][0],
                                                  kwargs['location_start'][1],
                                                  kwargs['location_start'][2]),
                                              rotation=(0.0, 0.0, 0.0),)
        self.obj = bpy.context.active_object
        Replicant.__init__(self, **kwargs)


class IcoSphere_Appear(AppearMixin, Replicant):
    """Mesh Ico Sphere Object to Replicate, will appear in final location"""
    def __init__(self, **kwargs):
        IcoSphere.__init__(self, **kwargs)


class IcoSphere_Inflate(InflateMixin, Replicant):
    """Mesh Ico Sphere Object to Replicate, will inflate in place"""
    def __init__(self, **kwargs):
        IcoSphere.__init__(self, **kwargs)


class Cylinder(Replicant):
    """Mesh Cylinder
    """
    def __init__(self, **kwargs):
        bpy.ops.mesh.primitive_cylinder_add(radius=1.0, enter_editmode=False,
                                            align='WORLD',
                                            location=(
                                                kwargs['location_start'][0],
                                                kwargs['location_start'][1],
                                                kwargs['location_start'][2]),
                                            rotation=(0.0, 0.0, 0.0),)
        self.obj = bpy.context.active_object
        Replicant.__init__(self, **kwargs)


class Cylinder_Appear(AppearMixin, Replicant):
    """Mesh Cylinder Object to Replicate, will appear in final location"""
    def __init__(self, **kwargs):
        Cylinder.__init__(self, **kwargs)


class Cylinder_Inflate(InflateMixin, Replicant):
    """Mesh Cylinder Object to Replicate, will inflate in place"""
    def __init__(self, **kwargs):
        Cylinder.__init__(self, **kwargs)


class Cone(Replicant):
    """Mesh Cone
    """
    def __init__(self, **kwargs):
        bpy.ops.mesh.primitive_cone_add(radius1=1.0, radius2=0,
                                        enter_editmode=False,
                                        align='WORLD',
                                        location=(
                                            kwargs['location_start'][0],
                                            kwargs['location_start'][1],
                                            kwargs['location_start'][2]),
                                        rotation=(0.0, 0.0, 0.0),)
        self.obj = bpy.context.active_object
        Replicant.__init__(self, **kwargs)


class Cone_Appear(AppearMixin, Replicant):
    """Mesh Cone Object to Replicate, will appear in final location"""
    def __init__(self, **kwargs):
        Cone.__init__(self, **kwargs)


class Cone_Inflate(InflateMixin, Replicant):
    """Mesh Cone Object to Replicate, will inflate in place"""
    def __init__(self, **kwargs):
        Cone.__init__(self, **kwargs)


class Torus(Replicant):
    """Torus Cone
    """
    def __init__(self, **kwargs):
        bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=.25,
                                         abso_major_rad=1.25,
                                         abso_minor_rad=0.75,
                                         align='WORLD',
                                         location=(
                                             kwargs['location_start'][0],
                                             kwargs['location_start'][1],
                                             kwargs['location_start'][2]),
                                         rotation=(0, 0, 0),)
        self.obj = bpy.context.active_object
        Replicant.__init__(self, **kwargs)


class Torus_Appear(AppearMixin, Replicant):
    """Mesh Torus Object to Replicate, will appear in final location"""
    def __init__(self, **kwargs):
        Cone.__init__(self, **kwargs)


class Torus_Inflate(InflateMixin, Replicant):
    """Mesh Torus Object to Replicate, will inflate in place"""
    def __init__(self, **kwargs):
        Cone.__init__(self, **kwargs)


class MeshCube(Replicant):
    """Mesh Cone Object to Replicate
    """
    def __init__(self, **kwargs):
        bpy.ops.mesh.primitive_cube_add(enter_editmode=False,
                                        align='WORLD',
                                        location=(
                                            kwargs['location_start'][0],
                                            kwargs['location_start'][1],
                                            kwargs['location_start'][2]),
                                        rotation=(0.0, 0.0, 0.0),)
        self.obj = bpy.context.active_object
        Replicant.__init__(self, **kwargs)


class MeshCube_Appear(AppearMixin, Replicant):
    """Mesh Cube Object to Replicate, will appear in final location"""
    def __init__(self, **kwargs):
        MeshCube.__init__(self, **kwargs)


class MeshCube_Inflate(InflateMixin, Replicant):
    """Mesh Cube Object to Replicate, will inflate in place"""
    def __init__(self, **kwargs):
        MeshCube.__init__(self, **kwargs)


class Custom(Replicant):
    """Mesh Circle
    """
    def __init__(self, location_start, location_end, parent=False,
                 scale_start=0, scale_end=False):
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
            scale_end = parent.obj_to_copy.scale

        Replicant.__init__(self, location_start=location_start,
                           location_end=location_end,
                           parent=parent, scale_start=scale_start,
                           scale_end=scale_end)


class Custom_Appear(AppearMixin, Replicant):
    """Custom Object to Replicate, will appear out of thin air"""
    def __init__(self, **kwargs):
        Custom.__init__(self, **kwargs)


class Custom_Inflate(InflateMixin, Replicant):
    """Custom Object to Replicate, will inflate in place"""
    def __init__(self, **kwargs):
        Custom.__init__(self, **kwargs)


###############
# Replicators #
###############

class MBall_Replicator(Replicator):
    behavior_objs = {
        "DIVIDE": MBall, "APPEAR": MBall_Appear,
        "INFLATE": MBall_Inflate, "DIVIDE_AND_MERGE": MBall_DivideAndMerge}

    def __init__(self, offset=4.0, start_x=0, start_y=0, start_z=0,
                 frame_start=0, frames_to_spawn=15, scale_start=0,
                 scale_end=[1, 1, 1], behavior="DIVIDE"):
        # Assign Behavior #
        self.obj_type = self._getBehaviorObject(behavior)
        Replicator.__init__(self, offset=offset, start_x=start_x,
                            start_y=start_y, start_z=start_z,
                            frame_start=frame_start,
                            frames_to_spawn=frames_to_spawn,
                            scale_start=scale_start, scale_end=scale_end,)


class MeshCircle_Replicator(Replicator):
    def __init__(self, offset=4.0, start_x=0, start_y=0, start_z=0,
                 frame_start=0, frames_to_spawn=15, scale_start=.2,
                 scale_end=[1, 1, 1], behavior="DIVIDE"):
        # Assign Behavior #
        self.obj_type = self._getBehaviorObject(behavior)
        Replicator.__init__(self, offset=offset, start_x=start_x,
                            start_y=start_y, start_z=start_z,
                            frame_start=frame_start, scale_end=scale_end,
                            frames_to_spawn=frames_to_spawn)


class MeshSphere_Replicator(Replicator):
    behavior_objs = {
        "DIVIDE": MeshSphere, "APPEAR": MeshSphere_Appear,
        "INFLATE": MeshSphere_Inflate}

    def __init__(self, offset=4.0, start_x=0, start_y=0, start_z=0,
                 frame_start=0, frames_to_spawn=15, scale_start=.2,
                 scale_end=[1, 1, 1], behavior="DIVIDE"):
        # Assign Behavior #
        self.obj_type = self._getBehaviorObject(behavior)
        Replicator.__init__(self, offset=offset, start_x=start_x,
                            start_y=start_y, start_z=start_z,
                            frame_start=frame_start, scale_end=scale_end,
                            frames_to_spawn=frames_to_spawn)


class IcoSphere_Replicator(Replicator):
    behavior_objs = {
        "DIVIDE": IcoSphere, "APPEAR": IcoSphere_Appear,
        "INFLATE": IcoSphere_Inflate}

    def __init__(self, behavior="DIVIDE", **kwargs):
        # Assign Behavior #
        self.obj_type = self._getBehaviorObject(behavior)
        Replicator.__init__(self, **kwargs)


class Cylinder_Replicator(Replicator):
    behavior_objs = {
        "DIVIDE": Cylinder, "APPEAR": Cylinder_Appear,
        "INFLATE": Cylinder_Inflate}

    def __init__(self, behavior="DIVIDE", **kwargs):
        # Assign Behavior #
        self.obj_type = self._getBehaviorObject(behavior)
        Replicator.__init__(self, **kwargs)


class Cone_Replicator(Replicator):
    behavior_objs = {
        "DIVIDE": Cone, "APPEAR": Cone_Appear,
        "INFLATE": Cone_Inflate}

    def __init__(self, behavior="DIVIDE", **kwargs):
        # Assign Behavior #
        self.obj_type = self._getBehaviorObject(behavior)
        Replicator.__init__(self, **kwargs)


class Torus_Replicator(Replicator):
    behavior_objs = {
        "DIVIDE": Torus, "APPEAR": Torus_Appear,
        "INFLATE": Torus_Inflate}

    def __init__(self, behavior="DIVIDE", **kwargs):
        # Assign Behavior #
        self.obj_type = self._getBehaviorObject(behavior)
        Replicator.__init__(self, **kwargs)


class MeshCube_Replicator(Replicator):
    behavior_objs = {
        "DIVIDE": MeshCube, "APPEAR": MeshCube_Appear,
        "INFLATE": MeshCube_Inflate}

    def __init__(self, behavior="DIVIDE", **kwargs):
        # Assign Behavior #
        self.obj_type = self._getBehaviorObject(behavior)
        Replicator.__init__(self, **kwargs)


class CustomObj_Replicator(Replicator):
    behavior_objs = {
        "DIVIDE": Custom, "APPEAR": Custom_Appear,
        "INFLATE": Custom_Inflate}

    def __init__(self, behavior="DIVIDE", offset=4.0,
                 start_x=False, start_y=False, start_z=False,
                 frame_start=0, frames_to_spawn=15, scale_start=.2,
                 scale_end=[1, 1, 1]):
        # Assign Behavior #
        self.obj_type = self._getBehaviorObject(behavior)
        active_obj = bpy.context.active_object
        if active_obj is None:
            raise ValueError("For Custom Object Replicators, a blender object "
                             "must be selected. bpy.context.active_object must"
                             " not be None.")
        self.obj_to_copy = CustomObj_Replicator.copyActiveObject(active_obj)
        scale_end = self.obj_to_copy.scale
        Replicator.__init__(self, offset=offset, start_x=start_x,
                            start_y=start_y, start_z=start_z,
                            frame_start=frame_start, scale_end=scale_end,
                            frames_to_spawn=frames_to_spawn)

    def copyActiveObject(active_obj):
        C = bpy.context
        new_obj = active_obj.copy()
        new_obj.data = active_obj.data.copy()
        new_obj.animation_data_clear()
        C.collection.objects.link(new_obj)

        return new_obj


# TO do - way to select a frame then add a generation that ends at that frame
# To Do - Copy any object's properties and make it a replicant
if __name__ == "__main__":
    time_start = time.time()

    #register()
    replicator1 = CustomObj_Replicator(behavior="DIVIDE",
        offset=4, frames_to_spawn=10, scale_start=0)
    replicator1.generate(6)

    replicator2 = Torus_Replicator(
        offset=4, frames_to_spawn=10, scale_start=0, behavior="DIVIDE",
        start_x=10)
    replicator2.generate(6)


    print("Script duration: %.4f sec" % (time.time() - time_start))
