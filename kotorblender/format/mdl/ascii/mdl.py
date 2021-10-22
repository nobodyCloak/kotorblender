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

import collections
import os
import re
from datetime import datetime

import bpy

from ....exception.malformedmdl import MalformedMdl

from .... import armature, defines, glob, utils

from . import (
    anim as mdlanim,
    node as mdlnode
    )


class Mdl():
    def __init__(self):
        self.nodeDict      = collections.OrderedDict()
        self.animDict      = dict() # No need to retain order

        self.name           = "UNNAMED"
        self.supermodel     = defines.null
        self.animscale      = 1.0
        self.classification = defines.Classification.UNKNOWN
        self.unknownC1      = 0
        self.ignorefog      = False
        self.compress_quats = False
        self.headlink       = False
        self.lytposition    = None

        self.animations = []

        self.mdlnodes = []

    def load_ascii_node(self, asciiBlock):
        if asciiBlock is None:
            raise MalformedMdl("Empty Node")

        nodeType = ""
        try:
            nodeType = asciiBlock[0][1].lower()
        except (IndexError, AttributeError):
            raise MalformedMdl("Invalid node type")

        switch = {
            defines.Nodetype.DUMMY:      mdlnode.Dummy,
            defines.Nodetype.PATCH:      mdlnode.Patch,
            defines.Nodetype.REFERENCE:  mdlnode.Reference,
            defines.Nodetype.TRIMESH:    mdlnode.Trimesh,
            defines.Nodetype.DANGLYMESH: mdlnode.Danglymesh,
            defines.Nodetype.LIGHTSABER: mdlnode.Lightsaber,
            defines.Nodetype.SKIN:       mdlnode.Skinmesh,
            defines.Nodetype.EMITTER:    mdlnode.Emitter,
            defines.Nodetype.LIGHT:      mdlnode.Light,
            defines.Nodetype.AABB:       mdlnode.Aabb
        }
        try:
            node = switch[nodeType]()
        except KeyError:
            raise MalformedMdl("Invalid node type")

        # tell the node if it is part of a walkmesh (mdl is default)
        if isinstance(self, Xwk):
            node.roottype = self.walkmeshType

        # tell the node what model it is part of
        node.rootname = self.name

        node.load_ascii(asciiBlock)
        self.add_node(node)

    def add_node(self, newNode):
        # Blender requires unique object names. Names in mdls are only
        # unique for a parent, i.e. another object with the same name but
        # with a different parent may exist.
        # We'd need to save all names starting from root to resolve
        # this, but that's too much effort.
        # ParentName + Name should be enough.
        if newNode:
            key = newNode.parentName + newNode.name
            if key in self.nodeDict:
                print("KotorBlender: WARNING - node name conflict " + key + ".")
            else:
                self.nodeDict[key] = newNode
                self.mdlnodes.append(newNode)

    def add_animation(self, anim):
        if anim:
            if anim.name in self.animDict:
                print("KotorBlender: WARNING - animation name conflict.")
            else:
                self.animDict[anim.name] = anim

    def import_to_collection(self, collection, wkm, position = (0.0, 0.0, 0.0)):
        mdl_root = None
        objIdx = 0
        if (glob.importGeometry) and self.nodeDict:
            it = iter(self.nodeDict.items())

            # The first node should be the rootdummy.
            # If the first node has a parent or isn't a dummy we don't
            # even try to import the mdl
            (_, node) = next(it)
            if (type(node) == mdlnode.Dummy) and \
               (utils.is_null(node.parentName)):
                obj                    = node.add_to_collection(collection)
                obj.location           = position
                obj.kb.dummytype      = defines.Dummytype.MDLROOT
                obj.kb.supermodel     = self.supermodel
                obj.kb.classification = self.classification
                obj.kb.unknownC1      = self.unknownC1
                obj.kb.ignorefog      = (self.ignorefog >= 1)
                obj.kb.compress_quats = (self.compress_quats >= 1)
                obj.kb.headlink       = (self.headlink >= 1)
                obj.kb.animscale      = self.animscale
                mdl_root = obj

                obj.kb.imporder = objIdx
                objIdx += 1
            else:
                raise MalformedMdl("First node has to be a dummy without a parent.")

            for (_, node) in it:
                obj = node.add_to_collection(collection)
                obj.kb.imporder = objIdx
                objIdx += 1

                # If LYT position is specified, set it for the AABB node
                if self.lytposition and node.nodetype == "aabb":
                    node.lytposition = self.lytposition
                    obj.kb.lytposition = self.lytposition

                if (utils.is_null(node.parentName)):
                    # Node without parent and not the mdl root.
                    raise MalformedMdl(node.name + " has no parent.")
                else:
                    # Check if such an object exists
                    if obj.parent is not None:
                        print("WARNING: Node already parented: {}".format(obj.name))
                        pass
                    elif mdl_root and node.parentName in bpy.data.objects and \
                         utils.ancestor_node(
                             bpy.data.objects[node.parentName],
                             utils.is_root_dummy
                         ).name == mdl_root.name:
                        # parent named node exists and is in our model
                        obj.parent = bpy.data.objects[node.parentName]
                        if node.parentName != self.name:
                            # child of non-root, preserve orientation
                            obj.matrix_parent_inverse = obj.parent.matrix_world.inverted()
                    else:
                        # parent node was not found in our model,
                        # this should mean that a node of the same name already
                        # existed in the scene,
                        # perform search for parent node in our model,
                        # taking into account blender .001 suffix naming scheme,
                        # note: only searching 001-030
                        found = False
                        for altname in [node.parentName + ".{:03d}".format(i) for i in range(1,30)]:
                            if altname in bpy.data.objects and \
                               utils.ancestor_node(
                                   bpy.data.objects[altname],
                                   utils.is_root_dummy
                               ).name == mdl_root.name:
                                # parent node in our model exists with suffix
                                obj.parent = bpy.data.objects[altname]
                                obj.matrix_parent_inverse = obj.parent.matrix_world.inverted()
                                found = True
                                break
                        # Node with invalid parent.
                        if not found:
                            raise MalformedMdl(node.name + " has no parent " + node.parentName)

        # Import the walkmesh, it will use any placeholder dummies just imported,
        # and the walkmesh nodes will be copied during animation import
        if (glob.importWalkmesh) and not wkm is None and wkm.walkmeshType != "wok":
            wkm.import_to_collection(collection)

        # Attempt to import animations
        # Search for the MDL root if not already present
        if not mdl_root:
            for obj in collection.objects:
                if utils.is_root_dummy(obj, defines.Dummytype.MDLROOT):
                    mdl_root = obj
                    break
            # Still none ? Don't try to import anims then
            if not mdl_root:
                return

        armature_object = None
        if glob.createArmature:
            armature_object = armature.recreate_armature(mdl_root)
        else:
            # When armature creation is disabled, see if the MDL root already has an armature and use that
            skinmeshes = utils.search_node_all(mdl_root, lambda o: o.kb.meshtype == defines.Meshtype.SKIN)
            for skinmesh in skinmeshes:
                for modifier in skinmesh.modifiers:
                    if modifier.type == 'ARMATURE':
                        armature_object = modifier.object
                        break
                if armature_object:
                    break

        self._create_animations(mdl_root, armature_object)

    def _create_animations(self, mdl_root, armature_object):
        # Load the 'default' animation first, so it is at the front
        anims = [a for a in self.animations if a.name == "default"]
        for a in anims:
            a.add_to_objects(mdl_root)
        # Load the rest of the anims
        anims = [a for a in self.animations if a.name != "default"]
        for a in anims:
            a.add_to_objects(mdl_root)
        if armature_object:
            armature.create_armature_animations(mdl_root, armature_object)

    def load_ascii(self, ascii_block):
        geom_start = ascii_block.find("node ")
        anim_start = ascii_block.find("newanim ")
        geom_end   = ascii_block.find("endmodelgeom ")

        if (anim_start > 0) and (geom_start > anim_start):
            raise MalformedMdl("Animations before geometry")
        if (geom_start < 0):
            raise MalformedMdl("Unable to find geometry")

        self.read_ascii_header(ascii_block[:geom_start-1])
        # Import Geometry
        self.read_ascii_geom(ascii_block[geom_start:geom_end],
                            self.mdlnodes)
        # Import Animations
        if glob.importAnim and (anim_start > 0):
            self.read_ascii_anims(ascii_block[anim_start:])

    def read_ascii_anims(self, ascii_block):
        """Load all animations from an ascii mdl block."""
        delim = "newanim "
        animList = [delim + b for b in ascii_block.split(delim) if b]
        self.animations = list(map(
            lambda txt: mdlanim.Animation(ascii_data=txt),
            animList
        ))
        for anim in self.animations:
            self.add_animation(anim)

    def read_ascii_geom(self, ascii_block, nodelist):
        """Load all geometry nodes from an ascii mdl block."""
        delim = "node "
        ascii_nodes = [delim + b for b in ascii_block.split(delim) if b]
        for _, ascii_node in enumerate(ascii_nodes):
            ascii_lines = [l.strip().split() for l in ascii_node.splitlines()]
            node = None
            try:  # Read node type
                ascii_lines[0][1].lower()
            except (IndexError, AttributeError):
                raise MalformedMdl("Unable to read node type")
            try:  # Read node name
                ascii_lines[0][2].lower()
            except (IndexError, AttributeError):
                raise MalformedMdl("Unable to read node name")
            self.load_ascii_node(ascii_lines)
            nodelist.append(node)

    def read_ascii_header(self, ascii_block):
        ascii_lines = [l.strip().split() for l in ascii_block.splitlines()]
        for line in ascii_lines:
            try:
                label = line[0].lower()
            except (IndexError, AttributeError):
                continue  # Probably empty line, skip it
            if label == "newmodel":
                try:
                    self.name = line[1]
                except (ValueError, IndexError):
                    print("KotorBlender: WARNING - unable to read model name.")
            elif label == "setsupermodel":
                try:  # should be ['setsupermodel', modelname, supermodelname]
                    self.supermodel = line[2]
                except (ValueError, IndexError):
                    print("KotorBlender: WARNING - unable to read supermodel. \
                           Using default value " + self.supermodel)
            elif label == "classification":
                try:
                    self.classification = line[1].title()
                except (ValueError, IndexError):
                    print("KotorBlender: WARNING - unable to read \
                           classification. \
                           Using Default value " + self.classification)
                if self.classification not in defines.Classification.ALL:
                    print("KotorBlender: WARNING - invalid classification '{}'".format(self.classification))
                    self.classification = defines.Classification.UNKNOWN
            elif label == "classification_unk1":
                try:
                    self.unknownC1 = int(line[1])
                except IndexError:
                    print("KotorBlender: WARNING - unable to read classification unknown. Default value " + self.unknownC1)
            elif label == "ignorefog":
                try:
                    self.ignorefog = int(line[1])
                except IndexError:
                    print("KotorBlender: WARNING - unable to read ignorefog. Default value " + self.ignorefog)
            elif label == "compress_quaternions":
                try:
                    self.compress_quats = int(line[1])
                except IndexError:
                    print("KotorBlender: WARNING - unable to read compress_quaternions. Default value " + self.compress_quats)
            elif label == "headlink":
                try:
                    self.headlink = int(line[1])
                except IndexError:
                    print("KotorBlender: WARNING - unable to read headlink. Default value " + self.headlink)
            elif label == "setanimationscale":
                try:
                    self.animscale = float(line[1])
                except (ValueError, IndexError):
                    print("KotorBlender: WARNING - unable to read \
                           animationscale. \
                           Using default value " + self.animscale)
            elif label == "layoutposition":
                self.lytposition = [float(x) for x in line[1:]]

    def geometry_to_ascii(self, bObject, asciiLines, simple = False, nameDict = None):
        nodeType = utils.get_node_type(bObject)
        switch = {"dummy":      mdlnode.Dummy,
                  "patch":      mdlnode.Patch,
                  "reference":  mdlnode.Reference,
                  "trimesh":    mdlnode.Trimesh,
                  "danglymesh": mdlnode.Danglymesh,
                  "skin":       mdlnode.Skinmesh,
                  "emitter":    mdlnode.Emitter,
                  "light":      mdlnode.Light,
                  "aabb":       mdlnode.Aabb}
        try:
            node = switch[nodeType]()
        except KeyError:
            raise MalformedMdl("Invalid node type")

        node.to_ascii(bObject, asciiLines, self.classification, simple, nameDict=nameDict)

        childList = []
        for child in bObject.children:
            childList.append((child.kb.imporder, child))
        childList.sort(key=lambda tup: tup[0])

        for (_, child) in childList:
            self.geometry_to_ascii(child, asciiLines, simple, nameDict=nameDict)

    def generate_ascii_animations(self, ascii_lines, rootDummy, options={}):
        if rootDummy.kb.animList:
            for anim in rootDummy.kb.animList:
                print("export animation " + anim.name)
                mdlanim.Animation.generate_ascii(rootDummy, anim,
                                                 ascii_lines, options)

    def generate_ascii(self, asciiLines, rootDummy, exports = {"ANIMATION", "WALKMESH"}):
        self.name           = rootDummy.name
        self.classification = rootDummy.kb.classification
        self.supermodel     = rootDummy.kb.supermodel
        self.unknownC1      = rootDummy.kb.unknownC1
        self.ignorefog      = rootDummy.kb.ignorefog
        self.compress_quats = rootDummy.kb.compress_quats
        self.headlink       = rootDummy.kb.headlink
        self.animscale      = rootDummy.kb.animscale

        # feature: export of models loaded in scene multiple times
        # construct a name map that points any NAME.00n names to their base name,
        # needed for model and node names as well as parent node references
        object_name_map = {}
        all_nodes = utils.search_node_all(rootDummy, bool)
        for node in all_nodes:
            match = re.match(r'^(.+)\.\d\d\d$', node.name)
            if match:
                remap_name = True
                # if a node matching base name but without .00n suffix exists
                # in this model, do not remap name
                for test_node in all_nodes:
                    if test_node.name.lower() == match.group(1).lower():
                        remap_name = False
                        break
                # if the node base name has already been remapped, don't repeat
                if match.group(1) in object_name_map.values():
                    remap_name = False
                # add the name mapping
                if remap_name:
                    object_name_map[node.name] = match.group(1)
        # change the model name if root node is in object name map
        if self.name in object_name_map:
            self.name = object_name_map[self.name]
        # set object_name_map to none if feature is unused
        if not len(object_name_map.keys()):
            object_name_map = None

        # Header
        currentTime   = datetime.now()
        blendFileName = os.path.basename(bpy.data.filepath)
        if not blendFileName:
            blendFileName = "unknown"
        asciiLines.append("# Exported from blender at " + currentTime.strftime("%A, %Y-%m-%d"))
        asciiLines.append("filedependancy " + blendFileName)
        asciiLines.append("newmodel " + self.name)
        asciiLines.append("setsupermodel " + self.name + " " + self.supermodel)
        asciiLines.append("classification " + self.classification)
        asciiLines.append("classification_unk1 " + str(self.unknownC1))
        asciiLines.append("ignorefog " + str(int(self.ignorefog)))
        if self.compress_quats:
            # quaternion compression does not work with the rotations we export,
            # for unknown reasons...
            # therefore, just export it as disabled for now...
            asciiLines.append("compress_quaternions 0")
            # they actually work with mdlops now, not mdledit yet...
        if self.headlink:
            asciiLines.append("headlink " + str(int(self.headlink)))
        asciiLines.append("setanimationscale " + str(round(self.animscale, 7)))
        # Geometry
        asciiLines.append("beginmodelgeom " + self.name)
        aabb = utils.search_node(rootDummy, lambda x: x.kb.meshtype == defines.Meshtype.AABB)
        if aabb is not None and aabb.kb.lytposition != (0.0, 0.0, 0.0):
            lytposition = (aabb.kb.lytposition[0],
                           aabb.kb.lytposition[1],
                           aabb.kb.lytposition[2])
            if rootDummy.location.to_tuple() != (0.0, 0.0, 0.0):
                lytposition = (rootDummy.location[0],
                               rootDummy.location[1],
                               rootDummy.location[2])
            asciiLines.append("  layoutposition {: .7g} {: .7g} {: .7g}".format(*lytposition))
        self.geometry_to_ascii(rootDummy, asciiLines, False, nameDict=object_name_map)
        asciiLines.append("endmodelgeom " + self.name)
        # Animations
        if "ANIMATION" in exports:
            asciiLines.append("")
            asciiLines.append("# ANIM ASCII")
            self.generate_ascii_animations(asciiLines, rootDummy)
        # The End
        asciiLines.append("donemodel " + self.name)
        asciiLines.append("")


