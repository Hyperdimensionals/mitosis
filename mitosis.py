bl_info = {
    "name": "Mitosis",
    "blender": (3, 1, 0),
    "category": "Object",
}

import bpy
#import bpy_types
from math import radians
import mathutils

import time  # only imported for testing purposes


class Replicant():
    """"""
    def __init__(self, location_start,
                 location_end, obj=False, parent=False,
                 scale_start=mathutils.Vector((0, 0, 0)),
                 scale_end=mathutils.Vector((1, 1, 1))):
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

    def setAttributesStart(self, frame_current, frames_to_spawn=False):
        """Sets start attributes, before replicant moves to final position"""
        self.setScaleStart()

        bpy.data.objects[self.obj.name].select_set(True)
        self.setKeyframesStart(frame_current)

        # Make sure replicants aren't visible before their spawn animation 
        self.setViewportVisAnimation(
            frame_visible=frame_current - 1, frames_to_spawn=frames_to_spawn)

    def setScaleStart(self):
        """Sets size of replicant before it moves to its final position"""
        self.obj.scale[0] = self.scale_start[0]
        self.obj.scale[1] = self.scale_start[1]
        self.obj.scale[2] = self.scale_start[2]

    def assignMotionPath(self, location_start, location_end):
        self.location_start = location_start
        self.location_end = location_end

    def setKeyframesStart(self, current_frame):
        """Insert any keyframes for start of animation"""
        self.obj.keyframe_insert(
            data_path="scale", frame=current_frame)
        self.obj.keyframe_insert(
            data_path="location", frame=current_frame)

    def setKeyframesEnd(self, current_frame):
        """Insert any keyframes for end of animation"""
        self.obj.keyframe_insert(
            data_path="scale", frame=current_frame)
        self.obj.keyframe_insert(
            data_path="location", frame=current_frame)

    def setViewportVisAnimation(
            self, frame_visible, frame_hidden=False, frames_to_spawn=False):
        """Add viewport visibility keyframes.
        Only run this after all other replicant properties are set
        Object is hidden when fcurve y-value is greater than or equal to 1.
        Arguments
        obj -- The blender object to animate
        frame_visible -- Set frame at which the object will become visible
        frame_hidden -- Optional argument, frame to hide object again
                        not currently implemented"""
        #self.obj.animation_data_create()
        #ac = bpy.data.actions.new('Viewport Visibility')
        frame_visible = (frame_visible - 1) if frame_visible >= 0 else 0

        if self.obj.animation_data is None:
            self.obj.animation_data_create()
        ac = self.obj.animation_data.action
        frame_visible = frame_visible # + self.frames_to_spawn

        coordinate_list = [0, 1, frame_visible, 1, frame_visible + 1, 0]
        num_keyframes = int(len(coordinate_list) / 2)
        assert ((len(coordinate_list) % 2) is 0
                ), "coordinate_list must contain even number of items."

        print("hide_veiwport fcurve: {0}".format(ac.fcurves.find(data_path='hide_viewport')))
        if ac.fcurves.find(data_path='hide_viewport') is None:
            fc = ac.fcurves.new(data_path='hide_viewport')
            final_cordinates = coordinate_list
        else:
            fc = ac.fcurves.find(data_path='hide_viewport')
            print(fc)
            current_keyframes = []
            for a,b in fc.keyframe_points.items():
                print("{0} and {1} ".format(a, b.co))
                current_keyframes += [b.co[0], b.co[1]]
            print(current_keyframes)
            final_cordinates = current_keyframes + coordinate_list
        print("keyframe points: {0}".format(len(fc.keyframe_points)))
        fc.keyframe_points.add(num_keyframes)
        fc.keyframe_points.foreach_set('co', final_cordinates)

        fc.update()  # Without this, left keyframe tangents/"Bézier handles"
                     # will extend to zero,  warping the shape of the curves
                     # enough to lead to seemingly unpredictable changes in visibility
        if ac.fcurves.find(data_path='hide_render') is None:
            fc_hide_render = ac.fcurves.new(data_path='hide_render')
            final_cordinates = coordinate_list
        else:
            fc_hide_render = ac.fcurves.find(data_path='hide_render')
            current_keyframes = []
            for a, b in fc_hide_render.keyframe_points.items():
                current_keyframes += [b.co[0], b.co[1]]
            final_cordinates = current_keyframes + coordinate_list

        fc_hide_render.keyframe_points.add(num_keyframes)
        fc_hide_render.keyframe_points.foreach_set('co', final_cordinates)

        fc_hide_render.update()

    def setPostBehaviors(self, behaviors, frame_current):
        """Adds post replication animation behaviors to replicant"""
        for behavior in behaviors:
            BehaviorModifiers.setBehavior(
                blender_obj=self.obj, keyframe_start=frame_current,
                data_path=behavior['data_path'], length=behavior['length'],
                delay=behavior['delay'], value=behavior['value'],
                index=behavior['index'])
        pass


