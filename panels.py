import bpy
from bpy.types import Panel
from . import server
from .operators import is_qrcode_available
import os


STATUS_ICONS = {
    'INFO':    'INFO',
    'SUCCESS': 'CHECKMARK',
    'WARNING': 'ERROR',
    'ERROR':   'CANCEL',
    'RENDER':  'RENDER_STILL',
}


# ─── Main Panel ──────────────────────────────────────────────────────────────

class GYRO360_PT_Main(Panel):
    bl_label = "Gyro 360 Preview"
    bl_idname = "GYRO360_PT_Main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "360 Preview"

    def draw(self, context):
        layout = self.layout
        props = context.scene.gyro360

        status_box = layout.box()
        icon = STATUS_ICONS.get(props.status_type, 'INFO')
        row = status_box.row(align=True)
        row.label(text="", icon=icon)
        row.label(text=props.status_message[:60])


# ─── Render Panel ────────────────────────────────────────────────────────────

class GYRO360_PT_Render(Panel):
    bl_label = "Render"
    bl_idname = "GYRO360_PT_Render"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "360 Preview"
    bl_parent_id = "GYRO360_PT_Main"
    bl_options = set()

    def draw_header(self, context):
        self.layout.label(text="", icon='RENDER_STILL')

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.gyro360

        col = layout.column(align=True)
        col.label(text="Resolution Preset:", icon='IMAGE_DATA')
        col.prop(props, "render_resolution", text="")

        if props.render_resolution == 'CUSTOM':
            row = col.row(align=True)
            row.prop(props, "custom_width", text="W")
            row.prop(props, "custom_height", text="H")

        col.separator()
        col.prop(props, "auto_refresh", text="Auto-Refresh Mobile", icon='FILE_REFRESH')
        col.prop(props, "auto_open_browser", text="Auto-Open Browser", icon='WORLD')

        col.separator()

        if props.render_count > 0:
            box = col.box()
            box.label(text=f"Renders this session: {props.render_count}", icon='RENDER_RESULT')
            if props.render_output_path:
                box.label(text=f"Last: {bpy.path.basename(props.render_output_path)}",
                          icon='FILE_IMAGE')

        col.separator()

        # Single render button
        render_row = col.row()
        render_row.scale_y = 1.8
        render_row.operator(
            "gyro360.render_360",
            text="Render 360",
            icon='NONE'
        )


# ─── Output Settings Sub-Panel ───────────────────────────────────────────────

class GYRO360_PT_Output(Panel):
    bl_label = "Output Settings"
    bl_idname = "GYRO360_PT_Output"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "360 Preview"
    bl_parent_id = "GYRO360_PT_Render"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        self.layout.label(text="", icon='FILE_FOLDER')

    def draw(self, context):
        layout = self.layout
        props = context.scene.gyro360

        col = layout.column(align=True)
        col.label(text="Save Folder:", icon='FILE_FOLDER')
        col.prop(props, "output_folder", text="")
        if not props.output_folder:
            col.label(text="(default: Blender temp folder)", icon='INFO')

        col.separator()
        col.label(text="Filename:", icon='FILE_TEXT')
        col.prop(props, "render_name", text="")

        col.separator()
        col.prop(props, "auto_version", text="Auto-Version (_v001, _v002...)", icon='LINENUMBERS_ON')


# ─── Server Panel ────────────────────────────────────────────────────────────

