# ***** BEGIN GPL LICENSE BLOCK *****
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ***** END GPL LICENCE BLOCK *****

bl_info = {
    "name": "Copy Bone Weights",
    "author": "Luke Hares, Gaia Clary, IRIE Shinsuke",
    "version": (0, 1),
    "blender": (2, 78, 0),
    "location": "View3D > Tool Shelf > Copy Bone Weights Panel",
    "description": "Copy Bone Weights from Active Object to Selected Objects",
    "tracker_url": "https://github.com/iRi-E/blender_copy_bone_weights/issues",
    "category": "3D View"}


import bpy
from bpy.props import *
import mathutils


class BWCUi(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = "Tools"
    bl_label = "Bone Weight Copy"
    bl_context = "objectmode"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        try:
            return context.active_object.type == "MESH"
        except AttributeError:
            return False

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        col = layout.column(align=False)
        col.prop(scn, 'BWCNamedBones')
        col.prop(scn, 'BWCEmptyGroups')
        col.operator("object.bwc", text="Copy Bone Weights")


def boneWeightCopy(tempObj, targetObject, onlyNamedBones, keepEmptyGroups):
    modifiers = tempObj.modifiers
    mesh = tempObj.data

    boneSet = []
    for modifier in modifiers:
        if modifier.type == 'ARMATURE':
            armature = modifier.object.data
            bones = armature.bones

            for bone in bones:
                boneSet.append(bone.name)

                if keepEmptyGroups:
                    if bone.use_deform and bone.name not in targetObject.vertex_groups:
                        targetObject.vertex_groups.new(bone.name)

    # get active object vertices and transform to world space
    WSTargetVertsCo = [targetObject.matrix_world * v.co for v in targetObject.data.vertices]

    kd = None
    ncopied = 0

    for targetVert, WSTargetVertCo in zip(targetObject.data.vertices, WSTargetVertsCo):
        if targetVert.select:
            try:
                faceFound, nearestCo, normal, faceIndex = tempObj.closest_point_on_mesh(WSTargetVertCo)
            except RuntimeError:  # there is no polygon
                faceFound = False

            if faceFound:
                polygon = mesh.polygons[faceIndex].vertices
                ipWeights = mathutils.interpolate.poly_3d_calc([mesh.vertices[i].co for i in polygon], nearestCo)
            else:
                # fallback
                if not kd:
                    print("falling back to nearest vertex method...")

                    # build kd-tree
                    size = len(mesh.vertices)
                    kd = mathutils.kdtree.KDTree(size)
                    for i, v in enumerate(mesh.vertices):
                        kd.insert(v.co, i)
                    kd.balance()

                nearestCo, activeIndex, minDist = kd.find(WSTargetVertCo)

            copied = False
            for group in tempObj.vertex_groups:
                groupName = group.name

                if (groupName in boneSet or not onlyNamedBones):
                    if faceFound:
                        weight = 0.0

                        for i, w in zip(polygon, ipWeights):
                            try:
                                weight += group.weight(i) * w
                            except RuntimeError:  # vertex doesn't belong to this group
                                pass
                    else:
                        try:
                            weight = group.weight(activeIndex)
                        except RuntimeError:  # nearest vertex doesn't belong to this group
                            weight = 0.0

                    if weight:
                        if groupName not in targetObject.vertex_groups:
                            targetObject.vertex_groups.new(groupName)

                        targetObject.vertex_groups[groupName].add([targetVert.index], weight, 'REPLACE')
                        copied = True
                    elif groupName in targetObject.vertex_groups:
                        targetObject.vertex_groups[groupName].remove([targetVert.index])

            if copied:
                ncopied += 1

    return ncopied


def main(context):
    '''Copies the bone weights'''

    if context.active_object.type != 'MESH':
        return

    targetObjects = context.selected_objects
    baseObj = context.active_object

    bpy.ops.object.select_all(action='DESELECT')
    baseObj.select = True

    bpy.ops.object.duplicate()
    tempObj = context.active_object

    # apply mirrors, to process target objects not mirrored
    for modifier in tempObj.modifiers:
        if modifier.type == 'MIRROR':
            if tempObj.data.shape_keys:
                bpy.ops.object.shape_key_remove(all=True)
            bpy.ops.object.modifier_apply(apply_as='DATA', modifier=modifier.name)

    for v in tempObj.data.vertices:
        v.co = baseObj.matrix_world * v.co

    for targetObject in targetObjects:
        if (targetObject.type == 'MESH') & (targetObject != baseObj):
            print("Copy bone weights from '{}' to '{}'".format(baseObj.name, targetObject.name))
            n = boneWeightCopy(tempObj, targetObject, context.scene.BWCNamedBones, context.scene.BWCEmptyGroups)
            print("Transferred weights of {} vertices".format(n))

    bpy.ops.object.delete()


# Copy Bone Weights Operator
class BWCOperator(bpy.types.Operator):
    '''Copy bone weights from active object to selected vertices in other selected objects'''

    bl_idname = "object.bwc"
    bl_label = "Copy Bone Weights Active Object to Selected Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        main(context)
        return {'FINISHED'}


# registring
def register():
    bpy.utils.register_module(__name__)

    bpy.types.Scene.BWCNamedBones = BoolProperty(
        name="Only Named Bones",
        description="Copy only the bone related weight groups to Target (Skip all other weight groups)",
        default=False)
    bpy.types.Scene.BWCEmptyGroups = BoolProperty(
        name="Copy Empty Groups",
        description="Create bone related weight groups in Target, even if they contain no vertices",
        default=False)


def unregister():
    del bpy.types.Scene.BWCNamedBones
    del bpy.types.Scene.BWCEmptyGroups

    bpy.utils.unregister_module(__name__)


if __name__ == "__main__":
    register()
