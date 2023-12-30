bl_info = {
    "name": "Mitosis",
    "author": "Brendan Krueger",
    "description": "Procedurally animate replication of objects and 'flock behavior'",
    "version": (0, 1, 0, 0),
    "blender": (3, 1, 0),
    "warning": "",
    "category": "Object",
}
import sys

import bpy
from math import radians
import mathutils
import random

import time  # only imported for testing purposes

class Replicant():
    """Represents attributes of a single replicated object.
    """
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

        :param frame_visible: Int, frame at which the obj will become visible
        :param frame_hidden: Int, frame to hide object again
                             NOT CURRENTLY IMPLEMENTED
        :return: None"""
        frame_visible = (frame_visible - 1) if frame_visible >= 0 else 0

        if self.obj.animation_data is None:
            self.obj.animation_data_create()
        ac = self.obj.animation_data.action
        frame_visible = frame_visible

        coordinate_list = [0, 1, frame_visible, 1, frame_visible + 1, 0]
        num_keyframes = int(len(coordinate_list) / 2)
        assert ((len(coordinate_list) % 2) is 0
                ), "coordinate_list must contain even number of items."

        fc_hide_vp = ac.fcurves.find(data_path='hide_viewport')

        if fc_hide_vp is None:
            fc_hide_vp = ac.fcurves.new(data_path='hide_viewport')
            final_cordinates = coordinate_list
        else:
            current_keyframes = []
            for a, b in fc_hide_vp.keyframe_points.items():
                current_keyframes += [b.co[0], b.co[1]]
            final_cordinates = current_keyframes + coordinate_list
        fc_hide_vp.keyframe_points.add(num_keyframes)
        fc_hide_vp.keyframe_points.foreach_set('co', final_cordinates)

        fc_hide_vp.update()
        # Without fc.update(), left keyframe tangents/"Bézier handles"
        # will extend to zero,  warping the shape of the curves
        # enough to lead to seemingly unpredictable changes in visibility

        fc_hide_render = ac.fcurves.find(data_path='hide_render')
        if fc_hide_render is None:
            fc_hide_render = ac.fcurves.new(data_path='hide_render')
            final_cordinates = coordinate_list
        else:
            current_keyframes = []
            for a, b in fc_hide_render.keyframe_points.items():
                current_keyframes += [b.co[0], b.co[1]]
            final_cordinates = current_keyframes + coordinate_list

        fc_hide_render.keyframe_points.add(num_keyframes)
        fc_hide_render.keyframe_points.foreach_set('co', final_cordinates)

        fc_hide_render.update()

    def setBehaviorMods(self, behaviors, frame_current):
        """Adds post replication animation behaviors to replicant"""
        for behavior in behaviors:
            BehaviorModifiers.setBehavior(
                blender_obj=self.obj, keyframe_start=frame_current,
                data_path=behavior['data_path'], duration=behavior['duration'],
                delay=behavior['delay'], value=behavior['value'],
                index=behavior['index'])
        pass


class Replicator():
    """
    Contains and controls a given replication process and its settings
    """
    # Describors of the object's replication animation ###
    BEHAVIORS = ["DIVIDE", "SEPARATE", "APPEAR", "INFLATE", "DIVIDE_AND_MERGE"]

    def __init__(self, offset=4.0, frame_start=0, frames_to_spawn=15,
                 scale_start=[0, 0, 0], scale_end=[1, 1, 1],
                 start_x=0, start_y=0, start_z=0,
                 use_x=True, use_y=True, use_z=True, linked=True):
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
        self.linked = linked

        self.replicants = []
        self._replicants_new = []  # stores newly replicated objects
        self.num_replicants = 0
        self.end_replicants_created = None

        # Create Collection / Folder for Replicants
        collection_name = self.obj_to_copy.name + ' Replicants'
        self.collection = bpy.context.blend_data.collections.new(
            name=collection_name)
        bpy.context.scene.collection.children.link(self.collection)
        print("COLLECTION: {0}".format(self.collection))

        self.frame_start = frame_start
        self.frames_to_spawn = frames_to_spawn
        self.frame_current = frame_start

        self.use_x = use_x
        self.use_y = use_y
        self.use_z = use_z

        self.behavior_mods = []

        self.scale_start = scaleTypeCheck(scale_start)
        self.scale_end = scaleTypeCheck(scale_end)

        if start_x is False:  # If this is CustomObj_Replicator
            location_start = self.obj_to_copy.location
            first_replicant = Replicant(  # First one is the original object
                location_start, location_start, parent=self,
                scale_start=1, scale_end=1)
            first_replicant.obj = self.obj_to_copy
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
            replicant.setBehaviorMods(self.behavior_mods, self.frame_current)
        self._replicants_new.clear()

    def generate(self, generations=5):
        """Runs Replicator for given number of generations
        :param generations: int, n of times any existing replicators will spawn
        :return: None
        """
        i = 0
        while i < generations:
            self.newGeneration()
            i += 1

    def _addReplicant(self, location_start, location_end=False):
        """Adds a new object
        :param location_start: mathutils.Vector, start point of added replicant
        :param location_end: mathutils.Vector, end point of added replicant
        :return: Replicant"""
        self.num_replicants += 1
        replicant = self.obj_type(location_start=location_start,
                                  location_end=location_end, parent=self,
                                  scale_start=self.scale_start,
                                  scale_end=self.scale_end,
                                  linked=self.linked)
        replicant.setAttributesStart(self.frame_current, self.frames_to_spawn)

        self.replicants.append(replicant)
        self._replicants_new.append(replicant)

        return replicant

    def spawn(self, replicant, direction=0):
        """Multiplies given replicant in the first available empty space
        :param replicant: Replicant Object
        :param direction: Int, representing a direction around given replicant
        :return: mathutils.Vector, location of spawned replicant"""
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
        """ Checks if spawn location is already occupied by another replicant
        :param location_vector: mathutils.Vector, location to check
        :return: Bool, True if location empty"""
        for replicant in self.replicants:
            if (replicant.obj.location == location_vector) or (
                    replicant.location_end == location_vector):
                return False
        return True

    def addBehaviorMod(
            self, new_behavior):
        """Creates a behavior each replicant will perform after replicating
        :return: None"""
        assert isinstance(
            new_behavior, dict), "Argument must be a dict of behavior settings"
        self._behaviorModInputCheck(  # Doesn't check everything yet
            new_behavior)

        self.behavior_mods.append(
            new_behavior)

    def addBehaviorMods(self, new_behaviors):
        """Adds new behavior modifying instructions, from given dicts
        Each dictionary should contain these keys:
        behavior -- String of data_path of object property
        duration -- number of keyframes to execute animation
        delay -- optional, number of frames to delay before starting animation
        value -- value of change, default used if none
        index -- index of property, default used if none

        :param new_behaviors: list of dicts, each dict contains behavior
                              modifying instructions
        :return: None
        """

        # self.behavior_mods is cleared, Behavior Mod settings are stored in
        # Blender PropertyCollection (See UI section of code)
        self.behavior_mods = []

        for behavior in new_behaviors:
            try:
                assert isinstance(
                    behavior, dict), "Every item in behavior list must be "
                "a dictionary, instead received a {0}".format(type(behavior))
                self.addBehaviorMod(behavior)
            except KeyError as E:
                raise ValueError("The dictionary that is index {} "
                                 "in the given behavior list is missing"
                                 " the following key: {}".format(
                                     new_behaviors.index(behavior), E)
                                 )

    def _behaviorModInputCheck(self, behavior_dict):
        """Checks inputs of addBehaviorMod and addBehaviorMods methods"""
        # Eventually check all keys/values of behavior dict here
        assert isinstance(
            behavior_dict['data_path'], str), "data_path value must be string "
        "representing blender object's data_path"

        return True

    def _getBehaviorObject(self, behavior):
        behavior = behavior.upper()
        if (behavior in Replicator.BEHAVIORS) and (
                behavior in self.behavior_objs.keys()):
            return self.behavior_objs[behavior]
        else:
            raise ValueError("behavior keyword must be string describing "
                             "spawn behavior from the following list: " + str(
                                 self.behavior_objs.keys()))

    def saveBehaviorMods(self, name="Behaviors"):
        """Save replicator state, including behavior modifiers
        :return: None
        """
        # NOT TESTED #
        behavior_mods = []
        try:
            with open('behaviormods.pkl', 'rb') as input:
                behavior_mods = pickle.load(input)
        except FileNotFoundError as E:
            behavior_mods = []

        behavior_mods.append([name, self.behavior_mods])

        with open('behaviormods.pkl', 'wb') as o:
            pickle.dump(behavior_mods, o)

##########################
# Behavior Mixin Methods #
##########################
# For Replicant Objects

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
            data_path='hide_viewport', duration=1)


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
    # Key is behavior description string, value is blender data_path
    # for behavior
    mods = {"ROTATE": 'rotation_euler', "MOVE": 'delta_location',
            "CHANGE SCALE": 'delta_scale'}

    def __init__(self, keyframe_start, keyframe_end, behavior_mods=False):
        self.behavior_mods = behavior_mods  # move to store behavior mod dicts here instead of in Replicator?

    def setBehavior(blender_obj, data_path, duration,
                    delay=0, value=5, index=0, keyframe_start=None):
        """Generalized func to animate specified obj property via fcurves
        Arguments:
        obj -- blender object to animate
        data_path -- string representing data_path of obj property
        duration -- integer, number of frames behavior is animated
        delay -- integer, # of frames after replication animation will begin
        value -- value to assign to data path
        index -- data path index to access
                 (ex: for rotation, determines rotation direction)
        keyframe_start -- integer, frame animation begins
        """
        # tested with the following data paths: rotation_euler, delta_location,
        # delta_scale
        frame_start = keyframe_start + delay
        final_frame = keyframe_start + delay + duration

        blender_obj.animation_data_create()
            #bpy.data.actions.new('Modifier Action')

        ac = blender_obj.animation_data.action
        if ac.fcurves.find(data_path=data_path, index=index) is None:
            fc = ac.fcurves.new(data_path=data_path, index=index)
        else:
            fc = ac.fcurves.find(data_path=data_path, index=index)

        # Find current value of data_path at start frame
        try:
            current_value = fc.keyframe_points.values()[-1].co[1]
        except IndexError:
            current_value = blender_obj.__getattribute__(data_path)[index]

        bpy.context.scene.frame_current = frame_start

        #fc.keyframe_points.add(2)
        #fc.keyframe_points.foreach_set(  # first arg attribute, second sequence
        #    'co', [keyframe_start, current_value, final_frame, value])

        #print("FC final_frame: {0}".format(frame_start))
        fc.keyframe_points.insert(frame=frame_start, value=current_value)
        fc.keyframe_points.insert(frame=final_frame, value=value)

        fc.update()

    def rotate(blender_obj, duration,
               delay=False, amount=5, axis='x',
               index=None, value=None, keyframe_start=None):
        """Sets euler rotation with setBehavior(). 'axis' arg becomes index"""
        index = index if index else BehaviorModifiers._axisToIndex(axis)
        value = value if value else amount
        BehaviorModifiers.setBehavior(
            blender_obj, keyframe_start, data_path='rotation_euler',
            duration=duration, delay=delay, value=value, index=index)

    def move(blender_obj, duration, delay=False,
             amount=0, axis='x', index=None, value=None, keyframe_start=None):
        """Sets change in location as x,y,z coordinate, with setBehavior()
        Arguments:
        value -- number representing amount of change
        index -- an int from 0-2, represents direction
                 0 == x, 1 == y, 2 == z"""
        index = index if index else BehaviorModifiers._axisToIndex(axis)
        value = value if value else amount
        BehaviorModifiers.setBehavior(
            blender_obj, keyframe_start, duration=duration,
            data_path="delta_location", delay=delay, value=value, index=index)

    def move_rand_direction(num_axis=2):
        """Animates movement in random direction
        Can randomize amount of movement as well
        NOT IMPLEMENTED OR COMPLETED
        :num_axis: int, number of axises to randomize on
        """
        if num_axis not in [0, 1, 2]:
            raise ValueError("num_axis must be 0, 1, or 2")
        axis = BehaviorModifiers.getRandomAxis_3()

    def change_scale(blender_obj, duration, delay=False,
                     amount=0, axis='x', index=None, value=None, keyframe_start=None):
        """Sets change in scale in x,y, or z coordinate, with setBehavior()
        Arguments:
        value -- number representing amount of change
        index -- an int from 0-2, represents direction"""
        index = index if index else BehaviorModifiers._axisToIndex(axis)
        value = value if value else amount
        BehaviorModifiers.setBehavior(
            blender_obj, keyframe_start, duration=duration,
            data_path="delta_scale", delay=delay, value=value, index=index)

    def _axisToIndex(axis_str):
        axis_dict = {'x':0, 'y':1, 'z':2}
        if (axis_str >= 0) and (axis_str <= 2):
            return axis_str
        else:
            try:
                return axis_dict[axis_str]
            except IndexError:
                raise ValueError("axis_str argument must be 'x', 'y', or 'z', "
                                 "corresponding to the desired axis of rotation.")

    def _getRandomAxis():
        return random.randint(0, 2)

    def getRandomAxis_3(axis_1=False, axis_2=False, axis_3=False):
        """Animates movement in random direction"""
        if not axis_1:
            axis_1 = BehaviorModifiers._getRandomAxis()
        if not axis_2:
            axis_2 = BehaviorModifiers._getRandomAxis()
            if axis_1 is axis_2:
                return BehaviorModifiers._getRandomAxis_3(
                    axis_1=axis_1, axis_2=False)
        axis_3 = BehaviorModifiers._getRandomAxis()
        if (axis_1 is axis_3) or (axis_2 is axis_3):
            return BehaviorModifiers._getRandomAxis_3(
                axis_1=axis_1, axis_2=axis_2, axis_3=False)
        return [axis_1, axis_2, axis_3]

    def setBehaviorKeyInsert(obj, behavior, behavior_func, keyframe_start,
                             duration, delay=False, **kwargs):
        obj.keyframe_insert(
            data_path=behavior, frame=keyframe_start)
        if delay:
            obj.keyframe_insert(
                data_path=behavior, frame=(keyframe_start + delay))
            final_frame = keyframe_start + delay + duration
        else:
            final_frame = keyframe_start + duration

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
                 scale_start=0, scale_end=False, linked=True):
        try:
            self.obj = parent.obj_to_copy.copy()
            parent.collection.objects.link(self.obj)
            # MAKE objects as LINKED DUPLICATES AN OPTION SO ALL REPLICANT OBJECTS ARE CHANGED WHEN EDITED
        except AttributeError as e:
            raise AttributeError("Parent Replicator must have obj_to_copy "
                                 "attribute for Custom Replicants. Original "
                                 "error:\n" + str(e))
        context = bpy.context

        self.obj.name = parent.obj_to_copy.name + "_Replicant" \
            + str(parent.num_replicants)
        if not linked:  # Copying data unlinks the blender object from original
            self.obj.data = parent.obj_to_copy.data.copy()
        self.obj.animation_data_clear()
        self.obj.scale[0] = parent.obj_to_copy.scale[0]
        self.obj.scale[1] = parent.obj_to_copy.scale[1]
        self.obj.scale[2] = parent.obj_to_copy.scale[2]

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
                 scale_end=False, linked=True, **kwargs):
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
                            frames_to_spawn=frames_to_spawn, linked=linked, **kwargs)

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
        print(self)
        layout = self.layout

        # mitosis_props = km.keymap_items[0].properties
        mitosis_props = context.scene.mitosis_props

        for prop in mitosis_props.__annotations__.keys():
            # __annotations__ used at suggestion of
            # https://blender.stackexchange.com/questions/72402/how-to-iterate-through-a-propertygroup
            if prop == 'use_target_scale':
                box = layout.box()
                col = box.column()
                row = col.split(factor=.6)
                row.prop(mitosis_props, prop)
            elif prop == 'linked_data':
                row.prop(mitosis_props, prop)
            else:
                row = layout.row()
                row.prop(mitosis_props, prop)
        row = layout.row()
        row.operator("object.mod_list", text="Behavior Modifiers")
        if not isinstance(self, OBJECT_OT_MitosisPopupPanel):
            # Refrain from drawing execute button if drawing as popup
            row = layout.row()
            row.operator("object.mitosis", text="Execute")

    def execute(self, context):
        return context.window_manager.invoke_popup(self, width=300)

class MitosisProperties(bpy.types.PropertyGroup):
    """User defined variables for mitosis animations.
    """
    generations : bpy.props.IntProperty(
        name="Generations",
        description="Number of times replicated object will divide.",
        default=1, min=1
    )

    offset : bpy.props.FloatProperty(
        name="Spawn Offset",
        description="End distance between replicated objects.",
        min=0.0, default=4.0
    )

    frames_to_spawn : bpy.props.IntProperty(
        name="Frames to Spawn",
        description="Number of keyframes of each spawn animation.",
        min=0, default=15
    )

    frame_start: bpy.props.IntProperty(
        name="Starting Frame",
        description="Frame that replication animation begins.",
        default=0)

    use_x: bpy.props.BoolProperty(
        name="Spawn in X Axis", default=True,
        description="Spawn replicants in the X Axis direction.")
    use_y: bpy.props.BoolProperty(
        name="Spawn in Y Axis", default=True,
        description="Spawn replicants in the Y Axis direction.")
    use_z: bpy.props.BoolProperty(
        name="Spawn in Z Axis", default=True,
        description="Spawn replicants in the Z Axis direction.")

    scale_start: bpy.props.FloatVectorProperty(
        name="Starting Scale",
        #options='HIDDEN',
        description="Size of each spawned object upon start of animation.",
        min=0.0, default=[0.2, 0.2, 0.2]
    )

    scale_end: bpy.props.FloatVectorProperty(
        name="End Scale",
        description="Size of each spawned object at end of animation.",
        min=0.0, default=[1.0, 1.0, 1.0]
    )

    use_target_scale: bpy.props.BoolProperty(
        name="Use Target Object Scale",
        description="Make spawned objects the same size as target object",
        default=True)

    linked_data: bpy.props.BoolProperty(
        name="Linked Data",
        description="Link spawned objects data to original object",
        default=True)

    behavior_strings = []
    for b in CustomObj_Replicator.behavior_objs.keys():
        behavior_strings.append((b, b.capitalize(), ""))
    behavior_strings = tuple(behavior_strings)

    behavior: bpy.props.EnumProperty(
        name="Behavior",
        description="Determines the type of spawn animation",
        items=behavior_strings,
        default='DIVIDE')


class OBJECT_OT_MitosisAddon(bpy.types.Operator):
    """Object Replication Animation"""
    bl_idname = "object.mitosis"
    bl_label = "Mitosis"
    bl_options = {'REGISTER', 'UNDO'}

    # Consider whether it's better to have below propertyies here,
    # or directly register them with the Scene in register() function
    # registering them with Scene means values will be saved
    # to better understand: https://docs.blender.org/api/current/info_overview.html

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

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
        behavior=context.scene.mitosis_props.behavior,
        offset=context.scene.mitosis_props.offset,
        frames_to_spawn=context.scene.mitosis_props.frames_to_spawn,
        frame_start=context.scene.mitosis_props.frame_start,
        scale_start=context.scene.mitosis_props.scale_start,
        scale_end=end_scale, use_x=context.scene.mitosis_props.use_x,
        use_y=context.scene.mitosis_props.use_y,
        use_z=context.scene.mitosis_props.use_z,
        linked=context.scene.mitosis_props.linked_data)
    custom_replicator.addBehaviorMods(get_behavior_mod_values(context))
    custom_replicator.generate(context.scene.mitosis_props.generations)

def get_data_path_string(behavior_type):
    """Takes the selected behavior_type string and gets data_path string
    Data path is stored as value in BehaviorModifiers.mods dict """
    return BehaviorModifiers.mods[behavior_type]


def get_behavior_mod_values(context):
    """Returns dicts of mod settings formatted for use by replicators"""
    behavior_mods = []
    for mod in context.scene.mitosis_mod_props:
        behavior_mods.append({
            'data_path': get_data_path_string(mod.behavior_type),
            'index': int(mod.direction), 'value': mod.value,
            'duration': mod.duration, 'delay': mod.delay
        })
    return behavior_mods


def behavior_type_changed(self, context):
    """Func to call when behavior type is changed"""
    print("Behavior Modifier Type changed"
        "This will be used to update behavior mod UI if"
        "different behavior types need different settings"
        "displayed")


class ModProperties(bpy.types.PropertyGroup):
    """Properties for individual mitosis behavior modifiers.
    """
    behavior_mods = []  # List of dicts w/ each mod's settings
    behavior_type_strings = []
    for b in BehaviorModifiers.mods:
        behavior_type_strings.append((b, b.capitalize(), ""))
    behavior_type_strings = tuple(behavior_type_strings)

    behavior_type: bpy.props.EnumProperty(
        name="Behavior",
        description="Set pre or post replication behaviors",
        items=behavior_type_strings,
        default='ROTATE',
        update=behavior_type_changed
    )
    data_path_index: bpy.props.IntProperty(
        name="Data Path Index",
        description="Determines index for data path of fcurve",
        default=0,
    )
    direction: bpy.props.EnumProperty(
        name="Direction",
        description="XYZ Direction of behavior",
        items=[('0', 'X', "X Axis", 0), ('1', 'Y', "Y Axis", 1),
              ('2', 'Z', "Z Axis", 2)],
        )
    delay: bpy.props.IntProperty(
        name="Starting Keyframe",
        description="Set the number of keyframes before or after the "
                    "replication animation the behavior mod animation will "
                    "begin",
        default=0  # bpy.data.objects[0].mitosis_props.frames_to_spawn
    )
    duration: bpy.props.IntProperty(
        name="Duration (frames)",
        description="Number of keyframes of animation",
        min=1, default=15
    )
    value: bpy.props.IntProperty(
        name="Value",
        description="Generic Value. Ex: W/ rotation determines euler rotation "
        "amount",
        default=15
    )

    delete: bpy.props.BoolProperty(
        name="-",
        description="Delete this behavior mod",
        default=False
    )


class OBJECT_OT_BehaviorModOp(bpy.types.Operator):
    """Add a behavior modifier"""
    bl_idname = "object.behavior_mod"
    bl_label = "New Behavior Modifier"
    bl_options = {'REGISTER', 'UNDO'}

    #Try to call from ModProperties property group and then I can delete all these properties here
    behavior_type_strings = []
    for b in BehaviorModifiers.mods:
        behavior_type_strings.append((b, b.capitalize(), ""))
    behavior_type_strings = tuple(behavior_type_strings)

    behavior_type: bpy.props.EnumProperty(
        name="Behavior",
        description="Set pre/post spawn behaviors",
        items=behavior_type_strings,
        default='ROTATE',
        #update=bpy.ops.object.mitosis_behavior_mod('INVOKE_DEFAULT') # Call update function that opens behavior mod sub menu when mod is selected?
        )
    direction: bpy.props.EnumProperty(
        name="Direction",
        description="XYZ Direction of behavior",
        items=[('0', 'X', "X Axis", 0), ('1', 'Y', "Y Axis", 1),
              ('2', 'Z', "Z Axis", 2)])
    delay: bpy.props.IntProperty(
        name="Delay (frames)",
        description="Set the number of frames before or after spawn that "
                    "animation will begin",
        default=0 # bpy.data.objects[0].mitosis_props.frames_to_spawn
    )

    duration: bpy.props.IntProperty(
        name="Duration (frames)",
        description="Number of keyframes of animation",
        min=1, default=15
    )

    value: bpy.props.IntProperty(
        name="Value",
        description="Amount of behavior. Ex: W/ rotation, determines euler"
        " rotation amount",
        min=-10, default=15
    )

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        print(self.__annotations__.keys())
        new_mod = context.scene.mitosis_mod_props.add()
        new_mod.behavior_type = self.behavior_type
        new_mod.direction = self.direction
        new_mod.delay = self.delay
        new_mod.duration = self.duration
        new_mod.value = self.value

        # NOTE: This clears the mod CollectionProperty and adds back elements
        # sorted. I could not find a more direct way to sort properties:
        sort_collection_by_start_frame(context.scene.mitosis_mod_props)

        print_behavior_mods(context)
        return{'FINISHED'}


class OBJECT_OT_MitosisPopupPanel(bpy.types.Operator):
    """Mitosis Popup Menu
    See Mitosis settings via popup.
    Pressing 'OK' executes animation.
    """
    bl_idname = "object.mitosispopup"
    bl_label = "Mitosis Animation"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        """Draws panel from draw() func in OBJECT_PT_mitosis"""
        OBJECT_PT_MitosisPanel.draw(self, context)

    def execute(self, context):
        """Runs execute function shared with OBJECT_OT_MitosisAddon"""
        execute_func(self, context)
        return {'FINISHED'}


def add_to_obj_menu(self, context):
    """Appends Mitosis to object menu"""
    self.layout.operator(OBJECT_OT_MitosisPopupPanel.bl_idname)


class MitosisMenuPopup(bpy.types.Operator):
    """Object Replication Animation"""
    bl_idname = "object.mitosis_popup"
    bl_label = "Mitosis"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        wm = context.window_manager
        return wm.invoke_props_dialog(bpy.types.OBJECT_PT_mitosis, width=450)


class OBJECT_OT_BehaviorModRemove(bpy.types.Operator):
    """Delete Behavior Modifier with given index"""
    bl_idname = "object.behavior_mod_remove"
    bl_label = "Remove Behavior Modifier?"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty(
        name="Index",
        description="Index of Behavior Mod to remove",
        min=0, default=0
    )

    # draw func to produce confirm popup. Probably not necessary,
    # instead executing when invoked
    # def draw(self, context):
    #    layout = self.layout
    #    row = layout.row()
    #    row.label(text="")

    def invoke(self, context, event):
        """Invoke runs execute func to delete behavior mod"""
        return self.execute(context)

    def execute(self, context):
        """Delete behavior mod with the given index"""
        context.scene.mitosis_mod_props.remove(self.index)
        return{'FINISHED'}


class OBJECT_OT_BehaviorModList(bpy.types.Operator):
    """Displays Current behavior mods
    """
    bl_idname = "object.mod_list"
    bl_label = "See and edit current behavior modifiers"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        layout = self.layout

        mods = context.scene.mitosis_mod_props

        box = layout.box()

        # Reminder: factor of split() func determine % of available space used
        # by next column
        col1_factor = .25
        col2_factor = .2
        col3_factor = .3
        col4_factor = .4
        col5_factor = .6

        # First Row of Titles
        col = box.column()
        row = col.split(factor=col1_factor)
        row.label(text="Behavior")
        row = row.split(factor=col2_factor)
        row.label(text="Direction")
        row = row.split(factor=col3_factor)
        row.label(text="Delay (frames)")
        row = row.split(factor=col4_factor)
        row.label(text="Duration")
        row = row.split(factor=col5_factor)
        row.label(text="Value")
        row.label(text="delete")

        i = 0
        for mod in mods:  # Create row for each behavior mod
            col = box.column()
            row = col.split(factor=col1_factor)
            row.prop(mod, "behavior_type", text='')
            row = row.split(factor=col2_factor)
            row.prop(mod, "direction", text='')
            row = row.split(factor=col3_factor)
            row.prop(mod, "delay", text='')
            row = row.split(factor=col4_factor)
            row.prop(mod, "duration", text='')
            row = row.split(factor=col5_factor)
            row.prop(mod, "value", text='')
            row.operator("object.behavior_mod_remove", text="-").index = i
            i += 1

        row = layout.row()
        row.split(factor=.1)
        row.operator("object.behavior_mod", text="New Behavior Mod")

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=450)

    def execute(self, context):
        """Execute just closes the window at this point"""
        return{'FINISHED'}


def sort_collection_by_start_frame(collection):
    """Clears the given Property Collection and adds back elements sorted
       I could not find a more direct way to sort properties
       This only works on behavior mod collection because property attributes
       are referred to non-dynamically in this func
       :param collection: behavior mod CollectionProperty
       :return collection: new sorted collection """
    def copy_values(collection):
        copied_values = []
        for c in collection:
            copied_values.append(
                {'behavior_type': c.behavior_type,
                'delay': c.delay,
                'duration': c.duration,
                'value': c.value
                }
            )
        return copied_values

    def criteria(c):
        return c['delay']

    sortdicts = copy_values(collection)
    print("unsorted collection: {0}".format(sortdicts))
    sortdicts.sort(key=criteria)
    print("sorted collection: {0}".format(sortdicts))

    i = 0
    for c in sortdicts:
        collection[i].behavior_type = c['behavior_type']
        collection[i].delay = c['delay']
        collection[i].duration = c['duration']
        collection[i].value = c['value']
        i += 1
    return collection

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

    bpy.utils.register_class(MitosisProperties)
    bpy.types.Scene.mitosis_props = bpy.props.PointerProperty(
        type=MitosisProperties)
    bpy.utils.register_class(OBJECT_OT_BehaviorModRemove)
    bpy.utils.register_class(ModProperties)
    bpy.types.Scene.mitosis_mod_props = bpy.props.CollectionProperty(
        type=ModProperties)
    bpy.utils.register_class(OBJECT_PT_MitosisPanel)
    bpy.utils.register_class(MitosisMenuPopup)
    bpy.utils.register_class(OBJECT_OT_MitosisAddon)
    bpy.utils.register_class(OBJECT_OT_MitosisPopupPanel)
    bpy.utils.register_class(OBJECT_OT_BehaviorModOp)
    bpy.utils.register_class(OBJECT_OT_BehaviorModList)

    bpy.types.VIEW3D_MT_object.append(add_to_obj_menu)


def unregister():
    bpy.types.VIEW3D_MT_object.remove(add_to_obj_menu)

    bpy.utils.unregister_class(OBJECT_OT_BehaviorModList)
    bpy.utils.unregister_class(OBJECT_OT_BehaviorModOp)
    bpy.utils.unregister_class(OBJECT_OT_MitosisPopupPanel)
    bpy.utils.unregister_class(OBJECT_OT_MitosisAddon)
    bpy.utils.unregister_class(MitosisMenuPopup)
    bpy.utils.unregister_class(OBJECT_PT_MitosisPanel)
    bpy.utils.unregister_class(ModProperties)
    bpy.utils.unregister_class(OBJECT_OT_BehaviorModRemove)
    bpy.utils.unregister_class(MitosisProperties)


def print_behavior_mods(context):
    """Print a list of behavior modifiers
    :param context: Blender context object
    :return: None 
    """
    mods = context.scene.mitosis_mod_props

    print("Current Behavior Modifiers:")
    for mod in mods:
        print("MOD: {0}, VALUE: {1}, DURATION: {2}".format(
            mod.behavior_type, mod.value, mod.duration))

    print(mods.values())
    print("Behavior Mod list type {0}".format(type(mods)))

# TO do - way to select a frame then add a generation that ends at that frame
# To Do - Copy any object's properties and make it a replicant
if __name__ == "__main__":
    time_start = time.time()

    register()

    def test_behavior_mods():
        """
        Create Basic blender object, then add behavior mods to it and generate.
        """
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))

        replicator1 = CustomObj_Replicator(behavior="DIVIDE",
            offset=12, frames_to_spawn=5, scale_start=[0.2, 0.2, 0.2],
            use_x=True, use_z=False)
        replicator1.addBehaviorMods(
            [{'data_path': 'rotation_euler', 'value': 100, 'duration': 50,
             'delay': False, 'index': 0},
             {'data_path': 'delta_location', 'value': 50, 'duration': 50,
             'delay': False, 'index': 2}])
        replicator1.generate(7)
    #test_behavior_mods()

    print("Script duration: %.4f sec" % (time.time() - time_start))


