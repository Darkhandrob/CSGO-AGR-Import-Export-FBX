# AGR-FBX Import and Export Script by Darkhand
# https://www.youtube.com/user/Darkhandrob
# https://twitter.com/Darkhandrob
# Last change: 16.08.2018

import bpy,time,os

class ImpExportAgr(bpy.types.Operator):
    """CSGO AGR Importer-Exporter"""      # blender will use this as a tooltip for menu items and buttons.
    bl_idname = "custom.import_agr_to_fbx"     # unique identifier for buttons and menu items to reference.
    bl_label = "CSGO AGR Import-Export FBX"         # display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # enable undo for the operator.
    
    # Properties used by the file browser
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
    filename_ext = ".agr"
    filter_glob = bpy.props.StringProperty(default="*.agr", options={'HIDDEN'})
    
    def menu_draw_import(self, context):
        layout = self.layout
        layout.operator("custom.import_agr_to_fbx", text="AGR Import and Export FBX")
    
    # Layout for the Properties of the file Browser
    def draw(self, context):
        layout = self.layout
        box_import = layout.box()
        box_import.prop(self, "frameRate")
        box_import.prop(self, "framerateBase") 
        box_import.prop(self, "assetPath")
        box_import.prop(self, "interKey")
        box_import.prop(self, "global_scale")
        box_import.prop(self, "scaleInvisibleZero")
        box_import.prop(self, "skipRemDoubles")
        
        box_export = layout.box()
        box_export.prop(self, "exportingPath")

    # Custom properties 
    frameRate = bpy.props.IntProperty(
        name="FPS:",
        description="Set the Framerate to which the agr was recorded.",
        default=60,
        soft_min=1,
        soft_max=120,
    )
    framerateBase = bpy.props.FloatProperty(
        name="/:",
        description="Framerate base; Divisor of FPS:Base = Framerate",
        default=1.0,
        soft_min=0.1,
        soft_max=120.0,
        step=10,
        precision=3,
    )
    assetPath = bpy.props.StringProperty(
        name="Asset Path",
        description="Directory path containing the (decompiled) assets in a folder structure as in the pak01_dir.pak.",
        default="",
    )
    interKey = bpy.props.BoolProperty(
        name="Add interpolated key frames",
        description="Create interpolated key frames for frames in-between the original key frames.",
        default=False,
    )
    global_scale = bpy.props.FloatProperty(
        name="Scale",
        description="Scale everything by this value",
        min=0.000001, max=1000000.0,
        soft_min=0.001, soft_max=1.0,
        default=0.01,
    )    
    scaleInvisibleZero = bpy.props.BoolProperty(
        name="Scale invisible to zero",
        description="If set entities will scaled to zero when not visible.",
        default=False,
    )
    skipRemDoubles = bpy.props.BoolProperty(
        name="Preserve SMD Polygons & Normals",
        description="Import raw (faster), disconnected polygons from SMD files; these are harder to edit but a closer match to the original mesh",
        default=True,
    )
    exportingPath = bpy.props.StringProperty(
        name="Export Path",
        description="Directory path to export FBX files",
        default="",
    )
    
    def MergeInvAnims(self, context):
        # Ragdollanimation .hide_render is set as True at Frame 1
        # But if he was killed before starting recording, it is also the Ragdoll is False and Run is True
        # Each Type of Model gets its own Array inside the Array
        PlayerAnims = []
        for CurrMdl in bpy.data.objects:
            # Find Player Models
            if (CurrMdl.name.find("afx.") != -1 and CurrMdl.name.find("tm") != -1):
                # Get RagdollAnimation and Changing Point 
                CurrHideRender = CurrMdl.animation_data.action.fcurves[0]
                if CurrHideRender.keyframe_points[1].co[0] > 1.0:
                    ChgKeyframe = int(CurrHideRender.keyframe_points[1].co[0])
                    # Find RunAnimation
                    for CurrSecMdl in bpy.data.objects:
                        if CurrMdl.name.find("afx.") != -1:
                            if CurrSecMdl.name.find(CurrMdl.name.split()[1]) != -1:
                                # Dont use the same object-model
                                if not CurrMdl == CurrSecMdl:
                                    SecHideRender = CurrSecMdl.animation_data.action.fcurves[0]
                                    if SecHideRender.keyframe_points[ChgKeyframe].co[1] == 1.0:
                                        if SecHideRender.keyframe_points[ChgKeyframe-1].co[1] == 0.0: 
                                            PlayerAnims.append([CurrSecMdl,CurrMdl])
                                                                                         
        # Edit Animation-strips
        for i in range(len(PlayerAnims)):
            RagdollStart = PlayerAnims[i][1].animation_data.action.fcurves[1].range()[0] 
            PlayerAnims[i][1].keyframe_delete(data_path="hide_render", frame=0.0)
            RunDataAnim = PlayerAnims[i][0].animation_data.action
            RagdollDataAnim = PlayerAnims[i][1].animation_data.action
            # Push Action down to new Strip
            PlayerAnims[i][0].animation_data_clear()
            PlayerAnims[i][0].animation_data_create()
            ComplAnim = PlayerAnims[i][0].animation_data.nla_tracks.new()
            ComplAnim.strips.new(name="RunData", start=0.0, action=RunDataAnim)
            # RunAnim already jumps on the frame, where the first keyframe of RagdollAnim is
            ComplAnim.strips[RunDataAnim.name].action_frame_end = RagdollStart - 1
            ComplAnim.strips.new(name="RagdollDataAnim", start=RagdollStart, action=RagdollDataAnim)
            # Delete model
            for C in PlayerAnims[i][1].children:
                bpy.data.objects.remove(C)
            bpy.data.objects.remove(PlayerAnims[i][1])
            PlayerAnims[i][0].name = PlayerAnims[i][0].name + "RunAndDeathAnim"
        print("Merging Run and DeathAimation finished")
    
    # Open the filebrowser with the custom properties
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    # Main funktion
    def execute(self, context):
        # Timing Runtime
        time_start = time.time()
        # Change Framerate of Scene
        bpy.context.scene.render.fps = self.frameRate
        bpy.context.scene.render.fps_base = self.framerateBase
        # Import agr with input filepath
        bpy.ops.advancedfx.agr_importer(
            filepath=self.filepath,
            assetPath=self.assetPath,
            interKey =self.interKey,
            global_scale = self.global_scale,
            scaleInvisibleZero=self.scaleInvisibleZero,
            skipRemDoubles=self.skipRemDoubles
        )
        # Create Directory
        if not self.exportingPath:
            NewExportPath = os.path.join(os.path.dirname(self.filepath), bpy.path.display_name_from_filepath(self.filepath))
        else:
            NewExportPath = os.path.join(self.exportingPath, bpy.path.display_name_from_filepath(self.filepath))
        os.makedirs(name=NewExportPath, exist_ok=True)
        self.exportingPath = NewExportPath
        
        # Execute method
        self.MergeInvAnims(context)
        # Delete physics(maybe include into merge_anim class for runtime)
        for CurrMdl in bpy.data.objects: 
            if CurrMdl.name.find("physics") != -1:
                bpy.data.objects.remove(CurrMdl)
                
        print("Deleting Physics finished.")
        NumberMdl = 0
        for CurrMdl in bpy.data.objects:
            if CurrMdl.name.find("afx.") != -1:
                #select all keyframes
                if CurrMdl.name.find("RunAndDeathAnim") != -1:
                    bpy.context.scene.frame_end = CurrMdl.animation_data.nla_tracks[0].strips[1].action_frame_end
                else:
                    bpy.context.scene.frame_end = CurrMdl.animation_data.action.frame_range[1]
                # select root
                CurrMdl.select = True
                # select childrens
                for CurrentChildren in CurrMdl.children:
                    CurrentChildren.select = True
                # rename top to root
                CurrObjName = CurrMdl.name
                CurrMdl.name = "root"
                # export single object as fbx
                CurrentObjectName = CurrObjName.split()[1] + " " +  CurrObjName.split()[0]
                fullfiles = self.exportingPath + "/" + CurrentObjectName + ".fbx"
                NumberMdl += 1
                bpy.ops.export_scene.fbx(
                    filepath = fullfiles, 
                    use_selection = True, 
                    bake_anim_use_nla_strips = False, 
                    bake_anim_use_all_actions = False, 
                    bake_anim_simplify_factor = 0,
                    add_leaf_bones=False
                    )
                # undo all changes
                CurrMdl.name = CurrObjName
                CurrMdl.select = False
                for CurrentChildren in CurrMdl.children:
                    CurrentChildren.select = False
                
        print("Exporting "+ str(NumberMdl) +" Models finished.")    
        #export camera
        if bpy.data.objects.find("afxCam") != -1:
            bpy.data.objects["afxCam"].select = True
            fullfiles_cam = self.exportingPath + "/afxcam.fbx"
            bpy.ops.export_scene.fbx(
                filepath = fullfiles_cam, 
                use_selection = True, 
                bake_anim_use_nla_strips = False, 
                bake_anim_use_all_actions = False, 
                bake_anim_simplify_factor = 0,
                add_leaf_bones=False)
            bpy.data.objects["afxCam"].select = False
            
        print("Exporting Camera Finished.")
        print(" ")
        print ("FBX-Export script finished in %.4f sec." % (time.time() - time_start))
        return {'FINISHED'} 
    
    
def register():
    bpy.utils.register_class(ImpExportAgr)
    bpy.types.INFO_MT_file_import.append(ImpExportAgr.menu_draw_import)
    
def unregister():
    bpy.types.INFO_MT_file_import.remove(ImpExportAgr.menu_draw_import)
    bpy.utils.unregister_class(ImpExportAgr)
        
# This allows you to run the script directly from blenders text editor
# to test the addon without having to install it.
if __name__ == "__main__":
    register()