class Replicator():
    """"""
    # Describes the object's replication animation ###
    behaviors = ["DIVIDE", "SEPARATE", "APPEAR", "INFLATE", "DIVIDE_AND_MERGE"]

    def __init__(self, offset=4.0, frame_start=0, frames_to_spawn=15,
                 scale_start=[0, 0, 0], scale_end=[1, 1, 1],
                 start_x=0, start_y=0, start_z=0,
                 use_x=True, use_y=True, use_z=True):
        def scaleTypeCheck(scale_list):
            if ((isinstance(scale_list, list) or (
                    isinstance(scale_list, bpy.types.bpy_prop_array) or (
                    isinstance(scale_list, mathutils.Vector)))
                 ) and len(scale_list) == 3):
                for scle in scale_list:
                    try:
                        1 + scle
                    except TypeError:
                        raise TypeError("All items in scale keyword args"
                                        "list must be numbers.")
                return mathutils.Vector(
                    (scale_list[0], scale_list[1], scale_list[2]))
            else:
                raise TypeError("Scale keyword arguments must be "
                                "lists with 3 numbers")
        self.offset = offset

        self.replicants = []
        self._replicants_new = []  # stores newly replicated objects
        self.num_replicants = 0
        self.end_replicants_created = None

        self.frame_start = frame_start
        self.frames_to_spawn = frames_to_spawn
        self.frame_current = frame_start

        self.use_x = use_x
        self.use_y = use_y
        self.use_z = use_z

        self.post_behaviors = []

        self.scale_start = scaleTypeCheck(scale_start)
        self.scale_end = scaleTypeCheck(scale_end)

        if start_x is False:  # If this is CustomObj_Replicator
            location_start = self.obj_to_copy.location
            first_replicant = Replicant( # First replicant is just the original object
                location_start, location_start, parent=self,
                scale_start=1, scale_end=1)
            first_replicant.obj = self.obj_to_copy
            # I'm not sure why I originally had these lines, trying to figure out
            # error where one of the first spawn locations ends up empty
            #first_replicant.setAttributesStart(self.frame_current, self.frames_to_spawn)
            #first_replicant.setViewportVisAnimation(self.frame_start)
            self.replicants.append(first_replicant)
            print("Replicant list: {0}".format(self.replicants))
        else:
            location_start = mathutils.Vector((start_x, start_y, start_z))
            self._addReplicant(
                location_start=location_start, location_end=location_start)

    def newGeneration(self):
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
            replicant.setPostBehaviors(self.post_behaviors, self.frame_current)
        self._replicants_new.clear()

    def generate(self, generations=5):
        """Runs Replicator for given number of generations"""
        i = 0
        while i < generations:
            self.newGeneration()
            i += 1

    def _addReplicant(self, location_start, location_end=False):
        """Adds a new object"""
        self.num_replicants += 1
        replicant = self.obj_type(location_start=location_start,
                                  location_end=location_end, parent=self,
                                  scale_start=self.scale_start,
                                  scale_end=self.scale_end)
        replicant.setAttributesStart(self.frame_current, self.frames_to_spawn)
        #replicant.obj.active_material.name = 
        #replicant.obj.setMaterials()

        self.replicants.append(replicant)
        self._replicants_new.append(replicant)

        return replicant

    def spawn(self, replicant, direction=0):
        """Multiplies given replicant in the first available empty space
        Arguments:
        direction -- Integer representing a direction around given replicant
        use_x, use_y, & use_z -- Set true to allow spawn in that dimension"""
        direction += 1
        # \/ Change order of these to alter replication behavior
        if (direction is 1) and (self.use_x is True):
            spawn_location = replicant.obj.location + mathutils.Vector((
                self.offset, 0.0, 0.0))
        elif (direction is 2) and (self.use_x is True):
            spawn_location = replicant.obj.location + mathutils.Vector((
                -self.offset, 0.0, 0.0))
        elif (direction is 3) and (self.use_y is True):
            spawn_location = replicant.obj.location + mathutils.Vector((
                0.0, self.offset, 0.0))
        elif (direction is 4) and (self.use_y is True):
            spawn_location = replicant.obj.location + mathutils.Vector((
                0.0, -self.offset, 0.0))
        elif (direction is 5) and (self.use_z is True):
            spawn_location = replicant.obj.location + mathutils.Vector((
                0.0, 0.0, self.offset))
        elif (direction is 6) and (self.use_z is True):
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
            self.spawn(replicant, direction)

    def locationIsEmpty(self, location_vector):
        for replicant in self.replicants:
            if (replicant.obj.location == location_vector) or (
                    replicant.location_end == location_vector):
                return False
        return True

    def useActiveObject(self):
        obj_to_replicate = bpy.context.active_object

    def addPostBehavior(
            self, behavior):
        """Creates a behavior each replicant will perform after replicating
        Arguments:

        behavior -- String of data_path of object property
        length -- number of keyframes to execute animation
        delay -- optional, # of frames to delay behavior after replication
        value -- value of change, default used if none given
        index -- index of property, default used if none given"""
        assert isinstance(
            behavior, dict), "Argument must be a dict"
        self._postBehaviorInputCheck(  # Doesn't check everything yet
            behavior)

        self.post_behaviors.append(
            behavior)

    def addPostBehaviors(self, *behaviors):
        """Accepts any number of dicts containing post-behavior instructions
        Each dict should contain these keys:
        behavior -- String of data_path of object property
        length -- number of keyframes to execute animation
        delay -- optional, number of frames to delay before starting animation
        value -- value of change, default used if none
        index -- index of property, default used if none"""

        for behavior in behaviors:
            try:
                assert isinstance(
                    behavior, dict), "Every item in behavior list must be "
                "a dictionary."
                self.addPostBehavior(behavior)
            except KeyError as E:
                raise ValueError("The dictionary that is index {} "
                                 "in the given behavior list is missing"
                                 " the following key: {}".format(
                                     behaviors.index(behavior), E)
                                 )

    def _postBehaviorInputCheck(self, behavior_dict):
        """Checks inputs of addPostBehavior and addPostBehaviors methods"""
        # Eventually check all keys/values of behavior dict here
        assert isinstance(
            behavior_dict['data_path'], str), "data_path value must be string "
        "representing blender object's data_path"

        return True

    def _getBehaviorObject(self, behavior):
        behavior = behavior.upper()
        if (behavior in Replicator.behaviors) and (
                behavior in self.behavior_objs.keys()):
            return self.behavior_objs[behavior]
        else:
            raise ValueError("behavior keyword must be string describing "
                             "spawn behavior from the following list: " + str(
                                 self.behavior_objs.keys()))


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

    def setViewportVisAnimation(self, frame_visible, frame_hidden=False,
        frames_to_spawn=False):
        """Modified original func to make visible frame last frame of spawn"""
        frame_visible = frame_visible + self.parent.frames_to_spawn
        Replicant.setViewportVisAnimation(self, frame_visible,
            frame_hidden=False, frames_to_spawn=False)

    def animateViewportVisiblity(self, frame_visible, frame_hidden=False):
        """DOESNT DO ANYTIHNG YET Deciding whether to replace above method to not repeat code w/ BehaviorModifiers"""
        BehaviorModifiers.setBehavior(
            blender_obj=self.obj, keyframe_start=frame_visible,
            data_path='hide_viewport', length=1)


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

