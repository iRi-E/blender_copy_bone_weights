# AlingTools.py (c) 2009, 2010 Gabriel Beaudin (gabhead)
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
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
#
# Modified by Gaia Clary, gaia.clary@machinimatrix.org :
#
# 31-aug-2011(GC): adapted to Blender-2.59 Python API
# 02-Sep-2011(GC): Added checkmarks for 
#              - copy only bone related weight groups
#              - create weight groups on target even if they are empty
# 18-Jan-2012(GC): adapted to Blender-2.62 Python API



bl_info = {
    "name": "Copy Bone Weights",
    "author": "Luke Hares, Gaia Clary",
    "version": (0,1),
    "blender": (2, 6, 3),
    "api": 45996,
    "location": "View3D > Tool Shelf > Copy Bone Weights Panel",
    "description": "Copy Bone Weights from Active Object to Selected Objects",
    "warning": "",
    "category": "3D View"}

"""Copy Bone Weights to Selected Objects"""

import bpy
from bpy.props import *

bpy.types.Scene.BWCInter = IntProperty(name="Interpolation",
    description="Base Mesh subdivides (Higher interpolation -> Better matching weights)",
    min=0,
    max=10,
    default=2)
bpy.types.Scene.BWCNamedBones = BoolProperty(name="Only Named Bones",
    description="Copy only the bone related weight groups to Target (Skip all other weight groups)",
    default=False)
bpy.types.Scene.BWCEmptyGroups = BoolProperty(name="Copy Empty Groups",
    description="Create bone related weight groups in Target, even if they contain no vertices",
    default=False)


class BWCUi(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'

    bl_label = "Bone Weight Copy"
    bl_context = "objectmode"


    @classmethod
    def poll(cls, context):
        try:
            type = context.active_object.type == "MESH"
            return type
        except:
            return False
    

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        layout.prop(scn, 'BWCInter')
        layout.prop(scn, 'BWCNamedBones')
        layout.prop(scn, 'BWCEmptyGroups')
        col = layout.column(align=False)
        col.operator("object.bwc",text="Copy Bone Weights")
        


def boneWeightCopy(tempObj,targetObject, onlyNamedBones, keepEmptyGroups):
    print("Weight group Copy to ", targetObject.name)
    modifiers = tempObj.modifiers
    boneSet = []
    for modifier in modifiers:
        type = modifier.type
        if type == 'ARMATURE':
            armature = modifier.object.data
            bones = armature.bones
            for bone in bones:
                #print ("bone ", bone.name)
                boneSet.append(bone.name)
                if keepEmptyGroups == True:
                    if not(bone.name in targetObject.vertex_groups):
                        targetObject.vertex_groups.new(bone.name)

    #get active object vertices and transform to world space
    
    WSTargetVertsCo = [targetObject.matrix_world * v.co for v in targetObject.data.vertices]
    for targetVert,WSTargetVertCo in zip(targetObject.data.vertices,WSTargetVertsCo):
        dists = [(WSTargetVertCo-v.co).length for v in tempObj.data.vertices]
        activeIndex = dists.index(min(dists))
        nearestVertex = tempObj.data.vertices[activeIndex]
        for group in nearestVertex.groups:
            groupName = tempObj.vertex_groups[group.group].name
            #print ("Group name is", groupName)
            if ( onlyNamedBones == False or groupName in boneSet):
                if not(groupName in targetObject.vertex_groups):
                    targetObject.vertex_groups.new(groupName)
                targetObject.vertex_groups[groupName].add([targetVert.index],group.weight,'REPLACE')
                #print ("copied group", groupName)
            #else:
            #    print ("Skipping group", groupName)

def main(context):
    '''Copies the bone weights'''
    #print(context.scene.BWCInter, context.scene.BWCNamedBones, context.scene.BWCEmptyGroups )
    if context.active_object.type != 'MESH':
        return
    targetObjects = context.selected_objects
    baseObj = context.active_object
    bpy.ops.object.select_all(action='DESELECT')
    baseObj.select=True
    bpy.ops.object.duplicate()
    tempObj = context.active_object
    if context.scene.BWCInter > 0:
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.quads_convert_to_tris(use_beauty=True)
        bpy.ops.mesh.subdivide(number_cuts=context.scene.BWCInter, smoothness=0)
        bpy.ops.object.editmode_toggle()
    for v in tempObj.data.vertices:
        v.co = baseObj.matrix_world * v.co
    for targetObject in targetObjects:
        if (targetObject.type == 'MESH') & (targetObject != baseObj):
             boneWeightCopy(tempObj,targetObject, context.scene.BWCNamedBones, context.scene.BWCEmptyGroups)
    bpy.ops.object.delete()

## Copy Bone Weights Operator
class BWCOperator(bpy.types.Operator):
    ''''''
    bl_idname = "object.bwc"
    bl_label = "Copy Selected Object Bone Weights to Active"    


    def execute(self, context):
        main(context)
        return {'FINISHED'}



## registring
def register():
    bpy.utils.register_module(__name__)

    pass

def unregister():
    bpy.utils.unregister_module(__name__)

    pass

if __name__ == "__main__":
    register()
