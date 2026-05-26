import bpy
import os
import sys
import subprocess
import importlib
import webbrowser
from bpy.types import Operator

from . import server


# ─── Helpers ─────────────────────────────────────────────────────────────────

def set_status(scene, msg, status_type='INFO'):
    props = scene.gyro360
    props.status_message = msg
    props.status_type = status_type
    if bpy.context.screen:
        for area in bpy.context.screen.areas:
            area.tag_redraw()


def get_render_resolution(props):
    res_map = {'1K': (1024, 512), '2K': (2048, 1024), '4K': (4096, 2048)}
    if props.render_resolution == 'CUSTOM':
        return props.custom_width, props.custom_height
    return res_map[props.render_resolution]


def get_output_dir(props):
    """Return the user's chosen output folder, or fall back to temp."""
    if props.output_folder:
        path = bpy.path.abspath(props.output_folder)
        os.makedirs(path, exist_ok=True)
        return path
    base = bpy.app.tempdir
    out_dir = os.path.join(base, "gyro360_renders")
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def build_output_path(props):
    """Build full filepath, optionally with version suffix."""
    folder = get_output_dir(props)
    base_name = props.render_name.strip() or "render_360"
    if props.auto_version:
        v = 1
        while True:
            candidate = os.path.join(folder, f"{base_name}_v{v:03d}.jpg")
            if not os.path.exists(candidate):
                return candidate
            v += 1
    return os.path.join(folder, f"{base_name}.jpg")


def is_qrcode_available():
    try:
        importlib.invalidate_caches()
        if 'qrcode' in sys.modules and sys.modules['qrcode'] is None:
            del sys.modules['qrcode']
        import qrcode  # noqa
        return True
    except ImportError:
        return False
    except Exception:
        return False


def sync_resolution_to_scene(scene):
    props = scene.gyro360
    w, h = get_render_resolution(props)
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = 100


# ─── Rendering ────────────────────────────────────────────────────────────────

class GYRO360_OT_Render360(Operator):
    bl_idname = "gyro360.render_360"
    bl_label = "Render 360"
    bl_description = "Render equirectangular 360° image and update mobile preview"
    bl_options = {'REGISTER'}

    _timer = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            if not bpy.app.is_job_running('RENDER'):
                self.cancel(context)
                self._post_render(context)
                return {'FINISHED'}
        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        scene = context.scene
        props = scene.gyro360

        if not scene.camera:
            self.report({'ERROR'}, "No camera in scene. Add a camera first.")
            set_status(scene, "No camera in scene.", 'ERROR')
            return {'CANCELLED'}

        # Auto-configure camera
        cam = scene.camera.data
        if cam.type != 'PANO':
            cam.type = 'PANO'
        if hasattr(cam, 'panorama_type'):
            cam.panorama_type = 'EQUIRECTANGULAR'

        if scene.render.engine != 'CYCLES':
            scene.render.engine = 'CYCLES'

        sync_resolution_to_scene(scene)
        w, h = get_render_resolution(props)

        out_path = build_output_path(props)

        scene.render.image_settings.file_format = 'JPEG'
        scene.render.image_settings.quality = 92
        scene.render.filepath = out_path
        props.render_output_path = out_path
        props.render_count += 1

        set_status(scene, f"Rendering {w}x{h}...", 'RENDER')

        bpy.ops.render.render('INVOKE_DEFAULT', write_still=True)

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.5, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)

    def _post_render(self, context):
        scene = context.scene
        props = scene.gyro360
        out_path = props.render_output_path

        if os.path.exists(out_path):
            server.set_image_path(out_path)
            fname = os.path.basename(out_path)
            set_status(scene, f"Render done - {fname} | Preview updated", 'SUCCESS')
            self.report({'INFO'}, f"Render saved: {out_path}")
        else:
            set_status(scene, "Render output not found.", 'ERROR')


# ─── Server ───────────────────────────────────────────────────────────────────

class GYRO360_OT_StartServer(Operator):
    bl_idname = "gyro360.start_server"
    bl_label = "Start Mobile Preview"
    bl_description = "Start local HTTP server for mobile preview"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        props = scene.gyro360

        try:
            ip, port = server.start_server(props.server_port)
            props.server_ip = ip
            props.server_port = port
            props.server_running = True

            url = f"http://{ip}:{port}"
            set_status(scene, f"Server running -> {url}", 'SUCCESS')
            self.report({'INFO'}, f"Mobile preview server started at {url}")

            if props.render_output_path and os.path.exists(props.render_output_path):
                server.set_image_path(props.render_output_path)

            if props.auto_open_browser:
                webbrowser.open(url)

        except Exception as e:
            set_status(scene, f"Server error: {str(e)}", 'ERROR')
            self.report({'ERROR'}, f"Failed to start server: {str(e)}")

        return {'FINISHED'}


