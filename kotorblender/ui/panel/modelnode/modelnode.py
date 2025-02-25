# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy

from .... import utils


class KB_PT_modelnode(bpy.types.Panel):
    bl_label = "KotOR Model Node"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        return context.object

    def draw(self, context):
        obj = context.object
        layout = self.layout
        layout.use_property_split = True

        if obj.type == 'EMPTY':
            row = layout.row()
            row.prop(obj.kb, "dummytype")
        elif obj.type == 'MESH':
            row = layout.row()
            row.prop(obj.kb, "meshtype")

        if utils.is_exported_to_mdl(obj):
            row = layout.row()
            row.prop(obj.kb, "node_number")
