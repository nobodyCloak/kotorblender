﻿# ##### BEGIN GPL LICENSE BLOCK #####
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

from .defines import *


def is_mdl_root(obj):
    return is_dummy_type(obj, DummyType.MDLROOT)


def is_pwk_root(obj):
    return is_dummy_type(obj, DummyType.PWKROOT)


def is_dwk_root(obj):
    return is_dummy_type(obj, DummyType.DWKROOT)


def is_path_point(obj):
    return is_dummy_type(obj, DummyType.PATHPOINT)


def is_skin_mesh(obj):
    return is_mesh_type(obj, MeshType.SKIN)


def is_dummy_type(obj, dummytype):
    return obj and obj.type == 'EMPTY' and obj.kb.dummytype == dummytype


def is_mesh_type(obj, meshtype):
    return obj and obj.type == 'MESH' and obj.kb.meshtype == meshtype


def is_exported_to_mdl(obj):
    if not obj:
        return False
    if obj.type in ['MESH', 'LIGHT']:
        return True
    return obj.type == 'EMPTY' and obj.kb.dummytype in [DummyType.NONE, DummyType.MDLROOT, DummyType.REFERENCE]


def get_object_root(obj):
    if is_mdl_root(obj):
        return obj
    if not obj.parent:
        return None
    return get_object_root(obj.parent)


def find_object(obj, test=lambda _: True):
    if test(obj):
        return obj
    for child in obj.children:
        match = find_object(child, test)
        if match:
            return match
    return None


def find_objects(obj, test=lambda _: True):
    nodes = []
    if test(obj):
        nodes.append(obj)
    for child in obj.children:
        nodes.extend(find_objects(child, test))
    return nodes


def is_null(s):
    return not s or s.lower() == NULL.lower()


def is_not_null(s):
    return not is_null(s)


def is_close(a, b, rel_tol, abs_tol=0.0):
    return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


def is_close_2(a, b, rel_tol):
    return is_close(a[0], b[0], rel_tol) and is_close(a[1], b[1], rel_tol)


def is_close_3(a, b, rel_tol):
    return (is_close(a[0], b[0], rel_tol) and
            is_close(a[1], b[1], rel_tol) and
            is_close(a[2], b[2], rel_tol))


def color_to_hex(color):
    return "{}{}{}".format(
        int_to_hex(float_to_byte(color[0])),
        int_to_hex(float_to_byte(color[1])),
        int_to_hex(float_to_byte(color[2])))


def float_to_byte(val):
    return int(val * 255)


def int_to_hex(val):
    return "{:02X}".format(val)
