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

import os

from ..binwriter import BinaryWriter


class MdlSaver:
    def __init__(self, path, model):
        self.mdl = BinaryWriter(path, 'little')

        basepath, _ = os.path.splitext(path)
        mdx_path = basepath + ".mdx"
        self.mdx = BinaryWriter(mdx_path, 'little')

        self.model = model

    def save(self):
        mdl_size = 0
        mdx_size = 0

        self.mdl.put_uint32(0)
        self.mdl.put_uint32(mdl_size)
        self.mdl.put_uint32(mdx_size)