class Xwk(Mdl):
    def __init__(self, wkmType = "pwk"):
        Mdl.__init__(self)

        self.walkmeshType   = wkmType

    def load_ascii_animation(self, asciiBlock):
        pass # No animations in walkmeshes

    def load_ascii(self, asciiLines):
        # Parse the walkmesh
        blockStart = -1
        for idx, line in enumerate(asciiLines):
            try:
                label = line[0]
            except IndexError:
                # Probably empty line or whatever, just skip it
                continue
            if (label == "node"):
                blockStart = idx
            elif (label == "endnode"):
                if (blockStart >= 0):
                    self.load_ascii_node(asciiLines[blockStart:idx+1])
                    blockStart = -1
                else:
                    # "endnode" before "node"
                    raise MalformedMdl("Unexpected 'endnode' at line " + str(idx))

    def generate_ascii(self, asciiLines, rootDummy, exports = {"ANIMATION", "WALKMESH"}):
        self.name = rootDummy.name

        # Header
        currentTime = datetime.now()
        asciiLines.append("# Exported from blender at " + currentTime.strftime("%A, %Y-%m-%d"))
        # Geometry
        for child in rootDummy.children:
            self.geometry_to_ascii(child, asciiLines, True)

    def import_to_collection(self, collection):
        if self.nodeDict:
            # Walkmeshes have no rootdummys. We need to create one ourselves
            # Unless the rootdummy is in the model already, because that happens

            # Also, kotormax puts the rootdummy into the PWK and probably DWK,
            # making this not work.
            # Even worse, it parents the use dummies to the mesh,
            # making this doubly not work.

            # Our format expectations are more like what mdlops exports,
            # which is in line with the format used in NWN.

            # Look for the node parents for the list of parents. They should
            # all have the same name
            nameList = []
            for (_, node) in self.nodeDict.items():
                if node.parentName not in nameList:
                    nameList.append(node.parentName)
            self.name = nameList[0]

            if self.name in collection.objects and bpy.data.objects[self.name].kb.dummytype != defines.Dummytype.MDLROOT:
                node = bpy.data.objects[self.name].kb
                if self.walkmeshType == "dwk":
                    node.dummytype = defines.Dummytype.DWKROOT
                else:
                    node.dummytype = defines.Dummytype.PWKROOT
                rootdummy = bpy.data.objects[self.name]
            else:
                mdl_name = self.name
                wkm_name = self.name
                if not wkm_name.lower().endswith("_" + self.walkmeshType):
                    wkm_name += "_" + self.walkmeshType
                if mdl_name.lower().endswith("_" + self.walkmeshType):
                    mdl_name = mdl_name[0:-4]
                node = mdlnode.Dummy(wkm_name)
                if self.walkmeshType == "dwk":
                    node.dummytype = defines.Dummytype.DWKROOT
                else:
                    node.dummytype = defines.Dummytype.PWKROOT
                node.name = wkm_name
                rootdummy = node.add_to_collection(collection)
                if mdl_name in bpy.data.objects:
                    rootdummy.parent = bpy.data.objects[mdl_name]
                else:
                    pass
            mdlroot = utils.ancestor_node(rootdummy, lambda o: o.kb.dummytype == defines.Dummytype.MDLROOT)
            if mdlroot is None and rootdummy.parent:
                mdlroot = rootdummy.parent
            if self.walkmeshType == "dwk":
                dp_open1 = utils.search_node(mdlroot, lambda o: "dwk_dp" in o.name.lower() and o.name.lower().endswith("open1_01"))
                dp_open2 = utils.search_node(mdlroot, lambda o: "dwk_dp" in o.name.lower() and o.name.lower().endswith("open2_01"))
                dp_closed01 = utils.search_node(mdlroot, lambda o: "dwk_dp" in o.name.lower() and o.name.lower().endswith("closed_01"))
                dp_closed02 = utils.search_node(mdlroot, lambda o: "dwk_dp" in o.name.lower() and o.name.lower().endswith("closed_02"))
                wg_open1 = utils.search_node(mdlroot, lambda o: "dwk_wg" in o.name.lower() and o.name.lower().endswith("open1"))
                wg_open2 = utils.search_node(mdlroot, lambda o: "dwk_wg" in o.name.lower() and o.name.lower().endswith("open2"))
                wg_closed = utils.search_node(mdlroot, lambda o: "dwk_wg" in o.name.lower() and o.name.lower().endswith("closed"))
            if self.walkmeshType == "pwk":
                pwk_wg = utils.search_node(mdlroot, lambda o: o.name.lower().endswith("_wg"))
                pwk_use01 = utils.search_node(mdlroot, lambda o: o.name.lower().endswith("pwk_use01"))
                pwk_use02 = utils.search_node(mdlroot, lambda o: o.name.lower().endswith("pwk_use02"))

            for (_, node) in self.nodeDict.items():
                # the node names may only be recorded in the MDL,
                # this means that the named dummy nodes already exist in-scene,
                # use these names to translate the WKM's special node names
                if "dp_open1_01" in node.name.lower() and dp_open1:
                    node.name = dp_open1.name
                if "dp_open2_01" in node.name.lower() and dp_open2:
                    node.name = dp_open2.name
                if "dp_closed_01" in node.name.lower() and dp_closed01:
                    node.name = dp_closed01.name
                if "dp_closed_02" in node.name.lower() and dp_closed02:
                    node.name = dp_closed02.name
                if "dwk_wg_open1" in node.name.lower() and wg_open1:
                    node.name = wg_open1.name
                if "dwk_wg_open2" in node.name.lower() and wg_open2:
                    node.name = wg_open2.name
                if "dwk_wg_closed" in node.name.lower() and wg_closed:
                    node.name = wg_closed.name
                if node.name.lower().endswith("_wg") and pwk_wg:
                    node.name = pwk_wg.name
                if node.name.lower().endswith("pwk_use01") and pwk_use01:
                    node.name = pwk_use01.name
                if node.name.lower().endswith("pwk_use02") and pwk_use02:
                    node.name = pwk_use02.name
                # remove pre-existing nodes that were added as part of a model
                if node.name in collection.objects:
                    obj = collection.objects[node.name]
                    collection.objects.unlink(obj)
                    bpy.data.objects.remove(obj)
                obj = node.add_to_collection(collection)
                # Check if such an object exists
                if node.parentName.lower() in [k.lower() for k in bpy.data.objects.keys()]:
                    parent_name = utils.get_real_name(node.parentName)
                    obj.parent = bpy.data.objects[parent_name]
                    obj.matrix_parent_inverse = obj.parent.matrix_world.inverted()
                else:
                    # Node with invalid parent.
                    raise MalformedMdl(node.name + " has no parent " + node.parentName)


class Wok(Xwk):
    def __init__(self, name = "UNNAMED", wkmType = "wok"):
        self.nodeDict       = collections.OrderedDict()
        self.name           = name
        self.walkmeshType   = "wok"
        self.classification = defines.Classification.UNKNOWN

    def geometry_to_ascii(self, bObject, asciiLines, simple):
        nodeType = utils.get_node_type(bObject)
        if nodeType == "aabb":
            node = mdlnode.Aabb()
            node.roottype = "wok"
            node.nodetype = "trimesh"
            node.get_room_links(bObject.data)
            node.to_ascii(bObject, asciiLines, simple)
            return  # We'll take the first aabb object
        else:
            for child in bObject.children:
                self.geometry_to_ascii(child, asciiLines, simple)

    def generate_ascii(self, asciiLines, rootDummy, exports = {"ANIMATION", "WALKMESH"}):
        self.name = rootDummy.name

        # Header
        currentTime   = datetime.now()
        asciiLines.append("# Exported from blender at " + currentTime.strftime("%A, %Y-%m-%d"))
        # Geometry = AABB
        self.geometry_to_ascii(rootDummy, asciiLines, True)

    def import_to_collection(self, collection):
        pass