class BehaviorModifiers():
    """Class for adding behaviors beyond simple replication
    """
    mods = ["ROTATE", "MOVE", "CHANGE SCALE"]

    def __init__(self, keyframe_start, keyframe_end):
        pass

    def setBehavior(blender_obj, keyframe_start, data_path, length,
                    delay=False, value=5, index=0):
        """Generalized func to animate specified obj property via fcurves
        Arguments
        obj -- blender object to animate
        behavior -- string representing data_path of obj property
        keyframe_start -- integer, frame animation begins
        length -- integer, number of frames behavior is animated
        delay -- integer, # of frames after replication animation will begin"""
        # tested with the following data paths: rotation_euler, delta_location,
        # delta_scale
        if delay:
            keyframe_start = keyframe_start + delay
            final_frame = keyframe_start + delay + length
        else:
            final_frame = keyframe_start + length

        if blender_obj.animation_data is None:
            blender_obj.animation_data_create()
            #bpy.data.actions.new('Modifier Action')

        ac = blender_obj.animation_data.action
        fc = ac.fcurves.new(data_path=data_path, index=index)

        # Find current value of data_path at start frame
        bpy.context.scene.frame_current = keyframe_start
        current_value = blender_obj.__getattribute__(data_path)[index]

        fc.keyframe_points.add(2)
        fc.keyframe_points.foreach_set(
            'co', [keyframe_start, current_value, final_frame, value])
        fc.update()

    def rotate(blender_obj, keyframe_start, length,
               delay=False, amount=5, axis='x',
               index=None, value=None):
        """Sets euler rotation with setBehavior(). 'axis' arg becomes index"""
        index = index if index else BehaviorModifiers._axisToIndex(axis)
        value = value if value else amount
        BehaviorModifiers.setBehavior(
            blender_obj, keyframe_start, data_path='rotation_euler',
            length=length, delay=delay, value=value, index=index)

    def move(blender_obj, keyframe_start, length, delay=False,
             amount=0, axis='x', index=None, value=None):
        """Sets change in location as x,y,z coordinate, with setBehavior()
        Arguments:
        value -- number representing amount of change
        index -- an int from 0-2, represents direction
                 0 == x, 1 == y, 2 == z"""
        index = index if index else BehaviorModifiers._axisToIndex(axis)
        value = value if value else amount
        BehaviorModifiers.setBehavior(
            blender_obj, keyframe_start, length=length,
            data_path="delta_location", delay=delay, value=value, index=index)

    def change_scale(blender_obj, keyframe_start, length, delay=False,
                     amount=0, axis='x', index=None, value=None):
        """Sets change in scale in x,y, or z coordinate, with setBehavior()
        Arguments:
        value -- number representing amount of change
        index -- an int from 0-2, represents direction"""
        index = index if index else BehaviorModifiers._axisToIndex(axis)
        value = value if value else amount
        BehaviorModifiers.setBehavior(
            blender_obj, keyframe_start, length=length,
            data_path="delta_scale", delay=delay, value=value, index=index)

    def _axisToIndex(axis_string):
        if axis_string == 'x':
            index = 0
        elif axis_string == 'y':
            index = 1
        elif axis_string == 'z':
            index = 2
        else:
            raise ValueError("axis argument must be 'x', 'y', or 'z', "
                             "corresponding to the desired axis of rotation.")
        return index

    def setBehaviorKeyInsert(obj, behavior, behavior_func, keyframe_start,
                             length, delay=False, **kwargs):
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


