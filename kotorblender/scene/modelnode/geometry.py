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

from mathutils import Matrix, Quaternion

from ...defines import RootType


class GeometryNode:

    def __init__(self, name="UNNAMED"):
        self.nodetype = "undefined"
        self.roottype = RootType.MODEL

        self.node_number = 0
        self.export_order = 0
        self.name = name
        self.position = (0.0, 0.0, 0.0)
        self.orientation = (1.0, 0.0, 0.0, 0.0)
        self.scale = 1.0

        self.parent = None
        self.children = []
        self.from_root = Matrix()

    def add_to_collection(self, collection, options):
        obj = bpy.data.objects.new(self.name, None)
        self.set_object_data(obj, options)
        collection.objects.link(obj)
        return obj

    def set_object_data(self, obj, options):
        obj.kb.node_number = self.node_number
        obj.kb.export_order = self.export_order
        obj.location = self.position
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = Quaternion(self.orientation)
        obj.scale = (self.scale, self.scale, self.scale)

    def load_object_data(self, obj, options):
        self.node_number = obj.kb.node_number
        self.export_order = obj.kb.export_order
        self.position = obj.location
        self.orientation = obj.rotation_quaternion
        self.scale = obj.scale[0]

        self.from_root = obj.matrix_local
        if self.parent:
            self.from_root = self.parent.from_root @ self.from_root

    def find_node(self, test):
        if test(self):
            return self
        for child in self.children:
            if test(child):
                return child
        return None
