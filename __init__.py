bl_info = {
    "name": "Gyro 360 Preview",
    "author": "Gyro360",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > 360 Preview",
    "description": "Render 360 equirectangular images and preview on mobile with gyroscope controls",
    "category": "Render",
}

import bpy
from . import operators, panels, server, properties


def register():
    properties.register()
    operators.register()
    panels.register()


def unregister():
    panels.unregister()
    operators.unregister()
    properties.unregister()


if __name__ == "__main__":
    register()