class GYRO360_PT_Server(Panel):
    bl_label = "Mobile Preview"
    bl_idname = "GYRO360_PT_Server"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "360 Preview"
    bl_parent_id = "GYRO360_PT_Main"
    bl_options = set()

    def draw_header(self, context):
        self.layout.label(text="", icon='NETWORK_DRIVE')

    def draw(self, context):
        layout = self.layout
        props = context.scene.gyro360

        col = layout.column(align=True)

        actual_running = server.is_running()
        if actual_running != props.server_running:
            props.server_running = actual_running

        if not props.server_running:
            col.prop(props, "server_port", text="Port")
            col.separator()
            start_row = col.row()
            start_row.scale_y = 1.8
            start_row.operator(
                "gyro360.start_server",
                text="Start Mobile Preview",
                icon='PLAY'
            )
        else:
            url_box = col.box()
            url_box.label(text="Server Running", icon='CHECKMARK')
            url_str = f"http://{props.server_ip}:{props.server_port}"
            url_box.label(text=url_str, icon='LINKED')

            action_row = url_box.row(align=True)
            action_row.operator("gyro360.copy_url", text="Copy URL", icon='COPYDOWN')
            action_row.operator("gyro360.open_browser", text="Open Browser", icon='WORLD')

            col.separator()
            stop_row = col.row()
            stop_row.scale_y = 1.3
            stop_row.operator("gyro360.stop_server", text="Stop Server", icon='PAUSE')


# ─── QR Code Panel ───────────────────────────────────────────────────────────

class GYRO360_PT_QR(Panel):
    bl_label = "QR Code"
    bl_idname = "GYRO360_PT_QR"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "360 Preview"
    bl_parent_id = "GYRO360_PT_Main"
    bl_options = set()

    def draw_header(self, context):
        self.layout.label(text="", icon='TEXTURE')

    def draw(self, context):
        layout = self.layout
        props = context.scene.gyro360

        col = layout.column(align=True)
        qr_ok = is_qrcode_available()

        if not qr_ok:
            col.label(text="QR module not installed:", icon='ERROR')
            install_row = col.row(align=True)
            install_row.scale_y = 1.6
            install_row.alert = True
            install_row.operator(
                "gyro360.install_qr",
                text="Install QR Module",
                icon='IMPORT'
            )
            refresh_row = col.row()
            refresh_row.scale_y = 1.1
            refresh_row.operator(
                "gyro360.refresh_ui",
                text="Refresh (after install)",
                icon='FILE_REFRESH'
            )
        else:
            if not props.server_running:
                col.label(text="Start server first to generate QR", icon='INFO')
            else:
                gen_row = col.row()
                gen_row.scale_y = 1.6
                gen_row.operator(
                    "gyro360.generate_qr",
                    text="Generate QR Code",
                    icon='TEXTURE'
                )

                # Show QR inline if generated
                if props.qr_generated:
                    col.separator()

                    # Display QR image inline using template_icon with preview
                    img = bpy.data.images.get("Gyro360_QR")
                    if img:
                        qr_box = col.box()
                        qr_box.label(text="Scan with your phone:")
                        
                        # Ensure preview is generated
                        if img.preview is None:
                            try:
                                img.preview_ensure()
                            except Exception:
                                pass
                        
                        # Display the image using template_icon with the preview icon_id
                        if img.preview and img.preview.icon_id:
                            icon_row = qr_box.row()
                            icon_row.alignment = 'CENTER'
                            icon_row.template_icon(icon_value=img.preview.icon_id, scale=10.0)
                        else:
                            qr_box.label(text="(Preview loading...)", icon='IMAGE_DATA')
                            qr_box.label(text=f"File: {os.path.basename(props.qr_image_path)}")

                        # URL display
                        col.separator()
                        url_str = f"http://{props.server_ip}:{props.server_port}"
                        url_box = col.box()
                        url_box.label(text=url_str)

                        col.separator()

                        # Action buttons
                        action_row = col.row(align=True)
                        action_row.scale_y = 1.2
                        action_row.operator("gyro360.save_qr", text="Save to Disk", icon='EXPORT')
                        action_row.operator("gyro360.copy_url", text="Copy URL", icon='COPYDOWN')
                        
                        # Popup as backup
                        col.separator(factor=0.5)
                        popup_row = col.row()
                        popup_row.scale_y = 1.0
                        popup_row.operator("gyro360.show_qr_popup", text="View Larger", icon='WINDOW')


# ─── Registration ─────────────────────────────────────────────────────────────

classes = [
    GYRO360_PT_Main,
    GYRO360_PT_Render,
    GYRO360_PT_Output,
    GYRO360_PT_Server,
    GYRO360_PT_QR,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
