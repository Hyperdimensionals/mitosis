import bpy
import bpy_types

ob = bpy.context.active_object
ob.animation_data_create()

ac = bpy.data.actions.new('Rotate Action')
ob.animation_data.action = ac
fc = ac.fcurves.new(data_path='rotation_euler', index=2)
fc.keyframe_points.add(2)
fc.keyframe_points.foreach_set('co', [0, 0, 30, 10])
fc.update()

fc2 = ac.fcurves.new(data_path='rotation_euler', index=0)
fc2.keyframe_points.add(2)
fc2.keyframe_points.foreach_set('co', [0, 0, 30, 10])
fc2.update()