##############
# Replicants #
##############

class Custom(Replicant):
    """Holds data and methods for individual spawned objects
    Arguments:
    location_start -- Location of object pre animation
    location_end -- Location of object post replication animation
    parent -- Replicator object which created this Replicant object
    scale_start -- Size of object pre animation
    scale_end -- Size of object after replication animation
    """
    def __init__(self, location_start, location_end, parent=False,
                 scale_start=0, scale_end=False):
        try:
            self.obj = parent.obj_to_copy.copy()
            # MAKE objects as LINKED DUPLICATES AN OPTION SO ALL REPLICANT OBJECTS ARE CHANGED WHEN EDITED
        except AttributeError as e:
            raise AttributeError("Parent Replicator must have obj_to_copy "
                                 "attribute for Custom Replicants. Original "
                                 "error:\n" + str(e))
        C = bpy.context

        self.obj.name = parent.obj_to_copy.name + "_Replicant" \
            + str(parent.num_replicants)
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

class CustomObj_Replicator(Replicator):
    behavior_objs = {
        "DIVIDE": Custom, "APPEAR": Custom_Appear,
        "INFLATE": Custom_Inflate}

    def __init__(self, behavior="DIVIDE", offset=4.0,
                 start_x=False, start_y=False, start_z=False,
                 frame_start=0, frames_to_spawn=15, scale_start=[.2, .2, .2],
                 scale_end=False, **kwargs):
        # Assign Behavior #
        self.obj_type = self._getBehaviorObject(behavior)
        self.obj_to_copy = bpy.context.active_object
        if self.obj_to_copy is None:
            raise ValueError("For Custom Object Replicators, a blender object "
                             "must be selected. bpy.context.active_object must"
                             " not be None.")
        if scale_end is False:
            scale_end = self.obj_to_copy.scale
        Replicator.__init__(self, offset=offset, start_x=start_x,
                            start_y=start_y, start_z=start_z,
                            frame_start=frame_start, scale_start=scale_start,
                            scale_end=scale_end,
                            frames_to_spawn=frames_to_spawn, **kwargs)

    def copyActiveObject(active_obj):
        C = bpy.context
        new_obj = active_obj.copy()
        new_obj.data = active_obj.data.copy()
        new_obj.animation_data_clear()
        C.collection.objects.link(new_obj)

        return new_obj


