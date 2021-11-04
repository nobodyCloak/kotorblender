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

import bmesh
import bpy

from bpy_extras.io_utils import unpack_list
from mathutils import Vector

from ... import defines, glob, utils

from .. import material

from .geometry import GeometryNode

UV_MAP_DIFFUSE = "UVMap"
UV_MAP_LIGHTMAP = "UVMap_lm"


class FaceList:
    def __init__(self):
        self.faces = []  # int 3-tuple, vertex indices
        self.uvIdx = []  # int 3-tuple, texture/uv vertex indices
        self.matId = []  # int, material index
        self.normals = []  # float 3-tuple, normal


class TrimeshNode(GeometryNode):

    def __init__(self, name="UNNAMED"):
        GeometryNode.__init__(self, name)
        self.nodetype = "trimesh"

        self.meshtype = defines.Meshtype.TRIMESH
        self.center = (0.0, 0.0, 0.0)  # Unused ?
        self.lightmapped = 0
        self.render = 1
        self.shadow = 1
        self.beaming = 0
        self.inheritcolor = 0  # Unused ?
        self.background_geometry = 0
        self.dirt_enabled = 0
        self.dirt_texture = 1
        self.dirt_worldspace = 1
        self.hologram_donotdraw = 0
        self.animateuv = 0
        self.uvdirectionx = 1.0
        self.uvdirectiony = 1.0
        self.uvjitter = 0.0
        self.uvjitterspeed = 0.0
        self.alpha = 1.0
        self.transparencyhint = 0
        self.selfillumcolor = (0.0, 0.0, 0.0)
        self.ambient = (0.0, 0.0, 0.0)
        self.diffuse = (0.0, 0.0, 0.0)
        self.bitmap = defines.NULL
        self.bitmap2 = defines.NULL
        self.tangentspace = 0
        self.rotatetexture = 0
        self.verts = []
        self.normals = []
        self.tangents = []
        self.bitangents = []
        self.tangentspacenormals = []
        self.facelist = FaceList()
        self.tverts = []  # list of texture vertices
        self.tverts1 = []  # list of texture vertices

    def add_to_collection(self, collection):
        mesh = self.create_mesh(self.name)
        obj = bpy.data.objects.new(self.name, mesh)
        self.set_object_data(obj)

        if glob.import_materials and self.roottype == "mdl":
            material.rebuild_material(obj)

        collection.objects.link(obj)
        return obj

    def create_mesh(self, name):
        # Create the mesh itself
        mesh = bpy.data.meshes.new(name)
        mesh.vertices.add(len(self.verts))
        mesh.vertices.foreach_set("co", unpack_list(self.verts))
        num_faces = len(self.facelist.faces)
        mesh.loops.add(3 * num_faces)
        mesh.loops.foreach_set("vertex_index", unpack_list(self.facelist.faces))
        mesh.polygons.add(num_faces)
        mesh.polygons.foreach_set("loop_start", range(0, 3 * num_faces, 3))
        mesh.polygons.foreach_set("loop_total", (3,) * num_faces)

        # Special handling for mesh in walkmesh files
        if self.roottype in ["pwk", "dwk", "wok"]:
            # Create walkmesh materials
            for wok_mat in defines.WOK_MATERIALS:
                mat_name = wok_mat[0]
                # Walkmesh materials will be shared across multiple walkmesh
                # objects
                if mat_name in bpy.data.materials:
                    material = bpy.data.materials[mat_name]
                else:
                    material = bpy.data.materials.new(mat_name)
                    material.diffuse_color = [*wok_mat[1], 1.0]
                    material.specular_color = (0.0, 0.0, 0.0)
                    material.specular_intensity = wok_mat[2]
                mesh.materials.append(material)

            # Apply the walkmesh materials to each face
            for idx, polygon in enumerate(mesh.polygons):
                polygon.material_index = self.facelist.matId[idx]

        # Create UV map
        if len(self.tverts) > 0:
            uv = unpack_list([self.tverts[i] for indices in self.facelist.uvIdx for i in indices])
            uv_layer = mesh.uv_layers.new(name=UV_MAP_DIFFUSE, do_init=False)
            uv_layer.data.foreach_set("uv", uv)

        # Create lightmap UV map
        if len(self.tverts1) > 0:
            uv = unpack_list([self.tverts1[i] for indices in self.facelist.uvIdx for i in indices])
            uv_layer = mesh.uv_layers.new(name=UV_MAP_LIGHTMAP, do_init=False)
            uv_layer.data.foreach_set("uv", uv)

        mesh.update()
        return mesh

    def set_object_data(self, obj):
        GeometryNode.set_object_data(self, obj)

        obj.kb.meshtype = self.meshtype
        obj.kb.bitmap = self.bitmap if not utils.is_null(self.bitmap) else ""
        obj.kb.bitmap2 = self.bitmap2 if not utils.is_null(self.bitmap2) else ""
        obj.kb.alpha = self.alpha
        obj.kb.lightmapped = (self.lightmapped == 1)
        obj.kb.render = (self.render == 1)
        obj.kb.shadow = (self.shadow == 1)
        obj.kb.beaming = (self.beaming == 1)
        obj.kb.tangentspace = (self.tangentspace == 1)
        obj.kb.inheritcolor = (self.inheritcolor == 1)
        obj.kb.rotatetexture = (self.rotatetexture == 1)
        obj.kb.background_geometry = (self.background_geometry == 1)
        obj.kb.dirt_enabled = (self.dirt_enabled == 1)
        obj.kb.dirt_texture = self.dirt_texture
        obj.kb.dirt_worldspace = self.dirt_worldspace
        obj.kb.hologram_donotdraw = (self.hologram_donotdraw == 1)
        obj.kb.animateuv = (self.animateuv == 1)
        obj.kb.uvdirectionx = self.uvdirectionx
        obj.kb.uvdirectiony = self.uvdirectiony
        obj.kb.uvjitter = self.uvjitter
        obj.kb.uvjitterspeed = self.uvjitterspeed
        obj.kb.transparencyhint = self.transparencyhint
        obj.kb.selfillumcolor = self.selfillumcolor
        obj.kb.diffuse = self.diffuse
        obj.kb.ambient = self.ambient

    def load_object_data(self, obj):
        GeometryNode.load_object_data(self, obj)

        self.meshtype = obj.kb.meshtype
        self.bitmap = obj.kb.bitmap if obj.kb.bitmap else defines.NULL
        self.bitmap2 = obj.kb.bitmap2 if obj.kb.bitmap2 else ""
        self.alpha = obj.kb.alpha
        self.lightmapped = 1 if obj.kb.lightmapped else 0
        self.render = 1 if obj.kb.render else 0
        self.shadow = 1 if obj.kb.shadow else 0
        self.beaming = 1 if obj.kb.beaming else 0
        self.tangentspace = 1 if obj.kb.tangentspace else 0
        self.inheritcolor = 1 if obj.kb.inheritcolor else 0
        self.rotatetexture = 1 if obj.kb.rotatetexture else 0
        self.background_geometry = 1 if obj.kb.background_geometry else 0
        self.dirt_enabled = 1 if obj.kb.dirt_enabled else 0
        self.dirt_texture = obj.kb.dirt_texture
        self.dirt_worldspace = obj.kb.dirt_worldspace
        self.hologram_donotdraw = 1 if obj.kb.hologram_donotdraw else 0
        self.animateuv = 1 if obj.kb.animateuv else 0
        self.uvdirectionx = obj.kb.uvdirectionx
        self.uvdirectiony = obj.kb.uvdirectiony
        self.uvjitter = obj.kb.uvjitter
        self.uvjitterspeed = obj.kb.uvjitterspeed
        self.transparencyhint = obj.kb.transparencyhint
        self.selfillumcolor = obj.kb.selfillumcolor
        self.diffuse = obj.kb.diffuse
        self.ambient = obj.kb.ambient

        mesh = obj.data

        # Triangulation
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()

        for vert in mesh.vertices:
            self.verts.append(vert.co[:3])
            self.normals.append(vert.normal[:3])

        self.tverts = self.get_tverts_from_uv_layer(mesh, UV_MAP_DIFFUSE)
        self.tverts1 = self.get_tverts_from_uv_layer(mesh, UV_MAP_LIGHTMAP)

        if self.tangentspace and self.tverts:
            mesh.calc_tangents(uvmap=UV_MAP_DIFFUSE)
            num_verts = len(mesh.vertices)
            self.tangents = [Vector() for _ in range(num_verts)]
            self.bitangents = [Vector() for _ in range(num_verts)]
            self.tangentspacenormals = [Vector() for _ in range(num_verts)]

        for polygon in mesh.polygons:
            self.facelist.faces.append(polygon.vertices[:3])
            self.facelist.uvIdx.append(polygon.vertices[:3])
            self.facelist.matId.append(polygon.material_index)
            self.facelist.normals.append(polygon.normal)

            if self.tangentspace and self.tverts:
                for loop in [mesh.loops[i] for i in polygon.loop_indices]:
                    vert_idx = loop.vertex_index
                    self.tangents[vert_idx] += loop.tangent
                    self.bitangents[vert_idx] += loop.bitangent
                    self.tangentspacenormals[vert_idx] += loop.normal

        if self.tangentspace and self.tverts:
            for vert_idx in range(num_verts):
                self.tangents[vert_idx].normalize()
                self.bitangents[vert_idx].normalize()
                self.tangentspacenormals[vert_idx].normalize()

    def get_tverts_from_uv_layer(self, mesh, layer_name):
        if not layer_name in mesh.uv_layers:
            return []
        layer_data = mesh.uv_layers[layer_name].data
        tverts = dict()
        for polygon_idx, polygon in enumerate(mesh.polygons):
            for i in range(3):
                tverts[polygon.vertices[i]] = layer_data[3 * polygon_idx + i].uv[:2]
        return [v for _, v in sorted(tverts.items())]