class GYRO360_OT_StopServer(Operator):
    bl_idname = "gyro360.stop_server"
    bl_label = "Stop Server"
    bl_description = "Stop the mobile preview server"
    bl_options = {'REGISTER'}

    def execute(self, context):
        server.stop_server()
        context.scene.gyro360.server_running = False
        context.scene.gyro360.server_ip = ""
        set_status(context.scene, "Server stopped", 'INFO')
        return {'FINISHED'}


class GYRO360_OT_OpenBrowser(Operator):
    bl_idname = "gyro360.open_browser"
    bl_label = "Open in Browser"
    bl_description = "Open the 360 preview in your desktop browser"
    bl_options = {'REGISTER'}

    def execute(self, context):
        props = context.scene.gyro360
        if props.server_running and props.server_ip:
            url = f"http://{props.server_ip}:{props.server_port}"
            webbrowser.open(url)
        else:
            self.report({'WARNING'}, "Server not running. Start Mobile Preview first.")
        return {'FINISHED'}


# ─── QR Code ─────────────────────────────────────────────────────────────────

class GYRO360_OT_InstallQR(Operator):
    bl_idname = "gyro360.install_qr"
    bl_label = "Install QR Module"
    bl_description = "Install the qrcode[pil] Python package into Blender's Python"
    bl_options = {'REGISTER'}

    def execute(self, context):
        python_exe = sys.executable
        set_status(context.scene, "Installing qrcode[pil]... please wait", 'INFO')

        try:
            subprocess.run(
                [python_exe, "-m", "ensurepip", "--upgrade"],
                check=False, capture_output=True, timeout=60
            )

            result = subprocess.run(
                [python_exe, "-m", "pip", "install", "qrcode[pil]",
                 "--upgrade", "--user"],
                capture_output=True, text=True, timeout=180
            )

            if result.returncode != 0:
                result = subprocess.run(
                    [python_exe, "-m", "pip", "install", "qrcode[pil]", "--upgrade"],
                    capture_output=True, text=True, timeout=180
                )

            if result.returncode == 0:
                importlib.invalidate_caches()
                import site
                user_site = site.getusersitepackages()
                if user_site and os.path.isdir(user_site) and user_site not in sys.path:
                    sys.path.insert(0, user_site)
                for mod_name in list(sys.modules.keys()):
                    if mod_name == 'qrcode' or mod_name.startswith('qrcode.'):
                        try:
                            del sys.modules[mod_name]
                        except KeyError:
                            pass

                try:
                    import qrcode  # noqa
                    set_status(context.scene, "QR module installed! Ready to generate.", 'SUCCESS')
                    self.report({'INFO'}, "qrcode[pil] installed successfully")
                except ImportError as e:
                    set_status(context.scene,
                               "Installed - please restart Blender to load it.", 'WARNING')
                    self.report({'WARNING'},
                                f"Installed but not importable yet. Please restart Blender. {e}")
            else:
                err = (result.stderr or result.stdout or "Unknown error")[:200]
                set_status(context.scene, "Install failed. Check console.", 'ERROR')
                self.report({'ERROR'}, f"pip install failed: {err}")

        except subprocess.TimeoutExpired:
            set_status(context.scene, "Install timed out.", 'ERROR')
        except Exception as e:
            set_status(context.scene, f"Install error: {str(e)[:60]}", 'ERROR')

        if context.screen:
            for area in context.screen.areas:
                area.tag_redraw()
        return {'FINISHED'}


class GYRO360_OT_GenerateQR(Operator):
    bl_idname = "gyro360.generate_qr"
    bl_label = "Generate QR Code"
    bl_description = "Generate QR code for mobile preview URL"
    bl_options = {'REGISTER'}

    def execute(self, context):
        props = context.scene.gyro360

        if not props.server_running or not props.server_ip:
            self.report({'WARNING'}, "Start the Mobile Preview server first.")
            set_status(context.scene, "Start server before generating QR.", 'WARNING')
            return {'CANCELLED'}

        if not is_qrcode_available():
            self.report({'ERROR'}, "qrcode module not installed.")
            return {'CANCELLED'}

        try:
            import qrcode

            url = f"http://{props.server_ip}:{props.server_port}"
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            qr_dir = get_output_dir(props)
            qr_path = os.path.join(qr_dir, "gyro360_qr.png")
            img.save(qr_path)
            props.qr_image_path = qr_path
            props.qr_generated = True

            # Load into Blender image datablock
            img_name = "Gyro360_QR"
            if img_name in bpy.data.images:
                bpy.data.images.remove(bpy.data.images[img_name])
            bl_img = bpy.data.images.load(qr_path, check_existing=False)
            bl_img.name = img_name
            bl_img.reload()
            
            # Force preview generation - this is critical for icon_id to work
            try:
                bl_img.preview_ensure()
            except Exception as e:
                self.report({'WARNING'}, f"Preview generation issue: {e}")
            
            # Set the pointer property for template_ID display
            props.qr_image_datablock = bl_img

            set_status(context.scene, f"QR ready for {url}", 'SUCCESS')
            self.report({'INFO'}, f"QR code generated for {url}")

        except Exception as e:
            set_status(context.scene, f"QR error: {str(e)}", 'ERROR')
            self.report({'ERROR'}, str(e))

        return {'FINISHED'}


