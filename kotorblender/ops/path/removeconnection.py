import bpy

from ... import utils


class KB_OT_remove_connection(bpy.types.Operator):
    bl_idname = "kb.remove_path_connection"
    bl_label = "Remove Odyssey Path Connection"

    @classmethod
    def poll(cls, context):
        return utils.is_path_point(context.object) and (len(context.object.kb.path_connections) > 0)

    def execute(self, context):
        context.object.kb.path_connections.remove(context.object.kb.active_path_connection)
        return {'FINISHED'}