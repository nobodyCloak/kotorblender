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
import bpy_extras

from ... import io


class KB_OT_import_mdl(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """Import Odyssey Engine model (.mdl)"""

    bl_idname = "kb.mdlimport"
    bl_label = "Import Odyssey MDL"
    bl_options = {'UNDO'}

    filename_ext = ".mdl"

    filter_glob: bpy.props.StringProperty(
        default="*.mdl",
        options={'HIDDEN'})

    import_normals: bpy.props.BoolProperty(
        name="Import Normals",
        default=True)

    import_animations: bpy.props.BoolProperty(
        name="Import Animations",
        default=True)

    import_walkmeshes: bpy.props.BoolProperty(
        name="Import Walkmeshes",
        description="Import area, door and placeable walkmeshes",
        default=True)

    import_materials: bpy.props.BoolProperty(
        name="Import Materials",
        default=True)

    import_armatures: bpy.props.BoolProperty(
        name="Import Armatures",
        description="Create an animated armature from model nodes",
        default=True)

    texture_search_recursive: bpy.props.BoolProperty(
        name="Recursive Texture Search",
        description="Search for textures in subdirectories",
        default=False)

    def execute(self, context):
        io.load_mdl(**self.as_keywords(ignore=("filter_glob",)))
        return {'FINISHED'}
