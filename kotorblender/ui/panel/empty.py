import bpy

from ... import defines


class KB_PT_empty(bpy.types.Panel):
    """
    Property panel for additional properties needed for the mdl file
    format. This is only available for EMPTY objects.
    It is located under the object data panel in the properties window
    """
    bl_label = "Odyssey Dummy Properties"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'EMPTY')

    def draw(self, context):
        obj    = context.object
        layout = self.layout

        row = layout.row()
        row.prop(obj.kb, "dummytype", text="Type")
        layout.separator()

        # Display properties depending on type of the empty
        if (obj.kb.dummytype == defines.Dummytype.MDLROOT):
            row = layout.row()
            box = row.box()
            split = box.split()
            col = split.column()
            col.label(text = "Classification:")
            col.label(text = "Supermodel:")
            col.label(text = "Ignore Fog:")
            col.label(text = "Animation Scale:")
            if obj.kb.classification == defines.Classification.CHARACTER:
                col.label(text = "Head Model:")
            col = split.column()
            col.prop(obj.kb, "classification", text = "")
            col.prop(obj.kb, "supermodel", text = "")
            col.prop(obj.kb, "ignorefog", text = "")
            col.prop(obj.kb, "animscale", text = "")
            if obj.kb.classification == defines.Classification.CHARACTER:
                col.prop(obj.kb, "headlink", text = "")
            box.operator("kb.recreate_armature")
            layout.separator()

            # All Children Settings Helper
            row = layout.row()
            box = row.box()
            box.label(text="Child Node Settings")
            row = box.row()
            row.label(text="Smoothgroups")
            row = box.row()
            op = row.operator("kb.children_smoothgroup", text="Direct")
            op.action = "DRCT"
            op = row.operator("kb.children_smoothgroup", text="Auto")
            op.action = "AUTO"
            op = row.operator("kb.children_smoothgroup", text="Single")
            op.action = "SING"
            op = row.operator("kb.children_smoothgroup", text="Separate")
            op.action = "SEPR"

        elif (obj.kb.dummytype == defines.Dummytype.PWKROOT):
            pass

        elif (obj.kb.dummytype == defines.Dummytype.DWKROOT):
            pass

        elif (obj.kb.dummytype == defines.Dummytype.REFERENCE):
            row = layout.row()
            box = row.box()

            row = box.row()
            row.prop(obj.kb, "refmodel")
            row = box.row()
            row.prop(obj.kb, "reattachable")

        else:
            row = layout.row()
            box = row.box()

            row = box.row()
            row.prop(obj.kb, "wirecolor")
            row = box.row()
            row.prop(obj.kb, "dummysubtype")