class GYRO360_OT_SaveQR(Operator):
    bl_idname = "gyro360.save_qr"
    bl_label = "Save QR to Disk"
    bl_description = "Save the QR code image to a chosen location"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def invoke(self, context, event):
        props = context.scene.gyro360
        if not props.qr_image_path or not os.path.exists(props.qr_image_path):
            self.report({'WARNING'}, "No QR code generated yet.")
            return {'CANCELLED'}

        # Default filename
        self.filepath = "gyro360_qr.png"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        props = context.scene.gyro360
        src = props.qr_image_path

        if not src or not os.path.exists(src):
            self.report({'ERROR'}, "QR code file not found.")
            return {'CANCELLED'}

        try:
            import shutil
            shutil.copy(src, self.filepath)
            self.report({'INFO'}, f"QR code saved to {self.filepath}")
            set_status(context.scene, f"QR saved to {os.path.basename(self.filepath)}", 'SUCCESS')
        except Exception as e:
            self.report({'ERROR'}, f"Failed to save: {e}")

        return {'FINISHED'}


class GYRO360_OT_ShowQRPopup(Operator):
    """Display QR code in a popup window."""
    bl_idname = "gyro360.show_qr_popup"
    bl_label = "QR Code"
    bl_description = "Show QR code in a popup window"
    bl_options = {'REGISTER'}

    def invoke(self, context, event):
        props = context.scene.gyro360
        img = bpy.data.images.get("Gyro360_QR")

        if not img:
            self.report({'WARNING'}, "QR not generated yet.")
            return {'CANCELLED'}

        return context.window_manager.invoke_popup(self, width=400)

    def execute(self, context):
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.gyro360
        img = bpy.data.images.get("Gyro360_QR")

        if not img:
            layout.label(text="QR image not found.", icon='ERROR')
            return

        col = layout.column(align=True)
        
        # Title
        header = col.row()
        header.alignment = 'CENTER'
        header.label(text="Scan with your phone")
        
        col.separator()

        # Ensure preview is generated
        if img.preview is None:
            try:
                img.preview_ensure()
            except Exception:
                pass

        # Display the QR image using template_icon (large)
        if img.preview and img.preview.icon_id:
            icon_row = col.row()
            icon_row.alignment = 'CENTER'
            icon_row.template_icon(icon_value=img.preview.icon_id, scale=15.0)
        else:
            col.label(text="(Preview loading...)", icon='IMAGE_DATA')
            col.label(text=f"File: {os.path.basename(props.qr_image_path)}")

        col.separator()

        # URL display
        url = f"http://{props.server_ip}:{props.server_port}"
        url_box = col.box()
        url_row = url_box.row()
        url_row.alignment = 'CENTER'
        url_row.label(text=url)

        # Action buttons
        col.separator()
        actions = col.row(align=True)
        actions.scale_y = 1.3
        actions.operator("gyro360.save_qr", text="Save to Disk", icon='EXPORT')
        actions.operator("gyro360.copy_url", text="Copy URL", icon='COPYDOWN')


# ─── Utilities ────────────────────────────────────────────────────────────────

class GYRO360_OT_CopyURL(Operator):
    bl_idname = "gyro360.copy_url"
    bl_label = "Copy URL"
    bl_description = "Copy mobile preview URL to clipboard"

    def execute(self, context):
        props = context.scene.gyro360
        if props.server_ip:
            url = f"http://{props.server_ip}:{props.server_port}"
            context.window_manager.clipboard = url
            self.report({'INFO'}, f"Copied: {url}")
        return {'FINISHED'}


class GYRO360_OT_RefreshUI(Operator):
    bl_idname = "gyro360.refresh_ui"
    bl_label = "Refresh"
    bl_description = "Re-check if QR module is now installed"

    def execute(self, context):
        is_qrcode_available()
        if context.screen:
            for area in context.screen.areas:
                area.tag_redraw()
        return {'FINISHED'}


# ─── Registration ─────────────────────────────────────────────────────────────

classes = [
    GYRO360_OT_Render360,
    GYRO360_OT_StartServer,
    GYRO360_OT_StopServer,
    GYRO360_OT_OpenBrowser,
    GYRO360_OT_InstallQR,
    GYRO360_OT_GenerateQR,
    GYRO360_OT_SaveQR,
    GYRO360_OT_ShowQRPopup,
    GYRO360_OT_CopyURL,
    GYRO360_OT_RefreshUI,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
