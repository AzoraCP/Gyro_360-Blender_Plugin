import bpy
from bpy.props import (
    StringProperty, BoolProperty, EnumProperty,
    IntProperty, PointerProperty
)
from bpy.types import PropertyGroup


RES_MAP = {
    '1K': (1024, 512),
    '2K': (2048, 1024),
    '4K': (4096, 2048),
}


def _update_resolution(self, context):
    """Sync resolution preset to Blender's render properties in real time."""
    scene = context.scene
    if self.render_resolution == 'CUSTOM':
        w, h = self.custom_width, self.custom_height
    else:
        w, h = RES_MAP[self.render_resolution]
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = 100


class GYRO360_Properties(PropertyGroup):

    # Server state
    server_running: BoolProperty(name="Server Running", default=False)
    server_port: IntProperty(name="Port", default=8765, min=1024, max=65535)
    server_ip: StringProperty(name="Server IP", default="")

    # Render resolution
    render_resolution: EnumProperty(
        name="Resolution",
        items=[
            ('1K', '1K - 1024x512', 'Quick preview quality'),
            ('2K', '2K - 2048x1024', 'Standard quality'),
            ('4K', '4K - 4096x2048', 'High quality final render'),
            ('CUSTOM', 'Custom', 'Set your own resolution'),
        ],
        default='1K',
        update=_update_resolution
    )

    // 

    custom_width: IntProperty(
        name="Width", default=2048, min=64, max=16384, update=_update_resolution
    )
    custom_height: IntProperty(
        name="Height", default=1024, min=32, max=8192, update=_update_resolution
    )

    # Output path & names
    output_folder: StringProperty(
        name="Output Folder",
        description="Folder where renders are saved (leave empty for temp folder)",
        subtype='DIR_PATH',
        default=""
    )

    render_name: StringProperty(
        name="Render Name",
        description="Filename for renders (without extension)",
        default="render_360"
    )

    auto_version: BoolProperty(
        name="Auto-Version Renders",
        description="Append a version number to avoid overwriting",
        default=True
    )

    # Behavior
    auto_refresh: BoolProperty(
        name="Auto-Refresh Mobile",
        description="Automatically push updated render to mobile browser",
        default=True
    )

    auto_open_browser: BoolProperty(
        name="Auto-Open Desktop Browser",
        description="Open preview in desktop browser after starting server",
        default=False
    )

    # Status
    status_message: StringProperty(name="Status", default="Ready")
    status_type: EnumProperty(
        name="Status Type",
        items=[
            ('INFO', 'Info', ''),
            ('SUCCESS', 'Success', ''),
            ('WARNING', 'Warning', ''),
            ('ERROR', 'Error', ''),
            ('RENDER', 'Rendering', ''),
        ],
        default='INFO'
    )

    # Output state
    render_output_path: StringProperty(name="Output Path", subtype='FILE_PATH', default="")
    render_count: IntProperty(name="Render Count", default=0)

    # QR state
    qr_generated: BoolProperty(name="QR Generated", default=False)
    qr_image_path: StringProperty(name="QR Image Path", default="")
    qr_image_datablock: PointerProperty(
        name="QR Image",
        type=bpy.types.Image,
        description="QR code image for display"
    )


def register():
    bpy.utils.register_class(GYRO360_Properties)
    bpy.types.Scene.gyro360 = PointerProperty(type=GYRO360_Properties)


def unregister():
    del bpy.types.Scene.gyro360
    bpy.utils.unregister_class(GYRO360_Properties)
