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

from ...defines import Nodetype

from ... import defines

from ..binwriter import BinaryWriter

from .types import *


class MdlSaver:
    def __init__(self, path, model, tsl):
        self.mdl = BinaryWriter(path, 'little')

        basepath, _ = os.path.splitext(path)
        mdx_path = basepath + ".mdx"
        self.mdx = BinaryWriter(mdx_path, 'little')

        self.model = model
        self.tsl = tsl

        self.mdl_pos = 0
        self.mdx_pos = 0
        self.mdl_size = 0
        self.mdx_size = 0
        self.off_name_offsets = 0

        self.nodes = []
        self.name_offsets = []
        self.node_offsets = []
        self.children_offsets = []

        self.parent_indices = []
        self.child_indices = []

        self.controller_keys = []
        self.controller_data = []
        self.controller_offsets = []
        self.controller_counts = []
        self.controller_data_offsets = []
        self.controller_data_counts = []

        self.verts_offsets = dict()
        self.faces_offsets = dict()
        self.index_count_offsets = dict()
        self.index_offset_offsets = dict()
        self.inv_count_offsets = dict()
        self.indices_offsets = dict()
        self.mdx_offsets = dict()

    def save(self):
        self.peek_model()

        self.save_file_header()
        self.save_geometry_header()
        self.save_model_header()
        self.save_names()
        self.save_nodes()

    def peek_model(self):
        self.mdl_pos = 80 + 116  # geometry header + model header
        self.off_name_offsets = self.mdl_pos

        self.peek_nodes(self.model.root_node)

        self.mdl_pos += 4 * len(self.nodes)  # name offsets

        self.peek_node_names()
        self.peek_node_data()

        self.mdl_size = self.mdl_pos
        self.mdx_size = self.mdx_pos

    def peek_nodes(self, node, parent_idx=None):
        node_idx = len(self.nodes)
        self.nodes.append(node)
        self.parent_indices.append(parent_idx)
        self.child_indices.append([])

        for child in node.children:
            child_idx = len(self.nodes)
            self.child_indices[node_idx].append(child_idx)
            self.peek_nodes(child, node_idx)

    def peek_node_names(self):
        for node in self.nodes:
            self.name_offsets.append(self.mdl_pos)
            self.mdl_pos += len(node.name) + 1

    def peek_node_data(self):
        for node_idx, node in enumerate(self.nodes):
            self.node_offsets.append(self.mdl_pos)
            self.mdl_pos += 80  # geometry header

            type_flags = self.get_node_flags(node)
            if type_flags & NODE_MESH:
                self.mdl_pos += 332  # mesh header
                if self.tsl:
                    self.mdl_pos += 8

                self.faces_offsets[node_idx] = self.mdl_pos
                self.mdl_pos += 32 * len(node.facelist.faces)  # faces

                self.index_offset_offsets[node_idx] = self.mdl_pos
                self.mdl_pos += 4  # index offset

                self.verts_offsets[node_idx] = self.mdl_pos
                self.mdl_pos += 4 * 3 * len(node.verts)  # vertices

                self.index_count_offsets[node_idx] = self.mdl_pos
                self.mdl_pos += 4  # index count

                self.inv_count_offsets[node_idx] = self.mdl_pos
                self.mdl_pos += 4  # inverted count

                self.indices_offsets[node_idx] = self.mdl_pos
                self.mdl_pos += 2 * 3 * len(node.facelist.faces)  # indices

                self.mdx_offsets[node_idx] = self.mdx_pos
                self.mdx_pos += 4 * 3 * (len(node.verts) + 1)
                self.mdx_pos += 4 * 3 * (len(node.normals) + 1)
                if node.tverts:
                    self.mdx_pos += 4 * 2 * (len(node.tverts) + 1)
                if node.tverts1:
                    self.mdx_pos += 4 * 2 * (len(node.tverts1) + 1)

            ctrl_keys = []
            ctrl_data = []
            self.peek_controllers(node, type_flags, ctrl_keys, ctrl_data)
            ctrl_count = len(ctrl_keys)
            ctrl_data_count = len(ctrl_data)
            self.controller_keys.append(ctrl_keys)
            self.controller_data.append(ctrl_data)
            self.controller_counts.append(ctrl_count)
            self.controller_data_counts.append(ctrl_data_count)

            self.children_offsets.append(self.mdl_pos)
            self.mdl_pos += 4 * len(node.children)

            self.controller_offsets.append(self.mdl_pos)
            self.mdl_pos += 16 * ctrl_count

            self.controller_data_offsets.append(self.mdl_pos)
            self.mdl_pos += 4 * ctrl_data_count

    def peek_controllers(self, node, type_flags, out_keys, out_data):
        if node.parent:
            return

        data_count = 0

        out_keys.append(ControllerKey(CTRL_BASE_POSITION, 1, data_count, data_count + 1, 3))
        out_data.append(0.0)  # timekey
        for val in node.position:
            out_data.append(val)
        data_count += 4

        out_keys.append(ControllerKey(CTRL_BASE_ORIENTATION, 1, data_count, data_count + 1, 4))
        out_data.append(0.0)  # timekey
        for val in node.orientation:
            out_data.append(val)
        data_count += 5

        if type_flags & NODE_MESH:
            out_keys.append(ControllerKey(CTRL_MESH_ALPHA, 1, data_count, data_count + 1, 1))
            out_data.append(0.0)  # timekey
            out_data.append(node.alpha)
            data_count += 2

            out_keys.append(ControllerKey(CTRL_MESH_SELFILLUMCOLOR, 1, data_count, data_count + 1, 3))
            out_data.append(0.0)  # timekey
            for val in node.selfillumcolor:
                out_data.append(val)
            data_count += 4

    def save_file_header(self):
        self.mdl.put_uint32(0)  # pseudo signature
        self.mdl.put_uint32(self.mdl_size)
        self.mdl.put_uint32(self.mdx_size)

    def save_geometry_header(self):
        if self.tsl:
            fn_ptr1 = MODEL_FN_PTR_1_K2_PC
            fn_ptr2 = MODEL_FN_PTR_2_K2_PC
        else:
            fn_ptr1 = MODEL_FN_PTR_1_K1_PC
            fn_ptr2 = MODEL_FN_PTR_2_K1_PC
        model_name = self.model.name.ljust(32, '\0')
        off_root_node = self.node_offsets[0]
        total_num_nodes = len(self.nodes)
        ref_count = 0
        model_type = 2

        self.mdl.put_uint32(fn_ptr1)
        self.mdl.put_uint32(fn_ptr2)
        self.mdl.put_string(model_name)
        self.mdl.put_uint32(off_root_node)
        self.mdl.put_uint32(total_num_nodes)
        self.put_array_def(0, 0)  # runtime array
        self.put_array_def(0, 0)  # runtime array
        self.mdl.put_uint32(ref_count)
        self.mdl.put_uint8(model_type)
        for _ in range(3):
            self.mdl.put_uint8(0)  # padding

    def save_model_header(self):
        classification = next(iter(key for key, value in CLASS_BY_VALUE.items() if value == self.model.classification))
        subclassification = self.model.subclassification
        affected_by_fog = 0 if self.model.ignorefog else 1
        num_child_models = 0
        supermodel_ref = 0
        bounding_box = [-5.0, -5.0, -1.0, 5.0, 5.0, 10.0]
        radius = 7.0  # TODO
        scale = self.model.animscale
        supermodel_name = self.model.supermodel.ljust(32, '\0')
        off_head_root_node = self.node_offsets[0]
        mdx_size = self.mdx_size
        mdx_offset = 0

        self.mdl.put_uint8(classification)
        self.mdl.put_uint8(subclassification)
        self.mdl.put_uint8(0)  # unknown
        self.mdl.put_uint8(affected_by_fog)
        self.mdl.put_uint32(num_child_models)
        self.put_array_def(0, 0)  # animation array
        self.mdl.put_uint32(supermodel_ref)
        for val in bounding_box:
            self.mdl.put_float(val)
        self.mdl.put_float(radius)
        self.mdl.put_float(scale)
        self.mdl.put_string(supermodel_name)
        self.mdl.put_uint32(off_head_root_node)
        self.mdl.put_uint32(0)  # unknown
        self.mdl.put_uint32(mdx_size)
        self.mdl.put_uint32(mdx_offset)
        self.put_array_def(self.off_name_offsets, len(self.nodes))  # name offsets

    def save_names(self):
        for offset in self.name_offsets:
            self.mdl.put_uint32(offset)
        for node in self.nodes:
            self.mdl.put_c_string(node.name)

    def save_nodes(self):
        for node_idx, node in enumerate(self.nodes):
            type_flags = self.get_node_flags(node)
            supernode_number = node_idx
            name_index = node_idx
            off_root = 0
            parent_idx = self.parent_indices[node_idx]
            off_parent = self.node_offsets[parent_idx] if parent_idx is not None else 0
            position = node.position
            orientation = node.orientation
            child_indices = self.child_indices[node_idx]

            self.mdl.put_uint16(type_flags)
            self.mdl.put_uint16(supernode_number)
            self.mdl.put_uint16(name_index)
            self.mdl.put_uint16(0)  # padding
            self.mdl.put_uint32(off_root)
            self.mdl.put_uint32(off_parent)
            for val in position:
                self.mdl.put_float(val)
            for val in orientation:
                self.mdl.put_float(val)
            self.put_array_def(self.children_offsets[node_idx], len(child_indices))
            self.put_array_def(self.controller_offsets[node_idx], self.controller_counts[node_idx])
            self.put_array_def(self.controller_data_offsets[node_idx], self.controller_data_counts[node_idx])

            if type_flags & NODE_MESH:
                if self.tsl:
                    fn_ptr1 = MESH_FN_PTR_1_K2_PC
                    fn_ptr2 = MESH_FN_PTR_2_K2_PC
                else:
                    fn_ptr1 = MESH_FN_PTR_1_K1_PC
                    fn_ptr2 = MESH_FN_PTR_2_K1_PC
                bounding_box = [0.0] * 6
                radius = 0.0
                average = [0.0] * 3
                diffuse = node.diffuse
                ambient = node.ambient
                transparency_hint = node.transparencyhint
                bitmap = node.bitmap.ljust(32, '\0')
                bitmap2 = node.bitmap2.ljust(32, '\0')
                bitmap3 = "".ljust(12, '\0')
                bitmap4 = "".ljust(12, '\0')
                animate_uv = node.animateuv
                uv_dir_x = node.uvdirectionx
                uv_dir_y = node.uvdirectiony
                uv_jitter = node.uvjitter
                uv_jitter_speed = node.uvjitterspeed

                mdx_data_size = 4 * (3 + 3)
                mdx_data_bitmap = MDX_FLAG_VERTEX | MDX_FLAG_NORMAL
                off_mdx_verts = 0
                off_mdx_normals = 4 * 3
                off_mdx_colors = 0xffffffff
                off_mdx_uv1 = 0xffffffff
                off_mdx_uv2 = 0xffffffff
                off_mdx_uv3 = 0xffffffff
                off_mdx_uv4 = 0xffffffff
                off_mdx_tan_space1 = 0xffffffff
                off_mdx_tan_space2 = 0xffffffff
                off_mdx_tan_space3 = 0xffffffff
                off_mdx_tan_space4 = 0xffffffff
                if node.tverts:
                    mdx_data_bitmap |= MDX_FLAG_UV1
                    off_mdx_uv1 = mdx_data_size
                    mdx_data_size += 4 * 2
                if node.tverts1:
                    mdx_data_bitmap |= MDX_FLAG_UV2
                    off_mdx_uv2 = mdx_data_size
                    mdx_data_size += 4 * 2

                num_verts = len(node.verts)
                num_textures = 0
                has_lightmap = node.lightmapped
                rotate_texture = node.rotatetexture
                background_geometry = node.background_geometry
                shadow = node.shadow
                beaming = node.beaming
                render = node.render
                dirt_enabled = node.dirt_enabled
                dirt_texture = node.dirt_texture
                dirt_coord_space = node.dirt_worldspace
                hide_in_holograms = node.hologram_donotdraw
                total_area = 0.0
                mdx_offset = self.mdx_offsets[node_idx]
                off_vert_array = self.verts_offsets[node_idx]

                self.mdl.put_uint32(fn_ptr1)
                self.mdl.put_uint32(fn_ptr2)
                self.put_array_def(self.faces_offsets[node_idx], len(node.facelist.faces))  # faces
                for val in bounding_box:
                    self.mdl.put_float(val)
                self.mdl.put_float(radius)
                for val in average:
                    self.mdl.put_float(val)
                for val in diffuse:
                    self.mdl.put_float(val)
                for val in ambient:
                    self.mdl.put_float(val)
                self.mdl.put_uint32(transparency_hint)
                self.mdl.put_string(bitmap)
                self.mdl.put_string(bitmap2)
                self.mdl.put_string(bitmap3)
                self.mdl.put_string(bitmap4)
                self.put_array_def(self.index_count_offsets[node_idx], 1)  # indices count
                self.put_array_def(self.index_offset_offsets[node_idx], 1)  # indices offset
                self.put_array_def(self.inv_count_offsets[node_idx], 1)  # inv counter
                self.mdl.put_uint32(0xffffffff)  # unknown
                self.mdl.put_uint32(0xffffffff)  # unknown
                self.mdl.put_uint32(0)  # unknown
                self.mdl.put_uint8(3)  # saber unknown
                for _ in range(7):
                    self.mdl.put_uint8(0)  # saber unknown
                self.mdl.put_uint32(animate_uv)
                self.mdl.put_float(uv_dir_x)
                self.mdl.put_float(uv_dir_y)
                self.mdl.put_float(uv_jitter)
                self.mdl.put_float(uv_jitter_speed)
                self.mdl.put_uint32(mdx_data_size)
                self.mdl.put_uint32(mdx_data_bitmap)
                self.mdl.put_uint32(off_mdx_verts)
                self.mdl.put_uint32(off_mdx_normals)
                self.mdl.put_uint32(off_mdx_colors)
                self.mdl.put_uint32(off_mdx_uv1)
                self.mdl.put_uint32(off_mdx_uv2)
                self.mdl.put_uint32(off_mdx_uv3)
                self.mdl.put_uint32(off_mdx_uv4)
                self.mdl.put_uint32(off_mdx_tan_space1)
                self.mdl.put_uint32(off_mdx_tan_space2)
                self.mdl.put_uint32(off_mdx_tan_space3)
                self.mdl.put_uint32(off_mdx_tan_space4)
                self.mdl.put_uint16(num_verts)
                self.mdl.put_uint16(num_textures)
                self.mdl.put_uint8(has_lightmap)
                self.mdl.put_uint8(rotate_texture)
                self.mdl.put_uint8(background_geometry)
                self.mdl.put_uint8(shadow)
                self.mdl.put_uint8(beaming)
                self.mdl.put_uint8(render)

                if self.tsl:
                    self.mdl.put_uint8(dirt_enabled)
                    self.mdl.put_uint8(0)  # padding
                    self.mdl.put_uint16(dirt_texture)
                    self.mdl.put_uint16(dirt_coord_space)
                    self.mdl.put_uint8(hide_in_holograms)
                    self.mdl.put_uint8(0)  # padding

                self.mdl.put_uint16(0)  # padding
                self.mdl.put_float(total_area)
                self.mdl.put_uint32(0)  # padding
                self.mdl.put_uint32(mdx_offset)
                self.mdl.put_uint32(off_vert_array)

                for i in range(len(node.facelist.faces)):
                    normal = node.facelist.normals[i]
                    plane_distance = 0.0
                    material_id = node.facelist.matId[i]
                    adjacent_faces = [0xffff] * 3
                    vert_indices = node.facelist.faces[i]

                    for val in normal:
                        self.mdl.put_float(val)
                    self.mdl.put_float(plane_distance)
                    self.mdl.put_uint32(material_id)
                    for val in adjacent_faces:
                        self.mdl.put_uint16(val)
                    for val in vert_indices:
                        self.mdl.put_uint16(val)

                self.mdl.put_uint32(self.indices_offsets[node_idx])

                for vert_idx, vert in enumerate(node.verts):
                    for val in vert:
                        self.mdl.put_float(val)
                        self.mdx.put_float(val)
                    for val in node.normals[vert_idx]:
                        self.mdx.put_float(val)
                    if node.tverts:
                        for val in node.tverts[vert_idx]:
                            self.mdx.put_float(val)
                    if node.tverts1:
                        for val in node.tverts1[vert_idx]:
                            self.mdx.put_float(val)

                # Extra MDX data
                for _ in range(6):
                    self.mdx.put_float(0.0)
                if node.tverts:
                    for _ in range(2):
                        self.mdx.put_float(0.0)
                if node.tverts1:
                    for _ in range(2):
                        self.mdx.put_float(0.0)

                self.mdl.put_uint32(3 * len(node.facelist.faces))  # index count
                self.mdl.put_uint32(98)  # inverted count

                for face in node.facelist.faces:
                    for val in face:
                        self.mdl.put_uint16(val)

            # TODO: support all node types

            for child_idx in child_indices:
                self.mdl.put_uint32(self.node_offsets[child_idx])

            for key in self.controller_keys[node_idx]:
                unk1 = 0xffff

                self.mdl.put_uint32(key.ctrl_type)
                self.mdl.put_uint16(unk1)
                self.mdl.put_uint16(key.num_rows)
                self.mdl.put_uint16(key.timekeys_start)
                self.mdl.put_uint16(key.values_start)
                self.mdl.put_uint8(key.num_columns)

                for _ in range(3):
                    self.mdl.put_uint8(0)  # padding

            for val in self.controller_data[node_idx]:
                self.mdl.put_float(val)

    def put_array_def(self, offset, count):
        self.mdl.put_uint32(offset)
        self.mdl.put_uint32(count)
        self.mdl.put_uint32(count)

    def get_node_flags(self, node):
        switch = {
            Nodetype.DUMMY: NODE_BASE,
            Nodetype.REFERENCE: NODE_BASE,  # NODE_REFERENCE
            Nodetype.TRIMESH: NODE_BASE | NODE_MESH,
            Nodetype.DANGLYMESH: NODE_BASE | NODE_MESH,  # NODE_DANGLY
            Nodetype.SKIN: NODE_BASE | NODE_MESH,  # NODE_SKIN
            Nodetype.EMITTER: NODE_BASE,  # NODE_EMITTER
            Nodetype.LIGHT: NODE_BASE,  # NODE_LIGHT
            Nodetype.AABB: NODE_BASE | NODE_MESH,  # NODE_AABB
            Nodetype.LIGHTSABER: NODE_BASE | NODE_MESH  # NODE_SABER
        }
        return switch[node.nodetype]