#######
# GUI #
#######

class OBJECT_PT_MitosisPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window
    This is used if I make MitosisAddon a bpy.types.Operator
    """
    bl_label = "Mitosis Animation"
    bl_idname = "OBJECT_PT_mitosis"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    bpy.types.Scene.mod_title = bpy.props.StringProperty(
        name="Behavior Modifiers",
        description="My description",
    )  # assigned w/ row.prop(context.scene, "mod_title")
    def draw(self, context):
        layout = self.layout

        # Access properties that are stored via addon keymaps
        # This is done in register() function
        wm = bpy.context.window_manager
        km = wm.keyconfigs.addon.keymaps['Object Mode']
        mitosis_props = km.keymap_items[0].properties
        mitosis_props = context.scene.mitosis_props

        for prop in mitosis_props.__annotations__.keys():
            # __annotations__ used at suggestion of
            # https://blender.stackexchange.com/questions/72402/how-to-iterate-through-a-propertygroup
            row = layout.row()
            if prop == "modifier":
                row.label(text="Behavior Modifiers")
                row = layout.row()
                col = layout.column()
                col.prop(mitosis_props, prop, icon_only=True)
            else:
                row.prop(mitosis_props, prop)
        row = layout.row()
        row.operator("object.mitosis", text="Execute")


class MitosisProperties(bpy.types.PropertyGroup):
    """User defined variables for mitosis animations.
    """
    generations : bpy.props.IntProperty(
        name="Generations",
        description="Number of times replicants will divide",
        default=1, min=1
    )

    offset : bpy.props.FloatProperty(
        name="Spawn Offset",
        description="End distance between replicated objects ",
        min=0.0, default=4.0
    )

    frames_to_spawn : bpy.props.IntProperty(
        name="Frames to Spawn",
        description="Number of keyframes of each spawn animation",
        min=0, default=15
    )

    use_x: bpy.props.BoolProperty(
        name="Spawn in X Axis", default=True,
        description="Replicants will spawn in the X Axis direction")
    use_y: bpy.props.BoolProperty(
        name="Spawn in Y Axis", default=True,
        description="Replicants will spawn in the Y Axis direction")
    use_z: bpy.props.BoolProperty(
        name="Spawn in Z Axis", default=True,
        description="Replicants will spawn in the Z Axis direction")

    scale_start: bpy.props.FloatVectorProperty(
        name="Starting Scale",
        #options='HIDDEN',
        description="Size of each spawn upon start of animation",
        min=0.0, default=[0.2, 0.2, 0.2]
    )

    scale_end: bpy.props.FloatVectorProperty(
        name="End Scale",
        description="Size of each spawn at end of animation",
        min=0.0, default=[1.0, 1.0, 1.0]
    )

    use_target_scale: bpy.props.BoolProperty(
        name="Use Target Object Scale",
        description="Spawned objects will be the same size as target object")

    behavior_strings = []
    for b in CustomObj_Replicator.behavior_objs.keys():
        behavior_strings.append((b, b.capitalize(), ""))
    behavior_strings = tuple(behavior_strings)

    behavior: bpy.props.EnumProperty(
        name="Behavior",
        description="Determines the animation of the replication",
        items=behavior_strings,
        default='DIVIDE')

    # Behavior Modifiers #
    modifier_strings = []
    for b in BehaviorModifiers.mods:
        modifier_strings.append((b, b.capitalize(), ""))
    modifier_strings = tuple(modifier_strings)

    modifier: bpy.props.EnumProperty(
        name="Behavior Modifiers",
        description="Set pre or post replication behaviors",
        items=modifier_strings,
        default='ROTATE',
        #update=bpy.ops.object.mitosis_behavior_mod('INVOKE_DEFAULT') # Call update function that opens behavior mod sub menu when mod is selected?
        )

class OBJECT_OT_MitosisAddon(bpy.types.Operator):
    """Object Replication Animation"""
    bl_idname = "object.mitosis"
    bl_label = "Mitosis"
    bl_options = {'REGISTER', 'UNDO'}

    # Consider whether it's better to have below propertyies here,
    # or directly register them with the Scene in register() function
    # registering them with Scene means values will be saved
    # to better understand: https://docs.blender.org/api/current/info_overview.html

    def invoke(self, context, event):
        # wm = context.window_manager
        # return wm.invoke_props_dialog(self)
        # /\ Makes props dialog box open
        print("EVENT: {0}".format(event))
        return self.execute(context)

    def execute(self, context):
        execute_func(self, context)
        return{'FINISHED'}

def execute_func(self, context):
    # MIGHT WANT TO PASS context arg TO REPLICATOR INSTEAD OF USING BPY.CONTEXT IN ALL THE CODE ABOVE
    # SINCE SOME CODE MAY PASS CUSTOM CONTEXT TO OPERATORS
    end_scale = context.scene.mitosis_props.scale_end if context.scene.mitosis_props.use_target_scale is False else False
    custom_replicator = CustomObj_Replicator(
        behavior=context.scene.mitosis_props.behavior, offset=context.scene.mitosis_props.offset,
        frames_to_spawn=context.scene.mitosis_props.frames_to_spawn,
        scale_start=context.scene.mitosis_props.scale_start, scale_end=end_scale,
        use_x=context.scene.mitosis_props.use_x, use_y=context.scene.mitosis_props.use_y, use_z=context.scene.mitosis_props.use_z)
    custom_replicator.generate(context.scene.mitosis_props.generations)


class OBJECT_OT_BehaviorModOp(bpy.types.Operator):
    """Object Replication Animation"""
    bl_idname = "object.drawtest"
    bl_label = "Mitosis Drawtest"
    bl_options = {'REGISTER', 'UNDO'}

    # Consider whether it's better to have below propertyies here,
    # or directly register them with the Scene in register() function
    # registering them with Scene means values will be saved
    # to better understand: https://docs.blender.org/api/current/info_overview.html

    generations : bpy.props.IntProperty(
        name="Generations",
        description="Number of times replicants will divide",
        default=1, min=1
    )

    offset : bpy.props.FloatProperty(
        name="Spawn Offset",
        description="End distance between replicated objects ",
        min=0.0, default=4.0
    )

    frames_to_spawn : bpy.props.IntProperty(
        name="Frames to Spawn",
        description="Number of keyframes of each spawn animation",
        min=0, default=15
    )

    use_x: bpy.props.BoolProperty(
        name="Spawn in X Axis", default=True,
        description="Replicants will spawn in the X Axis direction")
    use_y: bpy.props.BoolProperty(
        name="Spawn in Y Axis", default=True,
        description="Replicants will spawn in the Y Axis direction")
    use_z: bpy.props.BoolProperty(
        name="Spawn in Z Axis", default=True,
        description="Replicants will spawn in the Z Axis direction")

    scale_start: bpy.props.FloatVectorProperty(
        name="Starting Scale",
        #options='HIDDEN',
        description="Size of each spawn upon start of animation",
        min=0.0, default=[0.2, 0.2, 0.2]
    )

    scale_end: bpy.props.FloatVectorProperty(
        name="End Scale",
        description="Size of each spawn at end of animation",
        min=0.0, default=[1.0, 1.0, 1.0]
    )

    use_target_scale: bpy.props.BoolProperty(
        name="Use Target Object Scale",
        description="Spawned objects will be the same size as target object")

    behavior_strings = []
    for b in CustomObj_Replicator.behavior_objs.keys():
        behavior_strings.append((b, b.capitalize(), ""))
    behavior_strings = tuple(behavior_strings)

    behavior: bpy.props.EnumProperty(
        name="Behavior",
        description="Determines the animation of the replication",
        items=behavior_strings,
        default='DIVIDE')

    modifier_strings = []
    for b in BehaviorModifiers.mods:
        modifier_strings.append((b, b.capitalize(), ""))
    modifier_strings = tuple(modifier_strings)

    modifier: bpy.props.EnumProperty(
        name="Behavior Modifiers",
        description="Set pre or post replication behaviors",
        items=modifier_strings,
        default='ROTATE',
        #update=bpy.ops.object.mitosis_behavior_mod('INVOKE_DEFAULT') # Call update function that opens behavior mod sub menu when mod is selected?
        )

    def draw(self, context):
        layout = self.layout

        col=layout.column()
        col.label(text="asdf")
        row = col.row()
        row.prop(self, "generations")

        row = layout.row()
        row.prop(self, "offset")

        row = layout.row()
        row.prop(self, "frames_to_spawn")

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        end_scale = self.scale_end if self.use_target_scale is False else False
        custom_replicator = CustomObj_Replicator(
            behavior=self.behavior, offset=self.offset,
            frames_to_spawn=self.frames_to_spawn,
            scale_start=self.scale_start, scale_end=end_scale,
            use_x=self.use_x, use_y=self.use_y, use_z=self.use_z)
        custom_replicator.generate(self.generations)

        return{'FINISHED'}


def menu_func(self, context):
    self.layout.operator(OBJECT_OT_MitosisAddon.bl_idname)

class OBJECT_PT_BehaviorModPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_behavior_mods"
    bl_label = "Add a behavior modifier to the spawn animations"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        layout = self.layout

        # Access properties that are stored via addon keymaps
        # This is done in register() function
        wm = bpy.context.window_manager
        km = wm.keyconfigs.addon.keymaps['Object Mode']
        mitosis_props = context.scene.mitosis_props

        row = layout.row()
        row.operator("object.mitosis", text="Execute")

def mod_menu_func(self, context):
    self.layout.operator_context = 'INVOKE_DEFAULT'
    self.layout.operator(BehaviorModMenu.bl_idname, text="Behavior Modifier")

    #def draw(self, context):
    #    pass


def add_panel_func(self, context):
    """Appends to a panel"""
    """Add to current panel"""
    layout = self.layout

    row = layout.row(align=True)
    row.prop(context.scene, "generations")
    #row.prop(bpy.types.object.behaviormod, "my_float")

# store keymaps here to access after registration
addon_keymaps = []

def register():
    bpy.types.Scene.generations = bpy.props.IntProperty(
        name="Generations",
        description="Number of times object will divide",
        min=1
    )

    bpy.types.Scene.offset = bpy.props.FloatProperty(
        name="Spawn Offset",
        description="End distance between replicated objects ",
        min=0.0, default=4.0
    )

    # Custom Keymaps
    # object.mitosis Operator w/ the addon's properties is stored here
    # because properties won't be editable in panel UI if not
    # (they'd only be editable in popup)
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Object Mode', space_type='EMPTY')
    kmi = bpy.context.window_manager.keyconfigs.addon.keymaps['Object Mode'].keymap_items.new(
        "object.mitosis", "NONE", "ANY")
    addon_keymaps.append((km, kmi))

    bpy.utils.register_class(MitosisProperties)
    bpy.types.Scene.mitosis_props = bpy.props.PointerProperty(type=MitosisProperties)

    bpy.utils.register_class(OBJECT_PT_MitosisPanel)
    bpy.utils.register_class(OBJECT_OT_MitosisAddon)
    bpy.utils.register_class(OBJECT_OT_BehaviorModOp)

    print("Panels: {0}".format(bpy.types.Panel))
    #bpy.types.OBJECT_PT_mitosis.append(add_panel_func)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.types.VIEW3D_MT_object.remove(menu_func)

    bpy.utils.unregister_class(OBJECT_OT_BehaviorModOp)
    bpy.utils.unregister_class(OBJECT_OT_MitosisAddon)
    bpy.utils.unregister_class(OBJECT_PT_MitosisPanel)
    bpy.utils.unregister_class(MitosisProperties)

    del bpy.types.Scene.string_prop_1


# TO do - way to select a frame then add a generation that ends at that frame
# To Do - Copy any object's properties and make it a replicant
if __name__ == "__main__":
    time_start = time.time()

    register()

def pasas():
    replicator1 = CustomObj_Replicator(behavior="DIVIDE",
        offset=12, frames_to_spawn=5, scale_start=0,
        use_x=True, use_z=False)
    replicator1.addPostBehaviors(
        {'data_path': 'rotation_euler', 'value': 10, 'length': 50,
         'delay': False, 'index': 0},
         {'data_path': 'delta_location', 'value': 50, 'length': 50,
         'delay': False, 'index': 2})
    replicator1.generate(10)

    print("Script duration: %.4f sec" % (time.time() - time_start))

