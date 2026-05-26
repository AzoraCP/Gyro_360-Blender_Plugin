# Gyro 360 Preview — Blender Add-on

**Render 360° equirectangular images in Blender and preview them instantly on your phone with gyroscope controls.**

No external servers. No localhost setup. No separate web dev team.

---

## Features

| Feature | Details |
|---|---|
| 360° Camera Setup | One-click Cycles equirectangular camera |
| Render Presets | 1K / 2K / 4K / Custom resolution |
| Local Preview Server | Automatic IP detection, no config needed |
| Mobile Viewer | Three.js — gyro + touch, no roll weirdness |
| QR Code | Scan to open preview instantly |
| Auto-Refresh | Mobile updates after each render |
| Version History | Numbered render outputs per session |

---

## Installation

1. **Download** `gyro_360_preview_v1.0.0.zip`
2. Open Blender → **Edit → Preferences → Add-ons**
3. Click **Install…** and select the zip file
4. Enable **"Gyro 360 Preview"** in the add-ons list
5. Find the panel in **View3D → Sidebar (N) → 360 Preview**

> Requires Blender 3.6 or later. Tested with Blender 4.x.

---

## Quick Start Workflow

### 1. Setup Camera
- Click **"Setup 360° Camera"**
- Automatically sets camera to Cycles Panoramic Equirectangular
- Creates a new camera or configures your existing one

### 2. Render
- **Quick Render** — 1024×512 preview (seconds)
- **Final Render** — Use your chosen resolution preset
- Renders auto-save to Blender's temp folder

### 3. Start Mobile Preview
- Click **"▶ Start Mobile Preview"**
- The panel shows your local network URL, e.g. `http://192.168.1.42:8765`

### 4. Install QR Module (first time only)
- If the **red "Install QR Module"** button appears, click it once
- Installs `qrcode[pil]` into Blender's Python automatically
- Button turns green after install

### 5. Generate & Scan QR Code
- Click **"Generate QR Code"**
- Click **"View QR Code"** to see it in Blender's Image Editor
- Scan with your phone — opens the 360 preview instantly

---

## Mobile Viewer Controls

| Control | Action |
|---|---|
| **Drag right** | Pan right |
| **Drag left** | Pan left |
| **Drag up** | Look up |
| **Drag down** | Look down |
| **Tilt phone** | Gyroscope control |
| **Gyro button** | Toggle gyroscope on/off |
| **Reset View** | Return to center |
| **Fullscreen** | Enter/exit fullscreen |

### iOS Gyro Note
On iOS 13+, the viewer will ask permission to use the gyroscope — tap **"Enable Gyroscope"** when prompted.

---

## Technical Details

### Add-on Structure
```
gyro_360_preview/
├── __init__.py       — Registration entry point
├── properties.py     — All custom scene properties
├── operators.py      — Blender operators (camera, render, server, QR)
├── panels.py         — UI panels (View3D sidebar)
└── server.py         — Local HTTP server + Three.js viewer HTML
```

### How the Server Works
- Uses Python's built-in `http.server` — no Flask or extra deps
- Automatically detects your local Wi-Fi IP
- Serves the Three.js viewer at `/`
- Serves the rendered image at `/image`
- Exposes `/api/status` for polling (auto-refresh without page reload)
- Mobile browser polls every 2.5 seconds — updates texture seamlessly

### Three.js Viewer
- Equirectangular sphere with inside-out geometry
- `camera.rotation.order = 'YXZ'` — yaw/pitch only, zero roll
- Gyro uses delta from baseline — re-calibrates on "Reset View"
- Touch drag and gyro are cleanly separated (gyro pauses during touch)

### Render Output
- Saves to `{blender_temp}/gyro360_renders/render_360_vNNN.jpg`
- JPEG quality 92 — good balance of quality and serve speed
- Version counter increments each session

---

## Requirements

| Requirement | Detail |
|---|---|
| Blender | 3.6+ (4.x recommended) |
| Render Engine | Cycles (set automatically) |
| Network | Phone and computer on same Wi-Fi |
| QR module | Auto-installed on demand |
| Phone | Any modern smartphone with browser |

---

## Troubleshooting

**"No camera found"**  
→ Run "Setup 360° Camera" or select your camera and enable "Configure Existing Camera"

**Server won't start**  
→ Try a different port (default 8765) in Settings. Check firewall rules.

**Phone can't reach the server**  
→ Ensure your phone and computer are on the **same Wi-Fi network**  
→ Disable VPN if active

**QR module install fails**  
→ Try: Blender terminal → `import subprocess; subprocess.run(["python", "-m", "pip", "install", "qrcode[pil]"])`

**Gyroscope not working on iOS**  
→ Tap "Enable Gyroscope" when the permission dialog appears  
→ Settings → Safari → Motion & Orientation Access → ON

**Black sphere / no image**  
→ Render an image first, then start the server  
→ Or: start server, render, the mobile view auto-refreshes

---

## Changelog

### v1.0.0
- Initial release
- Full render pipeline: camera setup → render → serve → QR
- Three.js viewer with gyro, touch, auto-refresh
- Auto IP detection, self-contained server
- One-click QR module installation

---

*Gyro 360 Preview — Built for Blender artists.*
